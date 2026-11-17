"""G1 — Export des dépotoirs vérifiés pour OpenStreetMap (admin)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from backend import db
from backend.deps import acces_db
from backend.export_osm import STATUTS_TERRAIN, exporter_depotoirs
from backend.schemas import Role, StatutDepotoir
from backend.securite import exiger_role
from backend.utilisateurs import journaliser

router = APIRouter(tags=["export"])


@router.get("/admin/export/depotoirs.geojson")
def export_depotoirs(
    request: Request,
    statut: list[StatutDepotoir] | None = Query(None, description="par défaut : actif, intervention_planifiee"),
    utilisateur=Depends(exiger_role(Role.admin)),
):
    """GeoJSON téléchargeable ; propriétés = étiquettes OSM seulement, aucune donnée personnelle."""
    statuts = tuple(s.value for s in statut) if statut else STATUTS_TERRAIN
    with acces_db(request) as conn:
        contenu = exporter_depotoirs(conn, request.app.state.config, statuts)
        with db.transaction(conn):
            journaliser(conn, utilisateur["id"], "export_osm", "depotoir", None)
    return JSONResponse(
        contenu,
        media_type="application/geo+json",
        headers={"Content-Disposition": 'attachment; filename="depotoirs_yilgmde.geojson"'},
    )
