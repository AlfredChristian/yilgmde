"""B1 — Carte publique : dépotoirs vérifiés au format GeoJSON.

La table `depotoir` ne contient que des dépotoirs issus de signalements validés
(règle de cohérence 1) : rien de non vérifié n'est exposé ici.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.deps import acces_db
from backend.schemas import StatutDepotoir

router = APIRouter(tags=["depotoirs"])


@router.get("/depotoirs")
def lister_depotoirs(
    request: Request,
    statut: StatutDepotoir | None = None,
    zone_id: int | None = None,
):
    requete = (
        "SELECT id, latitude, longitude, statut, legalite, volume_estime,"
        " nb_signalements, zone_id, derniere_maj FROM depotoir"
    )
    conditions, valeurs = [], []
    if statut is not None:
        conditions.append("statut = ?")
        valeurs.append(statut.value)
    if zone_id is not None:
        conditions.append("zone_id = ?")
        valeurs.append(zone_id)
    if conditions:
        requete += " WHERE " + " AND ".join(conditions)
    requete += " ORDER BY id"

    with acces_db(request) as conn:
        lignes = conn.execute(requete, valeurs).fetchall()

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [l["longitude"], l["latitude"]]},
                "properties": {
                    "id": l["id"],
                    "statut": l["statut"],
                    "legalite": l["legalite"],
                    "volume_estime": l["volume_estime"],
                    "nb_signalements": l["nb_signalements"],
                    "zone_id": l["zone_id"],
                    "derniere_maj": l["derniere_maj"],
                },
            }
            for l in lignes
        ],
    }
