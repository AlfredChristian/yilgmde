"""F1/F2 — Mots de passe, jetons JWT et contrôle des rôles côté serveur.

- Mots de passe : bcrypt (jamais stockés en clair).
- Jeton : JWT HS256. Le secret vient de `YILGMDE_JWT_SECRET` ; à défaut, un secret
  aléatoire est généré au démarrage (les jetons n'y survivent pas) — jamais de
  secret dans le dépôt (D11).
- Chaque requête authentifiée recharge l'utilisateur en base : un compte désactivé
  ou un rôle modifié prend effet immédiatement, sans attendre l'expiration du jeton.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Header, HTTPException, Request

from backend.deps import acces_db
from backend.schemas import Role

ALGORITHME = "HS256"
DUREE_TOKEN_MIN_DEFAUT = 480  # [H] repli si `securite.duree_token_min` manque dans la config

_secret_processus = secrets.token_urlsafe(32)

# Hash factice pour que « email inconnu » coûte autant de temps que « mot de passe faux ».
_HASH_FACTICE = bcrypt.hashpw(b"factice", bcrypt.gensalt()).decode()


def _secret() -> str:
    return os.environ.get("YILGMDE_JWT_SECRET") or _secret_processus


def hasher_mot_de_passe(mot_de_passe: str) -> str:
    return bcrypt.hashpw(mot_de_passe.encode("utf-8"), bcrypt.gensalt()).decode()


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str | None) -> bool:
    """Toujours un calcul bcrypt, même si l'utilisateur n'existe pas (hash_stocke=None)."""
    cible = (hash_stocke or _HASH_FACTICE).encode()
    try:
        ok = bcrypt.checkpw(mot_de_passe.encode("utf-8"), cible)
    except ValueError:  # mot de passe > 72 octets ou hash illisible
        return False
    return ok and hash_stocke is not None


def creer_token(utilisateur_id: int, role: str, duree_min: float = DUREE_TOKEN_MIN_DEFAUT) -> str:
    maintenant = datetime.now(timezone.utc)
    charge = {
        "sub": str(utilisateur_id),
        "role": role,
        "iat": maintenant,
        "exp": maintenant + timedelta(minutes=duree_min),
    }
    return jwt.encode(charge, _secret(), algorithm=ALGORITHME)


def lire_token(token: str) -> dict | None:
    """Charge du jeton, ou None s'il est invalide ou expiré."""
    try:
        return jwt.decode(token, _secret(), algorithms=[ALGORITHME], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        return None


def utilisateur_courant(request: Request, authorization: str | None = Header(None)) -> dict:
    """Dépendance FastAPI : l'utilisateur authentifié (ligne `utilisateur`) ou 401."""
    erreur = HTTPException(401, "authentification requise", headers={"WWW-Authenticate": "Bearer"})
    if not authorization:
        raise erreur
    schema, _, token = authorization.partition(" ")
    if schema.lower() != "bearer" or not token:
        raise erreur
    charge = lire_token(token.strip())
    if charge is None or not str(charge["sub"]).isdigit():
        raise erreur
    with acces_db(request) as conn:
        ligne = conn.execute(
            "SELECT id, nom, email, role, actif FROM utilisateur WHERE id = ?", (int(charge["sub"]),)
        ).fetchone()
    if ligne is None or not ligne["actif"]:
        raise erreur
    return dict(ligne)


def exiger_role(*roles: Role):
    """Dépendance : l'utilisateur doit avoir l'un de ces rôles, sinon 403 (F2)."""
    autorises = {r.value for r in roles}

    def verifier(request: Request, authorization: str | None = Header(None)) -> dict:
        utilisateur = utilisateur_courant(request, authorization)
        if utilisateur["role"] not in autorises:
            raise HTTPException(403, "droits insuffisants pour cette action")
        return utilisateur

    return verifier
