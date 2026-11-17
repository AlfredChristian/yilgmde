"""Charge des données fictives dans la base de développement ou de démonstration.

Deux jeux :
- `data/sample/` (défaut) : 2 petites zones, quelques dépotoirs, utilisé par les tests ;
- `data/ouaga/` : jeu **réaliste** de Ouagadougou (livrable 4) : 52 secteurs des 12
  arrondissements (population RGPH 2019), 215 dépotoirs dont 35 centres de collecte,
  930 signalements anonymes. Généré par `scripts/generer_donnees_ouaga.py`.

Idempotent : une table déjà remplie n'est pas touchée.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from backend import db
from backend.zones import importer_zones_geojson

DOSSIER_SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample"
DOSSIER_OUAGA = Path(__file__).resolve().parent.parent / "data" / "ouaga"


def _fichier(dossier: Path, nom: str) -> Path:
    """`zones.geojson` (jeu de Ouaga) ou `zones_exemple.geojson` (jeu d'exemple)."""
    direct = dossier / f"{nom}.geojson"
    return direct if direct.exists() else dossier / f"{nom}_exemple.geojson"


def _lire(chemin: Path) -> dict:
    return json.loads(chemin.read_text(encoding="utf-8"))


def charger_exemples(conn: sqlite3.Connection, dossier: Path | None = None) -> dict:
    """Renvoie le nombre de zones, de dépotoirs et de signalements insérés."""
    dossier = Path(dossier) if dossier else DOSSIER_SAMPLE
    resultat = {"zones": 0, "depotoirs": 0, "signalements": 0}

    if conn.execute("SELECT COUNT(*) FROM zone").fetchone()[0] == 0:
        resultat["zones"] = importer_zones_geojson(conn, _lire(_fichier(dossier, "zones")))

    if conn.execute("SELECT COUNT(*) FROM depotoir").fetchone()[0] == 0:
        collection = _lire(_fichier(dossier, "depotoirs"))
        with db.transaction(conn):
            for f in collection["features"]:
                p = f["properties"]
                lon, lat = f["geometry"]["coordinates"]
                conn.execute(
                    "INSERT INTO depotoir (id, latitude, longitude, zone_id, volume_estime, statut, legalite,"
                    " nb_signalements, nb_reapparitions, premiere_detection, derniere_maj)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (p["id"], lat, lon, p.get("zone_id"), p["volume_estime"], p["statut"], p["legalite"],
                     p["nb_signalements"], p.get("nb_reapparitions", 0),
                     p.get("premiere_detection", p["derniere_maj"]), p["derniere_maj"]),
                )
                resultat["depotoirs"] += 1

    chemin = dossier / "signalements.geojson"      # historique : seulement dans le jeu de Ouaga
    if chemin.exists() and conn.execute("SELECT COUNT(*) FROM signalement").fetchone()[0] == 0:
        with db.transaction(conn):
            for f in _lire(chemin)["features"]:
                p = f["properties"]
                lon, lat = f["geometry"]["coordinates"]
                conn.execute(
                    "INSERT INTO signalement (id, latitude, longitude, type_dechet, volume_estime, code_suivi,"
                    " statut, motif, depotoir_id, alertes, cree_le) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', ?)",
                    (p["id"], lat, lon, p["type_dechet"], p["volume_estime"], f"OUA-{p['id']:04d}",
                     p["statut"], p.get("motif"), p.get("depotoir_id"), p["cree_le"]),
                )
                resultat["signalements"] += 1
    return resultat
