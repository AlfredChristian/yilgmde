"""G1 — Export GeoJSON des dépotoirs vérifiés, prêt pour OpenStreetMap.

Un dépotoir n'existe en base que s'il vient d'un signalement **validé** par la
modération (A3) ou d'un import vérifié : c'est ce qu'on appelle « vérifié ». Par
défaut, seuls les dépotoirs présents sur le terrain sont exportés (`actif`,
`intervention_planifiee`) : un site éradiqué n'est plus un dépotoir à cartographier.

Étiquettes (D30, à valider avec la communauté OSM du Burkina avant tout versement) :
- illégal  → `amenity=waste_dump_site` (« lieu où des déchets ont été déposés
  illégalement », étiquette en usage, notamment en Afrique de l'Ouest) ;
- officiel → `landuse=landfill` ;
- `waste=*` seulement pour les types qui ont une valeur OSM claire, les autres
  restent dans `description` ;
- `check_date` = dernière mise à jour, `source=survey;YilGmdé`.

**Aucune donnée personnelle** : ni photo, ni contributeur, ni description libre
d'un citoyen. Les propriétés du GeoJSON ne sont que des étiquettes OSM, pour être
ouvertes telles quelles dans JOSM ; l'identifiant interne est dans le `id` de la
Feature, pas dans les étiquettes. Rappel : un versement dans OSM est un import, qui
suit la procédure de la communauté (discussion, licence ODbL des signalements).
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import datetime, timezone

STATUTS_TERRAIN = ("actif", "intervention_planifiee")

# Seuls les types dont la valeur OSM `waste=*` est sans ambiguïté.
WASTE_OSM = {"menager": "trash", "plastiques": "plastic", "organique": "organic"}
LIBELLES = {
    "menager": "ménagers", "gravats": "gravats", "encombrants": "encombrants",
    "plastiques": "plastiques", "organique": "organiques", "autre": "autres",
}


def _types_dechets(conn: sqlite3.Connection, depotoir_id: int) -> list[str]:
    """Types de déchets des signalements validés du dépotoir, du plus fréquent au moins fréquent."""
    lignes = conn.execute(
        "SELECT type_dechet FROM signalement WHERE depotoir_id = ? AND statut = 'verifie'", (depotoir_id,)
    ).fetchall()
    compte = Counter(l["type_dechet"] for l in lignes)
    return [t for t, _ in sorted(compte.items(), key=lambda x: (-x[1], x[0]))]


def etiquettes(depotoir: dict, types: list[str], config: dict) -> dict:
    export = config.get("export_osm", {})
    tags = {"amenity": "waste_dump_site"} if depotoir["legalite"] == "illegal" else {"landuse": "landfill"}
    waste = [WASTE_OSM[t] for t in types if t in WASTE_OSM]
    if waste:
        tags["waste"] = ";".join(waste)
    if types:
        tags["description"] = "Déchets " + ", ".join(LIBELLES.get(t, t) for t in types)
    tags["check_date"] = depotoir["derniere_maj"][:10]
    tags["source"] = export.get("source", "survey;YilGmdé")
    return tags


def exporter_depotoirs(conn: sqlite3.Connection, config: dict, statuts: tuple[str, ...] = STATUTS_TERRAIN) -> dict:
    export = config.get("export_osm", {})
    min_sig = int(export.get("min_signalements", 1))
    marques = ",".join("?" for _ in statuts)
    lignes = conn.execute(
        f"SELECT * FROM depotoir WHERE statut IN ({marques}) AND nb_signalements >= ? ORDER BY id",
        (*statuts, min_sig),
    ).fetchall()
    features = []
    for l in lignes:
        d = dict(l)
        features.append(
            {
                "type": "Feature",
                "id": f"yilgmde/depotoir/{d['id']}",
                "geometry": {"type": "Point", "coordinates": [round(d["longitude"], 7), round(d["latitude"], 7)]},
                "properties": etiquettes(d, _types_dechets(conn, d["id"]), config),
            }
        )
    return {
        "type": "FeatureCollection",
        "metadata": {
            "genere_le": datetime.now(timezone.utc).isoformat(),
            "commune": config.get("ville"),
            "statuts": list(statuts),
            "min_signalements": min_sig,
            "nombre": len(features),
            "licence": export.get("licence"),
            "avertissement": (
                "Données à verser dans OpenStreetMap selon la procédure d'import de la communauté "
                "(discussion préalable, licence ODbL). Aucune donnée personnelle."
            ),
        },
        "features": features,
    }
