"""Journée animée d'un secteur (D62) : ménages, précollecteurs, points de regroupement, camion.

`journee_quartier(...)` est une fonction pure (D09) : le hasard vient d'un `random.Random(graine)`
local, le réseau routier est passé en argument. Elle produit l'emploi du temps de chaque acteur,
minute par minute ; l'écran « Simulation d'un quartier » le rejoue.

Ce qui est réel : les maisons (bâtiments Open Buildings du secteur, D58), les points de
regroupement du plan, les dépotoirs connus, les rues (D52). Ce qui est simulé, avec les
mêmes règles que le simulateur multi-agents (simulation/agents.py) :

1. Le matin, chaque ménage sort sa poubelle devant chez lui.
2. Une part `population.taux_abonnement_precollecteurs` est abonnée : un précollecteur passe
   en tricycle, par les rues, de maison en maison, puis vide au point de regroupement.
3. Un non-abonné à moins de `points_regroupement.distance_max_a_pied_m` d'un point y porte
   lui-même ses déchets avec la probabilité `simulation.prob_apport_volontaire` (divisée par
   le coefficient de dépôts sauvages de la saison) ; sinon il les jette dans un dépôt sauvage :
   le dépotoir connu le plus proche, ou à défaut le terrain vague du secteur le plus éloigné
   des maisons.
4. Le camion de la mairie passe vider les points après le dernier apport.

Le navigateur ne peut pas animer des milliers de ménages : `quartier.maisons_affichees` maisons
sont tirées parmi les bâtiments, au prorata de leur surface, et chacune représente
`menages_par_maison` ménages pour les quantités.
"""

from __future__ import annotations

import math
import random

import numpy as np

from simulation.geometrie import distance_m, echantillonner, point_dans_geometrie

STATUTS_DEPOTOIR_ACTIF = ("actif", "intervention_planifiee")


def _parametres(config: dict) -> dict:
    q = config.get("quartier") or {}
    pop = config["population"]
    saison = config["saisons"][config["scenario"]["saison"]]
    s = config.get("simulation") or {}
    heures = lambda v: [float(x) * 60 for x in v]
    return {
        "maisons": int(q.get("maisons_affichees", 150)),
        "par_tricycle": max(1, int(q.get("maisons_par_tricycle", 20))),
        "v_tricycle": float(q.get("vitesse_tricycle_kmh", 8)) * 1000 / 60,      # m/min
        "v_pied": float(q.get("vitesse_a_pied_kmh", 4)) * 1000 / 60,
        "arret": float(q.get("arret_maison_min", 1.5)),
        "vidage": float(q.get("vidage_min", 6)),
        "sortie": heures(q.get("sortie_poubelles", [6.0, 7.5])),
        "depart_tricycles": float(q.get("depart_tricycles", 7.0)) * 60,
        "apports": heures(q.get("heures_apport", [6.5, 9.0])),
        "delai_camion": float(q.get("delai_camion_min", 30)),
        "approche_camion": float(q.get("approche_camion_m", 2500)),
        "taux_abonnement": float(pop["taux_abonnement_precollecteurs"]),
        "prob_apport": min(1.0, float(s.get("prob_apport_volontaire", 0.6)) / float(saison.get("coef_depots_sauvages", 1.0))),
        "distance_pied": float(config["points_regroupement"]["distance_max_a_pied_m"]),
        "habitants_par_menage": float(pop.get("habitants_par_menage", 6)),
        "kg_hab_jour": float(pop["production_dechets_kg_hab_jour"]) * float(saison.get("coef_production", 1.0)),
    }


def _plus_proche(lat, lon, sites):
    meilleur = min(range(len(sites)), key=lambda k: distance_m(lat, lon, sites[k]["latitude"], sites[k]["longitude"]))
    return meilleur, distance_m(lat, lon, sites[meilleur]["latitude"], sites[meilleur]["longitude"])


def _longueur(trace) -> float:
    return sum(distance_m(a[0], a[1], b[0], b[1]) for a, b in zip(trace, trace[1:]))


def _arrondir(trace, n=5):
    return [[round(p[0], n), round(p[1], n)] for p in trace]


def _fin_de_trace(trace, longueur_m):
    """Les `longueur_m` derniers mètres d'une polyligne."""
    reste, sortie = longueur_m, [trace[-1]]
    for a, b in zip(trace[::-1][1:], trace[::-1]):
        d = distance_m(a[0], a[1], b[0], b[1])
        if d >= reste:
            f = reste / d if d else 0
            sortie.append([b[0] + (a[0] - b[0]) * f, b[1] + (a[1] - b[1]) * f])
            break
        sortie.append(a)
        reste -= d
    return sortie[::-1]


def _terrain_vague(geometrie, maisons) -> tuple[float, float] | None:
    """Point du secteur le plus éloigné des maisons : là où s'installe un dépôt sauvage."""
    grille = echantillonner(geometrie, 60, 600)
    if not grille or not maisons:
        return grille[0] if grille else None
    return max(grille, key=lambda g: min(distance_m(g[0], g[1], m[0], m[1]) for m in maisons))


def cercle(lat: float, lon: float, rayon_m: float, n: int = 32) -> dict:
    """Polygone GeoJSON approchant un cercle (pour montrer le quartier simulé)."""
    dlat = rayon_m / 111_320.0
    dlon = rayon_m / (111_320.0 * math.cos(math.radians(lat)))
    anneau = [[round(lon + dlon * math.cos(2 * math.pi * k / n), 6), round(lat + dlat * math.sin(2 * math.pi * k / n), 6)]
              for k in range(n)]
    return {"type": "Polygon", "coordinates": [anneau + [anneau[0]]]}


def fenetre(zone: dict, batiments: np.ndarray, points: list[dict], rayon_m: float, centre_id=None):
    """Le quartier animé : un disque de `rayon_m` autour d'un point de regroupement du secteur.

    Par défaut, le point qui a le plus de surface bâtie autour de lui. Renvoie le point
    central, les bâtiments du disque, les points du disque (le central d'abord) et la part
    de la surface bâtie du secteur qu'il contient (pour la population).
    """
    if not points:
        raise ValueError("aucun point de regroupement pour ce secteur : calculez d'abord le plan")
    m_lat = 111_320.0
    def dans(b, pt):
        m_lon = m_lat * math.cos(math.radians(pt["latitude"]))
        return ((b[:, 0] - pt["latitude"]) * m_lat) ** 2 + ((b[:, 1] - pt["longitude"]) * m_lon) ** 2 <= rayon_m ** 2
    if centre_id is not None:
        centre = next((pt for pt in points if pt["id"] == centre_id), None)
        if centre is None:
            raise ValueError("point de regroupement inconnu dans ce secteur")
    elif len(batiments):
        centre = max(points, key=lambda pt: float(batiments[dans(batiments, pt), 2].sum()))
    else:
        centre = points[0]
    sous = batiments[dans(batiments, centre)] if len(batiments) else batiments
    proches = sorted((pt for pt in points
                      if distance_m(pt["latitude"], pt["longitude"], centre["latitude"], centre["longitude"]) <= rayon_m),
                     key=lambda pt: distance_m(pt["latitude"], pt["longitude"], centre["latitude"], centre["longitude"]))
    total = float(batiments[:, 2].sum()) if len(batiments) else 0.0
    part = float(sous[:, 2].sum()) / total if total else 1.0
    return centre, sous, proches, part


def journee_quartier(zone: dict, batiments: np.ndarray, points: list[dict], depotoirs: list[dict],
                     depot: tuple[float, float], config: dict, graine: int, reseau=None) -> dict:
    """Emploi du temps d'une matinée dans le secteur `zone` (voir le module).

    `batiments` : tableau (lat, lon, surface) des bâtiments du secteur. `points` : points de
    regroupement (id, latitude, longitude), ceux du secteur d'abord. `depotoirs` : dépotoirs
    illégaux connus du secteur. `reseau` : réseau routier (simulation.routes.Reseau) ou None
    (lignes droites).
    """
    p = _parametres(config)
    rng = random.Random(graine)
    if not points:
        raise ValueError("aucun point de regroupement pour ce secteur : calculez d'abord le plan")

    # 1. Maisons : tirées parmi les bâtiments, au prorata de la surface bâtie.
    if len(batiments):
        n = min(p["maisons"], len(batiments))
        poids = np.maximum(batiments[:, 2], 1.0)
        idx = np.random.default_rng(graine).choice(len(batiments), size=n, replace=False, p=poids / poids.sum())
        positions = [(float(batiments[i, 0]), float(batiments[i, 1])) for i in sorted(idx)]
    else:
        positions = echantillonner(zone["geometrie"], 80, p["maisons"])
    if not positions:
        raise ValueError("secteur sans maison ni surface exploitable")
    menages_total = max(1.0, float(zone.get("population") or 0) / p["habitants_par_menage"]) if zone.get("population") else len(positions)
    menages_par_maison = menages_total / len(positions)
    kg_par_maison = menages_par_maison * p["habitants_par_menage"] * p["kg_hab_jour"]

    # Dépôts sauvages : dépotoirs connus du secteur, sinon le terrain vague le plus isolé.
    sauvages = [
        {"id": f"d{d['id']}", "latitude": d["latitude"], "longitude": d["longitude"], "existant": True, "depotoir_id": d["id"]}
        for d in depotoirs if d.get("statut", "actif") in STATUTS_DEPOTOIR_ACTIF
    ]
    if not sauvages:
        vague = _terrain_vague(zone["geometrie"], positions)
        if vague:
            sauvages = [{"id": "v1", "latitude": vague[0], "longitude": vague[1], "existant": False, "depotoir_id": None}]

    # 2. Qui fait quoi : abonné, apport volontaire ou dépôt sauvage (mêmes règles que agents.py).
    maisons = []
    for k, (la, lo) in enumerate(positions):
        i_point, d_point = _plus_proche(la, lo, points)
        if rng.random() < p["taux_abonnement"]:
            mode = "abonne"
        elif d_point <= p["distance_pied"] and rng.random() < p["prob_apport"]:
            mode = "apport"
        else:
            mode = "sauvage" if sauvages else "apport"
        m = {"id": k + 1, "latitude": la, "longitude": lo, "mode": mode, "point": i_point,
             "sortie_min": round(rng.uniform(*p["sortie"]), 1)}
        if mode == "sauvage":
            m["sauvage"], _ = _plus_proche(la, lo, sauvages)
        maisons.append(m)

    # Trajets sur les rues : un seul calcul pour tous les sites (dépôt, points, sauvages, maisons).
    sites = [depot] + [(pt["latitude"], pt["longitude"]) for pt in points] \
        + [(s["latitude"], s["longitude"]) for s in sauvages] + positions
    i_point = lambda i: 1 + i
    i_sauvage = lambda i: 1 + len(points) + i
    i_maison = lambda m: 1 + len(points) + len(sauvages) + (m["id"] - 1)
    if reseau is not None:
        from simulation.routes import Itineraires

        itin = Itineraires(reseau, sites)
        trajet = lambda a, b: [list(x) for x in itin.trajet(a, b)]
    else:
        trajet = lambda a, b: [list(sites[a]), list(sites[b])]

    def deplacement(a, b, t0, vitesse):
        tr = trajet(a, b)
        duree = max(0.5, _longueur(tr) / vitesse)
        return {"t0": round(t0, 2), "t1": round(t0 + duree, 2), "trace": _arrondir(tr)}, t0 + duree

    def pause(site, t0, duree):
        return {"t0": round(t0, 2), "t1": round(t0 + duree, 2), "trace": _arrondir([sites[site]])}, t0 + duree

    # 3. Tricycles : abonnés d'un point, par plus proche voisin depuis le point, par tournées.
    tricycles, vidages = [], {i: [] for i in range(len(points))}
    for ip in range(len(points)):
        a_faire = [m for m in maisons if m["mode"] == "abonne" and m["point"] == ip]
        depart = (points[ip]["latitude"], points[ip]["longitude"])
        ordre, courant = [], depart
        while a_faire:
            m = min(a_faire, key=lambda x: distance_m(courant[0], courant[1], x["latitude"], x["longitude"]))
            a_faire.remove(m)
            ordre.append(m)
            courant = (m["latitude"], m["longitude"])
        for k in range(0, len(ordre), p["par_tricycle"]):
            groupe = ordre[k:k + p["par_tricycle"]]
            t = p["depart_tricycles"] + 4 * len([x for x in tricycles if x["point_id"] == points[ip]["id"]])
            segments, arrets, ici = [], [], i_point(ip)
            for m in groupe:
                seg, t = deplacement(ici, i_maison(m), t, p["v_tricycle"])
                segments.append(seg)
                attente = max(0.0, m["sortie_min"] - t)          # la poubelle n'est pas encore sortie
                seg, t = pause(i_maison(m), t, attente + p["arret"])
                segments.append(seg)
                m["collecte_min"] = round(t, 2)
                arrets.append({"maison_id": m["id"], "t": round(t, 2)})
                ici = i_maison(m)
            seg, t = deplacement(ici, i_point(ip), t, p["v_tricycle"])
            segments.append(seg)
            seg, t = pause(i_point(ip), t, p["vidage"])
            segments.append(seg)
            vidages[ip].append((t, len(groupe)))
            tricycles.append({"id": len(tricycles) + 1, "point_id": points[ip]["id"], "segments": segments,
                              "arrets": arrets, "vidage_min": round(t, 2), "poubelles": len(groupe)})

    # 4. Les autres portent eux-mêmes leurs déchets, au point ou au dépôt sauvage, puis rentrent.
    pietons, apports_sauvages = [], {i: [] for i in range(len(sauvages))}
    for m in maisons:
        if m["mode"] == "abonne":
            continue
        t0 = max(m["sortie_min"], rng.uniform(*p["apports"]))
        cible = i_point(m["point"]) if m["mode"] == "apport" else i_sauvage(m["sauvage"])
        aller, t = deplacement(i_maison(m), cible, t0, p["v_pied"])
        depose, t = pause(cible, t, 1.0)
        retour, t = deplacement(cible, i_maison(m), t, p["v_pied"])
        m["depart_min"] = round(t0, 2)
        m["depot_min"] = depose["t0"]
        if m["mode"] == "apport":
            vidages[m["point"]].append((depose["t0"], 1))
        else:
            apports_sauvages[m["sauvage"]].append(depose["t0"])
        pietons.append({"maison_id": m["id"], "mode": m["mode"], "segments": [aller, depose, retour]})

    # 5. Le camion vient vider chaque point après le dernier apport, puis repart.
    camions = []
    for ip, pt in enumerate(points):
        if not vidages[ip]:
            continue
        arrivee = max(t for t, _ in vidages[ip]) + p["delai_camion"]
        approche = _fin_de_trace(trajet(0, i_point(ip)), p["approche_camion"])
        duree = max(1.0, _longueur(approche) / (25 * 1000 / 60))           # 25 km/h dans le secteur [H]
        pt_vide = arrivee + p["vidage"]
        camions.append({
            "point_id": pt["id"], "vide_min": round(pt_vide, 2),
            "segments": [
                {"t0": round(arrivee - duree, 2), "t1": round(arrivee, 2), "trace": _arrondir(approche)},
                {"t0": round(arrivee, 2), "t1": round(pt_vide, 2), "trace": _arrondir([approche[-1]])},
                {"t0": round(pt_vide, 2), "t1": round(pt_vide + duree, 2), "trace": _arrondir(approche[::-1])},
            ],
        })
    vide = {c["point_id"]: c["vide_min"] for c in camions}

    compte = {mode: sum(1 for m in maisons if m["mode"] == mode) for mode in ("abonne", "apport", "sauvage")}
    fin = max([s["t1"] for x in tricycles + pietons + camions for s in x["segments"]] + [p["sortie"][1]])
    return {
        "zone": {"id": zone["id"], "nom": zone.get("nom"), "population": zone.get("population"), "geometrie": zone["geometrie"]},
        "graine": graine,
        "horaire": {"debut": math.floor(p["sortie"][0] - 15), "fin": math.ceil(fin + 10)},
        "echelle": {"maisons": len(maisons), "batiments_du_quartier": int(len(batiments)),
                    "menages_par_maison": round(menages_par_maison, 1), "kg_par_maison": round(kg_par_maison, 1)},
        "regles": {"taux_abonnement": p["taux_abonnement"], "prob_apport": round(p["prob_apport"], 3),
                   "distance_max_a_pied_m": p["distance_pied"], "sur_les_voies": reseau is not None},
        "maisons": [{k: v for k, v in m.items() if k not in ("point", "sauvage")}
                    | {"point_id": points[m["point"]]["id"]}
                    | ({"sauvage_id": sauvages[m["sauvage"]]["id"]} if m["mode"] == "sauvage" else {})
                    for m in maisons],
        "points": [{"id": pt["id"], "latitude": pt["latitude"], "longitude": pt["longitude"], "vide_min": vide.get(pt["id"]),
                    "dans_le_secteur": point_dans_geometrie(pt["latitude"], pt["longitude"], zone["geometrie"])}
                   for pt in points],
        "sauvages": [{k: s[k] for k in ("id", "latitude", "longitude", "existant", "depotoir_id")} for s in sauvages],
        "tricycles": tricycles,
        "pietons": pietons,
        "camions": camions,
        "resume": {
            "abonnes": compte["abonne"], "apport_volontaire": compte["apport"], "depot_sauvage": compte["sauvage"],
            "kg_precollectes": round(compte["abonne"] * kg_par_maison), "kg_apportes": round(compte["apport"] * kg_par_maison),
            "kg_sauvages": round(compte["sauvage"] * kg_par_maison), "tricycles": len(tricycles),
        },
    }
