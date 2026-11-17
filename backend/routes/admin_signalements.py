"""A3 — Modération des signalements par l'administrateur.

- liste de la file de revue (avec alertes et score de la vérification A2) ;
- valider : crée un dépotoir, ou fusionne dans un dépotoir existant (règle 2 :
  on fusionne, on ne duplique pas) ;
- rejeter, avec un motif obligatoire ;
- servir les photos, réservé aux admins (rien de non vérifié n'est public).

Cycle de vie (B5) : fusionner dans un dépotoir `eradique`, `sous_surveillance` ou
`classe` signale une **réapparition** : il repasse `actif` et `nb_reapparitions` augmente.
Toute action est écrite dans `journal_audit` (règle 5).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from backend import db
from backend.deps import acces_db
from backend.routes.signalements import dossier_uploads
from backend.schemas import (
    DepotoirSortie,
    RejeterEntree,
    ResultatValidation,
    Role,
    SignalementAdmin,
    StatutDepotoir,
    StatutSignalement,
    ValiderEntree,
)
from backend.securite import exiger_role
from backend.confiance import ajuster_confiance_signalement
from backend.utilisateurs import journaliser
from backend.zones import zone_id_pour_point

router = APIRouter(prefix="/admin", tags=["moderation"])

# Statuts d'un dépotoir pour lesquels un nouveau signalement vérifié est une réapparition.
STATUTS_REAPPARITION = (
    StatutDepotoir.eradique.value,
    StatutDepotoir.sous_surveillance.value,
    StatutDepotoir.classe.value,
)

TYPES_PHOTO = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

_COLONNES_SIGNALEMENT = (
    "id, latitude, longitude, type_dechet, volume_estime, photo, statut, score_auto,"
    " alertes, motif, depotoir_id, cree_le"
)


def _signalement_sortie(ligne) -> SignalementAdmin:
    return SignalementAdmin(
        id=ligne["id"],
        latitude=ligne["latitude"],
        longitude=ligne["longitude"],
        type_dechet=ligne["type_dechet"],
        volume_estime=ligne["volume_estime"],
        photo_url=f"/admin/signalements/{ligne['id']}/photo" if ligne["photo"] else None,
        statut=ligne["statut"],
        score_auto=ligne["score_auto"],
        alertes=db.depuis_json(ligne["alertes"], []),
        motif=ligne["motif"],
        depotoir_id=ligne["depotoir_id"],
        cree_le=ligne["cree_le"],
    )


def _depotoir_sortie(ligne) -> DepotoirSortie:
    return DepotoirSortie(**{cle: ligne[cle] for cle in ligne.keys() if cle != "id"}, id=ligne["id"])


def _lire_signalement(conn, signalement_id: int):
    ligne = conn.execute(
        f"SELECT {_COLONNES_SIGNALEMENT} FROM signalement WHERE id = ?", (signalement_id,)
    ).fetchone()
    if ligne is None:
        raise HTTPException(404, "signalement introuvable")
    return ligne


def _exiger_en_attente(ligne) -> None:
    if ligne["statut"] != StatutSignalement.en_attente_revue.value:
        raise HTTPException(409, f"signalement déjà traité (statut : {ligne['statut']})")


@router.get("/signalements", response_model=list[SignalementAdmin])
def lister_signalements(
    request: Request,
    statut: StatutSignalement | None = None,
    _admin: dict = Depends(exiger_role(Role.admin)),
):
    """File de modération : les plus anciens d'abord."""
    requete = f"SELECT {_COLONNES_SIGNALEMENT} FROM signalement"
    valeurs: list = []
    if statut is not None:
        requete += " WHERE statut = ?"
        valeurs.append(statut.value)
    requete += " ORDER BY cree_le, id"
    with acces_db(request) as conn:
        lignes = conn.execute(requete, valeurs).fetchall()
    return [_signalement_sortie(l) for l in lignes]


@router.get("/signalements/{signalement_id}/photo")
def photo_signalement(
    signalement_id: int,
    request: Request,
    _admin: dict = Depends(exiger_role(Role.admin)),
):
    with acces_db(request) as conn:
        ligne = conn.execute(
            "SELECT photo FROM signalement WHERE id = ?", (signalement_id,)
        ).fetchone()
    if ligne is None or not ligne["photo"]:
        raise HTTPException(404, "pas de photo pour ce signalement")
    nom = Path(ligne["photo"]).name            # jamais de chemin venu de la base tel quel
    chemin = dossier_uploads() / nom
    if not chemin.is_file():
        raise HTTPException(404, "photo introuvable")
    return FileResponse(chemin, media_type=TYPES_PHOTO.get(chemin.suffix.lower(), "application/octet-stream"))


@router.post("/signalements/{signalement_id}/valider", response_model=ResultatValidation)
def valider_signalement(
    signalement_id: int,
    request: Request,
    donnees: ValiderEntree | None = Body(default=None),
    admin: dict = Depends(exiger_role(Role.admin)),
):
    fusionner_avec = donnees.fusionner_avec if donnees else None
    maintenant = datetime.now(timezone.utc).isoformat()

    with acces_db(request) as conn:
        sig = _lire_signalement(conn, signalement_id)
        _exiger_en_attente(sig)

        with db.transaction(conn):
            if fusionner_avec is None:
                # Zone du dépotoir : None si le point n'est dans aucune zone connue.
                zone_id = zone_id_pour_point(conn, sig["latitude"], sig["longitude"])
                curseur = conn.execute(
                    "INSERT INTO depotoir (latitude, longitude, zone_id, volume_estime, statut, legalite,"
                    " nb_signalements, nb_reapparitions, premiere_detection, derniere_maj)"
                    " VALUES (?, ?, ?, ?, 'actif', 'illegal', 1, 0, ?, ?)",
                    (sig["latitude"], sig["longitude"], zone_id, sig["volume_estime"], maintenant, maintenant),
                )
                depotoir_id = curseur.lastrowid
            else:
                depotoir = conn.execute(
                    "SELECT id, statut FROM depotoir WHERE id = ?", (fusionner_avec,)
                ).fetchone()
                if depotoir is None:
                    raise HTTPException(404, "dépotoir à fusionner introuvable")
                depotoir_id = depotoir["id"]
                reapparition = depotoir["statut"] in STATUTS_REAPPARITION
                conn.execute(
                    "UPDATE depotoir SET nb_signalements = nb_signalements + 1, derniere_maj = ?,"
                    " statut = CASE WHEN ? THEN 'actif' ELSE statut END,"
                    " nb_reapparitions = nb_reapparitions + CASE WHEN ? THEN 1 ELSE 0 END"
                    " WHERE id = ?",
                    (maintenant, reapparition, reapparition, depotoir_id),
                )

            conn.execute(
                "UPDATE signalement SET statut = 'verifie', depotoir_id = ?, valide_par = ?, valide_le = ?"
                " WHERE id = ?",
                (depotoir_id, admin["id"], maintenant, signalement_id),
            )
            journaliser(conn, admin["id"], "valider_signalement", "signalement", signalement_id)
            ajuster_confiance_signalement(conn, signalement_id, "valide", request.app.state.config)

        sig = _lire_signalement(conn, signalement_id)
        depotoir = conn.execute("SELECT * FROM depotoir WHERE id = ?", (depotoir_id,)).fetchone()
        return ResultatValidation(signalement=_signalement_sortie(sig), depotoir=_depotoir_sortie(depotoir))


@router.post("/signalements/{signalement_id}/rejeter", response_model=SignalementAdmin)
def rejeter_signalement(
    signalement_id: int,
    donnees: RejeterEntree,
    request: Request,
    admin: dict = Depends(exiger_role(Role.admin)),
):
    maintenant = datetime.now(timezone.utc).isoformat()
    with acces_db(request) as conn:
        sig = _lire_signalement(conn, signalement_id)
        _exiger_en_attente(sig)
        with db.transaction(conn):
            conn.execute(
                "UPDATE signalement SET statut = 'rejete', motif = ?, valide_par = ?, valide_le = ?"
                " WHERE id = ?",
                (donnees.motif, admin["id"], maintenant, signalement_id),
            )
            journaliser(conn, admin["id"], "rejeter_signalement", "signalement", signalement_id)
            ajuster_confiance_signalement(conn, signalement_id, "rejete", request.app.state.config)
        return _signalement_sortie(_lire_signalement(conn, signalement_id))
