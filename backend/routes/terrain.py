"""Vues de terrain sur le plan courant (scénario actif).

- C6 chauffeur : sa tournée de collecte, arrêts à cocher, incidents. Une `panne`
  rend son camion indisponible dans le scénario actif : le plan est recalculé (D2).
- H1–H3 brigade Laabal : dépotoirs à traiter par priorité, tournée d'intervention,
  intervention (`en_cours` → `intervention_planifiee`, `eradique`) et surveillance.
- Admin : affecter une tournée à un chauffeur ou à une brigade.

Le travail du jour survit aux recalculs : affectations et arrêts effectués sont
repris d'un plan à l'autre (`backend/plans.py`). Tout est tracé dans `journal_audit`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from backend import db, plans
from backend.deps import acces_db
from backend.masquage import MasquageIndisponible, masquer_photo
from backend.routes.signalements import _extension_photo, dossier_uploads
from backend.schemas import Role, StatutDepotoir
from backend.securite import exiger_role
from backend.utilisateurs import journaliser
from simulation.tournees import depotoirs_a_traiter

router = APIRouter(tags=["terrain"])
chauffeur = exiger_role(Role.chauffeur)
laabal = exiger_role(Role.laabal)
admin = exiger_role(Role.admin)

TAILLE_PHOTO_MAX_MO_DEFAUT = 5


class TypeIncident(str, Enum):
    panne = "panne"
    route_impraticable = "route_impraticable"


class IncidentEntree(BaseModel):
    type: TypeIncident
    description: str | None = Field(default=None, max_length=500)
    camion_id: str | None = None      # par défaut : le camion de la tournée affectée au chauffeur


class AffecterEntree(BaseModel):
    utilisateur_id: int


class StatutIntervention(str, Enum):
    en_cours = "en_cours"
    eradique = "eradique"


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat()


def _plan_courant(request: Request) -> dict:
    with acces_db(request) as conn:
        actif = plans.scenario_actif(conn)
    if actif is None:
        raise HTTPException(404, "aucun scénario actif")
    return plans.calculer_et_enregistrer(lambda: acces_db(request), request.app.state.config, actif["id"])


def _mes_tournees(plan: dict, type_: str, utilisateur_id: int) -> list[dict]:
    return [t for t in plan["tournees"] if t["type"] == type_ and t.get("affectee_a") == utilisateur_id]


def _arret_du_plan(plan: dict, arret_id: int) -> tuple[dict, dict] | None:
    for t in plan["tournees"]:
        for a in t["arrets"]:
            if a["id"] == arret_id:
                return t, a
    return None


# --- Admin : affectation ------------------------------------------------------------

@router.post("/admin/tournees/{tournee_id}/affecter")
def affecter(request: Request, tournee_id: int, entree: AffecterEntree, utilisateur=Depends(admin)):
    """Collecte → un chauffeur ; intervention → un compte Laabal. Seulement dans le plan courant."""
    plan = _plan_courant(request)
    tournee = next((t for t in plan["tournees"] if t["id"] == tournee_id), None)
    if tournee is None:
        raise HTTPException(404, "tournée inconnue dans le plan courant")
    role_attendu = Role.chauffeur.value if tournee["type"] == "collecte" else Role.laabal.value
    with acces_db(request) as conn:
        cible = conn.execute("SELECT id, role, actif FROM utilisateur WHERE id = ?", (entree.utilisateur_id,)).fetchone()
        if cible is None or not cible["actif"]:
            raise HTTPException(404, "utilisateur inconnu ou désactivé")
        if cible["role"] != role_attendu:
            raise HTTPException(422, f"une tournée de type {tournee['type']} s'affecte à un compte {role_attendu}")
        with db.transaction(conn):
            conn.execute("UPDATE tournee SET affectee_a = ? WHERE id = ?", (entree.utilisateur_id, tournee_id))
            journaliser(conn, utilisateur["id"], "affecter_tournee", "tournee", tournee_id)
    return dict(tournee, affectee_a=entree.utilisateur_id)


# --- Suivi de la flotte (admin) -------------------------------------------------------

@router.get("/admin/suivi")
def suivi_flotte(request: Request, _=Depends(admin)):
    """Avancement réel du plan courant, pour la vue « Suivi de la flotte » (D51).

    Chaque tournée avec ses arrêts (position, statut, heure où le chauffeur ou la brigade
    l'a coché, lue dans le journal d'audit) et l'agent affecté. Le dépôt sert au tracé
    départ / retour. Pas de GPS : la position d'un camion entre deux arrêts cochés n'est
    pas connue, le front la montre comme un horaire prévu, distinct de l'avancement réel.
    """
    plan = _plan_courant(request)
    ids = [a["id"] for t in plan["tournees"] for a in t["arrets"]]
    with acces_db(request) as conn:
        noms = {l["id"]: l["nom"] for l in conn.execute("SELECT id, nom FROM utilisateur")}
        coches = {}
        for debut in range(0, len(ids), 500):          # limite de paramètres SQLite
            lot = ids[debut:debut + 500]
            for l in conn.execute(
                f"SELECT objet_id, MAX(date) AS quand FROM journal_audit WHERE action = 'arret_effectue' "
                f"AND objet_type = 'arret_tournee' AND objet_id IN ({','.join('?' * len(lot))}) GROUP BY objet_id",
                lot,
            ):
                coches[l["objet_id"]] = l["quand"]
    tournees = []
    for t in plan["tournees"]:
        arrets = [
            {"id": a["id"], "ordre": a["ordre"], "latitude": a.get("latitude"), "longitude": a.get("longitude"),
             "cible_type": a["cible_type"], "cible_id": a["cible_id"], "statut": a["statut"],
             "effectue_le": coches.get(a["id"])}
            for a in t["arrets"]
        ]
        faits = sum(1 for a in arrets if a["statut"] == "effectue")
        tournees.append({
            "id": t["id"], "type": t["type"], "camion_id": t.get("camion_id"), "brigade": t.get("brigade"),
            "jour": t.get("jour", 1), "rotation": t.get("rotation", 1),
            "distance_km": t["distance_km"], "duree_min": t["duree_min"],
            "affectee_a": t.get("affectee_a"), "affectee_nom": noms.get(t.get("affectee_a")),
            "arrets_effectues": faits, "arrets_total": len(arrets),
            "derniere_activite": max((a["effectue_le"] for a in arrets if a["effectue_le"]), default=None),
            "trace": t.get("trace"),          # D52 : un tronçon par trajet, sur les voies (absent sans réseau routier)
            "arrets": arrets,
        })
    depot = request.app.state.config["collecte"].get("depot") or {}
    total = sum(t["arrets_total"] for t in tournees)
    faits = sum(t["arrets_effectues"] for t in tournees)
    return {
        "plan_id": plan["id"],
        "depot": {"latitude": depot.get("latitude"), "longitude": depot.get("longitude")},
        "jours": sorted({t["jour"] for t in tournees if t["type"] == "collecte"}) or [1],
        "resume": {
            "arrets_total": total, "arrets_effectues": faits,
            "tournees_affectees": sum(1 for t in tournees if t["affectee_a"]),
            "tournees_terminees": sum(1 for t in tournees if t["arrets_total"] and t["arrets_effectues"] == t["arrets_total"]),
        },
        "tournees": tournees,
    }


# --- C6 : chauffeur ------------------------------------------------------------------

@router.get("/chauffeur/tournee")
def tournee_chauffeur(request: Request, utilisateur=Depends(chauffeur)):
    """Tournées de collecte (rotations) affectées au chauffeur dans le plan courant."""
    plan = _plan_courant(request)
    return {"plan_id": plan["id"], "tournees": _mes_tournees(plan, "collecte", utilisateur["id"])}


def _cocher(request: Request, arret_id: int, utilisateur: dict, type_: str) -> dict:
    plan = _plan_courant(request)
    trouve = _arret_du_plan(plan, arret_id)
    if trouve is None:
        raise HTTPException(404, "arrêt inconnu dans le plan courant")
    tournee, arret = trouve
    if tournee["type"] != type_ or tournee.get("affectee_a") != utilisateur["id"]:
        raise HTTPException(403, "cet arrêt n'est pas dans une de vos tournées")
    with acces_db(request) as conn:
        with db.transaction(conn):
            conn.execute("UPDATE arret_tournee SET statut = 'effectue' WHERE id = ?", (arret_id,))
            journaliser(conn, utilisateur["id"], "arret_effectue", "arret_tournee", arret_id)
    return dict(arret, statut="effectue")


@router.post("/chauffeur/arrets/{arret_id}/effectue")
def arret_effectue(request: Request, arret_id: int, utilisateur=Depends(chauffeur)):
    return _cocher(request, arret_id, utilisateur, "collecte")


@router.post("/chauffeur/incidents")
def incident(request: Request, entree: IncidentEntree, utilisateur=Depends(chauffeur)):
    """`panne` : le camion devient indisponible dans le scénario actif et le plan est recalculé.
    `route_impraticable` : tracé dans le journal pour l'admin (pas de carte routière dans le MVP)."""
    with acces_db(request) as conn:
        actif = plans.scenario_actif(conn)
    if actif is None:
        raise HTTPException(404, "aucun scénario actif")

    if entree.type is TypeIncident.route_impraticable:
        with acces_db(request) as conn:
            with db.transaction(conn):
                journaliser(conn, utilisateur["id"], "incident_route_impraticable", "scenario", actif["id"])
        return {"type": entree.type.value, "enregistre": True, "plan": None}

    camion_id = entree.camion_id
    if camion_id is None:
        mes = _mes_tournees(_plan_courant(request), "collecte", utilisateur["id"])
        if not mes:
            raise HTTPException(422, "camion_id requis : aucune tournée ne vous est affectée")
        camion_id = mes[0]["camion_id"]
    if camion_id not in {c["id"] for c in plans.config_effective(request.app.state.config, actif).get("camions", [])}:
        raise HTTPException(404, "camion inconnu")

    parametres = plans.fusionner_parametres(actif["parametres"], {"camions": [{"id": camion_id, "disponible": False}]})
    with acces_db(request) as conn:
        with db.transaction(conn):
            conn.execute("UPDATE scenario SET parametres = ? WHERE id = ?", (db.en_json(parametres), actif["id"]))
            journaliser(conn, utilisateur["id"], "incident_panne", "scenario", actif["id"])
    plan = _plan_courant(request)
    return {"type": entree.type.value, "camion_id": camion_id, "enregistre": True, "plan": plan}


# --- H1–H3 : brigade Laabal ------------------------------------------------------------

def _lire_depotoir(conn, depotoir_id: int):
    ligne = conn.execute("SELECT * FROM depotoir WHERE id = ?", (depotoir_id,)).fetchone()
    if ligne is None:
        raise HTTPException(404, "dépotoir inconnu")
    return ligne


@router.get("/laabal/depotoirs-a-traiter")
def a_traiter(request: Request, _=Depends(laabal)):
    """Dépotoirs illégaux actifs ou en intervention, du plus prioritaire au moins prioritaire."""
    with acces_db(request) as conn:
        donnees = plans.lire_donnees(conn)
    return [
        {k: d[k] for k in ("id", "latitude", "longitude", "zone_id", "statut", "volume_estime",
                           "nb_signalements", "nb_reapparitions", "priorite", "raison")}
        for d in depotoirs_a_traiter(donnees["depotoirs"], request.app.state.config)
    ]


@router.get("/laabal/tournee")
def tournee_laabal(request: Request, utilisateur=Depends(laabal)):
    """Tournées d'intervention affectées à ce compte dans le plan courant."""
    plan = _plan_courant(request)
    return {"plan_id": plan["id"], "tournees": _mes_tournees(plan, "intervention", utilisateur["id"]),
            "en_attente": plan.get("laabal_en_attente", [])}


@router.post("/laabal/arrets/{arret_id}/effectue")
def arret_laabal_effectue(request: Request, arret_id: int, utilisateur=Depends(laabal)):
    return _cocher(request, arret_id, utilisateur, "intervention")


@router.post("/laabal/depotoirs/{depotoir_id}/intervention")
def intervention(
    request: Request,
    depotoir_id: int,
    statut: StatutIntervention = Form(...),
    photo: UploadFile | None = File(None),
    utilisateur=Depends(laabal),
):
    """B5 : `en_cours` → dépotoir `intervention_planifiee` ; `eradique` → dépotoir `eradique`.

    Seuls les dépotoirs illégaux `actif` ou `intervention_planifiee` se traitent (409 sinon).
    Photo optionnelle (JPEG, PNG, WebP), masquée (visages, plaques) puis gardée hors du
    dépôt git (D11, D36), jamais publique.
    """
    contenu, extension = None, None
    if photo is not None and photo.filename:
        taille_max = int(
            float(request.app.state.config.get("verification", {}).get("photo_taille_max_mo", TAILLE_PHOTO_MAX_MO_DEFAUT))
            * 1024 * 1024
        )
        contenu = photo.file.read(taille_max + 1)
        if len(contenu) > taille_max:
            raise HTTPException(413, "photo trop volumineuse")
        if _extension_photo(contenu) is None:
            raise HTTPException(422, "photo invalide (JPEG, PNG ou WebP attendu)")
        # Photo d'intervention : visages et plaques masqués comme pour les citoyens (D36).
        try:
            masque = masquer_photo(contenu, request.app.state.config)
        except MasquageIndisponible:
            raise HTTPException(503, "masquage des photos indisponible : réessayez plus tard")
        except ValueError:
            raise HTTPException(422, "photo illisible")
        contenu, extension = masque.contenu, masque.extension

    with acces_db(request) as conn:
        depotoir = _lire_depotoir(conn, depotoir_id)
        if depotoir["legalite"] != "illegal":
            raise HTTPException(409, "un site officiel ne s'éradique pas")
        if depotoir["statut"] not in (StatutDepotoir.actif.value, "intervention_planifiee"):
            raise HTTPException(409, f"dépotoir déjà {depotoir['statut']}")
        nouveau = "intervention_planifiee" if statut is StatutIntervention.en_cours else StatutDepotoir.eradique.value
        maintenant = _maintenant()
        with db.transaction(conn):
            curseur = conn.execute(
                "INSERT INTO intervention (depotoir_id, laabal_id, statut, date) VALUES (?, ?, ?, ?)",
                (depotoir_id, utilisateur["id"], statut.value, maintenant),
            )
            intervention_id = curseur.lastrowid
            if contenu is not None:
                dossier = dossier_uploads() / "interventions"
                dossier.mkdir(parents=True, exist_ok=True)
                nom = f"interventions/{intervention_id}{extension}"
                (dossier_uploads() / nom).write_bytes(contenu)
                conn.execute("UPDATE intervention SET photo = ? WHERE id = ?", (nom, intervention_id))
            conn.execute("UPDATE depotoir SET statut = ?, derniere_maj = ? WHERE id = ?", (nouveau, maintenant, depotoir_id))
            journaliser(conn, utilisateur["id"], f"intervention_{statut.value}", "depotoir", depotoir_id)
        return {"intervention_id": intervention_id, "depotoir_id": depotoir_id, "statut_depotoir": nouveau,
                "photo": contenu is not None}


@router.post("/laabal/depotoirs/{depotoir_id}/surveillance")
def surveillance(request: Request, depotoir_id: int, utilisateur=Depends(laabal)):
    """B5 : un dépotoir `eradique` passe `sous_surveillance` (409 sinon)."""
    with acces_db(request) as conn:
        depotoir = _lire_depotoir(conn, depotoir_id)
        if depotoir["statut"] != StatutDepotoir.eradique.value:
            raise HTTPException(409, "seul un dépotoir éradiqué peut être mis sous surveillance")
        with db.transaction(conn):
            conn.execute("UPDATE depotoir SET statut = 'sous_surveillance', derniere_maj = ? WHERE id = ?",
                         (_maintenant(), depotoir_id))
            journaliser(conn, utilisateur["id"], "surveillance", "depotoir", depotoir_id)
        return {"depotoir_id": depotoir_id, "statut_depotoir": "sous_surveillance"}


# --- Constats et amendes (P2) ------------------------------------------------------------

MAX_PREUVES = 5


def _constat_sortie(ligne) -> dict:
    d = dict(ligne)
    d["preuves"] = len(db.depuis_json(d["preuves"], []))   # nombre seulement : les fichiers ne sont jamais publics
    return d


@router.post("/laabal/constats", status_code=201)
def creer_constat(
    request: Request,
    depotoir_id: int = Form(...),
    description: str | None = Form(None, max_length=500),
    montant_xof: float | None = Form(None, ge=0),
    preuves: list[UploadFile] | None = File(None),
    utilisateur=Depends(laabal),
):
    """Constat d'un dépôt illégal pris sur le fait, avec amende et preuves photo (0 à 5).

    `montant_xof` par défaut : `laabal.montant_amende_xof`. Un site officiel ne donne pas
    lieu à constat (409). Les preuves suivent les mêmes règles que les photos (D11) mais
    ne sont **pas** masquées : elles servent à identifier l'auteur de l'infraction (D36).
    """
    config = request.app.state.config
    fichiers = [p for p in (preuves or []) if p is not None and p.filename]
    if len(fichiers) > MAX_PREUVES:
        raise HTTPException(422, f"{MAX_PREUVES} preuves au plus")
    taille_max = int(float(config.get("verification", {}).get("photo_taille_max_mo", TAILLE_PHOTO_MAX_MO_DEFAUT))
                     * 1024 * 1024)
    contenus = []
    for p in fichiers:
        contenu = p.file.read(taille_max + 1)
        if len(contenu) > taille_max:
            raise HTTPException(413, "preuve trop volumineuse")
        extension = _extension_photo(contenu)
        if extension is None:
            raise HTTPException(422, "preuve invalide (JPEG, PNG ou WebP attendu)")
        contenus.append((contenu, extension))
    montant = float(config["laabal"].get("montant_amende_xof", 0)) if montant_xof is None else montant_xof

    with acces_db(request) as conn:
        depotoir = _lire_depotoir(conn, depotoir_id)
        if depotoir["legalite"] != "illegal":
            raise HTTPException(409, "pas de constat sur un site officiel")
        with db.transaction(conn):
            curseur = conn.execute(
                "INSERT INTO constat (depotoir_id, laabal_id, date, description, montant_xof) VALUES (?, ?, ?, ?, ?)",
                (depotoir_id, utilisateur["id"], _maintenant(), description or None, montant),
            )
            constat_id = curseur.lastrowid
            noms = []
            if contenus:
                dossier = dossier_uploads() / "constats"
                dossier.mkdir(parents=True, exist_ok=True)
                for n, (contenu, extension) in enumerate(contenus, start=1):
                    nom = f"constats/{constat_id}_{n}{extension}"
                    (dossier_uploads() / nom).write_bytes(contenu)
                    noms.append(nom)
                conn.execute("UPDATE constat SET preuves = ? WHERE id = ?", (db.en_json(noms), constat_id))
            journaliser(conn, utilisateur["id"], "creer_constat", "constat", constat_id)
        return _constat_sortie(conn.execute("SELECT * FROM constat WHERE id = ?", (constat_id,)).fetchone())


@router.get("/laabal/constats")
def mes_constats(request: Request, utilisateur=Depends(laabal)):
    with acces_db(request) as conn:
        return [_constat_sortie(l) for l in conn.execute(
            "SELECT * FROM constat WHERE laabal_id = ? ORDER BY id DESC", (utilisateur["id"],))]


@router.get("/admin/constats")
def tous_les_constats(request: Request, _=Depends(admin)):
    """Tous les constats, avec le total des amendes."""
    with acces_db(request) as conn:
        constats = [_constat_sortie(l) for l in conn.execute("SELECT * FROM constat ORDER BY id DESC")]
    return {"nombre": len(constats), "montant_total_xof": sum(c["montant_xof"] or 0 for c in constats),
            "constats": constats}
