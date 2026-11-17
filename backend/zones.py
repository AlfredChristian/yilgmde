"""Zones (quartiers ou secteurs) : lecture, import GeoJSON, rattachement d'un point."""

from __future__ import annotations

import sqlite3

from backend import db
from simulation.geometrie import point_dans_geometrie, zone_pour_point


def lire_zones(conn: sqlite3.Connection) -> list[dict]:
    """Zones avec leur géométrie décodée, par id croissant."""
    return [
        {
            "id": l["id"],
            "nom": l["nom"],
            "geometrie": db.depuis_json(l["geometrie"], {}),
            "population": l["population"],
            "densite": l["densite"],
            "arrondissement": l["arrondissement"],
        }
        for l in conn.execute("SELECT id, nom, geometrie, population, densite, arrondissement FROM zone ORDER BY id")
    ]


def zone_id_pour_point(conn: sqlite3.Connection, latitude: float, longitude: float) -> int | None:
    return zone_pour_point(latitude, longitude, lire_zones(conn))


def importer_zones_geojson(conn: sqlite3.Connection, collection: dict) -> int:
    """Insère les zones d'une `FeatureCollection` de Polygon/MultiPolygon. Renvoie leur nombre.

    Propriétés lues : `nom` (obligatoire), `population`, `densite`, `arrondissement`
    (entier), `id` (optionnel, pour garder des identifiants stables d'un jeu de données
    à l'autre).
    Tout ou rien : une zone invalide annule l'import.
    """
    if collection.get("type") != "FeatureCollection":
        raise ValueError("FeatureCollection attendue")
    zones = []
    for i, feature in enumerate(collection.get("features", []), start=1):
        proprietes = feature.get("properties") or {}
        nom = (proprietes.get("nom") or "").strip()
        if not nom:
            raise ValueError(f"zone {i} : propriété 'nom' manquante")
        geometrie = feature.get("geometry") or {}
        try:
            point_dans_geometrie(0.0, 0.0, geometrie)   # valide le type de géométrie
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise ValueError(f"zone {nom!r} : géométrie invalide ({e})") from e
        arrondissement = proprietes.get("arrondissement")
        if arrondissement is not None and (isinstance(arrondissement, bool) or not isinstance(arrondissement, int)):
            raise ValueError(f"zone {nom!r} : 'arrondissement' doit être un entier")
        zones.append((proprietes.get("id"), nom, geometrie, proprietes.get("population"), proprietes.get("densite"),
                      arrondissement))
    with db.transaction(conn):
        for zone_id, nom, geometrie, population, densite, arrondissement in zones:
            conn.execute(
                "INSERT INTO zone (id, nom, geometrie, population, densite, arrondissement) VALUES (?, ?, ?, ?, ?, ?)",
                (zone_id, nom, db.en_json(geometrie), population, densite, arrondissement),
            )
    return len(zones)
