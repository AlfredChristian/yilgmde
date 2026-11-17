"""Préparation de la démonstration : comptes de terrain, scénarios prêts à comparer, tournées affectées.

Appelé par `python scripts/charger_exemples.py --ouaga --demo`. Idempotent : relancer ne crée
ni doublon de compte ni doublon de scénario. Les mots de passe sont ceux de la démo, affichés
par le script : à changer (page Comptes) si l'application sort de la démo.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from backend import db, plans
from backend.schemas import Role
from backend.utilisateurs import creer_admin_si_absent, creer_utilisateur, journaliser

COMPTES_DEMO = [
    ("Issa Ouédraogo", "chauffeur@ouaga.bf", "chauffeur123", Role.chauffeur),
    ("Brigade Laabal 1", "laabal@ouaga.bf", "laabal1234", Role.laabal),
]
ARRONDISSEMENT_DEMO = 9      # celui du rapport (docs/rapport/)


def _scenarios_demo(config: dict) -> list[tuple[str, dict]]:
    perimetre = {"perimetre": {"arrondissements": [ARRONDISSEMENT_DEMO]}}
    camions = config.get("camions", [])
    en_panne = [{"id": c["id"], "disponible": False} for c in camions[: max(0, len(camions) - 10)]]
    return [
        ("pluies", {**perimetre, "scenario": {"saison": "pluies"}}),
        ("panne", {**perimetre, "camions": en_panne}),
        ("sensibilisation", {**perimetre, "simulation": {"prob_apport_volontaire": 0.8}}),
    ]


def preparer_demo(conn: sqlite3.Connection, config: dict) -> dict:
    """Comptes, scénarios « base / pluies / panne / sensibilisation » sur l'arrondissement 9,
    plan de base calculé, deux rotations au chauffeur et une tournée à la brigade Laabal."""
    creer_admin_si_absent(conn)
    plans.creer_scenario_base_si_absent(conn)
    comptes = {}
    for nom, email, mdp, role in COMPTES_DEMO:
        ligne = conn.execute("SELECT id FROM utilisateur WHERE email = ?", (email,)).fetchone()
        comptes[role] = ligne["id"] if ligne else creer_utilisateur(conn, nom, email, mdp, role)["id"]

    base = conn.execute("SELECT id FROM scenario ORDER BY id LIMIT 1").fetchone()["id"]
    existants = {l["nom"] for l in conn.execute("SELECT nom FROM scenario")}
    with db.transaction(conn):
        conn.execute(
            "UPDATE scenario SET parametres = ? WHERE id = ?",
            (db.en_json({"perimetre": {"arrondissements": [ARRONDISSEMENT_DEMO]}}), base),
        )
        for nom, parametres in _scenarios_demo(config):
            if nom not in existants:
                plans.creer_scenario(conn, nom, parametres, None)
        plans.activer_scenario(conn, base)

    @contextmanager
    def acces():
        yield conn

    plan = plans.calculer_et_enregistrer(acces, config, base)
    collecte = [t for t in plan["tournees"] if t["type"] == "collecte"][:2]
    intervention = [t for t in plan["tournees"] if t["type"] == "intervention"][:1]
    with db.transaction(conn):
        for t in collecte:
            conn.execute("UPDATE tournee SET affectee_a = ? WHERE id = ?", (comptes[Role.chauffeur], t["id"]))
            journaliser(conn, None, "affecter_tournee", "tournee", t["id"])
        for t in intervention:
            conn.execute("UPDATE tournee SET affectee_a = ? WHERE id = ?", (comptes[Role.laabal], t["id"]))
            journaliser(conn, None, "affecter_tournee", "tournee", t["id"])
    return {
        "comptes": [(email, mdp, role.value) for _, email, mdp, role in COMPTES_DEMO],
        "scenarios": [l["nom"] for l in conn.execute("SELECT nom FROM scenario ORDER BY id")],
        "tournees_affectees": len(collecte) + len(intervention),
        "points": len(plan["points_regroupement"]),
    }
