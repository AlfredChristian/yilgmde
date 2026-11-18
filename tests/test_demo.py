"""--demo : comptes, scénarios et affectations prêts, sans doublon si on relance."""

from backend import db
from backend.config import charger_config
from backend.demo import preparer_demo
from backend.exemples import DOSSIER_OUAGA, charger_exemples


def test_preparer_demo_est_complet_et_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("YILGMDE_ADMIN_EMAIL", "admin@ouaga.bf")
    monkeypatch.setenv("YILGMDE_ADMIN_PASSWORD", "admin12345")
    conn = db.connecter(tmp_path / "demo.sqlite3")
    db.initialiser(conn)
    charger_exemples(conn, DOSSIER_OUAGA)
    config = charger_config("ouagadougou")
    d = preparer_demo(conn, config)
    assert d["scenarios"] == ["base", "pluies", "panne", "sensibilisation"]
    assert d["tournees_affectees"] == 3
    roles = {l["role"] for l in conn.execute("SELECT role FROM utilisateur")}
    assert roles == {"admin", "chauffeur", "laabal"}
    preparer_demo(conn, config)
    assert conn.execute("SELECT COUNT(*) FROM utilisateur").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM scenario").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM tournee WHERE affectee_a IS NOT NULL").fetchone()[0] == 3


def test_historique_de_demo_pour_le_suivi_de_l_eradication(tmp_path, monkeypatch):
    monkeypatch.setenv("YILGMDE_ADMIN_EMAIL", "admin@ouaga.bf")
    monkeypatch.setenv("YILGMDE_ADMIN_PASSWORD", "admin12345")
    conn = db.connecter(tmp_path / "demo.sqlite3")
    db.initialiser(conn)
    charger_exemples(conn, DOSSIER_OUAGA)
    config = charger_config("ouagadougou")
    d = preparer_demo(conn, config)
    assert d["interventions_historiques"] > 0
    avances = conn.execute(
        "SELECT COUNT(*) FROM depotoir WHERE legalite = 'illegal' AND statut IN ('intervention_planifiee', 'eradique', 'sous_surveillance')"
    ).fetchone()[0]
    avec = conn.execute("SELECT COUNT(DISTINCT depotoir_id) FROM intervention").fetchone()[0]
    assert avec == avances
    assert conn.execute("SELECT COUNT(*) FROM signalement WHERE statut = 'verifie' AND valide_le IS NULL").fetchone()[0] == 0
    # Chaque éradication vient après la première détection du dépotoir.
    for l in conn.execute(
        "SELECT i.date, d.premiere_detection FROM intervention i JOIN depotoir d ON d.id = i.depotoir_id"
    ):
        assert l["date"] >= l["premiere_detection"][:19]
    n = conn.execute("SELECT COUNT(*) FROM intervention").fetchone()[0]
    preparer_demo(conn, config)
    assert conn.execute("SELECT COUNT(*) FROM intervention").fetchone()[0] == n
