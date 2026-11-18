import copy
import json
import math

import pytest

from backend.config import appliquer_surcharges, charger_config
from simulation.geometrie import (
    aire_m2,
    depuis_metres,
    distance_m,
    echantillonner,
    point_dans_geometrie,
    vers_metres,
)
from simulation.regroupement import jours_entre_passages, placer_points


@pytest.fixture
def config():
    c = charger_config("ouagadougou")
    c["population"]["batiments"] = None      # grille uniforme : tests indépendants du fichier réel (voir test_batiments.py)
    return c


def carre(lat, lon, cote_deg):
    return {"type": "Polygon", "coordinates": [[
        [lon, lat], [lon + cote_deg, lat], [lon + cote_deg, lat + cote_deg], [lon, lat + cote_deg], [lon, lat],
    ]]}


# ~1,1 km de côté (≈ 1,2 km²) : rapide à calculer, plusieurs points nécessaires.
ZONE_A = {"id": 1, "nom": "A", "population": 6000, "geometrie": carre(12.36, -1.53, 0.01)}
ZONE_B = {"id": 2, "nom": "B", "population": 3000, "geometrie": carre(12.39, -1.50, 0.01)}
DEPOTOIRS = [
    {"id": 10, "latitude": 12.3612, "longitude": -1.5288, "zone_id": 1},   # coin sud-ouest de A
    {"id": 11, "latitude": 12.4500, "longitude": -1.4500, "zone_id": None},   # hors zone
    {"id": 12, "latitude": 12.4505, "longitude": -1.4503, "zone_id": None},   # à ~60 m du 11
]


# --- Géométrie ---------------------------------------------------------------------

def test_distance_m_ordre_de_grandeur():
    assert distance_m(12.37, -1.52, 12.37, -1.52) == 0
    assert distance_m(12.0, -1.5, 12.01, -1.5) == pytest.approx(1112, rel=0.01)   # 0,01° de latitude


def test_projection_aller_retour():
    x, y = vers_metres(12.38, -1.51, 12.37, -1.52)
    lat, lon = depuis_metres(x, y, 12.37, -1.52)
    assert (lat, lon) == pytest.approx((12.38, -1.51), abs=1e-9)
    assert math.hypot(x, y) == pytest.approx(distance_m(12.38, -1.51, 12.37, -1.52), rel=0.001)


def test_aire_carre_et_trou():
    g = carre(12.36, -1.53, 0.01)
    attendu = 1113.2 * 0.9780 * 1113.2 * 1.0 * 1.0   # côté est-ouest réduit par cos(12,36°)
    assert aire_m2(g) == pytest.approx(attendu * 1.0, rel=0.01)
    avec_trou = {"type": "Polygon", "coordinates": g["coordinates"] + carre(12.362, -1.528, 0.002)["coordinates"]}
    assert aire_m2(avec_trou) == pytest.approx(aire_m2(g) - aire_m2(carre(12.362, -1.528, 0.002)), rel=0.001)


def test_echantillons_dans_la_zone_et_bornes():
    g = carre(12.36, -1.53, 0.01)
    pts = echantillonner(g, 100, 2000)
    assert 100 <= len(pts) <= 130 and all(point_dans_geometrie(la, lo, g) for la, lo in pts)
    assert len(echantillonner(g, 1, 50)) <= 60          # pas agrandi pour respecter la borne
    minuscule = carre(12.36, -1.53, 0.0001)               # ~11 m de côté < pas
    assert len(echantillonner(minuscule, 100, 2000)) == 1


# --- Placement ---------------------------------------------------------------------

def test_fonction_pure_et_reproductible(config):
    zones, depotoirs = [ZONE_A, ZONE_B], DEPOTOIRS
    avant = json.dumps([zones, depotoirs, config], sort_keys=True)
    a = placer_points(depotoirs, zones, config)
    b = placer_points(copy.deepcopy(depotoirs), copy.deepcopy(zones), copy.deepcopy(config))
    assert a == b
    assert json.dumps([zones, depotoirs, config], sort_keys=True) == avant


def test_points_dans_leur_zone_numerotes_et_expliques(config):
    r = placer_points(DEPOTOIRS, [ZONE_A, ZONE_B], config)
    pts = r["points"]
    assert [p["id"] for p in pts] == list(range(1, len(pts) + 1))
    geos = {1: ZONE_A["geometrie"], 2: ZONE_B["geometrie"]}
    for p in pts:
        assert p["explication"]
        assert p["capacite_kg"] == config["points_regroupement"]["capacite_kg"]
        if p["zone_id"] is not None:
            assert point_dans_geometrie(p["latitude"], p["longitude"], geos[p["zone_id"]])


def test_couverture_a_pied_atteinte(config):
    r = placer_points([], [ZONE_A], config)
    assert r["non_couverts"] == []
    rayon = config["points_regroupement"]["distance_max_a_pied_m"]
    menages = echantillonner(ZONE_A["geometrie"], 100, 2000)
    proches = sum(
        1 for la, lo in menages
        if min(distance_m(la, lo, p["latitude"], p["longitude"]) for p in r["points"]) <= rayon
    )
    assert proches / len(menages) >= config["points_regroupement"]["couverture_cible"]


def test_demande_repartie_entre_les_points(config):
    r = placer_points([], [ZONE_A], config)
    total = sum(p["charge_kg_jour"] for p in r["points"])
    attendu = 6000 * config["population"]["production_dechets_kg_hab_jour"]
    assert total == pytest.approx(attendu, rel=0.01)
    for p in r["points"]:
        assert p["stock_entre_passages_kg"] == pytest.approx(p["charge_kg_jour"] * jours_entre_passages(config), abs=0.2)


def test_plus_de_demande_ou_moins_de_passages_donne_plus_de_points(config):
    dense = dict(ZONE_A, population=30_000)
    base = len(placer_points([], [dense], config)["points"])
    rare = appliquer_surcharges(config, {"collecte": {"frequence_passages_par_semaine": 1}})
    assert len(placer_points([], [dense], rare)["points"]) > base
    pluies = appliquer_surcharges(config, {"scenario": {"saison": "pluies"}})
    assert len(placer_points([], [dense], pluies)["points"]) >= base
    # capacité respectée : le stock entre deux passages tient dans les points de la zone
    r = placer_points([], [dense], config)["points"]
    assert len(r) * config["points_regroupement"]["capacite_kg"] >= sum(p["stock_entre_passages_kg"] for p in r)


def test_point_sature_signale(config):
    petit = appliquer_surcharges(config, {"points_regroupement": {"capacite_kg": 100, "max_points_par_zone": 3}})
    r = placer_points([], [dict(ZONE_A, population=200_000)], petit)
    assert len(r["points"]) == 3
    assert all(p["sature"] for p in r["points"])
    assert "capacité dépassée" in r["points"][0]["explication"]
    assert "capacité insuffisante" in r["non_couverts"][0]["raison"]


def test_depotoir_actif_desservi_a_distance_de_marche(config):
    r = placer_points(DEPOTOIRS[:1], [ZONE_A], config)
    rayon = config["points_regroupement"]["distance_max_a_pied_m"]
    porteur = [p for p in r["points"] if 10 in p["depotoirs_desservis"]]
    assert len(porteur) == 1
    assert distance_m(12.3612, -1.5288, porteur[0]["latitude"], porteur[0]["longitude"]) <= rayon
    assert "[10]" in porteur[0]["explication"]


def test_depotoirs_hors_zone_regroupes(config):
    r = placer_points(DEPOTOIRS[1:], [], config)
    assert len(r["points"]) == 1
    p = r["points"][0]
    assert p["zone_id"] is None and p["depotoirs_desservis"] == [11, 12] and p["charge_kg_jour"] is None
    assert "Hors des zones connues" in p["explication"]


def test_population_inconnue(config):
    inconnue = dict(ZONE_A, population=None)
    r = placer_points([], [inconnue], config)
    assert r["points"] == [] and r["non_couverts"][0]["zone_id"] == 1
    assert "population inconnue" in r["non_couverts"][0]["raison"]
    r = placer_points(DEPOTOIRS[:1], [inconnue], config)   # un dépotoir : un point pour lui seul
    assert len(r["points"]) == 1 and r["points"][0]["depotoirs_desservis"] == [10]
    assert r["non_couverts"] == []


def test_population_nulle_sans_depotoir(config):
    assert placer_points([], [dict(ZONE_A, population=0)], config) == {"points": [], "non_couverts": []}


def test_limite_de_points_signale_une_zone_mal_couverte(config):
    borne = appliquer_surcharges(config, {"points_regroupement": {"max_points_par_zone": 2}})
    r = placer_points([], [ZONE_A], borne)
    assert len(r["points"]) == 2
    assert r["non_couverts"][0]["zone_id"] == 1 and "limite de 2 points" in r["non_couverts"][0]["raison"]


def test_frequence_nulle_refusee(config):
    zero = appliquer_surcharges(config, {"collecte": {"frequence_passages_par_semaine": 0}})
    with pytest.raises(ValueError):
        placer_points([], [ZONE_A], zero)
