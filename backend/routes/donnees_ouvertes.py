"""Livrable 4 : jeu de signalements GeoJSON sous licence ouverte (ODbL), public.

Seuls les signalements **vérifiés** par la modération sont publiés, anonymisés (D40) :
- position arrondie à `donnees_ouvertes.decimales_position` décimales (4 ≈ 11 m) ;
- date au jour près ;
- ni appareil, ni photo, ni note vocale, ni texte libre, ni code de suivi.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.deps import acces_db
from backend.zones import lire_zones

router = APIRouter(tags=["donnees-ouvertes"])


@router.get("/donnees/signalements.geojson")
def signalements_ouverts(request: Request):
    config = request.app.state.config
    d = config.get("donnees_ouvertes", {})
    decimales = int(d.get("decimales_position", 4))
    with acces_db(request) as conn:
        zones = {z["id"]: z for z in lire_zones(conn)}
        lignes = conn.execute(
            "SELECT s.id, s.latitude, s.longitude, s.type_dechet, s.volume_estime, s.depotoir_id,"
            " COALESCE(s.capture_le, s.cree_le) AS quand, dep.zone_id"
            " FROM signalement s LEFT JOIN depotoir dep ON dep.id = s.depotoir_id"
            " WHERE s.statut = 'verifie' ORDER BY s.id"
        ).fetchall()
    features = []
    for l in lignes:
        zone = zones.get(l["zone_id"]) or {}
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(l["longitude"], decimales), round(l["latitude"], decimales)]},
            "properties": {
                "id": l["id"],
                "type_dechet": l["type_dechet"],
                "volume_estime": l["volume_estime"],
                "date": (l["quand"] or "")[:10],
                "depotoir_id": l["depotoir_id"],
                "zone_id": l["zone_id"],
                "arrondissement": zone.get("arrondissement"),
            },
        })
    contenu = {
        "type": "FeatureCollection",
        "metadata": {
            "titre": f"Signalements de dépotoirs vérifiés — {config.get('ville') or 'commune'}",
            "licence": d.get("licence", "ODbL-1.0"),
            "licence_url": "https://opendatacommons.org/licenses/odbl/1-0/",
            "attribution": d.get("attribution", "yilgmde et contributeurs"),
            "genere_le": datetime.now(timezone.utc).isoformat(),
            "nombre": len(features),
            "anonymisation": f"positions arrondies à {decimales} décimales, date au jour ; ni appareil, ni photo, "
                             "ni texte libre",
        },
        "features": features,
    }
    return JSONResponse(contenu, media_type="application/geo+json",
                        headers={"Content-Disposition": 'attachment; filename="signalements_yilgmde.geojson"'})
