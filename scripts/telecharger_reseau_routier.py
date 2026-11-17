"""Télécharge le réseau routier de Ouagadougou depuis OpenStreetMap (Overpass), pour que les
tournées suivent les vraies voies au lieu de lignes droites (D52).

    python scripts/telecharger_reseau_routier.py

À lancer sur une machine qui a accès à Internet (aucune dépendance : bibliothèque standard).
Écrit `data/ouaga/reseau_routier.json.gz` (~ quelques Mo), à committer : ensuite le moteur
calcule les itinéraires **hors ligne**, sans service extérieur, le jour de la démo compris.

Ce qui est gardé : les voies carrossables (de l'autoroute à la rue résidentielle et aux voies
de service). Ce qui est retiré : accès interdit ou privé, voies militaires, allées de parking,
et toute voie située dans un camp militaire ou un aéroport. Les sens uniques sont conservés.
Données © contributeurs OpenStreetMap, licence ODbL.
"""

from __future__ import annotations

import gzip
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "data" / "ouaga" / "reseau_routier.json.gz"
BBOX = (12.24, -1.66, 12.50, -1.39)          # sud, ouest, nord, est (config/ouagadougou.yaml)
SERVEURS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
TYPES = ("motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|"
         "tertiary|tertiary_link|unclassified|residential|living_street|service|road")

REQUETE = f"""
[out:json][timeout:300];
(
  wr["landuse"="military"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  wr["aeroway"="aerodrome"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  wr["military"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
)->.zones_interdites;
.zones_interdites map_to_area ->.interdit;
way(area.interdit)["highway"]->.dedans;
way["highway"~"^({TYPES})$"]
   ["access"!~"^(no|private|military)$"]
   ["motor_vehicle"!~"^(no|private)$"]
   ["motorcar"!~"^(no|private)$"]
   ["service"!~"^(parking_aisle|driveway|drive-through)$"]
   ["area"!="yes"]
   ({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]})->.routes;
(.routes; - .dedans;)->.ok;
.ok out body;
.ok >;
out skel qt;
"""


def telecharger() -> dict:
    corps = urllib.parse.urlencode({"data": REQUETE}).encode()
    for url in SERVEURS:
        for essai in range(2):
            try:
                print(f"Requête à {url} (essai {essai + 1}) : 1 à 3 minutes…", flush=True)
                req = urllib.request.Request(url, data=corps, headers={"User-Agent": "yilgmde/1.0 (hackathon Ouagadougou)"})
                with urllib.request.urlopen(req, timeout=400) as r:
                    return json.loads(r.read().decode("utf-8"))
            except Exception as e:  # serveur saturé ou coupé : on essaie le suivant
                print(f"  échec : {e}", flush=True)
                time.sleep(10)
    sys.exit("Aucun serveur Overpass n'a répondu. Réessayez plus tard, ou avec le partage de connexion du téléphone.")


def compacter(brut: dict) -> dict:
    noeuds = {e["id"]: (round(e["lat"], 6), round(e["lon"], 6)) for e in brut["elements"] if e["type"] == "node"}
    voies = []
    for e in brut["elements"]:
        if e["type"] != "way":
            continue
        t = e.get("tags", {})
        ids = [n for n in e["nodes"] if n in noeuds]
        if len(ids) < 2:
            continue
        sens = t.get("oneway", "no")
        if t.get("junction") == "roundabout" and sens == "no":
            sens = "yes"
        voies.append({"n": ids, "h": t.get("highway"), "s": {"yes": 1, "true": 1, "1": 1, "-1": -1}.get(sens, 0),
                      **({"nom": t["name"]} if "name" in t else {})})
    utilises = {n for v in voies for n in v["n"]}
    return {
        "source": "OpenStreetMap (Overpass), © contributeurs OpenStreetMap, ODbL",
        "telecharge_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bbox": BBOX,
        "noeuds": {str(i): noeuds[i] for i in utilises},
        "voies": voies,
    }


def main() -> None:
    brut = telecharger()
    donnees = compacter(brut)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(SORTIE, "wt", encoding="utf-8") as f:
        json.dump(donnees, f, separators=(",", ":"))
    taille = SORTIE.stat().st_size / 1e6
    print(f"{len(donnees['voies'])} voies, {len(donnees['noeuds'])} nœuds → {SORTIE} ({taille:.1f} Mo)")


if __name__ == "__main__":
    main()
