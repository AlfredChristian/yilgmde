"""Comptes (admin, chauffeur, laabal). Pas d'inscription libre : l'admin les crée (F4)."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from backend import db
from backend.schemas import Role
from backend.securite import hasher_mot_de_passe


class EmailDejaUtilise(ValueError):
    """Un compte existe déjà avec cet email."""


def normaliser_email(email: str) -> str:
    return email.strip().lower()


def journaliser(conn: sqlite3.Connection, utilisateur_id: int | None, action: str, objet_type: str, objet_id: int | None) -> None:
    """Règle de cohérence 5 : toute action sensible est tracée dans `journal_audit`."""
    conn.execute(
        "INSERT INTO journal_audit (utilisateur_id, action, objet_type, objet_id, date) VALUES (?, ?, ?, ?, ?)",
        (utilisateur_id, action, objet_type, objet_id, datetime.now(timezone.utc).isoformat()),
    )


def creer_utilisateur(conn: sqlite3.Connection, nom: str, email: str, mot_de_passe: str, role: Role) -> dict:
    """Crée un compte actif. Lève `EmailDejaUtilise` si l'email existe."""
    email = normaliser_email(email)
    with db.transaction(conn):
        if conn.execute("SELECT 1 FROM utilisateur WHERE email = ?", (email,)).fetchone():
            raise EmailDejaUtilise(email)
        curseur = conn.execute(
            "INSERT INTO utilisateur (nom, email, mot_de_passe_hash, role, actif, cree_le) VALUES (?, ?, ?, ?, 1, ?)",
            (nom.strip(), email, hasher_mot_de_passe(mot_de_passe), role.value, datetime.now(timezone.utc).isoformat()),
        )
    return {"id": curseur.lastrowid, "nom": nom.strip(), "email": email, "role": role.value, "actif": True}


def creer_admin_si_absent(conn: sqlite3.Connection) -> bool:
    """Amorçage du tout premier admin depuis l'environnement, sans rien mettre dans le dépôt.

    Lit `YILGMDE_ADMIN_EMAIL` et `YILGMDE_ADMIN_PASSWORD` (et `YILGMDE_ADMIN_NOM`).
    Ne fait rien si les variables manquent ou si un admin existe déjà. Renvoie True si créé.
    """
    email = os.environ.get("YILGMDE_ADMIN_EMAIL")
    mot_de_passe = os.environ.get("YILGMDE_ADMIN_PASSWORD")
    if not email or not mot_de_passe:
        return False
    if conn.execute("SELECT 1 FROM utilisateur WHERE role = 'admin'").fetchone():
        return False
    creer_utilisateur(conn, os.environ.get("YILGMDE_ADMIN_NOM", "Administrateur"), email, mot_de_passe, Role.admin)
    return True
