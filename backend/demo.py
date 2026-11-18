"""Préparation de la démonstration : comptes de terrain, scénarios prêts à comparer, tournées affectées.

Appelé par `python scripts/charger_exemples.py --ouaga --demo`. Idempotent : relancer ne crée
ni doublon de compte ni doublon de scénario. Les mots de passe sont ceux de la démo, affichés
par le script : à changer (page Comptes) si l'application sort de la démo.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

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


def _historique_demo(conn: sqlite3.Connection, laabal_id: int) -> int:
    """Historique fictif mais cohérent pour le suivi de l'éradication (D60) : les dépotoirs
    importés avec un statut avancé reçoivent leurs interventions datées (brigade de démo),
    et les signalements vérifiés une date de validation (quelques heures après réception).
    Ne touche pas aux dépotoirs qui ont déjà un historique : relancer ne crée rien de plus."""
    ajoutes = 0
    def iso(t: datetime) -> str:
        return t.isoformat(timespec="seconds")
    for s in conn.execute("SELECT id, cree_le FROM signalement WHERE statut = 'verifie' AND valide_le IS NULL").fetchall():
        quand = datetime.fromisoformat(s["cree_le"]) + timedelta(hours=1 + (s["id"] * 7) % 20)
        conn.execute("UPDATE signalement SET valide_le = ? WHERE id = ?", (iso(quand), s["id"]))
    deja = {l["depotoir_id"] for l in conn.execute("SELECT DISTINCT depotoir_id FROM intervention")}
    for d in conn.execute(
        "SELECT id, statut, premiere_detection, derniere_maj FROM depotoir WHERE legalite = 'illegal' "
        "AND statut IN ('intervention_planifiee', 'eradique', 'sous_surveillance')"
    ).fetchall():
        if d["id"] in deja:
            continue
        # Dates du jeu importé : certaines sont dans le futur ou confondues ; on les remet en ordre.
        maintenant = datetime.now(timezone.utc) - timedelta(hours=1)
        fin = min(datetime.fromisoformat(d["derniere_maj"]), maintenant)
        debut = min(datetime.fromisoformat(d["premiere_detection"]), fin)
        def borne(t: datetime) -> datetime:
            return min(t, maintenant)
        if d["statut"] == "intervention_planifiee":
            etapes = [("en_cours", borne(max(fin, debut + timedelta(hours=3))))]
        elif d["statut"] == "eradique":
            en_cours = borne(max(debut + timedelta(hours=3), fin - max(timedelta(hours=6), (fin - debut) / 3)))
            etapes = [("en_cours", en_cours), ("eradique", borne(max(fin, en_cours + timedelta(hours=3))))]
        else:   # sous surveillance : éradiqué, puis surveillé quelques jours plus tard
            eradique = borne(max(debut + timedelta(hours=6), fin - timedelta(days=4)))
            en_cours = borne(max(debut + timedelta(hours=3), eradique - timedelta(days=1)))
            etapes = [("en_cours", min(en_cours, eradique)), ("eradique", eradique)]
            conn.execute(
                "INSERT INTO journal_audit (utilisateur_id, action, objet_type, objet_id, date) VALUES (?, 'surveillance', 'depotoir', ?, ?)",
                (laabal_id, d["id"], iso(borne(max(fin, eradique + timedelta(days=1))))),
            )
        for statut, quand in etapes:
            conn.execute("INSERT INTO intervention (depotoir_id, laabal_id, statut, date) VALUES (?, ?, ?, ?)",
                         (d["id"], laabal_id, statut, iso(quand)))
            ajoutes += 1
    return ajoutes


def preparer_demo(conn: sqlite3.Connection, config: dict) -> dict:
    """Comptes, scénarios « base / pluies / panne / sensibilisation » sur l'arrondissement 9,
    plan de base calculé, deux rotations au chauffeur et une tournée à la brigade Laabal,
    historique des interventions pour le suivi de l'éradication."""
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
        interventions = _historique_demo(conn, comptes[Role.laabal])
    return {
        "comptes": [(email, mdp, role.value) for _, email, mdp, role in COMPTES_DEMO],
        "scenarios": [l["nom"] for l in conn.execute("SELECT nom FROM scenario ORDER BY id")],
        "tournees_affectees": len(collecte) + len(intervention),
        "points": len(plan["points_regroupement"]),
        "interventions_historiques": interventions,
    }
