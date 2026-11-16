import copy
import json

import pytest

from backend.config import appliquer_surcharges, charger_config
from simulation.plan import calculer_plan, zones_du_scenario


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
        {"id": 2, "latitude": 12.385, "longitude": -1.505, "zone_id": 2, "statut": "eradique", "legalite": "illegal",
         "volume_estime": "moyen", "nb_signalements": 1, "nb_reapparitions": 0},
        {"id": 3, "latitude": 12.405, "longitude": -1.485, "zone_id": None, "statut": "actif", "legalite": "illegal",
         "volume_estime": "petit", "nb_signalements": 1, "nb_reapparitions": 1},
    ],
}
NOUVEAU_QUARTIER = {"type": "Feature", "properties": {"nom": "Extension nord", "population": 5000},
                    "geometry": carre(12.40, -1.49, 0.01)}


def test_plan_complet_et_coherent(config):
    plan = calculer_plan(DONNEES, config)
    assert set(plan) >= {"points_regroupement", "tournees", "indicateurs", "non_couverts"}
    assert [t["id"] for t in plan["tournees"]] == list(range(1, len(plan["tournees"]) + 1))
    types = {t["type"] for t in plan["tournees"]}
    assert types == {"collecte", "intervention"}
    ids_points = {p["id"] for p in plan["points_regroupement"]}
    for t in plan["tournees"]:
        for a in t["arrets"]:
            if a["cible_type"] == "point_regroupement":
                assert a["cible_id"] in ids_points
    ind = plan["indicateurs"]
    assert ind["depotoirs_actifs"] == 2                     # le dépotoir éradiqué ne compte pas (règle 3)
    assert ind["dechets_collectes_pct"] == 100.0 and plan["non_couverts"] == []
    assert ind["demande_totale_kg_jour"] == pytest.approx(10000 * config["population"]["production_dechets_kg_hab_jour"])
    assert ind["cout_total_xof"] == sum(t["cout_xof"] for t in plan["tournees"])
    assert ind["methode_tournees"] == "ortools"


def test_pur_et_reproductible(config):
    avant = json.dumps([DONNEES, config], sort_keys=True)
    a = calculer_plan(DONNEES, config)
    assert calculer_plan(copy.deepcopy(DONNEES), copy.deepcopy(config)) == a
    assert json.dumps([DONNEES, config], sort_keys=True) == avant


def test_eradique_pas_dans_laabal_ni_dans_les_points(config):
    plan = calculer_plan(DONNEES, config)
    cibles = {a["cible_id"] for t in plan["tournees"] if t["type"] == "intervention" for a in t["arrets"]}
    assert 2 not in cibles
    assert all(2 not in p["depotoirs_desservis"] for p in plan["points_regroupement"])


def test_panne_de_tous_les_camions_cree_des_non_couverts(config):
    panne = appliquer_surcharges(config, {"camions": [{"id": c["id"], "disponible": False} for c in config["camions"]]})
    plan = calculer_plan(DONNEES, panne)
    assert not any(t["type"] == "collecte" for t in plan["tournees"])
    assert plan["indicateurs"]["dechets_collectes_pct"] == 0
    assert plan["indicateurs"]["camions_indisponibles"] == [c["id"] for c in config["camions"]]
    deps = [nc for nc in plan["non_couverts"] if "depotoir_id" in nc]
    assert {d["depotoir_id"] for d in deps} == {1, 3}
    assert "aucun camion disponible" in deps[0]["raison"]


def test_saison_des_pluies(config):
    seche = calculer_plan(DONNEES, config)["indicateurs"]
    pluies = calculer_plan(DONNEES, appliquer_surcharges(config, {"scenario": {"saison": "pluies"}}))["indicateurs"]
    assert pluies["demande_totale_kg_jour"] > seche["demande_totale_kg_jour"]
    assert pluies["saison"] == "pluies"


def test_nouveau_quartier(config):
    avec = appliquer_surcharges(config, {"zones_ajoutees": [NOUVEAU_QUARTIER]})
    plan = calculer_plan(DONNEES, avec)
    assert plan["zones_ajoutees"] == [3]
    nouveaux = [p for p in plan["points_regroupement"] if p["zone_id"] == 3]
    assert nouveaux
    assert any(3 in p["depotoirs_desservis"] for p in nouveaux)      # le dépotoir hors zone y est rattaché
    assert plan["indicateurs"]["demande_totale_kg_jour"] > calculer_plan(DONNEES, config)["indicateurs"]["demande_totale_kg_jour"]


def test_zones_ajoutees_ids_et_erreurs():
    zones = zones_du_scenario(DONNEES["zones"], {"zones_ajoutees": [carre(0, 0, 1), dict(NOUVEAU_QUARTIER, properties={"id": 1})]})
    assert [z["id"] for z in zones] == [1, 2, 3, 4]                # id en conflit remplacé
    assert zones[2]["nom"] == "Nouveau quartier 1" and zones[2]["population"] is None
    with pytest.raises(ValueError):
        zones_du_scenario([], {"zones_ajoutees": [{"type": "Point", "coordinates": [0, 0]}]})
    with pytest.raises(ValueError):
        zones_du_scenario([], {"zones_ajoutees": ["pas un objet"]})


def test_budget(config):
    serre = appliquer_surcharges(config, {"mairie": {"budget_mensuel_xof": 1000}})
    ind = calculer_plan(DONNEES, serre)["indicateurs"]
    assert ind["budget_depasse"] is True and ind["cout_mensuel_estime_xof"] > 1000
    assert calculer_plan(DONNEES, config)["indicateurs"]["budget_depasse"] is False


def test_sans_donnees(config):
    plan = calculer_plan({"zones": [], "depotoirs": []}, config)
    assert plan["points_regroupement"] == [] and plan["tournees"] == []
    assert plan["indicateurs"]["dechets_collectes_pct"] == 100.0
