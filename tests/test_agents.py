import copy
import json

import pytest

from backend.config import appliquer_surcharges, charger_config
from simulation.agents import simuler
from simulation.plan import calculer_plan


def carre(lat, lon, cote):
    return {"type": "Polygon", "coordinates": [[[lon, lat], [lon + cote, lat], [lon + cote, lat + cote], [lon, lat + cote], [lon, lat]]]}


@pytest.fixture
def config():
    return charger_config("ouagadougou", surcharges={"collecte": {"depot": {"latitude": 12.37, "longitude": -1.52}}})


DONNEES = {
    "zones": [
        {"id": 1, "nom": "A", "population": 6000, "geometrie": carre(12.36, -1.53, 0.01)},
        {"id": 2, "nom": "B", "population": 4000, "geometrie": carre(12.38, -1.51, 0.01)},
    ],
    "depotoirs": [
        {"id": 1, "latitude": 12.365, "longitude": -1.525, "zone_id": 1, "statut": "actif", "legalite": "illegal",
         "volume_estime": "gros", "nb_signalements": 3, "nb_reapparitions": 0},
        {"id": 2, "latitude": 12.385, "longitude": -1.505, "zone_id": 2, "statut": "actif", "legalite": "illegal",
         "volume_estime": "moyen", "nb_signalements": 1, "nb_reapparitions": 0},
    ],
}


def resume(config, jours=30, graine=42, donnees=DONNEES):
    return simuler(donnees, config, jours, graine)["resume"]


def test_indicateurs_par_jour(config):
    r = simuler(DONNEES, config, 10, 1)
    assert r["graine"] == 1 and [i["jour"] for i in r["indicateurs"]] == list(range(1, 11))
    for i in r["indicateurs"]:
        assert {"pct_collecte", "depotoirs_actifs", "cout_xof", "distance_km"} <= set(i)   # contrat d'API
        assert 0 <= i["pct_collecte"] <= 100
        assert i["production_kg"] == pytest.approx(10000 * config["population"]["production_dechets_kg_hab_jour"])
    assert r["resume"]["jours"] == 10


def test_reproductible_par_graine_et_pur(config):
    avant = json.dumps([DONNEES, config], sort_keys=True)
    a = simuler(DONNEES, config, 20, 7)
    assert simuler(copy.deepcopy(DONNEES), copy.deepcopy(config), 20, 7) == a
    assert json.dumps([DONNEES, config], sort_keys=True) == avant
    autres = [simuler(DONNEES, config, 20, g)["indicateurs"] for g in (8, 9, 10)]
    assert any(x != a["indicateurs"] for x in autres)               # le hasard joue bien


def test_graine_par_defaut_de_la_config(config):
    r = simuler(DONNEES, config, 5)
    assert r["graine"] == config["scenario"]["graine_aleatoire"]


def test_conservation_des_dechets(config):
    """Production = arrivée aux points + dépôts sauvages, chaque jour."""
    for i in simuler(DONNEES, config, 15, 3)["indicateurs"]:
        arrive = i["production_kg"] * i["pct_collecte"] / 100
        assert arrive + i["dechets_sauvages_kg"] == pytest.approx(i["production_kg"], abs=1)


def test_passages_selon_la_frequence(config):
    r = simuler(DONNEES, config, 14, 1)
    passages = [i["jour"] for i in r["indicateurs"] if i["passage"]]
    attendu = config["collecte"]["frequence_passages_par_semaine"] * 2
    assert len(passages) == attendu
    plan = calculer_plan(DONNEES, config)
    cout = sum(t["cout_xof"] for t in plan["tournees"] if t["type"] == "collecte")
    assert r["resume"]["cout_total_xof"] == pytest.approx(cout * attendu, abs=attendu)
    assert all(i["stock_points_kg"] >= 0 for i in r["indicateurs"])


def test_plus_d_abonnements_plus_de_collecte(config):
    peu = appliquer_surcharges(config, {"population": {"taux_abonnement_precollecteurs": 0.0}})
    beaucoup = appliquer_surcharges(config, {"population": {"taux_abonnement_precollecteurs": 0.9},
                                             "precollecteurs": {"nombre": 200}})
    assert resume(beaucoup)["pct_collecte_moyen"] > resume(peu)["pct_collecte_moyen"]
    assert resume(beaucoup)["dechets_sauvages_kg"] < resume(peu)["dechets_sauvages_kg"]


def test_saison_des_pluies_plus_de_depots_sauvages(config):
    pluies = appliquer_surcharges(config, {"scenario": {"saison": "pluies"}})
    assert resume(pluies)["dechets_sauvages_kg"] > resume(config)["dechets_sauvages_kg"]


def test_sans_camion_les_points_debordent(config):
    hs = appliquer_surcharges(config, {"camions": [{"id": c["id"], "disponible": False} for c in config["camions"]]})
    r = resume(hs, jours=30)
    assert r["passages_collecte"] == 0 and r["cout_total_xof"] == 0
    assert r["dechets_sauvages_kg"] > resume(config, jours=30)["dechets_sauvages_kg"]


def test_budget_epuise_suspend_la_collecte(config):
    serre = appliquer_surcharges(config, {"mairie": {"budget_mensuel_xof": 10}})
    r = simuler(DONNEES, serre, 10, 1)
    assert r["resume"]["passages_collecte"] == 0 and r["resume"]["passages_suspendus_budget"] > 0
    assert any(i["collecte_suspendue"] for i in r["indicateurs"])


def test_laabal_eradique_et_surveille(config):
    r = simuler(DONNEES, config, 5, 1)
    assert r["indicateurs"][0]["depotoirs_eradiques"] == min(2, config["laabal"]["capacite_eradication_par_jour"])
    assert r["indicateurs"][1]["depotoirs_sous_surveillance"] >= 1
    sans = appliquer_surcharges(config, {"laabal": {"nombre_brigades": 0}})
    assert resume(sans)["depotoirs_eradiques"] == 0
    assert resume(sans)["depotoirs_actifs_fin"] > resume(config)["depotoirs_actifs_fin"]


def test_amendes_et_controles(config):
    toujours = appliquer_surcharges(config, {"laabal": {"taux_controle": 1.0},
                                              "simulation": {"prob_tentative_depot_surveille": 1.0}})
    r = resume(toujours, jours=10)
    assert r["constats"] > 0 and r["amendes_total_xof"] == r["constats"] * config["laabal"]["montant_amende_xof"]
    jamais = appliquer_surcharges(config, {"laabal": {"taux_controle": 0.0}})
    assert resume(jamais)["amendes_total_xof"] == 0


def test_zone_sans_point_tout_en_sauvage(config):
    sans_camion = appliquer_surcharges(config, {"points_regroupement": {"max_points_par_zone": 1}})
    donnees = {"zones": [dict(DONNEES["zones"][0], population=None)], "depotoirs": []}
    r = simuler(donnees, sans_camion, 3, 1)
    assert all(i["production_kg"] == 0 for i in r["indicateurs"])


def test_jours_invalides(config):
    for jours in (0, -1, 366):
        with pytest.raises(ValueError):
            simuler(DONNEES, config, jours, 1)
