"""A1/A5 — Création et suivi des signalements (citoyen anonyme).

Contrat : `docs/api-contract.md`. Le citoyen s'identifie par l'en-tête
`X-Device-Token` (D04), il n'a pas de compte.
"""

from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, Response, UploadFile

from backend import db
from backend.deps import acces_db
from backend.masquage import MasquageIndisponible, masquer_photo
from backend.schemas import (
    SignalementCree,
    StatutSignalement,
    SuiviSignalement,
    TypeDechet,
    VolumeEstime,
)
from backend.verification import contexte_depuis_db, verifier

router = APIRouter(tags=["signalements"])

# Sans I, O, 0, 1 : un code se dicte ou se recopie sans confusion.
ALPHABET_CODE = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TAILLE_PHOTO_MAX_MO_DEFAUT = 5  # [H] repli si la clé manque dans la config

# Signatures de fichier acceptées -> extension. On ne se fie pas au nom ni au Content-Type.
_SIGNATURES = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
)


def dossier_uploads() -> Path:
    """Dossier des photos, surchargeable par YILGMDE_UPLOADS (ignoré par git)."""
    return Path(os.environ.get("YILGMDE_UPLOADS", "uploads"))


def _extension_photo(contenu: bytes) -> str | None:
    for signature, extension in _SIGNATURES:
        if contenu.startswith(signature):
            return extension
    if contenu[:4] == b"RIFF" and contenu[8:12] == b"WEBP":
        return ".webp"
    return None


def _generer_code(conn: sqlite3.Connection) -> str:
    """Code de suivi au format `K7M-4QD`, unique en base."""
    while True:
        brut = "".join(secrets.choice(ALPHABET_CODE) for _ in range(6))
        code = f"{brut[:3]}-{brut[3:]}"
        if conn.execute("SELECT 1 FROM signalement WHERE code_suivi = ?", (code,)).fetchone() is None:
            return code


def _contributeur(conn: sqlite3.Connection, jeton: str) -> int:
    """Retrouve ou crée le contributeur anonyme associé au jeton d'appareil."""
    conn.execute(
        "INSERT INTO contributeur (jeton_appareil) VALUES (?) ON CONFLICT(jeton_appareil) DO NOTHING",
        (jeton,),
    )
    return conn.execute(
        "SELECT id FROM contributeur WHERE jeton_appareil = ?", (jeton,)
    ).fetchone()["id"]


def _extension_audio(contenu: bytes) -> str | None:
    """Format de la note vocale d'après sa signature (jamais d'après le nom)."""
    if contenu.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm"
    if contenu[4:8] == b"ftyp":
        return ".m4a"
    if contenu.startswith(b"OggS"):
        return ".ogg"
    if contenu.startswith(b"ID3") or contenu[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return ".mp3"
    if contenu[:4] == b"RIFF" and contenu[8:12] == b"WAVE":
        return ".wav"
    return None


def _lire_fichier(fichier: UploadFile, taille_max_mo: float, nom: str) -> bytes:
    taille_max = int(taille_max_mo * 1024 * 1024)
    contenu = fichier.file.read(taille_max + 1)
    if len(contenu) > taille_max:
        raise HTTPException(413, f"{nom} trop volumineuse")
    return contenu


def _deja_recu(conn: sqlite3.Connection, jeton: str, id_client: str) -> SignalementCree | None:
    ligne = conn.execute(
        "SELECT s.id, s.code_suivi, s.statut, s.motif, s.masquage FROM signalement s"
        " JOIN contributeur c ON c.id = s.contributeur_id"
        " WHERE c.jeton_appareil = ? AND s.id_client = ?",
        (jeton, id_client),
    ).fetchone()
    if ligne is None:
        return None
    return SignalementCree(id=ligne["id"], code_suivi=ligne["code_suivi"], statut=ligne["statut"],
                           motif=ligne["motif"], photo_masquee=db.depuis_json(ligne["masquage"], None),
                           deja_recu=True)


@router.post("/signalements", status_code=201, response_model=SignalementCree)
def creer_signalement(
    request: Request,
    response: Response,
    latitude: float = Form(..., ge=-90, le=90),
    longitude: float = Form(..., ge=-180, le=180),
    type_dechet: TypeDechet = Form(...),
    volume_estime: VolumeEstime = Form(...),
    description: str | None = Form(None, max_length=500),
    photo: UploadFile | None = File(None),
    note_vocale: UploadFile | None = File(None),
    id_client: str | None = Form(None, pattern=r"^[A-Za-z0-9_.:-]{8,64}$"),
    capture_le: datetime | None = Form(None),
    x_device_token: str = Header(..., pattern=r"^[A-Za-z0-9_-]{8,64}$"),
):
    """Signalement citoyen, en direct ou différé (file d'attente hors connexion).

    - `id_client` : identifiant choisi par l'application ; un renvoi du même signalement
      par le même appareil renvoie le premier (`200`, `deja_recu: true`), sans doublon.
    - `capture_le` : date de prise de vue ; sert à la limite par appareil.
    - la photo est **toujours** masquée (visages, plaques) et ré-encodée sans EXIF
      avant d'être gardée (D36) ; la note vocale n'est jamais publique.
    """
    config = request.app.state.config
    hors_ligne = config.get("hors_ligne", {})
    maintenant = datetime.now(timezone.utc)

    # Renvoi d'un signalement déjà reçu : on répond pareil, sans rien recréer.
    if id_client:
        with acces_db(request) as conn:
            deja = _deja_recu(conn, x_device_token, id_client)
        if deja is not None:
            response.status_code = 200
            return deja

    alertes_envoi: list[str] = []
    moment = maintenant
    if capture_le is not None:
        if capture_le.tzinfo is None:
            capture_le = capture_le.replace(tzinfo=timezone.utc)
        if capture_le > maintenant + timedelta(minutes=float(hors_ligne.get("tolerance_horloge_min", 5))):
            raise HTTPException(422, "capture_le est dans le futur")
        if capture_le < maintenant - timedelta(days=float(hors_ligne.get("anciennete_max_jours", 30))):
            alertes_envoi.append("capture_ancienne")
        moment = min(capture_le, maintenant)

    contenu: bytes | None = None
    if photo is not None and photo.filename:
        contenu = _lire_fichier(photo, config.get("verification", {}).get(
            "photo_taille_max_mo", TAILLE_PHOTO_MAX_MO_DEFAUT), "photo")
        if _extension_photo(contenu) is None:
            raise HTTPException(422, "photo invalide (JPEG, PNG ou WebP attendu)")
    audio: bytes | None = None
    extension_audio = None
    if note_vocale is not None and note_vocale.filename:
        audio = _lire_fichier(note_vocale, hors_ligne.get("note_vocale_taille_max_mo", 2), "note vocale")
        extension_audio = _extension_audio(audio)
        if extension_audio is None:
            raise HTTPException(422, "note vocale invalide (WebM, MP4/M4A, Ogg, MP3 ou WAV attendu)")

    with acces_db(request) as conn:
        # Plafond d'envois par heure de réception : empêche de contourner la limite en antidatant.
        plafond = int(hors_ligne.get("max_envois_par_heure", 30))
        recus = conn.execute(
            "SELECT COUNT(*) FROM signalement s JOIN contributeur c ON c.id = s.contributeur_id"
            " WHERE c.jeton_appareil = ? AND s.cree_le >= ?",
            (x_device_token, (maintenant - timedelta(hours=1)).isoformat()),
        ).fetchone()[0]
        if recus >= plafond:
            raise HTTPException(429, "trop d'envois depuis cet appareil, réessayez plus tard",
                                headers={"Retry-After": "600"})
        contexte = contexte_depuis_db(
            conn, x_device_token, latitude, longitude, config, avec_photo=contenu is not None, maintenant=moment,
        )
    verdict = verifier(latitude, longitude, config, contexte)
    alertes = list(verdict.alertes) + alertes_envoi
    garder = verdict.statut != StatutSignalement.rejete_auto   # rien n'est gardé d'un rejet d'office

    masque = None
    if contenu is not None and garder:
        try:
            masque = masquer_photo(contenu, config)
        except MasquageIndisponible:
            raise HTTPException(503, "masquage des photos indisponible : réessayez plus tard",
                                headers={"Retry-After": "600"})
        except ValueError:
            raise HTTPException(422, "photo illisible")

    with acces_db(request) as conn:
        try:
            with db.transaction(conn):
                contributeur_id = _contributeur(conn, x_device_token)
                code = _generer_code(conn)
                curseur = conn.execute(
                    "INSERT INTO signalement (contributeur_id, latitude, longitude, description,"
                    " type_dechet, volume_estime, code_suivi, statut, motif, score_auto, alertes, cree_le,"
                    " capture_le, id_client, masquage)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        contributeur_id, latitude, longitude, description or None,
                        type_dechet.value, volume_estime.value, code,
                        verdict.statut.value, verdict.motif, verdict.score_auto, db.en_json(alertes),
                        # Même format que `contexte_depuis_db` pour comparer les dates comme du texte.
                        maintenant.isoformat(),
                        capture_le.isoformat() if capture_le is not None else None,
                        id_client,
                        db.en_json(masque.resume()) if masque else None,
                    ),
                )
                signalement_id = curseur.lastrowid
                conn.execute(
                    "UPDATE contributeur SET nb_signalements = nb_signalements + 1 WHERE id = ?",
                    (contributeur_id,),
                )
                dossier = dossier_uploads()
                if masque is not None:
                    dossier.mkdir(parents=True, exist_ok=True)
                    nom = f"{signalement_id}{masque.extension}"
                    (dossier / nom).write_bytes(masque.contenu)
                    conn.execute("UPDATE signalement SET photo = ? WHERE id = ?", (nom, signalement_id))
                if audio is not None and garder:
                    (dossier / "audio").mkdir(parents=True, exist_ok=True)
                    nom = f"audio/{signalement_id}{extension_audio}"
                    (dossier / nom).write_bytes(audio)
                    conn.execute("UPDATE signalement SET note_vocale = ? WHERE id = ?", (nom, signalement_id))
        except sqlite3.IntegrityError:
            # Deux envois simultanés du même id_client : le premier a gagné.
            deja = _deja_recu(conn, x_device_token, id_client) if id_client else None
            if deja is None:
                raise
            response.status_code = 200
            return deja

    return SignalementCree(
        id=signalement_id, code_suivi=code, statut=verdict.statut, motif=verdict.motif,
        photo_masquee=masque.resume() if masque else None,
    )


@router.get("/signalements/suivi/{code_suivi}", response_model=SuiviSignalement)
def suivre_signalement(code_suivi: str, request: Request):
    with acces_db(request) as conn:
        ligne = conn.execute(
            "SELECT code_suivi, statut, motif, depotoir_id FROM signalement WHERE code_suivi = ?",
            (code_suivi.strip().upper(),),
        ).fetchone()
    if ligne is None:
        raise HTTPException(404, "code de suivi inconnu")
    return SuiviSignalement(**dict(ligne))
