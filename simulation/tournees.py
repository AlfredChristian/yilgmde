"""C3 — Tournées de collecte (et moteur commun réutilisé par C7, tournées Laabal).

Fonction pure (D09) : `planifier_tournees(points, config)` ne lit ni la base ni
l'horloge. Résultat reproductible : OR-Tools est lancé **sans métaheuristique
dépendante du temps** (recherche locale par descente, déterministe) ; le temps
limite `collecte.temps_calcul_max_s` n'est qu'une sécurité (contrainte 3).
Si OR-Tools ne trouve rien (ou n'est pas installé), repli sur l'heuristique du
plus proche voisin, toujours disponible.

Modèle [H] :
- tous les camions partent du dépôt `collecte.depot` et y reviennent (vidage) ;
- un camion indisponible n'est **jamais** utilisé (règle 4) ;
- chaque camion fait au plus `collecte.rotations_max_par_jour` rotations, chacune
  limitée par sa capacité et par `duree_max_tournee_min / rotations` ;
- à chaque passage, un point contient le stock accumulé depuis le passage
  précédent (`stock_entre_passages_kg`, C2) ; s'il est inconnu (point hors zone),
  on suppose le point plein (`capacite_kg`) ;
- distance routière = vol d'oiseau × `collecte.coef_detour` ; vitesse =
  `vitesse_moyenne_kmh × coef_vitesse_camion(saison)` ; `temps_arret_min` par arrêt ;
- coût = `cout_km_xof × km + cout_jour_xof` par camion utilisé dans la journée.

Les points qu'aucune tournée ne peut prendre vont dans `non_couverts` avec leur raison.
"""

from __future__ import annotations

import math
from typing import Sequence

from simulation.geometrie import distance_m

try:   # OR-Tools est une dépendance (D08), mais le repli doit marcher sans lui.
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
except ImportError:   # pragma: no cover - dépend de l'environnement
    pywrapcp = None

PENALITE_ABANDON = 10_000_000   # coût d'un arrêt non desservi : on ne l'abandonne que si c'est impossible


# --- Données d'entrée ----------------------------------------------------------------

def vitesse_m_par_min(config: dict) -> float:
    saison = config["saisons"][config["scenario"]["saison"]]
    kmh = config["collecte"]["vitesse_moyenne_kmh"] * saison.get("coef_vitesse_camion", 1.0)
    if kmh <= 0:
        raise ValueError("vitesse de collecte nulle ou négative")
    return kmh * 1000 / 60


def matrice_distances_m(sites: Sequence[tuple[float, float]], coef_detour: float) -> list[list[int]]:
    """Distances routières estimées (m, entiers pour OR-Tools)."""
    return [
        [int(round(distance_m(a[0], a[1], b[0], b[1]) * coef_detour)) for b in sites]
        for a in sites
    ]


def _depot(config: dict) -> tuple[float, float]:
    depot = config["collecte"].get("depot")
    if not depot:
        raise ValueError("collecte.depot manquant dans la config (latitude, longitude du dépôt)")
    return float(depot["latitude"]), float(depot["longitude"])


# --- Résolution ------------------------------------------------------------------------

def _resoudre_ortools(dist, demandes, temps_service, vehicules, vitesse, temps_max_s):
    """Renvoie une liste d'itinéraires (indices de sites, sans le dépôt 0) par véhicule, ou None."""
    if pywrapcp is None:
        return None
    n = len(dist)
    manager = pywrapcp.RoutingIndexManager(n, len(vehicules), 0)
    routing = pywrapcp.RoutingModel(manager)

    def cb_distance(i, j):
        return dist[manager.IndexToNode(i)][manager.IndexToNode(j)]

    def cb_demande(i):
        return demandes[manager.IndexToNode(i)]

    def cb_temps(i, j):
        a, b = manager.IndexToNode(i), manager.IndexToNode(j)
        return int(math.ceil(dist[a][b] / vitesse + temps_service[a]))

    t_dist = routing.RegisterTransitCallback(cb_distance)
    routing.SetArcCostEvaluatorOfAllVehicles(t_dist)
    for v, veh in enumerate(vehicules):
        routing.SetFixedCostOfVehicle(int(veh["cout_fixe"]), v)

    t_dem = routing.RegisterUnaryTransitCallback(cb_demande)
    routing.AddDimensionWithVehicleCapacity(t_dem, 0, [int(v["capacite"]) for v in vehicules], True, "charge")
    t_tps = routing.RegisterTransitCallback(cb_temps)
    routing.AddDimensionWithVehicleCapacity(t_tps, 0, [int(v["duree_max"]) for v in vehicules], True, "temps")

    for noeud in range(1, n):
        routing.AddDisjunction([manager.NodeToIndex(noeud)], PENALITE_ABANDON)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GREEDY_DESCENT
    params.time_limit.FromMilliseconds(int(temps_max_s * 1000))
    solution = routing.SolveWithParameters(params)
    if solution is None:
        return None

    itineraires = []
    for v in range(len(vehicules)):
        index = routing.Start(v)
        route = []
        while not routing.IsEnd(index):
            noeud = manager.IndexToNode(index)
            if noeud != 0:
                route.append(noeud)
            index = solution.Value(routing.NextVar(index))
        itineraires.append(route)
    return itineraires


def _resoudre_plus_proche_voisin(dist, demandes, temps_service, vehicules, vitesse):
    """Repli glouton : chaque véhicule va au site faisable le plus proche, puis rentre."""
    restants = set(range(1, len(dist)))
    itineraires = []
    for veh in vehicules:
        route, charge, temps, ici = [], 0, 0.0, 0
        while True:
            faisables = [
                j for j in restants
                if charge + demandes[j] <= veh["capacite"]
                and temps + (dist[ici][j] + dist[j][0]) / vitesse + temps_service[j] <= veh["duree_max"]
            ]
            if not faisables:
                break
            j = min(faisables, key=lambda k: (dist[ici][k], k))
            temps += dist[ici][j] / vitesse + temps_service[j]
            charge += demandes[j]
            route.append(j)
            restants.discard(j)
            ici = j
        itineraires.append(route)
    return itineraires


def resoudre(sites, demandes_kg, temps_service_min, vehicules, config, temps_max_s):
    """Moteur commun C3 / C7.

    - `sites` : [(lat, lon)], l'indice 0 est le dépôt ;
    - `demandes_kg` / `temps_service_min` : par site (0 pour le dépôt) ;
    - `vehicules` : dicts `capacite`, `duree_max` (min), `cout_fixe`.
    Renvoie `(itineraires, methode, matrice)` ; `methode` vaut `ortools` ou `plus_proche_voisin`.
    """
    coef = float(config["collecte"].get("coef_detour", 1.0))
    vitesse = vitesse_m_par_min(config)
    dist = matrice_distances_m(sites, coef)
    demandes = [int(math.ceil(d)) for d in demandes_kg]
    service = [float(t) for t in temps_service_min]
    vehs = [dict(v, capacite=int(v["capacite"]), duree_max=int(v["duree_max"])) for v in vehicules]
    if not vehs or len(sites) <= 1:
        return [[] for _ in vehs], "aucune", dist
    itineraires = _resoudre_ortools(dist, demandes, service, vehs, vitesse, temps_max_s)
    if itineraires is not None:
        return itineraires, "ortools", dist
    return _resoudre_plus_proche_voisin(dist, demandes, service, vehs, vitesse), "plus_proche_voisin", dist


def mesurer(route: Sequence[int], dist, temps_service, vitesse) -> tuple[float, float]:
    """(distance_km, duree_min) d'un itinéraire dépôt → sites → dépôt."""
    if not route:
        return 0.0, 0.0
    chemin = [0, *route, 0]
    metres = sum(dist[a][b] for a, b in zip(chemin, chemin[1:]))
    minutes = metres / vitesse + sum(temps_service[i] for i in route)
    return metres / 1000, minutes


# --- C3 --------------------------------------------------------------------------------

def planifier_tournees(points: Sequence[dict], config: dict, methode: str = "auto") -> dict:
    """Tournées de collecte des points de regroupement pour un passage.

    `points` : sortie de C2 (`id`, `latitude`, `longitude`, `capacite_kg`,
    `stock_entre_passages_kg`). `methode` : `auto` (OR-Tools puis repli) ou
    `plus_proche_voisin` (forcer le repli, utile pour comparer et tester).
    Renvoie `{"tournees": [...], "non_couverts": [...], "methode": str}`.
    """
    collecte = config["collecte"]
    rotations = max(1, int(collecte.get("rotations_max_par_jour", 1)))
    duree_jour = float(collecte.get("duree_max_tournee_min", 480))
    temps_arret = float(collecte.get("temps_arret_min", 10))
    temps_max_s = float(collecte.get("temps_calcul_max_s", 5))

    camions_hs = [c["id"] for c in config.get("camions", []) if not c.get("disponible", True)]
    camions = [c for c in config.get("camions", []) if c.get("disponible", True)]   # règle 4
    vehicules = []
    for c in camions:
        for r in range(1, rotations + 1):
            vehicules.append(
                {
                    "camion": c, "rotation": r, "capacite": c["capacite_kg"],
                    "duree_max": duree_jour / rotations,
                    # le coût journalier n'est payé qu'une fois : porté par la 1re rotation
                    "cout_fixe": c.get("cout_jour_xof", 0) if r == 1 else 0,
                }
            )

    sites = [_depot(config)] + [(p["latitude"], p["longitude"]) for p in points]
    demandes = [0.0] + [
        p["stock_entre_passages_kg"] if p.get("stock_entre_passages_kg") is not None else p["capacite_kg"]
        for p in points
    ]
    service = [0.0] + [temps_arret] * len(points)

    if methode == "plus_proche_voisin":
        coef = float(collecte.get("coef_detour", 1.0))
        dist = matrice_distances_m(sites, coef)
        vit = vitesse_m_par_min(config)
        vehs = [dict(v, capacite=int(v["capacite"]), duree_max=int(v["duree_max"])) for v in vehicules]
        itineraires = _resoudre_plus_proche_voisin(dist, [int(math.ceil(d)) for d in demandes], service, vehs, vit)
        utilisee = "plus_proche_voisin"
    elif methode == "auto":
        itineraires, utilisee, dist = resoudre(sites, demandes, service, vehicules, config, temps_max_s)
    else:
        raise ValueError(f"méthode inconnue : {methode!r}")
    vitesse = vitesse_m_par_min(config)

    tournees, desservis = [], set()
    for veh, route in zip(vehicules, itineraires):
        if not route:
            continue
        km, minutes = mesurer(route, dist, service, vitesse)
        c = veh["camion"]
        tournees.append(
            {
                "type": "collecte",
                "camion_id": c["id"],
                "rotation": veh["rotation"],
                "distance_km": round(km, 2),
                "duree_min": round(minutes, 1),
                "charge_kg": round(sum(demandes[i] for i in route), 1),
                "cout_xof": round(km * c.get("cout_km_xof", 0)),   # coût fixe ajouté plus bas
                "arrets": [
                    {
                        "ordre": k,
                        "cible_type": "point_regroupement",
                        "cible_id": points[i - 1]["id"],
                        "latitude": points[i - 1]["latitude"],
                        "longitude": points[i - 1]["longitude"],
                        "charge_kg": round(demandes[i], 1),
                        "statut": "a_faire",
                    }
                    for k, i in enumerate(route, start=1)
                ],
            }
        )
        desservis.update(route)

    # Coût journalier : une fois par camion réellement utilisé, sur sa première tournée.
    vus = set()
    for t in tournees:
        if t["camion_id"] not in vus:
            vus.add(t["camion_id"])
            t["cout_xof"] += round(next(c for c in camions if c["id"] == t["camion_id"]).get("cout_jour_xof", 0))
    for i, t in enumerate(tournees, start=1):
        t["id"] = i

    non_couverts = []
    raison_hs = f" ({', '.join(camions_hs)} indisponible{'s' if len(camions_hs) > 1 else ''})" if camions_hs else ""
    capacite_max = max((c["capacite_kg"] for c in camions), default=0)
    for i, p in enumerate(points, start=1):
        if i in desservis:
            continue
        if not camions:
            raison = "aucun camion disponible" + raison_hs
        elif demandes[i] > capacite_max:
            raison = f"stock ({demandes[i]:.0f} kg) supérieur à la capacité d'un camion ({capacite_max} kg)"
        else:
            raison = "capacité ou temps de collecte insuffisants" + raison_hs
        non_couverts.append({"point_regroupement_id": p["id"], "raison": raison})

    return {"tournees": tournees, "non_couverts": non_couverts, "methode": utilisee}
