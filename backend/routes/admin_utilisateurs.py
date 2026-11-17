"""F4 — Création et liste des comptes, réservées à l'administrateur."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.deps import acces_db
from backend.schemas import Role, UtilisateurAdmin, UtilisateurCreation
from backend.securite import exiger_role
from backend.utilisateurs import EmailDejaUtilise, creer_utilisateur, journaliser

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/utilisateurs", status_code=201, response_model=UtilisateurAdmin)
def creer_compte(
    donnees: UtilisateurCreation,
    request: Request,
    admin: dict = Depends(exiger_role(Role.admin)),
):
    with acces_db(request) as conn:
        try:
            cree = creer_utilisateur(conn, donnees.nom, donnees.email, donnees.mot_de_passe, donnees.role)
        except EmailDejaUtilise:
            raise HTTPException(409, "un compte existe déjà avec cet email")
        journaliser(conn, admin["id"], "creer_utilisateur", "utilisateur", cree["id"])
        conn.commit()
    return cree


@router.get("/utilisateurs", response_model=list[UtilisateurAdmin])
def lister_comptes(request: Request, _admin: dict = Depends(exiger_role(Role.admin))):
    with acces_db(request) as conn:
        lignes = conn.execute(
            "SELECT id, nom, email, role, actif FROM utilisateur ORDER BY id"
        ).fetchall()
    return [{**dict(l), "actif": bool(l["actif"])} for l in lignes]
