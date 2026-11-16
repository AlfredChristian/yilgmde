"""C2 — Placement des points de regroupement.

Fonction pure (D09) : `placer_points(depotoirs_actifs, zones, config)` ne lit ni la
base ni l'horloge et ne modifie pas ses arguments ; même entrée = même sortie
(k-means avec `scenario.graine_aleatoire`). Aucun paramètre en dur (D10).

Méthode, zone par zone (les zones ne se chevauchent pas, D23) :

1. **Combien de points ?** Le plus grand de deux besoins :
   - capacité : les déchets produits entre deux passages du camion
     (`demande_kg_jour × 7 / frequence_passages_par_semaine`) doivent tenir dans
     les points (`points_regroupement.capacite_kg` chacun) ;
   - marche : chaque point dessert un disque de rayon `distance_max_a_pied_m` ;
     il en faut au moins `aire de la zone / (π r²)`.
2. **Où ?** k-means (scikit-learn, D08) sur une grille d'échantillons de la zone,
   où les ménages sont supposés répartis uniformément [H], plus les dépotoirs
   actifs de la zone avec un poids `poids_depotoir` [H] : un dépotoir montre où les
   déchets s'accumulent faute de solution proche. Chaque centre est recalé sur
   l'échantillon le plus proche, donc **toujours dans la zone**.
3. **Couverture** : si moins de `couverture_cible` des échantillons sont à moins de
   `distance_max_a_pied_m` d'un point, on ajoute des points (jusqu'à
   `max_points_par_zone`). Ce qui reste hors de portée est signalé.

Les dépotoirs actifs hors de toute zone connue reçoivent quand même un point
(regroupement glouton par distance à pied) : sans population connue, leur charge
n'est pas estimée et c'est dit dans l'explication.

Chaque point porte une `explication` lisible (C5) ; les zones sans point ou mal
desservies sont listées dans `non_couverts` avec leur raison.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from sklearn.cluster import KMeans

from simulation.demande import estimer_demande
from simulation.geometrie import aire_m2, depuis_metres, distance_m, echantillonner, vers_metres


def jours_entre_passages(config: dict) -> float:
    frequence = config["collecte"]["frequence_passages_par_semaine"]
    if frequence <= 0:
        raise ValueError("collecte.frequence_passages_par_semaine doit être > 0")
    return 7.0 / frequence


def _parametres(config: dict) -> dict:
    p = config["points_regroupement"]
    return {
        "capacite_kg": float(p["capacite_kg"]),
        "distance_m": float(p["distance_max_a_pied_m"]),
        "pas_m": float(p.get("pas_echantillonnage_m", 100)),
        "max_echantillons": int(p.get("max_echantillons_par_zone", 2000)),
        "poids_depotoir": float(p.get("poids_depotoir", 5)),
        "couverture_cible": float(p.get("couverture_cible", 0.95)),
        "max_points": int(p.get("max_points_par_zone", 60)),
        "graine": int(config.get("scenario", {}).get("graine_aleatoire", 0)),
        "jours": jours_entre_passages(config),
    }


def _kmeans(xy: np.ndarray, poids: np.ndarray, k: int, graine: int) -> np.ndarray:
    """Centres (en mètres) de k groupes ; k est borné par le nombre de points distincts."""
    k = max(1, min(k, len(np.unique(xy, axis=0))))
    if k == 1:
        return (xy * poids[:, None]).sum(axis=0, keepdims=True) / poids.sum()
    modele = KMeans(n_clusters=k, n_init=4, random_state=graine)
    modele.fit(xy, sample_weight=poids)
    return modele.cluster_centers_


def _recaler(centres: np.ndarray, candidats: np.ndarray) -> np.ndarray:
    """Indices des candidats les plus proches de chaque centre, sans doublon."""
    choisis: list[int] = []
    for c in centres:
        ordre = np.argsort(((candidats - c) ** 2).sum(axis=1))
        for i in ordre:
            if int(i) not in choisis:
                choisis.append(int(i))
                break
    return np.array(choisis, dtype=int)


def _plus_proche(xy: np.ndarray, sites: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pour chaque point : indice du site le plus proche et distance en mètres."""
    d2 = ((xy[:, None, :] - sites[None, :, :]) ** 2).sum(axis=2)
    idx = d2.argmin(axis=1)
    return idx, np.sqrt(d2[np.arange(len(xy)), idx])


def _placer_dans_zone(zone: dict, demande: dict, depotoirs: list[dict], p: dict) -> tuple[list[dict], dict | None]:
    geometrie = zone["geometrie"]
    aire = aire_m2(geometrie)
    demande_jour = demande["demande_kg_jour"]

    if not demande["population_connue"] and not depotoirs:
        return [], {"zone_id": zone["id"], "raison": "population inconnue et aucun dépotoir actif : besoin non estimable"}
    if demande_jour <= 0 and not depotoirs:
        return [], None   # population nulle : rien à collecter

    echantillons = echantillonner(geometrie, p["pas_m"], p["max_echantillons"])
    lat0 = sum(e[0] for e in echantillons) / len(echantillons)
    lon0 = sum(e[1] for e in echantillons) / len(echantillons)
    xy_menages = np.array([vers_metres(la, lo, lat0, lon0) for la, lo in echantillons])
    xy_depotoirs = np.array([vers_metres(d["latitude"], d["longitude"], lat0, lon0) for d in depotoirs]).reshape(-1, 2)

    candidats = np.vstack([xy_menages, xy_depotoirs])
    poids = np.concatenate([np.ones(len(xy_menages)), np.full(len(xy_depotoirs), p["poids_depotoir"])])
    if not demande["population_connue"]:
        # sans population, on ne place des points que pour les dépotoirs
        candidats, poids = xy_depotoirs, np.ones(len(xy_depotoirs))

    stock_kg = demande_jour * p["jours"]
    k_capacite = math.ceil(stock_kg / p["capacite_kg"]) if stock_kg > 0 else 0
    k_marche = math.ceil(aire / (math.pi * p["distance_m"] ** 2)) if demande["population_connue"] else 0
    k = max(1, k_capacite, k_marche)
    k_initial = k
    a_couvrir = candidats if not demande["population_connue"] else xy_menages

    while True:
        k = min(k, p["max_points"])
        sites = candidats[_recaler(_kmeans(candidats, poids, k, p["graine"]), candidats)]
        _, dist = _plus_proche(a_couvrir, sites)
        couverture = float((dist <= p["distance_m"]).mean())
        if couverture >= p["couverture_cible"] or k >= p["max_points"] or k >= len(candidats):
            break
        k += max(1, k // 10)

    # Répartition de la demande : chaque échantillon de ménages va au point le plus proche.
    idx_menages, _ = _plus_proche(xy_menages, sites)
    idx_depotoirs, dist_depotoirs = _plus_proche(xy_depotoirs, sites) if len(depotoirs) else (np.array([], int), np.array([]))

    points = []
    for i, (x, y) in enumerate(sites):
        part = float((idx_menages == i).mean()) if demande["population_connue"] else 0.0
        charge = demande_jour * part
        ids_dep = [depotoirs[j]["id"] for j in range(len(depotoirs)) if idx_depotoirs[j] == i]
        lat, lon = depuis_metres(float(x), float(y), lat0, lon0)
        stock = charge * p["jours"]
        points.append(
            {
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "zone_id": zone["id"],
                "capacite_kg": p["capacite_kg"],
                "charge_kg_jour": round(charge, 1),
                "stock_entre_passages_kg": round(stock, 1),
                "sature": stock > p["capacite_kg"],
                "depotoirs_desservis": sorted(ids_dep),
                "_part_menages": part,
            }
        )

    for pt in points:
        pt["explication"] = _expliquer_zone(pt, zone, demande, p, k_initial, k_capacite, k_marche, len(points), couverture)

    non_couvert = None
    if demande["population_connue"] and couverture < p["couverture_cible"]:
        non_couvert = {
            "zone_id": zone["id"],
            "raison": (
                f"{(1 - couverture) * 100:.0f} % de la zone à plus de {p['distance_m']:.0f} m d'un point "
                f"(limite de {p['max_points']} points par zone atteinte)"
            ),
        }
    loin = [depotoirs[j]["id"] for j in range(len(depotoirs)) if dist_depotoirs[j] > p["distance_m"]]
    if loin and non_couvert is None:
        non_couvert = {"zone_id": zone["id"], "raison": f"dépotoirs à plus de {p['distance_m']:.0f} m d'un point : {loin}"}
    return points, non_couvert


def _expliquer_zone(pt: dict, zone: dict, demande: dict, p: dict, k_initial: int, k_capacite: int,
                    k_marche: int, n: int, couverture: float) -> str:
    nom = zone.get("nom") or f"zone {zone['id']}"
    morceaux = []
    if demande["population_connue"]:
        morceaux.append(
            f"{nom} : {demande['demande_kg_jour']:.0f} kg/jour, {n} point(s) "
            f"(capacité : {k_capacite}, marche ≤ {p['distance_m']:.0f} m : {k_marche}"
            + (f", ajoutés pour la couverture : {n - k_initial}" if n > k_initial else "")
            + f") ; couverture {couverture * 100:.0f} %."
        )
        morceaux.append(
            f"Ce point dessert environ {pt['_part_menages'] * 100:.0f} % des ménages de la zone, "
            f"soit {pt['charge_kg_jour']:.0f} kg/jour et {pt['stock_entre_passages_kg']:.0f} kg entre deux passages "
            f"(capacité {p['capacite_kg']:.0f} kg)."
        )
    else:
        morceaux.append(f"{nom} : population inconnue, point placé uniquement pour les dépotoirs actifs.")
    if pt["depotoirs_desservis"]:
        morceaux.append(
            f"Point le plus proche de {len(pt['depotoirs_desservis'])} dépotoir(s) actif(s) {pt['depotoirs_desservis']}, "
            "qui attirent le placement (les déchets s'y accumulent faute de solution proche)."
        )
    if pt["sature"]:
        morceaux.append("Attention : capacité dépassée entre deux passages, augmenter la fréquence de collecte.")
    return " ".join(morceaux)


def _placer_hors_zone(depotoirs: list[dict], p: dict) -> list[dict]:
    """Regroupement glouton : un point par groupe de dépotoirs à distance de marche."""
    groupes: list[list[dict]] = []
    for d in sorted(depotoirs, key=lambda d: d["id"]):
        for g in groupes:
            lat = sum(x["latitude"] for x in g) / len(g)
            lon = sum(x["longitude"] for x in g) / len(g)
            if distance_m(lat, lon, d["latitude"], d["longitude"]) <= p["distance_m"]:
                g.append(d)
                break
        else:
            groupes.append([d])
    points = []
    for g in groupes:
        ids = sorted(x["id"] for x in g)
        points.append(
            {
                "latitude": round(sum(x["latitude"] for x in g) / len(g), 6),
                "longitude": round(sum(x["longitude"] for x in g) / len(g), 6),
                "zone_id": None,
                "capacite_kg": p["capacite_kg"],
                "charge_kg_jour": None,
                "stock_entre_passages_kg": None,
                "sature": False,
                "depotoirs_desservis": ids,
                "explication": (
                    f"Hors des zones connues : centre de {len(g)} dépotoir(s) actif(s) {ids} "
                    f"à moins de {p['distance_m']:.0f} m les uns des autres ; charge non estimée (population inconnue)."
                ),
            }
        )
    return points


def placer_points(depotoirs_actifs: Sequence[dict], zones: Sequence[dict], config: dict) -> dict:
    """Points de regroupement du plan.

    - `depotoirs_actifs` : dicts avec `id`, `latitude`, `longitude`, `zone_id` (règle 3 :
      l'appelant ne passe que les dépotoirs `actif`) ;
    - `zones` : dicts avec `id`, `nom`, `geometrie` (GeoJSON), `population`.

    Renvoie `{"points": [...], "non_couverts": [...]}`. Les points sont numérotés
    à partir de 1 dans un ordre stable (zone, puis nord → sud, ouest → est).
    """
    p = _parametres(config)
    demandes = {d["zone_id"]: d for d in estimer_demande(zones, config)}
    ids_zones = {z["id"] for z in zones}

    points: list[dict] = []
    non_couverts: list[dict] = []
    for zone in sorted(zones, key=lambda z: z["id"]):
        dans_zone = [d for d in depotoirs_actifs if d.get("zone_id") == zone["id"]]
        pts, manque = _placer_dans_zone(zone, demandes[zone["id"]], dans_zone, p)
        points.extend(sorted(pts, key=lambda x: (-x["latitude"], x["longitude"])))
        if manque:
            non_couverts.append(manque)

    hors_zone = [d for d in depotoirs_actifs if d.get("zone_id") not in ids_zones]
    points.extend(_placer_hors_zone(hors_zone, p))

    for i, pt in enumerate(points, start=1):
        pt.pop("_part_menages", None)
        pt["id"] = i
    return {"points": points, "non_couverts": non_couverts}
