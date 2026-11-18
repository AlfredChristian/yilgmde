"""Simulation d'un quartier (D62) : la matinée d'un secteur, rejouée à l'écran.

`GET /admin/simulation-quartier/secteurs` : secteurs du plan courant, avec leurs points.
`GET /admin/simulation-quartier?zone_id=…&point_id=…&graine=…` : emploi du temps de chaque acteur
dans un quartier, disque de `quartier.rayon_m` autour d'un point de regroupement du secteur
(par défaut le plus habité ; `simulation/quartier.py`). Le résultat est gardé en mémoire par plan, secteur et graine.
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend import plans
from backend.deps import acces_db
from backend.routes.terrain import _plan_courant
from backend.schemas import Role
from backend.securite import exiger_role
from simulation.batiments import batiments_dans_zone, batiments_de
from simulation.geometrie import distance_m, emprise, point_dans_geometrie
from simulation.quartier import cercle, fenetre, journee_quartier
from simulation.routes import reseau_de

router = APIRouter(tags=["quartier"])
admin = exiger_role(Role.admin)
_CACHE: OrderedDict = OrderedDict()
TAILLE_CACHE = 12


def _zones(conn) -> dict[int, dict]:
    return {z["id"]: z for z in plans.lire_donnees(conn)["zones"]}


@router.get("/admin/simulation-quartier/secteurs")
def secteurs(request: Request, _=Depends(admin)):
    plan = _plan_courant(request)
    par_zone: dict[int, int] = {}
    for pt in plan["points_regroupement"]:
        par_zone[pt.get("zone_id")] = par_zone.get(pt.get("zone_id"), 0) + 1
    with acces_db(request) as conn:
        zones = _zones(conn)
    sortie = [{"id": z, "nom": zones[z].get("nom"), "population": zones[z].get("population"), "points": n}
              for z, n in par_zone.items() if z in zones]
    return sorted(sortie, key=lambda z: -(z["population"] or 0))


@router.get("/admin/simulation-quartier")
def simulation_quartier(request: Request, zone_id: int = Query(...), point_id: int | None = Query(None),
                        graine: int = Query(1, ge=0, le=10_000), _=Depends(admin)):
    plan = _plan_courant(request)
    cle = (plan["id"], zone_id, point_id, graine)
    if cle in _CACHE:
        _CACHE.move_to_end(cle)
        return _CACHE[cle]
    config = request.app.state.config
    with acces_db(request) as conn:
        donnees = plans.lire_donnees(conn)
    zone = next((z for z in donnees["zones"] if z["id"] == zone_id), None)
    if zone is None:
        raise HTTPException(404, "secteur inconnu")
    pts = [pt for pt in plan["points_regroupement"] if pt.get("zone_id") == zone_id]
    if not pts:
        # Secteur sans point à lui : les points voisins à moins de 1,5 km de son centre.
        s, o, n, e = emprise(zone["geometrie"])
        c = ((s + n) / 2, (o + e) / 2)
        pts = sorted((pt for pt in plan["points_regroupement"]
                      if distance_m(c[0], c[1], pt["latitude"], pt["longitude"]) < 1500),
                     key=lambda pt: distance_m(c[0], c[1], pt["latitude"], pt["longitude"]))[:3]
    if not pts:
        raise HTTPException(409, "aucun point de regroupement dans ce secteur : élargissez le périmètre du plan")
    tous = batiments_de(config)
    batiments = batiments_dans_zone(tous, zone["geometrie"]) if tous is not None else np.empty((0, 3))
    rayon = float((config.get("quartier") or {}).get("rayon_m", 450))
    try:
        centre, sous, proches, part = fenetre(zone, batiments, pts, rayon, point_id)
    except ValueError as e:
        raise HTTPException(409 if point_id is None else 404, str(e))
    disque = cercle(centre["latitude"], centre["longitude"], rayon)
    quartier = {"id": zone["id"], "nom": zone.get("nom"), "geometrie": disque,
                "population": round(zone["population"] * part) if zone.get("population") else None}
    depotoirs = [d for d in donnees["depotoirs"] if d.get("legalite") == "illegal"
                 and distance_m(d["latitude"], d["longitude"], centre["latitude"], centre["longitude"]) <= rayon + 200]
    depot = config["collecte"].get("depot") or {"latitude": centre["latitude"], "longitude": centre["longitude"]}
    try:
        resultat = journee_quartier(quartier, sous, proches, depotoirs, (float(depot["latitude"]), float(depot["longitude"])),
                                    config, graine, reseau_de(config))
    except ValueError as e:
        raise HTTPException(409, str(e))
    resultat["secteur"] = {"id": zone["id"], "nom": zone.get("nom"), "population": zone.get("population"),
                           "geometrie": zone["geometrie"]}
    resultat["centre"] = {"point_id": centre["id"], "latitude": centre["latitude"], "longitude": centre["longitude"], "rayon_m": rayon}
    resultat["points_du_secteur"] = [{"id": pt["id"], "latitude": pt["latitude"], "longitude": pt["longitude"]} for pt in pts]
    _CACHE[cle] = resultat
    while len(_CACHE) > TAILLE_CACHE:
        _CACHE.popitem(last=False)
    return resultat
