"""B2 — Couche « zones » de la carte, avec la demande de déchets estimée (C1)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.deps import acces_db
from backend.zones import lire_zones
from simulation.demande import estimer_demande

router = APIRouter(tags=["zones"])


@router.get("/zones")
def lister_zones(request: Request):
    """Zones en GeoJSON. La demande suit la config courante (saison, production par habitant)."""
    with acces_db(request) as conn:
        zones = lire_zones(conn)
    demandes = {d["zone_id"]: d for d in estimer_demande(zones, request.app.state.config)}
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": z["geometrie"],
                "properties": {
                    "id": z["id"],
                    "nom": z["nom"],
                    "population": z["population"],
                    "densite": z["densite"],
                    "demande_kg_jour": round(demandes[z["id"]]["demande_kg_jour"], 1),
                },
            }
            for z in zones
        ],
    }
