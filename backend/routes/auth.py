"""F1 — Connexion (JWT) et identité de l'utilisateur courant."""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Request

from backend import db
from backend.deps import acces_db
from backend.limitation import creer_limiteurs
from backend.schemas import LoginEntree, TokenSortie, UtilisateurSortie
from backend.securite import (
    DUREE_TOKEN_MIN_DEFAUT,
    creer_token,
    utilisateur_courant,
    verifier_mot_de_passe,
)
from backend.utilisateurs import journaliser, normaliser_email

router = APIRouter(prefix="/auth", tags=["auth"])


def limiteurs(request: Request) -> dict:
    """Limiteurs de l'application, créés au premier besoin depuis la config (D32)."""
    if getattr(request.app.state, "limiteurs_login", None) is None:
        request.app.state.limiteurs_login = creer_limiteurs(request.app.state.config)
    return request.app.state.limiteurs_login


def _trop_de_tentatives(attente_s: float) -> HTTPException:
    secondes = max(1, math.ceil(attente_s))
    return HTTPException(429, f"trop de tentatives, réessayez dans {math.ceil(secondes / 60)} min",
                         headers={"Retry-After": str(secondes)})


@router.post("/login", response_model=TokenSortie)
def connexion(donnees: LoginEntree, request: Request):
    email = normaliser_email(donnees.email)
    cles = {"email": email, "ip": request.client.host if request.client else "inconnue"}
    lim = limiteurs(request)
    attente = max(lim[k].attente_s(v) for k, v in cles.items())
    if attente > 0:
        raise _trop_de_tentatives(attente)

    with acces_db(request) as conn:
        ligne = conn.execute(
            "SELECT id, role, mot_de_passe_hash, actif FROM utilisateur WHERE email = ?", (email,)
        ).fetchone()
    hash_stocke = ligne["mot_de_passe_hash"] if ligne is not None and ligne["actif"] else None
    # Même message et même temps de calcul que l'email existe ou non : pas d'énumération de comptes.
    if not verifier_mot_de_passe(donnees.mot_de_passe, hash_stocke):
        bloques = [k for k, v in cles.items() if lim[k].echec(v)]
        if bloques:
            with acces_db(request) as conn:
                with db.transaction(conn):
                    journaliser(conn, None, f"connexion_bloquee_{'_'.join(bloques)}", "utilisateur",
                                ligne["id"] if ligne is not None else None)
        raise HTTPException(401, "identifiants invalides")
    lim["email"].succes(email)
    duree = request.app.state.config.get("securite", {}).get("duree_token_min", DUREE_TOKEN_MIN_DEFAUT)
    return TokenSortie(access_token=creer_token(ligne["id"], ligne["role"], duree), role=ligne["role"])


@router.get("/moi", response_model=UtilisateurSortie)
def moi(utilisateur: dict = Depends(utilisateur_courant)):
    return utilisateur
