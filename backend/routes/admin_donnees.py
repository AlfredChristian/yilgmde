"""Gestion des données par l'admin (P2) : sites officiels, cycle de vie, import par lot.

- B6 : `POST /admin/depotoirs` saisit un **site officiel** (ou un dépotoir connu) ;
  `PATCH /admin/depotoirs/{id}` change la légalité ou **classe** un dépotoir.
- B5 : `classe` (affaire réglée, plus suivi) seulement depuis `sous_surveillance` ;
  un signalement vérifié ensuite le fait quand même réapparaître (A3).
- A4 : `POST /admin/signalements/import` charge un lot de signalements (GeoJSON) qui
  passe par **la même vérification automatique** que les citoyens (A2) — rejet
  d'office ou mise en revue avec alertes, jamais de validation seule —, sans la
  limite par appareil ; les doublons à l'intérieur du lot sont détectés aussi.

Tout est tracé dans `journal_audit` (règle 5).
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from backend import db
from backend.deps import acces_db
from backend.routes.signalements import _generer_code
from backend.schemas import Legalite, Role, StatutDepotoir, TypeDechet, VolumeEstime
from backend.securite import exiger_role
from backend.utilisateurs import journaliser
from backend.verification import contexte_depuis_db, verifier
from backend.zones import zone_id_pour_point

router = APIRouter(prefix="/admin", tags=["admin-donnees"])
admin = exiger_role(Role.admin)

MAX_PAR_LOT_DEFAUT = 1000


class DepotoirCreation(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    volume_estime: VolumeEstime = VolumeEstime.moyen
    legalite: Legalite = Legalite.officiel


class DepotoirModification(BaseModel):
    legalite: Legalite | None = None
    statut: StatutDepotoir | None = None    # seule valeur acceptée : classe


class ProprietesImport(BaseModel):
    type_dechet: TypeDechet
    volume_estime: VolumeEstime
    description: str | None = Field(default=None, max_length=500)


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat()


def _depotoir(conn, depotoir_id: int) -> dict:
    ligne = conn.execute("SELECT * FROM depotoir WHERE id = ?", (depotoir_id,)).fetchone()
    if ligne is None:
        raise HTTPException(404, "dépotoir inconnu")
    return dict(ligne)


@router.post("/depotoirs", status_code=201)
def creer_depotoir(request: Request, entree: DepotoirCreation, utilisateur=Depends(admin)):
    """Saisie directe par la mairie : par défaut un site **officiel** (point de dépôt autorisé)."""
    maintenant = _maintenant()
    with acces_db(request) as conn:
        with db.transaction(conn):
            zone_id = zone_id_pour_point(conn, entree.latitude, entree.longitude)
            curseur = conn.execute(
                "INSERT INTO depotoir (latitude, longitude, zone_id, volume_estime, statut, legalite,"
                " nb_signalements, premiere_detection, derniere_maj) VALUES (?, ?, ?, ?, 'actif', ?, 0, ?, ?)",
                (entree.latitude, entree.longitude, zone_id, entree.volume_estime.value, entree.legalite.value,
                 maintenant, maintenant),
            )
            depotoir_id = curseur.lastrowid
            journaliser(conn, utilisateur["id"], "creer_depotoir", "depotoir", depotoir_id)
        return _depotoir(conn, depotoir_id)


@router.patch("/depotoirs/{depotoir_id}")
def modifier_depotoir(request: Request, depotoir_id: int, entree: DepotoirModification, utilisateur=Depends(admin)):
    """Légalité (`illegal` ↔ `officiel`) et classement (`sous_surveillance` → `classe`)."""
    if entree.legalite is None and entree.statut is None:
        raise HTTPException(422, "rien à modifier : legalite ou statut attendu")
    if entree.statut is not None and entree.statut is not StatutDepotoir.classe:
        raise HTTPException(422, "seul le statut `classe` se pose ici ; les autres suivent les interventions Laabal")
    with acces_db(request) as conn:
        d = _depotoir(conn, depotoir_id)
        if entree.statut is StatutDepotoir.classe and d["statut"] != StatutDepotoir.sous_surveillance.value:
            raise HTTPException(409, "seul un dépotoir sous surveillance peut être classé")
        changements, actions = {}, []
        if entree.legalite is not None and entree.legalite.value != d["legalite"]:
            changements["legalite"] = entree.legalite.value
            actions.append(f"legalite_{entree.legalite.value}")
        if entree.statut is StatutDepotoir.classe:
            changements["statut"] = "classe"
            actions.append("classer_depotoir")
        if changements:
            with db.transaction(conn):
                affectations = ", ".join(f"{k} = ?" for k in changements)
                conn.execute(f"UPDATE depotoir SET {affectations}, derniere_maj = ? WHERE id = ?",
                             (*changements.values(), _maintenant(), depotoir_id))
                for action in actions:
                    journaliser(conn, utilisateur["id"], action, "depotoir", depotoir_id)
        return _depotoir(conn, depotoir_id)


@router.post("/signalements/import")
def importer_signalements(request: Request, lot: dict = Body(...), utilisateur=Depends(admin)):
    """A4 : FeatureCollection de `Point` avec `type_dechet`, `volume_estime`, `description`.

    Chaque signalement valide passe par la vérification automatique (A2) et finit
    `en_attente_revue` (avec ses alertes) ou `rejete_auto` ; les entrées invalides sont listées
    dans `erreurs` (index dans le lot) sans bloquer les autres. Un seul enregistrement
    au journal pour le lot.
    """
    config = request.app.state.config
    max_par_lot = int(config.get("import", {}).get("max_par_lot", MAX_PAR_LOT_DEFAUT))
    if lot.get("type") != "FeatureCollection" or not isinstance(lot.get("features"), list):
        raise HTTPException(422, "GeoJSON FeatureCollection attendu")
    if len(lot["features"]) > max_par_lot:
        raise HTTPException(413, f"lot trop gros : {max_par_lot} signalements au plus")

    resultats, erreurs = [], []
    par_statut: dict[str, int] = {}
    with acces_db(request) as conn:
        with db.transaction(conn):
            for i, f in enumerate(lot["features"]):
                geometrie = (f or {}).get("geometry") or {}
                coords = geometrie.get("coordinates")
                if geometrie.get("type") != "Point" or not isinstance(coords, list) or len(coords) < 2:
                    erreurs.append({"index": i, "raison": "géométrie Point attendue"})
                    continue
                try:
                    lon, lat = float(coords[0]), float(coords[1])
                except (TypeError, ValueError):
                    erreurs.append({"index": i, "raison": "coordonnées non numériques"})
                    continue
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    erreurs.append({"index": i, "raison": "coordonnées hors bornes"})
                    continue
                try:
                    props = ProprietesImport(**((f or {}).get("properties") or {}))
                except ValidationError as e:
                    champs = sorted({str(x["loc"][0]) for x in e.errors() if x.get("loc")})
                    erreurs.append({"index": i, "raison": f"propriétés invalides : {', '.join(champs)}"})
                    continue

                maintenant = datetime.now(timezone.utc)
                contexte = contexte_depuis_db(conn, None, lat, lon, config, avec_photo=False, maintenant=maintenant)
                # Lot de l'admin : pas de limite par appareil ni de score d'appareil.
                contexte = dataclasses.replace(contexte, nb_signalements_derniere_heure=0, appareil_bloque=False,
                                               score_confiance_appareil=1.0)
                verdict = verifier(lat, lon, config, contexte)
                code = _generer_code(conn)
                curseur = conn.execute(
                    "INSERT INTO signalement (contributeur_id, latitude, longitude, description, type_dechet,"
                    " volume_estime, code_suivi, statut, motif, score_auto, alertes, cree_le)"
                    " VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (lat, lon, props.description or None, props.type_dechet.value, props.volume_estime.value, code,
                     verdict.statut.value, verdict.motif, verdict.score_auto, db.en_json(verdict.alertes),
                     maintenant.isoformat()),
                )
                par_statut[verdict.statut.value] = par_statut.get(verdict.statut.value, 0) + 1
                resultats.append({"index": i, "id": curseur.lastrowid, "code_suivi": code,
                                  "statut": verdict.statut.value, "motif": verdict.motif,
                                  "alertes": verdict.alertes})
            if resultats:
                journaliser(conn, utilisateur["id"], "importer_signalements", "signalement", None)
    return {"importes": len(resultats), "par_statut": par_statut, "erreurs": erreurs, "signalements": resultats}
