"""Télécharge les bâtiments de Ouagadougou depuis Google Open Buildings v3 (D58).

    python scripts/telecharger_batiments.py

À lancer sur une machine qui a accès à Internet (bibliothèque standard seulement).
Le fichier source couvre une cellule S2 (de ~100 km à ~600 km de côté) : il est lu **au fil de
l'eau**, sans être stocké, et seuls les bâtiments de la commune sont gardés. Écrit
`data/ouaga/batiments.csv.gz` (latitude, longitude, surface en m², confiance), à committer.

Le moteur s'en sert pour placer les points de regroupement là où sont les maisons et pour
répartir la population de chaque secteur entre ses bâtiments.
Données : Google Open Buildings v3, licence CC BY 4.0 et ODbL (https://sites.research.google/open-buildings/).
"""

from __future__ import annotations

import csv
import gzip
import io
import sys
import time
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "data" / "ouaga" / "batiments.csv.gz"
BBOX = (12.24, -1.66, 12.50, -1.39)          # sud, ouest, nord, est (config/ouagadougou.yaml)
CONFIANCE_MIN = 0.65                          # seuil conseillé par Open Buildings pour un usage courant
BASE = "https://storage.googleapis.com/open-buildings-data/v3"
# La boîte tient dans la cellule S2 de niveau 6 « 0e2f », elle-même dans la cellule de niveau 4 « 0e3 ».
# On essaie d'abord le petit fichier (niveau 6), puis le grand (niveau 4, plusieurs centaines de Mo,
# lu au fil de l'eau sans être stocké).
CHEMINS = [
    "points_s2_level_6_gzip_no_header/0e2f_buildings.csv.gz",
    "points_s2_level_6_gzip_no_header/0e2f.csv.gz",
    "points_s2_level_4_gzip/0e3_buildings.csv.gz",
]


def ouvrir():
    for chemin in CHEMINS:
        url = f"{BASE}/{chemin}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "yilgmde/1.0"})
            r = urllib.request.urlopen(req, timeout=120)
            taille = r.headers.get("Content-Length")
            print(f"Lecture de {url} ({int(taille) / 1e6:.0f} Mo)" if taille else f"Lecture de {url}", flush=True)
            return r
        except Exception as e:      # mauvais nom de fichier : on essaie le suivant
            print(f"  {url} : {e}", flush=True)
    sys.exit("Fichier Open Buildings introuvable. Vérifiez la connexion (partage de connexion du téléphone si besoin).")


def main() -> None:
    sud, ouest, nord, est = BBOX
    gardes, lus, debut = [], 0, time.time()
    flux = io.TextIOWrapper(gzip.GzipFile(fileobj=ouvrir()), encoding="utf-8")
    for ligne in csv.reader(flux):
        if not ligne or ligne[0] == "latitude":       # ligne d'en-tête éventuelle
            continue
        lus += 1
        if lus % 500_000 == 0:
            print(f"  {lus:,} bâtiments lus, {len(gardes):,} gardés ({time.time() - debut:.0f} s)".replace(",", " "), flush=True)
        try:
            lat, lon, surface, confiance = float(ligne[0]), float(ligne[1]), float(ligne[2]), float(ligne[3])
        except (ValueError, IndexError):
            continue
        if sud <= lat <= nord and ouest <= lon <= est and confiance >= CONFIANCE_MIN:
            gardes.append((round(lat, 6), round(lon, 6), round(surface, 1), round(confiance, 2)))
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(SORTIE, "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["latitude", "longitude", "surface_m2", "confiance"])
        w.writerows(sorted(gardes))
    print(f"{len(gardes):,} bâtiments gardés sur {lus:,} lus, écrits dans {SORTIE} ({SORTIE.stat().st_size / 1e6:.1f} Mo)".replace(",", " "))


if __name__ == "__main__":
    main()
