import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.main import app
from backend.schemas import SignalementEntree


def test_initialisation_idempotente():
    conn = db.connecter(":memory:")
    db.initialiser(conn)
    db.initialiser(conn)
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"signalement", "depotoir", "utilisateur", "contributeur", "journal_audit"} <= tables


def test_contraintes_de_statut():
    conn = db.connecter(":memory:")
    db.initialiser(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO signalement (latitude, longitude, type_dechet, volume_estime,"
            " code_suivi, statut, cree_le) VALUES (1, 1, 'menager', 'petit', 'X', 'bidon', 'now')"
        )


def test_transaction_annule_en_cas_d_erreur():
    conn = db.connecter(":memory:")
    db.initialiser(conn)
    with pytest.raises(RuntimeError):
        with db.transaction(conn):
            conn.execute(
                "INSERT INTO contributeur (jeton_appareil) VALUES ('abc')"
            )
            raise RuntimeError("échec")
    assert conn.execute("SELECT COUNT(*) FROM contributeur").fetchone()[0] == 0


def test_json_aller_retour():
    assert db.depuis_json(db.en_json(["doublon_probable:3"])) == ["doublon_probable:3"]
    assert db.depuis_json(None, []) == []


def test_schema_signalement_valide_les_entrees():
    ok = SignalementEntree(latitude=12.37, longitude=-1.52, type_dechet="menager", volume_estime="moyen")
    assert ok.description is None
    with pytest.raises(ValueError):
        SignalementEntree(latitude=120, longitude=-1.52, type_dechet="menager", volume_estime="moyen")
    with pytest.raises(ValueError):
        SignalementEntree(latitude=12.37, longitude=-1.52, type_dechet="inconnu", volume_estime="moyen")


def test_api_demarre_et_expose_la_config(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CHEMIN_DB_DEFAUT", tmp_path / "test.sqlite3")
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert app.state.config["ville"] == "Ouagadougou"
