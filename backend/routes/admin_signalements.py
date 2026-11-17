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
    SignalementDetail,
    StatutDepotoir,
    StatutSignalement,
    ValiderEntree,
)
from backend.securite import exiger_role
from backend.confiance import ajuster_confiance_signalement
from backend.utilisateurs import journaliser
from backend.zones import zone_id_pour_point
from simulation.geometrie import distance_m

router = APIRouter(prefix="/admin", tags=["moderation"])

# Statuts d'un dépotoir pour lesquels un nouveau signalement vérifié est une réapparition.
STATUTS_REAPPARITION = (
    StatutDepotoir.eradique.value,
    StatutDepotoir.sous_surveillance.value,
    StatutDepotoir.classe.value,
)

TYPES_PHOTO = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
TYPES_AUDIO = {".webm": "audio/webm", ".m4a": "audio/mp4", ".ogg": "audio/ogg", ".mp3": "audio/mpeg",
               ".wav": "audio/wav"}

_COLONNES_SIGNALEMENT = (
    "id, latitude, longitude, type_dechet, volume_estime, photo, statut, score_auto,"
    " alertes, motif, depotoir_id, cree_le, note_vocale, masquage, capture_le"
)


def _signalement_sortie(ligne) -> SignalementAdmin:
    return SignalementAdmin(
        id=ligne["id"],
        latitude=ligne["latitude"],
        longitude=ligne["longitude"],
        type_dechet=ligne["type_dechet"],
        volume_estime=ligne["volume_estime"],
        photo_url=f"/admin/signalements/{ligne['id']}/photo" if ligne["photo"] else None,
        note_vocale_url=f"/admin/signalements/{ligne['id']}/note-vocale" if ligne["note_vocale"] else None,
        photo_masquee=db.depuis_json(ligne["masquage"], None),
        capture_le=ligne["capture_le"],
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


RAYON_PROXIMITE_M = 300


@router.get("/signalements/{signalement_id}", response_model=SignalementDetail)
def detail_signalement(signalement_id: int, request: Request, _admin: dict = Depends(exiger_role(Role.admin))):
    """D54 : fiche complète pour décider. Quartier, fiabilité de l'appareil (sans l'identifier),
    dépotoirs connus et autres signalements à moins de 300 m (doublon probable, fusion possible)."""
    with acces_db(request) as conn:
        ligne = _lire_signalement(conn, signalement_id)
        extra = conn.execute("SELECT description, contributeur_id FROM signalement WHERE id = ?", (signalement_id,)).fetchone()
        lat, lon = ligne["latitude"], ligne["longitude"]
        zone_id = zone_id_pour_point(conn, lat, lon)
        zone = conn.execute("SELECT nom, arrondissement FROM zone WHERE id = ?", (zone_id,)).fetchone() if zone_id else None
        contributeur = None
        if extra["contributeur_id"] is not None:
            c = conn.execute("SELECT nb_signalements, score_confiance, bloque FROM contributeur WHERE id = ?",
                             (extra["contributeur_id"],)).fetchone()
            comptes = dict(conn.execute(
                "SELECT statut, COUNT(*) FROM signalement WHERE contributeur_id = ? GROUP BY statut",
                (extra["contributeur_id"],)).fetchall())
            contributeur = {"score_confiance": c["score_confiance"], "nb_signalements": c["nb_signalements"],
                            "verifies": comptes.get("verifie", 0),
                            "rejetes": comptes.get("rejete", 0) + comptes.get("rejete_auto", 0),
                            "bloque": bool(c["bloque"])}
        # Boîte large puis distance exacte (≈ 0,003° ≈ 330 m à cette latitude).
        d = RAYON_PROXIMITE_M / 111_000 * 1.2
        boite = (lat - d, lat + d, lon - d, lon + d)
        depotoirs = [
            {"id": r["id"], "distance_m": round(distance_m(lat, lon, r["latitude"], r["longitude"])),
             "latitude": r["latitude"], "longitude": r["longitude"], "statut": r["statut"], "legalite": r["legalite"],
             "volume_estime": r["volume_estime"], "nb_signalements": r["nb_signalements"]}
            for r in conn.execute("SELECT * FROM depotoir WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?", boite)
        ]
        voisins = [
            {"id": r["id"], "distance_m": round(distance_m(lat, lon, r["latitude"], r["longitude"])),
             "latitude": r["latitude"], "longitude": r["longitude"], "statut": r["statut"],
             "type_dechet": r["type_dechet"], "volume_estime": r["volume_estime"], "cree_le": r["cree_le"]}
            for r in conn.execute(
                "SELECT id, latitude, longitude, statut, type_dechet, volume_estime, cree_le FROM signalement "
                "WHERE id != ? AND latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?", (signalement_id, *boite))
        ]
    sortie = _signalement_sortie(ligne).model_dump()
    return SignalementDetail(
        **sortie,
        description=extra["description"],
        secteur=zone["nom"] if zone else None,
        arrondissement=zone["arrondissement"] if zone else None,
        contributeur=contributeur,
        depotoirs_proches=sorted((x for x in depotoirs if x["distance_m"] <= RAYON_PROXIMITE_M), key=lambda x: x["distance_m"]),
        signalements_proches=sorted((x for x in voisins if x["distance_m"] <= RAYON_PROXIMITE_M), key=lambda x: x["distance_m"])[:10],
    )


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


@router.get("/signalements/{signalement_id}/note-vocale")
def note_vocale_signalement(
    signalement_id: int,
    request: Request,
    _admin: dict = Depends(exiger_role(Role.admin)),
):
    """Note vocale du citoyen, réservée aux admins (jamais publique)."""
    with acces_db(request) as conn:
        ligne = conn.execute("SELECT note_vocale FROM signalement WHERE id = ?", (signalement_id,)).fetchone()
    if ligne is None or not ligne["note_vocale"]:
        raise HTTPException(404, "pas de note vocale pour ce signalement")
    chemin = dossier_uploads() / "audio" / Path(ligne["note_vocale"]).name   # jamais de chemin venu de la base
    if not chemin.is_file():
        raise HTTPException(404, "note vocale introuvable")
    return FileResponse(chemin, media_type=TYPES_AUDIO.get(chemin.suffix.lower(), "application/octet-stream"))


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
