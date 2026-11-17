"""Géométrie pure (sans dépendance) : appartenance d'un point à une zone.

Les polygones sont au format GeoJSON : coordonnées `[longitude, latitude]`, un
anneau extérieur puis d'éventuels trous. Algorithme du rayon (even-odd). Un point
exactement sur une frontière peut être classé de l'un ou l'autre côté : les zones
d'un jeu de données ne doivent pas se chevaucher.
"""

from __future__ import annotations

import math
from typing import Sequence

RAYON_TERRE_M = 6_371_000.0


def _dans_anneau(lon: float, lat: float, anneau: Sequence[Sequence[float]]) -> bool:
    dedans = False
    n = len(anneau)
    j = n - 1
    for i in range(n):
        xi, yi = anneau[i][0], anneau[i][1]
        xj, yj = anneau[j][0], anneau[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            dedans = not dedans
        j = i
    return dedans


def _polygones(geometrie: dict) -> list[list]:
    """Liste de polygones (chacun = liste d'anneaux), pour Polygon et MultiPolygon."""
    type_ = geometrie.get("type")
    if type_ == "Polygon":
        return [geometrie["coordinates"]]
    if type_ == "MultiPolygon":
        return list(geometrie["coordinates"])
    raise ValueError(f"géométrie non supportée : {type_!r} (Polygon ou MultiPolygon attendu)")


def point_dans_geometrie(latitude: float, longitude: float, geometrie: dict) -> bool:
    for anneaux in _polygones(geometrie):
        if not anneaux or not _dans_anneau(longitude, latitude, anneaux[0]):
            continue
        if any(_dans_anneau(longitude, latitude, trou) for trou in anneaux[1:]):
            continue
        return True
    return False


def zone_pour_point(latitude: float, longitude: float, zones: Sequence[dict]) -> int | None:
    """Id de la première zone (par ordre de la liste) qui contient le point, sinon None.

    Chaque zone est un dict avec `id` et `geometrie` (GeoJSON déjà décodé).
    """
    for zone in zones:
        if point_dans_geometrie(latitude, longitude, zone["geometrie"]):
            return zone["id"]
    return None


# --- Distances et projection locale (mètres) -------------------------------------
# À l'échelle d'une ville, une projection équirectangulaire autour d'un point de
# référence est précise à mieux que 0,1 % : pas besoin de pyproj pour le moteur.


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en mètres entre deux points WGS84 (haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * RAYON_TERRE_M * math.asin(math.sqrt(min(1.0, a)))


def vers_metres(latitude: float, longitude: float, lat0: float, lon0: float) -> tuple[float, float]:
    """(x, y) en mètres par rapport à l'origine (lat0, lon0)."""
    x = math.radians(longitude - lon0) * RAYON_TERRE_M * math.cos(math.radians(lat0))
    y = math.radians(latitude - lat0) * RAYON_TERRE_M
    return x, y


def depuis_metres(x: float, y: float, lat0: float, lon0: float) -> tuple[float, float]:
    """Inverse de `vers_metres` : renvoie (latitude, longitude)."""
    latitude = lat0 + math.degrees(y / RAYON_TERRE_M)
    longitude = lon0 + math.degrees(x / (RAYON_TERRE_M * math.cos(math.radians(lat0))))
    return latitude, longitude


def emprise(geometrie: dict) -> tuple[float, float, float, float]:
    """(min_lat, min_lon, max_lat, max_lon) des anneaux extérieurs."""
    lons, lats = [], []
    for anneaux in _polygones(geometrie):
        if anneaux:
            lons.extend(c[0] for c in anneaux[0])
            lats.extend(c[1] for c in anneaux[0])
    if not lons:
        raise ValueError("géométrie vide")
    return min(lats), min(lons), max(lats), max(lons)


def _aire_anneau_m2(anneau: Sequence[Sequence[float]], lat0: float, lon0: float) -> float:
    pts = [vers_metres(c[1], c[0], lat0, lon0) for c in anneau]
    s = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def aire_m2(geometrie: dict) -> float:
    """Aire approchée en m² (anneaux extérieurs moins les trous)."""
    min_lat, min_lon, max_lat, max_lon = emprise(geometrie)
    lat0, lon0 = (min_lat + max_lat) / 2, (min_lon + max_lon) / 2
    total = 0.0
    for anneaux in _polygones(geometrie):
        if not anneaux:
            continue
        total += _aire_anneau_m2(anneaux[0], lat0, lon0)
        total -= sum(_aire_anneau_m2(t, lat0, lon0) for t in anneaux[1:])
    return max(0.0, total)


def echantillonner(geometrie: dict, pas_m: float, max_points: int) -> list[tuple[float, float]]:
    """Points (lat, lon) d'une grille régulière à l'intérieur de la géométrie.

    Le pas est agrandi si besoin pour ne pas dépasser `max_points` (calcul rapide,
    contrainte 3 de CONTEXT.md). Une zone plus petite que le pas renvoie au moins
    un point : le centre de son emprise s'il est dedans, sinon un sommet.
    """
    min_lat, min_lon, max_lat, max_lon = emprise(geometrie)
    lat0, lon0 = (min_lat + max_lat) / 2, (min_lon + max_lon) / 2
    largeur, _ = vers_metres(lat0, max_lon, lat0, min_lon)
    _, hauteur = vers_metres(max_lat, lon0, min_lat, lon0)
    aire = aire_m2(geometrie)
    if aire > 0 and pas_m > 0 and aire / (pas_m * pas_m) > max_points:
        pas_m = math.sqrt(aire / max_points)
    pas_m = max(pas_m, 1.0)
    points = []
    nx = int(largeur // pas_m) + 1
    ny = int(hauteur // pas_m) + 1
    for j in range(ny):
        for i in range(nx):
            x = -largeur / 2 + (i + 0.5) * pas_m
            y = -hauteur / 2 + (j + 0.5) * pas_m
            lat, lon = depuis_metres(x, y, lat0, lon0)
            if point_dans_geometrie(lat, lon, geometrie):
                points.append((lat, lon))
    if not points:
        if point_dans_geometrie(lat0, lon0, geometrie):
            points.append((lat0, lon0))
        else:
            premier = _polygones(geometrie)[0][0][0]
            points.append((premier[1], premier[0]))
    return points
