import pytest

from simulation.geometrie import point_dans_geometrie, zone_pour_point

# Carré lon -1.54..-1.51, lat 12.36..12.38 (format GeoJSON : [lon, lat])
CARRE = {"type": "Polygon", "coordinates": [[[-1.54, 12.36], [-1.51, 12.36], [-1.51, 12.38], [-1.54, 12.38], [-1.54, 12.36]]]}


def test_point_dedans_et_dehors():
    assert point_dans_geometrie(12.37, -1.525, CARRE)
    assert not point_dans_geometrie(12.40, -1.525, CARRE)      # trop au nord
    assert not point_dans_geometrie(12.37, -1.50, CARRE)       # trop à l'est


def test_l_ordre_est_longitude_puis_latitude_dans_geojson():
    # (lat, lon) inversés : ne doit PAS tomber dans le carré
    assert not point_dans_geometrie(-1.525, 12.37, CARRE)


def test_trou_exclu():
    trou = [[-1.53, 12.365], [-1.52, 12.365], [-1.52, 12.375], [-1.53, 12.375], [-1.53, 12.365]]
    avec_trou = {"type": "Polygon", "coordinates": [CARRE["coordinates"][0], trou]}
    assert not point_dans_geometrie(12.37, -1.525, avec_trou)  # dans le trou
    assert point_dans_geometrie(12.362, -1.535, avec_trou)     # dans l'anneau, hors trou


def test_multipolygone():
    autre = [[[-1.48, 12.39], [-1.47, 12.39], [-1.47, 12.40], [-1.48, 12.40], [-1.48, 12.39]]]
    multi = {"type": "MultiPolygon", "coordinates": [CARRE["coordinates"], autre]}
    assert point_dans_geometrie(12.37, -1.525, multi)
    assert point_dans_geometrie(12.395, -1.475, multi)
    assert not point_dans_geometrie(12.45, -1.6, multi)


def test_polygone_non_convexe():
    # forme en L : le coin manquant (haut droit) est dehors
    forme_l = {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 1], [1, 1], [1, 2], [0, 2], [0, 0]]]}
    assert point_dans_geometrie(0.5, 1.5, forme_l)             # lat 0.5, lon 1.5 : bras horizontal
    assert point_dans_geometrie(1.5, 0.5, forme_l)             # bras vertical
    assert not point_dans_geometrie(1.5, 1.5, forme_l)         # coin manquant


def test_geometrie_non_supportee():
    with pytest.raises(ValueError):
        point_dans_geometrie(0, 0, {"type": "Point", "coordinates": [0, 0]})


def test_zone_pour_point_prend_la_premiere_qui_contient():
    zones = [
        {"id": 7, "geometrie": CARRE},
        {"id": 9, "geometrie": CARRE},   # chevauchement volontaire : la première gagne
    ]
    assert zone_pour_point(12.37, -1.525, zones) == 7
    assert zone_pour_point(0, 0, zones) is None
    assert zone_pour_point(12.37, -1.525, []) is None
