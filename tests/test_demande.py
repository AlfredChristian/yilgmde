import json

import pytest

from backend.config import appliquer_surcharges, charger_config
from simulation.demande import coefficient_production, demande_totale_kg_jour, estimer_demande


@pytest.fixture
def config():
    return charger_config("ouagadougou")


ZONES = [
    {"id": 1, "nom": "A", "population": 12000},
    {"id": 2, "nom": "B", "population": 8000},
    {"id": 3, "nom": "C", "population": None},
]


def test_demande_est_population_fois_production_fois_coefficient(config):
    par_hab = config["population"]["production_dechets_kg_hab_jour"]
    d = {x["zone_id"]: x for x in estimer_demande(ZONES, config)}
    assert d[1]["demande_kg_jour"] == pytest.approx(12000 * par_hab * 1.0)   # saison sèche : coefficient 1
    assert d[2]["demande_kg_jour"] == pytest.approx(8000 * par_hab)


def test_saison_des_pluies_augmente_la_demande(config):
    pluies = appliquer_surcharges(config, {"scenario": {"saison": "pluies"}})
    assert coefficient_production(pluies) == config["saisons"]["pluies"]["coef_production"]
    seche = estimer_demande(ZONES, config)[0]["demande_kg_jour"]
    humide = estimer_demande(ZONES, pluies)[0]["demande_kg_jour"]
    assert humide == pytest.approx(seche * config["saisons"]["pluies"]["coef_production"])
    assert humide > seche


def test_production_par_habitant_vient_de_la_config(config):
    double = appliquer_surcharges(config, {"population": {"production_dechets_kg_hab_jour": 1.0}})
    assert estimer_demande(ZONES, double)[0]["demande_kg_jour"] == pytest.approx(12000 * 1.0)


def test_population_inconnue_est_signalee_pas_inventee(config):
    inconnue = estimer_demande(ZONES, config)[2]
    assert inconnue["population_connue"] is False and inconnue["demande_kg_jour"] == 0.0
    assert estimer_demande(ZONES, config)[0]["population_connue"] is True


def test_total_et_ordre_des_zones(config):
    resultat = estimer_demande(ZONES, config)
    assert [r["zone_id"] for r in resultat] == [1, 2, 3]
    assert demande_totale_kg_jour(ZONES, config) == pytest.approx(sum(r["demande_kg_jour"] for r in resultat))
    assert demande_totale_kg_jour([], config) == 0


def test_fonction_pure_sans_effet_de_bord(config):
    avant_config = json.dumps(config, sort_keys=True)
    avant_zones = json.dumps(ZONES, sort_keys=True)
    a = estimer_demande(ZONES, config)
    b = estimer_demande(ZONES, config)
    assert a == b
    assert json.dumps(config, sort_keys=True) == avant_config and json.dumps(ZONES, sort_keys=True) == avant_zones
