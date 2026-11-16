"""A1/A5 — Création et suivi des signalements (citoyen anonyme).

Contrat : `docs/api-contract.md`. Le citoyen s'identifie par l'en-tête
`X-Device-Token` (D04), il n'a pas de compte.
"""

from __future__ import annotations

import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile

from backend import db
from backend.deps import acces_db
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


@router.post("/signalements", status_code=201, response_model=SignalementCree)
def creer_signalement(
    request: Request,
    latitude: float = Form(..., ge=-90, le=90),
    longitude: float = Form(..., ge=-180, le=180),
    type_dechet: TypeDechet = Form(...),
    volume_estime: VolumeEstime = Form(...),
    description: str | None = Form(None, max_length=500),
    photo: UploadFile | None = File(None),
    x_device_token: str = Header(..., pattern=r"^[A-Za-z0-9_-]{8,64}$"),
):
    config = request.app.state.config

    contenu: bytes | None = None
    extension = ""
    if photo is not None and photo.filename:
        taille_max = int(
            config.get("verification", {}).get("photo_taille_max_mo", TAILLE_PHOTO_MAX_MO_DEFAUT)
            * 1024
            * 1024
        )
        contenu = photo.file.read(taille_max + 1)
        if len(contenu) > taille_max:
            raise HTTPException(413, "photo trop volumineuse")
        extension = _extension_photo(contenu)
        if extension is None:
            raise HTTPException(422, "photo invalide (JPEG, PNG ou WebP attendu)")

    maintenant = datetime.now(timezone.utc)
    with acces_db(request) as conn:
        contexte = contexte_depuis_db(
            conn,
            x_device_token,
            latitude,
            longitude,
            config,
            avec_photo=contenu is not None,
            maintenant=maintenant,
        )
        verdict = verifier(latitude, longitude, config, contexte)

        with db.transaction(conn):
            contributeur_id = _contributeur(conn, x_device_token)
            code = _generer_code(conn)
            curseur = conn.execute(
                "INSERT INTO signalement (contributeur_id, latitude, longitude, description,"
                " type_dechet, volume_estime, code_suivi, statut, motif, score_auto, alertes, cree_le)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    contributeur_id,
                    latitude,
                    longitude,
                    description or None,
                    type_dechet.value,
                    volume_estime.value,
                    code,
                    verdict.statut.value,
                    verdict.motif,
                    verdict.score_auto,
                    db.en_json(verdict.alertes),
                    # Même format que `contexte_depuis_db` pour comparer les dates comme du texte.
                    maintenant.isoformat(),
                ),
            )
            signalement_id = curseur.lastrowid
            conn.execute(
                "UPDATE contributeur SET nb_signalements = nb_signalements + 1 WHERE id = ?",
                (contributeur_id,),
            )
            # Une photo n'est gardée que si le signalement n'est pas rejeté d'office.
            if contenu is not None and verdict.statut != StatutSignalement.rejete_auto:
                dossier = dossier_uploads()
                dossier.mkdir(parents=True, exist_ok=True)
                nom = f"{signalement_id}{extension}"
                (dossier / nom).write_bytes(contenu)
                conn.execute("UPDATE signalement SET photo = ? WHERE id = ?", (nom, signalement_id))

    return SignalementCree(
        id=signalement_id, code_suivi=code, statut=verdict.statut, motif=verdict.motif
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
