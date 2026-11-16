"""Charge les données d'exemple fictives (`data/sample/`) dans la base de développement.

Sert à développer et à répéter la démo sans attendre les vrais signalements : la
carte publique (`GET /depotoirs`, `GET /zones`) n'est alors plus vide.
Idempotent : une table déjà remplie n'est pas touchée.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from backend import db
from backend.zones import importer_zones_geojson

DOSSIER_SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample"


def _lire(chemin: Path) -> dict:
    return json.loads(chemin.read_text(encoding="utf-8"))


def charger_exemples(conn: sqlite3.Connection, dossier: Path | None = None) -> dict:
    """Renvoie le nombre de zones et de dépotoirs insérés."""
    dossier = Path(dossier) if dossier else DOSSIER_SAMPLE
    resultat = {"zones": 0, "depotoirs": 0}

    if conn.execute("SELECT COUNT(*) FROM zone").fetchone()[0] == 0:
        resultat["zones"] = importer_zones_geojson(conn, _lire(dossier / "zones_exemple.geojson"))

    if conn.execute("SELECT COUNT(*) FROM depotoir").fetchone()[0] == 0:
        collection = _lire(dossier / "depotoirs_exemple.geojson")
        with db.transaction(conn):
            for f in collection["features"]:
                p = f["properties"]
                lon, lat = f["geometry"]["coordinates"]
                conn.execute(
                    "INSERT INTO depotoir (id, latitude, longitude, zone_id, volume_estime, statut, legalite,"
                    " nb_signalements, premiere_detection, derniere_maj) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (p["id"], lat, lon, p.get("zone_id"), p["volume_estime"], p["statut"], p["legalite"],
                     p["nb_signalements"], p["derniere_maj"], p["derniere_maj"]),
                )
                resultat["depotoirs"] += 1
    return resultat
