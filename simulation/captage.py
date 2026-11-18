"""Part des déchets captée : combien de ce que produisent les ménages arrive aux points (D41).

À ne pas confondre avec la **capacité de collecte** du plan (les camions peuvent-ils
vider les points ?) : le plan suppose que tout arrive aux points, ce module estime
ce qui y arrive vraiment, selon le comportement des ménages. Formule commune au plan
(estimation) et à la simulation (jour par jour), par zone :

- pré-collecte : `taux_abonnement × min(1, capacité des pré-collecteurs / déchets des abonnés)` ;
- apport volontaire : les autres × part de la zone à distance de marche d'un point
  × `prob_apport_volontaire / coef_depots_sauvages(saison)` ;
- le reste n'est pas capté (dépôts sauvages, brûlage…).

La simulation ajoute un effet dynamique que l'estimation ne compte pas : la dissuasion
près des sites sous surveillance Laabal.
"""

from __future__ import annotations

from typing import Sequence

from simulation.batiments import batiments_de, menages_dans_zone
from simulation.geometrie import distance_m, echantillonner


def parametres_captage(config: dict) -> dict:
    s = config.get("simulation", {})
    saison = config["saisons"][config["scenario"]["saison"]]
    pre = config["precollecteurs"]
    return {
        "taux_abonnement": float(config["population"]["taux_abonnement_precollecteurs"]),
        "capacite_precollecte": float(pre["nombre"]) * float(pre["capacite_kg_jour"]),
        "prob_apport": min(1.0, float(s.get("prob_apport_volontaire", 0.6)) / float(saison.get("coef_depots_sauvages", 1.0))),
        "distance_marche": float(config["points_regroupement"]["distance_max_a_pied_m"]),
        "pas_m": float(config["points_regroupement"].get("pas_echantillonnage_m", 100)),
        "pas_couverture": int(s.get("max_echantillons_couverture", 400)),
        "batiments": batiments_de(config),       # D58 : None = grille uniforme
    }


def couverture(zone: dict, points: Sequence[dict], p: dict) -> tuple[float, list]:
    """Part des ménages de la zone à distance de marche d'un point, et la grille utilisée."""
    grille, poids = [], []
    if p.get("batiments") is not None:          # ménages là où sont les bâtiments, pondérés par leur surface (D58)
        grille, surfaces = menages_dans_zone(p["batiments"], zone["geometrie"], p["pas_m"], p["pas_couverture"])
        poids = surfaces.tolist()
    if not grille:
        grille = echantillonner(zone["geometrie"], p["pas_m"], p["pas_couverture"])
        poids = [1.0] * len(grille)
    proches = [pt for pt in points if pt.get("zone_id") == zone["id"]]
    if not proches:
        return 0.0, grille
    dedans = sum(
        w for (la, lo), w in zip(grille, poids)
        if min(distance_m(la, lo, pt["latitude"], pt["longitude"]) for pt in proches) <= p["distance_marche"]
    )
    return dedans / sum(poids), grille


def ratio_precollecte(zones: Sequence[dict], demandes: dict, avec_points: set, p: dict) -> float:
    """Part des déchets des abonnés que les pré-collecteurs peuvent ramasser (capacité partagée)."""
    abonnes = sum(demandes[z["id"]] * p["taux_abonnement"] for z in zones if z["id"] in avec_points)
    return min(1.0, p["capacite_precollecte"] / abonnes) if abonnes > 0 else 0.0


def estimer_captage(zones: Sequence[dict], points: Sequence[dict], demandes: dict, config: dict) -> dict:
    """Estimation statique, sans la dissuasion Laabal. `demandes` : {zone_id: kg/jour}."""
    p = parametres_captage(config)
    avec_points = {pt.get("zone_id") for pt in points}
    ratio = ratio_precollecte(zones, demandes, avec_points, p)
    production = pre_kg = apport_kg = 0.0
    for z in zones:
        kg = demandes[z["id"]]
        production += kg
        if z["id"] not in avec_points or kg <= 0:
            continue
        cov, _ = couverture(z, points, p)
        pre = kg * p["taux_abonnement"] * ratio
        pre_kg += pre
        apport_kg += (kg - pre) * cov * p["prob_apport"]
    if production <= 0:
        return {"part_captee_estimee_pct": 100.0, "precollecte_pct": 0.0, "apport_volontaire_pct": 0.0,
                "non_capte_pct": 0.0}
    pct = lambda x: round(100 * x / production, 1)
    return {
        "part_captee_estimee_pct": pct(pre_kg + apport_kg),
        "precollecte_pct": pct(pre_kg),
        "apport_volontaire_pct": pct(apport_kg),
        "non_capte_pct": pct(production - pre_kg - apport_kg),
    }
