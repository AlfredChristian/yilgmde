import copy
import json

import pytest

from backend.config import appliquer_surcharges, charger_config
from simulation.plan import calculer_plan, zones_du_scenario


def carre(lat, lon, cote):
    return {"type": "Polygon", "coordinates": [[[lon, lat], [lon + cote, lat], [lon + cote, lat + cote], [lon, lat + cote], [lon, lat]]]}


@pytest.fixture
def config():
    # Configuration générique : on teste le moteur, pas les valeurs de Ouaga (70 camions, etc.).
    return charger_config(None, surcharges={"collecte": {"depot": {"latitude": 12.37, "longitude": -1.52}}})


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
    assert ind["capacite_collecte_pct"] == 100.0 and plan["non_couverts"] == []
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
    assert plan["indicateurs"]["capacite_collecte_pct"] == 0
    assert plan["indicateurs"]["camions_indisponibles"] == [c["id"] for c in config["camions"]]
    assert plan["indicateurs"]["camions_flotte"] == [c["id"] for c in config["camions"]]
    assert set(plan["indicateurs"]["leviers"]) == {"taux_abonnement_precollecteurs", "evolution_population_pct", "frequence_passages_par_semaine", "prob_apport_volontaire"}
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
    assert plan["indicateurs"]["capacite_collecte_pct"] == 100.0


# --- Livrable 3 : plan d'un arrondissement ------------------------------------------------

from simulation.plan import restreindre_perimetre  # noqa: E402

PAR_ARR = {
    "zones": [dict(DONNEES["zones"][0], arrondissement=4), dict(DONNEES["zones"][1], arrondissement=7)],
    "depotoirs": DONNEES["depotoirs"],
}


def test_sans_perimetre_toute_la_commune(config):
    assert restreindre_perimetre(PAR_ARR, config) is None
    assert calculer_plan(PAR_ARR, config)["indicateurs"]["perimetre"] is None


def test_plan_d_un_arrondissement(config):
    arr4 = appliquer_surcharges(config, {"perimetre": {"arrondissements": [4]}})
    plan = calculer_plan(PAR_ARR, arr4)
    assert {p["zone_id"] for p in plan["points_regroupement"]} == {1}
    assert plan["indicateurs"]["perimetre"] == {"arrondissements": [4], "zones": [1], "population": 6000, "part_budget": 0.6}
    assert plan["indicateurs"]["demande_totale_kg_jour"] == pytest.approx(6000 * config["population"]["production_dechets_kg_hab_jour"])
    # les dépotoirs hors périmètre (zone 2, hors zone) ne sont ni desservis ni traités par Laabal
    assert plan["indicateurs"]["depotoirs_actifs"] == 1
    cibles = {a["cible_id"] for t in plan["tournees"] if t["type"] == "intervention" for a in t["arrets"]}
    assert cibles <= {1}
    assert all(set(p["depotoirs_desservis"]) <= {1} for p in plan["points_regroupement"])


def test_perimetre_par_zones_et_union(config):
    par_zone = appliquer_surcharges(config, {"perimetre": {"zones": [2]}})
    assert restreindre_perimetre(PAR_ARR, par_zone)["zones"] == [2]
    union = appliquer_surcharges(config, {"perimetre": {"arrondissements": [4], "zones": [2]}})
    assert restreindre_perimetre(PAR_ARR, union)["zones"] == [1, 2]


def test_perimetre_vide_ou_invalide(config):
    with pytest.raises(ValueError, match="périmètre vide"):
        restreindre_perimetre(PAR_ARR, appliquer_surcharges(config, {"perimetre": {"arrondissements": [99]}}))
    with pytest.raises(ValueError):
        restreindre_perimetre(PAR_ARR, dict(config, perimetre="x"))


def test_nouveau_quartier_garde_dans_le_perimetre(config):
    avec = appliquer_surcharges(config, {"perimetre": {"arrondissements": [4]}, "zones_ajoutees": [NOUVEAU_QUARTIER]})
    plan = calculer_plan(PAR_ARR, avec)
    assert plan["zones_ajoutees"] == [3]                     # id libre dans toute la commune, pas 2
    assert {p["zone_id"] for p in plan["points_regroupement"]} == {1, 3}   # la zone 2, hors périmètre, est exclue
    assert any(3 in p["depotoirs_desservis"] for p in plan["points_regroupement"] if p["zone_id"] == 3)


def test_simulation_d_un_arrondissement(config):
    from simulation.agents import simuler
    arr7 = appliquer_surcharges(config, {"perimetre": {"arrondissements": [7]}})
    r = simuler(PAR_ARR, arr7, 5, 1)
    assert r["indicateurs"][0]["production_kg"] == pytest.approx(4000 * config["population"]["production_dechets_kg_hab_jour"])
    assert r["resume"]["depotoirs_actifs_debut"] == 0          # le seul dépotoir de la zone 2 est éradiqué


def test_budget_au_prorata_du_perimetre(config):
    """Plan d'un arrondissement : sa part du budget communal, au prorata de la population (D39)."""
    from simulation.agents import simuler
    arr4 = appliquer_surcharges(config, {"perimetre": {"arrondissements": [4]}})
    ind = calculer_plan(PAR_ARR, arr4)["indicateurs"]
    assert ind["perimetre"]["part_budget"] == pytest.approx(6000 / 10000)
    assert ind["budget_mensuel_xof"] == round(config["mairie"]["budget_mensuel_xof"] * 0.6)
    commune = simuler(PAR_ARR, config, 1, 1)["indicateurs"][0]["budget_restant_xof"]
    arr = simuler(PAR_ARR, arr4, 1, 1)["indicateurs"][0]["budget_restant_xof"]
    assert arr < commune


def test_capacite_et_part_captee_sont_distinctes(config):
    """D41 : le plan dit si les camions suffisent ET estime la part des déchets qui arrive aux points."""
    from simulation.agents import simuler
    ind = calculer_plan(DONNEES, config)["indicateurs"]
    assert ind["capacite_collecte_pct"] == 100.0 == ind["dechets_collectes_pct"]           # alias déprécié
    assert ind["part_captee_estimee_pct"] < 100
    assert ind["precollecte_pct"] + ind["apport_volontaire_pct"] == pytest.approx(ind["part_captee_estimee_pct"], abs=0.2)
    assert ind["part_captee_estimee_pct"] + ind["non_capte_pct"] == pytest.approx(100, abs=0.2)
    # la simulation retrouve l'estimation le premier jour (pas encore de dissuasion Laabal)
    jour1 = simuler(DONNEES, config, 1, 1)["indicateurs"][0]
    assert jour1["part_captee_pct"] == pytest.approx(ind["part_captee_estimee_pct"], abs=1)
    # le levier « apport volontaire » agit sur la part captée, pas sur la capacité des camions
    plus = appliquer_surcharges(config, {"simulation": {"prob_apport_volontaire": 0.9}})
    ind2 = calculer_plan(DONNEES, plus)["indicateurs"]
    assert ind2["part_captee_estimee_pct"] > ind["part_captee_estimee_pct"]
    assert ind2["capacite_collecte_pct"] == ind["capacite_collecte_pct"]
