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
- un passage s'étale sur `jours_par_passage` jours (`jours_ouvres_par_semaine /
  frequence_passages_par_semaine`, D39) ; chaque jour, chaque camion fait au plus
  `collecte.rotations_max_par_jour` rotations, chacune limitée par sa capacité et par
  `duree_max_tournee_min / rotations` ;
- à chaque passage, un point contient le stock accumulé depuis le passage
  précédent (`stock_entre_passages_kg`, C2) ; s'il est inconnu (point hors zone),
  on suppose le point plein (`capacite_kg`) ;
- distance routière : sur le réseau OSM si `collecte.reseau_routier` (D52, `simulation/routes.py`),
  sinon vol d'oiseau × `collecte.coef_detour` ; vitesse =
  `vitesse_moyenne_kmh × coef_vitesse_camion(saison)` ; `temps_arret_min` par arrêt ;
- coût = `cout_km_xof × km + cout_jour_xof` par camion et par jour travaillé.

Les points qu'aucune tournée ne peut prendre vont dans `non_couverts` avec leur raison.
"""

from __future__ import annotations

import math
from typing import Sequence

from simulation.geometrie import distance_m
from simulation.routes import Itineraires, reseau_de

try:   # OR-Tools est une dépendance (D08), mais le repli doit marcher sans lui.
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
except ImportError:   # pragma: no cover - dépend de l'environnement
    pywrapcp = None

PENALITE_ABANDON = 10_000_000   # coût d'un arrêt non desservi : on ne l'abandonne que si c'est impossible


# --- Données d'entrée ----------------------------------------------------------------

def _repartir_sur_les_jours(tournees: list[dict], camions: list[dict], jours: int) -> None:
    """Étale les journées de travail sur les jours du passage pour mobiliser le moins de camions (D43).

    Le solveur traite les véhicules (camion, jour) comme interchangeables : il peut tout mettre
    le même jour et mobiliser 39 camions là où 13 suffisent sur 3 jours. Une journée (toutes
    les rotations d'un camion un jour donné) peut passer à un autre camion identique (mêmes
    capacité, coûts, vitesse) ou à un autre jour sans changer ni distance ni coût. On remplit
    donc chaque camion jour après jour avant d'en prendre un nouveau. Modifie `tournees` sur place.
    """
    if jours <= 1:
        return
    par_id = {c["id"]: c for c in camions}

    def modele(c):
        return tuple(sorted((k, repr(v)) for k, v in c.items() if k not in ("id", "nom", "disponible")))

    groupes: dict[tuple, list[str]] = {}
    for c in camions:
        groupes.setdefault(modele(c), []).append(c["id"])
    journees: dict[tuple, list[tuple[str, int]]] = {}
    for t in tournees:
        cle = (t["camion_id"], t["jour"])
        journees.setdefault(modele(par_id[t["camion_id"]]), [])
        if cle not in journees[modele(par_id[t["camion_id"]])]:
            journees[modele(par_id[t["camion_id"]])].append(cle)
    nouvelle = {}
    for m, liste in journees.items():
        ids = groupes[m]
        for k, cle in enumerate(sorted(liste, key=lambda j: (ids.index(j[0]), j[1]))):
            nouvelle[cle] = (ids[k // jours], k % jours + 1)
    for t in tournees:
        t["camion_id"], t["jour"] = nouvelle[(t["camion_id"], t["jour"])]
    tournees.sort(key=lambda t: (t["jour"], t["camion_id"], t["rotation"]))


def jours_par_passage(config: dict) -> int:
    """Jours dont disposent les camions pour faire le tour des points entre deux passages.

    `jours_ouvres_par_semaine / frequence_passages_par_semaine`, arrondi à l'inférieur, au moins 1 :
    collecte 2 fois par semaine et 6 jours ouvrés = 3 jours (lundi à mercredi, jeudi à samedi).
    Sans `jours_ouvres_par_semaine`, un passage se fait en une journée.
    """
    c = config["collecte"]
    ouvres = c.get("jours_ouvres_par_semaine")
    if not ouvres:
        return 1
    return max(1, int(float(ouvres) // float(c["frequence_passages_par_semaine"])))


def vitesse_m_par_min(config: dict) -> float:
    saison = config["saisons"][config["scenario"]["saison"]]
    kmh = config["collecte"]["vitesse_moyenne_kmh"] * saison.get("coef_vitesse_camion", 1.0)
    if kmh <= 0:
        raise ValueError("vitesse de collecte nulle ou négative")
    return kmh * 1000 / 60


def matrice_distances_m(sites: Sequence[tuple[float, float]], coef_detour: float) -> list[list[int]]:
    """Distances routières estimées (m, entiers pour OR-Tools) : ligne droite × coef_detour."""
    return [
        [int(round(distance_m(a[0], a[1], b[0], b[1]) * coef_detour)) for b in sites]
        for a in sites
    ]


def distances(sites: Sequence[tuple[float, float]], config: dict):
    """(matrice en m, itinéraires ou None). Sur le réseau routier si `collecte.reseau_routier`
    est configuré (D52), sinon ligne droite × `coef_detour`."""
    reseau = reseau_de(config, len(sites))
    if reseau is not None:
        itin = Itineraires(reseau, sites)
        return itin.matrice_entiers(), itin
    return matrice_distances_m(sites, float(config["collecte"].get("coef_detour", 1.0))), None


def _depot(config: dict) -> tuple[float, float]:
    depot = config["collecte"].get("depot")
    if not depot:
        raise ValueError("collecte.depot manquant dans la config (latitude, longitude du dépôt)")
    return float(depot["latitude"]), float(depot["longitude"])


# --- Résolution ------------------------------------------------------------------------

def _resoudre_ortools(dist, demandes, temps_service, vehicules, vitesse, temps_max_s, recherche_locale=True):
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
    if not recherche_locale:
        # Grandes instances : la solution de départ seule (≈ 0,1 s pour 350 arrêts, ~6 % plus longue)
        # plutôt qu'une recherche arrêtée par le chronomètre, qui dépendrait de la machine (D09, D38).
        params.solution_limit = 1
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


def resoudre(sites, demandes_kg, temps_service_min, vehicules, config, temps_max_s, matrice=None):
    """Moteur commun C3 / C7.

    - `sites` : [(lat, lon)], l'indice 0 est le dépôt ;
    - `demandes_kg` / `temps_service_min` : par site (0 pour le dépôt) ;
    - `vehicules` : dicts `capacite`, `duree_max` (min), `cout_fixe`.
    Renvoie `(itineraires, methode, matrice)` ; `methode` vaut `ortools` ou `plus_proche_voisin`.
    """
    vitesse = vitesse_m_par_min(config)
    dist = matrice if matrice is not None else matrice_distances_m(sites, float(config["collecte"].get("coef_detour", 1.0)))
    demandes = [int(math.ceil(d)) for d in demandes_kg]
    service = [float(t) for t in temps_service_min]
    vehs = [dict(v, capacite=int(v["capacite"]), duree_max=int(v["duree_max"])) for v in vehicules]
    if not vehs or len(sites) <= 1:
        return [[] for _ in vehs], "aucune", dist
    seuil = int(config["collecte"].get("max_arrets_recherche_locale", 150))
    locale = len(sites) - 1 <= seuil
    itineraires = _resoudre_ortools(dist, demandes, service, vehs, vitesse, temps_max_s, recherche_locale=locale)
    if itineraires is not None:
        return itineraires, "ortools" if locale else "ortools_rapide", dist
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

    jours = jours_par_passage(config)
    camions_hs = [c["id"] for c in config.get("camions", []) if not c.get("disponible", True)]
    camions = [c for c in config.get("camions", []) if c.get("disponible", True)]   # règle 4
    vehicules = []
    for jour in range(1, jours + 1):
        for c in camions:
            for r in range(1, rotations + 1):
                vehicules.append(
                    {
                        "camion": c, "jour": jour, "rotation": r, "capacite": c["capacite_kg"],
                        "duree_max": duree_jour / rotations,
                        # le coût journalier n'est payé qu'une fois par jour : porté par la 1re rotation
                        "cout_fixe": c.get("cout_jour_xof", 0) if r == 1 else 0,
                    }
                )

    sites = [_depot(config)] + [(p["latitude"], p["longitude"]) for p in points]
    demandes = [0.0] + [
        p["stock_entre_passages_kg"] if p.get("stock_entre_passages_kg") is not None else p["capacite_kg"]
        for p in points
    ]
    service = [0.0] + [temps_arret] * len(points)

    dist, itin = distances(sites, config)
    if methode == "plus_proche_voisin":
        vit = vitesse_m_par_min(config)
        vehs = [dict(v, capacite=int(v["capacite"]), duree_max=int(v["duree_max"])) for v in vehicules]
        itineraires = _resoudre_plus_proche_voisin(dist, [int(math.ceil(d)) for d in demandes], service, vehs, vit)
        utilisee = "plus_proche_voisin"
    elif methode == "auto":
        itineraires, utilisee, dist = resoudre(sites, demandes, service, vehicules, config, temps_max_s, matrice=dist)
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
                "jour": veh["jour"],
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
                # D52 : un tronçon par trajet (dépôt → arrêt 1, …, dernier arrêt → dépôt) qui suit les voies.
                **({"trace": itin.trace_tournee(route)} if itin is not None else {}),
            }
        )
        desservis.update(route)

    _repartir_sur_les_jours(tournees, camions, jours)

    # Coût journalier : une fois par camion et par jour réellement travaillé, sur sa première tournée du jour.
    vus = set()
    for t in tournees:
        if (t["camion_id"], t["jour"]) not in vus:
            vus.add((t["camion_id"], t["jour"]))
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


# --- C7 : tournées d'intervention Laabal ----------------------------------------------

STATUTS_A_TRAITER = ("actif", "intervention_planifiee")


def priorite_depotoir(depotoir: dict, config: dict) -> tuple[float, str]:
    """Score de priorité d'un dépotoir illégal et sa raison lisible.

    score = poids_volume[volume] + poids_reapparition × nb_reapparitions
            + poids_signalement × nb_signalements      (poids [H] dans `laabal.priorite`)
    """
    p = config["laabal"].get("priorite", {})
    volume = depotoir.get("volume_estime") or "moyen"
    reap = int(depotoir.get("nb_reapparitions") or 0)
    sig = int(depotoir.get("nb_signalements") or 0)
    score = (
        float(p.get("poids_volume", {}).get(volume, 1))
        + float(p.get("poids_reapparition", 0)) * reap
        + float(p.get("poids_signalement", 0)) * sig
    )
    morceaux = [f"volume {volume}"]
    if reap:
        morceaux.append(f"{reap} réapparition(s)")
    if sig:
        morceaux.append(f"{sig} signalement(s)")
    return round(score, 2), ", ".join(morceaux)


def depotoirs_a_traiter(depotoirs: Sequence[dict], config: dict) -> list[dict]:
    """Dépotoirs illégaux actifs, triés par priorité décroissante (puis id) avec leur raison."""
    resultat = []
    for d in depotoirs:
        if d.get("legalite", "illegal") != "illegal" or d.get("statut", "actif") not in STATUTS_A_TRAITER:
            continue
        score, raison = priorite_depotoir(d, config)
        resultat.append(dict(d, priorite=score, raison=raison))
    return sorted(resultat, key=lambda d: (-d["priorite"], d["id"]))


def planifier_interventions(depotoirs: Sequence[dict], config: dict) -> dict:
    """Tournées du jour des brigades Laabal sur les dépotoirs illégaux.

    Les `nombre_brigades × capacite_eradication_par_jour` dépotoirs les plus
    prioritaires sont répartis entre les brigades, l'ordre de visite est optimisé
    (même moteur que C3). Les autres restent `en_attente`, avec leur rang.
    Renvoie `{"tournees": [...], "en_attente": [...], "methode": str}`.
    """
    laabal = config["laabal"]
    brigades = max(0, int(laabal.get("nombre_brigades", 0)))
    par_jour = max(0, int(laabal.get("capacite_eradication_par_jour", 0)))
    base = laabal.get("base") or config["collecte"].get("depot")
    if not base:
        raise ValueError("laabal.base ou collecte.depot manquant dans la config")
    temps_intervention = float(laabal.get("temps_intervention_min", 60))
    duree = float(laabal.get("duree_max_tournee_min", config["collecte"].get("duree_max_tournee_min", 480)))

    a_traiter = depotoirs_a_traiter(depotoirs, config)
    retenus = a_traiter[: brigades * par_jour]
    en_attente = [
        {"depotoir_id": d["id"], "priorite": d["priorite"], "raison": d["raison"],
         "motif": f"capacité Laabal atteinte ({brigades} brigade(s) × {par_jour} dépotoir(s)/jour)"}
        for d in a_traiter[len(retenus):]
    ]

    vehicules = [{"capacite": par_jour, "duree_max": duree, "cout_fixe": 0} for _ in range(brigades)]
    sites = [(float(base["latitude"]), float(base["longitude"]))] + [(d["latitude"], d["longitude"]) for d in retenus]
    demandes = [0] + [1] * len(retenus)
    service = [0.0] + [temps_intervention] * len(retenus)
    dist, itin = distances(sites, config)
    itineraires, methode, dist = resoudre(
        sites, demandes, service, vehicules, config, float(config["collecte"].get("temps_calcul_max_s", 5)), matrice=dist
    )
    vitesse = vitesse_m_par_min(config)

    tournees, faits = [], set()
    for b, route in enumerate(itineraires, start=1):
        if not route:
            continue
        km, minutes = mesurer(route, dist, service, vitesse)
        tournees.append(
            {
                "type": "intervention",
                "camion_id": None,
                "brigade": b,
                "distance_km": round(km, 2),
                "duree_min": round(minutes, 1),
                "cout_xof": 0,
                "arrets": [
                    {
                        "ordre": k,
                        "cible_type": "depotoir",
                        "cible_id": retenus[i - 1]["id"],
                        "latitude": retenus[i - 1]["latitude"],
                        "longitude": retenus[i - 1]["longitude"],
                        "priorite": retenus[i - 1]["priorite"],
                        "raison": retenus[i - 1]["raison"],
                        "statut": "a_faire",
                    }
                    for k, i in enumerate(route, start=1)
                ],
                **({"trace": itin.trace_tournee(route)} if itin is not None else {}),
            }
        )
        faits.update(route)
    for i, d in enumerate(retenus, start=1):   # retenu mais hors de portée dans la journée
        if i not in faits:
            en_attente.append({"depotoir_id": d["id"], "priorite": d["priorite"], "raison": d["raison"],
                               "motif": "trop loin pour la durée d'une tournée"})
    en_attente.sort(key=lambda x: (-x["priorite"], x["depotoir_id"]))
    return {"tournees": tournees, "en_attente": en_attente, "methode": methode}
