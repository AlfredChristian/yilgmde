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
                    "arrondissement": z["arrondissement"],
                    "demande_kg_jour": round(demandes[z["id"]]["demande_kg_jour"], 1),
                },
            }
            for z in zones
        ],
    }


@router.get("/arrondissements")
def lister_arrondissements(request: Request):
    """Arrondissements présents dans les zones, pour choisir le périmètre d'un plan (livrable 3)."""
    with acces_db(request) as conn:
        zones = lire_zones(conn)
    demandes = {d["zone_id"]: d for d in estimer_demande(zones, request.app.state.config)}
    par_arr: dict[int, dict] = {}
    for z in zones:
        if z["arrondissement"] is None:
            continue
        a = par_arr.setdefault(z["arrondissement"], {"arrondissement": z["arrondissement"], "zones": [],
                                                      "population": 0, "population_inconnue": False,
                                                      "demande_kg_jour": 0.0})
        a["zones"].append(z["id"])
        if z["population"] is None:
            a["population_inconnue"] = True
        else:
            a["population"] += z["population"]
        a["demande_kg_jour"] = round(a["demande_kg_jour"] + demandes[z["id"]]["demande_kg_jour"], 1)
    return [par_arr[k] for k in sorted(par_arr)]
