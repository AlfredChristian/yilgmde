"""F1 — Connexion (JWT) et identité de l'utilisateur courant."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.deps import acces_db
from backend.schemas import LoginEntree, TokenSortie, UtilisateurSortie
from backend.securite import (
    DUREE_TOKEN_MIN_DEFAUT,
    creer_token,
    utilisateur_courant,
    verifier_mot_de_passe,
)
from backend.utilisateurs import normaliser_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenSortie)
def connexion(donnees: LoginEntree, request: Request):
    with acces_db(request) as conn:
        ligne = conn.execute(
            "SELECT id, role, mot_de_passe_hash, actif FROM utilisateur WHERE email = ?",
            (normaliser_email(donnees.email),),
        ).fetchone()
    hash_stocke = ligne["mot_de_passe_hash"] if ligne is not None and ligne["actif"] else None
    # Même message et même temps de calcul que l'email existe ou non : pas d'énumération de comptes.
    if not verifier_mot_de_passe(donnees.mot_de_passe, hash_stocke):
        raise HTTPException(401, "identifiants invalides")
    duree = request.app.state.config.get("securite", {}).get("duree_token_min", DUREE_TOKEN_MIN_DEFAUT)
    return TokenSortie(access_token=creer_token(ligne["id"], ligne["role"], duree), role=ligne["role"])


@router.get("/moi", response_model=UtilisateurSortie)
def moi(utilisateur: dict = Depends(utilisateur_courant)):
    return utilisateur
