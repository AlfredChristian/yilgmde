"""F4 — Gestion des comptes, réservée à l'administrateur : création, liste, modification, mot de passe (D49)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.deps import acces_db
from backend.schemas import MotDePasseReinitialisation, Role, UtilisateurAdmin, UtilisateurCreation, UtilisateurModification
from backend.securite import exiger_role, hasher_mot_de_passe
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


def _compte_ou_404(conn, utilisateur_id: int):
    ligne = conn.execute("SELECT id, nom, email, role, actif FROM utilisateur WHERE id = ?", (utilisateur_id,)).fetchone()
    if ligne is None:
        raise HTTPException(404, "compte inconnu")
    return ligne


@router.patch("/utilisateurs/{utilisateur_id}", response_model=UtilisateurAdmin)
def modifier_compte(
    utilisateur_id: int,
    donnees: UtilisateurModification,
    request: Request,
    admin: dict = Depends(exiger_role(Role.admin)),
):
    """D49 : renommer, changer de rôle, désactiver ou réactiver un compte.

    Pas de suppression : le journal d'audit et les tournées gardent la trace de qui a fait quoi.
    Un compte désactivé ne peut plus se connecter et son jeton en cours est refusé.
    Garde-fous (409) : un admin ne se désactive pas et ne se retire pas son rôle lui-même,
    et il reste toujours au moins un admin actif.
    """
    with acces_db(request) as conn:
        compte = _compte_ou_404(conn, utilisateur_id)
        nouveau_role = donnees.role.value if donnees.role is not None else compte["role"]
        nouvel_actif = donnees.actif if donnees.actif is not None else bool(compte["actif"])
        if utilisateur_id == admin["id"] and (not nouvel_actif or nouveau_role != Role.admin.value):
            raise HTTPException(409, "vous ne pouvez pas désactiver votre propre compte ni retirer votre rôle d'admin")
        if compte["role"] == Role.admin.value and compte["actif"] and (not nouvel_actif or nouveau_role != Role.admin.value):
            autres = conn.execute(
                "SELECT COUNT(*) FROM utilisateur WHERE role = 'admin' AND actif = 1 AND id != ?", (utilisateur_id,)
            ).fetchone()[0]
            if autres == 0:
                raise HTTPException(409, "il doit rester au moins un admin actif")
        nom = donnees.nom.strip() if donnees.nom is not None else compte["nom"]
        conn.execute(
            "UPDATE utilisateur SET nom = ?, role = ?, actif = ? WHERE id = ?",
            (nom, nouveau_role, int(nouvel_actif), utilisateur_id),
        )
        # Un compte désactivé ou qui change de rôle ne garde pas ses tournées : l'admin les réaffecte.
        if not nouvel_actif or nouveau_role != compte["role"]:
            conn.execute("UPDATE tournee SET affectee_a = NULL WHERE affectee_a = ?", (utilisateur_id,))
        journaliser(conn, admin["id"], "modifier_utilisateur", "utilisateur", utilisateur_id)
        conn.commit()
    return {"id": utilisateur_id, "nom": nom, "email": compte["email"], "role": nouveau_role, "actif": nouvel_actif}


@router.post("/utilisateurs/{utilisateur_id}/mot-de-passe", response_model=UtilisateurAdmin)
def reinitialiser_mot_de_passe(
    utilisateur_id: int,
    donnees: MotDePasseReinitialisation,
    request: Request,
    admin: dict = Depends(exiger_role(Role.admin)),
):
    """D49 : l'admin fixe un nouveau mot de passe (chauffeur qui l'a oublié, par exemple)."""
    with acces_db(request) as conn:
        compte = _compte_ou_404(conn, utilisateur_id)
        conn.execute(
            "UPDATE utilisateur SET mot_de_passe_hash = ? WHERE id = ?",
            (hasher_mot_de_passe(donnees.mot_de_passe), utilisateur_id),
        )
        journaliser(conn, admin["id"], "reinitialiser_mot_de_passe", "utilisateur", utilisateur_id)
        conn.commit()
    return {**dict(compte), "actif": bool(compte["actif"])}
