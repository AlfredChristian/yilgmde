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
    Photo optionnelle (JPEG, PNG, WebP), gardée hors du dépôt git (D11), jamais publique.
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
        extension = _extension_photo(contenu)
        if extension is None:
            raise HTTPException(422, "photo invalide (JPEG, PNG ou WebP attendu)")

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
