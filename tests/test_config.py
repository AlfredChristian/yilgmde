import copy

import pytest

from backend.config import (
    ConfigError,
    appliquer_surcharges,
    camions_disponibles,
    charger_config,
    coefficients_saison,
    fusion_profonde,
    valider_config,
)


def test_charge_default_et_ville():
    config = charger_config("ouagadougou")
    assert config["ville"] == "Ouagadougou"
    assert config["scenario"]["saison"] == "seche"
    assert config["verification"]["rayon_doublon_m"] == 30
    assert "bbox" in config["zone_etude"]


def test_sans_ville_charge_seulement_default():
    config = charger_config(None)
    assert "ville" not in config
    assert len(config["camions"]) == 3


def test_fusion_ne_modifie_pas_les_entrees():
    base = {"a": {"b": 1}, "l": [1, 2]}
    surcharge = {"a": {"c": 2}, "l": [3]}
    base_avant, surcharge_avant = copy.deepcopy(base), copy.deepcopy(surcharge)
    resultat = fusion_profonde(base, surcharge)
    assert resultat == {"a": {"b": 1, "c": 2}, "l": [3]}
    assert base == base_avant and surcharge == surcharge_avant


def test_fusion_des_camions_par_id():
    config = charger_config("ouagadougou")
    nouvelle = appliquer_surcharges(config, {"camions": [{"id": "camion_2", "disponible": False}]})
    par_id = {c["id"]: c for c in nouvelle["camions"]}
    assert par_id["camion_2"]["disponible"] is False
    assert par_id["camion_2"]["capacite_kg"] == 6000  # les autres champs sont conservés
    assert len(nouvelle["camions"]) == 3
    assert [c["id"] for c in camions_disponibles(nouvelle)] == ["camion_1", "camion_3"]
    # la config d'origine n'a pas bougé (fonction pure)
    assert all(c["disponible"] for c in config["camions"])


def test_ajout_d_un_camion():
    config = charger_config(None)
    nouvelle = appliquer_surcharges(config, {"camions": [{"id": "camion_4", "capacite_kg": 4000}]})
    assert [c["id"] for c in nouvelle["camions"]][-1] == "camion_4"


def test_saison_des_pluies():
    config = appliquer_surcharges(charger_config("ouagadougou"), {"scenario": {"saison": "pluies"}})
    coef = coefficients_saison(config)
    assert coef["coef_vitesse_camion"] == 0.7


def test_saison_invalide_refusee():
    with pytest.raises(ConfigError):
        appliquer_surcharges(charger_config(None), {"scenario": {"saison": "harmattan"}})


def test_camions_en_double_refuses():
    config = charger_config(None)
    config["camions"].append({"id": "camion_1", "capacite_kg": 1})
    with pytest.raises(ConfigError):
        valider_config(config)


def test_bbox_incoherente_refusee():
    bbox = {"min_lat": 12.5, "max_lat": 12.2, "min_lon": -1.6, "max_lon": -1.4}
    with pytest.raises(ConfigError):
        charger_config("ouagadougou", surcharges={"zone_etude": {"bbox": bbox}})


def test_fichier_ville_introuvable():
    with pytest.raises(ConfigError):
        charger_config("ville_inconnue")


def test_ville_choisie_par_variable_d_environnement(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from backend import db
    from backend.main import app

    monkeypatch.setattr(db, "CHEMIN_DB_DEFAUT", tmp_path / "test.sqlite3")
    monkeypatch.setenv("YILGMDE_VILLE", "")                     # vide : default.yaml seul
    with TestClient(app):
        assert app.state.config.get("ville") is None
    monkeypatch.delenv("YILGMDE_VILLE")
    with TestClient(app):
        assert app.state.config["ville"] == "Ouagadougou"
