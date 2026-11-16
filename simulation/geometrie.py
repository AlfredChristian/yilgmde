"""Géométrie pure (sans dépendance) : appartenance d'un point à une zone.

Les polygones sont au format GeoJSON : coordonnées `[longitude, latitude]`, un
anneau extérieur puis d'éventuels trous. Algorithme du rayon (even-odd). Un point
exactement sur une frontière peut être classé de l'un ou l'autre côté : les zones
d'un jeu de données ne doivent pas se chevaucher.
"""

from __future__ import annotations

from typing import Sequence


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
