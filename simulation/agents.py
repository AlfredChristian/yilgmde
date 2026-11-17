"""E1–E4 — Simulation multi-agents par pas journalier.

`simuler(donnees, config, jours, graine, plan=None)` est une fonction pure (D09) :
le hasard vient uniquement d'un `random.Random(graine)` local (E4), les entrées ne
sont pas modifiées. Boucle Python maison (D18) : quatre agents, des règles
simples et explicables, tous les coefficients dans `config/` (D10), marqués [H].

Chaque jour, zone par zone :

1. **Ménages** produisent `demande_kg_jour` (C1, saison comprise).
2. **Pré-collecteurs** ramassent chez les abonnés (`taux_abonnement_precollecteurs`)
   dans la limite de leur capacité totale (`nombre × capacite_kg_jour`), partagée
   entre zones au prorata des abonnés, et vident aux points de regroupement.
   Les autres ménages apportent eux-mêmes leurs déchets à un point s'ils habitent à
   distance de marche (part couverte de la zone, calculée sur le plan) avec la
   probabilité `simulation.prob_apport_volontaire / coef_depots_sauvages(saison)`.
   Le reste finit en **dépôt sauvage** ; près d'un site sous surveillance Laabal,
   `laabal.effet_dissuasion` de ce reste est ramené au point.
3. **Points de regroupement** : un point plein déborde, le surplus part en dépôt
   sauvage. Les jours de passage (tous les `7 / frequence_passages_par_semaine`
   jours), les points desservis par une tournée du plan sont vidés.
4. **Dépotoirs** : les dépôts sauvages grossissent les dépotoirs actifs de la zone ;
   un nouveau dépotoir apparaît avec la probabilité
   `min(1, sauvage_kg / simulation.seuil_nouveau_depotoir_kg)`.
5. **Brigade Laabal** éradique chaque jour les dépotoirs les plus prioritaires
   (C7), qui passent ensuite sous surveillance ; un site surveillé réapparaît avec
   la probabilité `simulation.prob_reapparition × (1 − effet_dissuasion)` ; les
   contrôles (`taux_controle`) donnent des amendes (`montant_amende_xof`).
6. **Mairie** paie les tournées les jours de passage tant que le budget le permet
   (`budget_mensuel_xof` réparti sur `simulation.jours_par_mois`, plus les
   amendes) ; sinon la collecte est suspendue ce jour-là.
"""

from __future__ import annotations

import math
import random
from typing import Sequence

from simulation.demande import estimer_demande
from simulation.geometrie import distance_m, echantillonner
from simulation.plan import calculer_plan, preparer
from simulation.regroupement import jours_entre_passages
from simulation.tournees import priorite_depotoir

JOURS_MAX = 365


def _parametres(config: dict) -> dict:
    s = config.get("simulation", {})
    saison = config["saisons"][config["scenario"]["saison"]]
    pre = config["precollecteurs"]
    laabal = config["laabal"]
    return {
        "taux_abonnement": float(config["population"]["taux_abonnement_precollecteurs"]),
        "capacite_precollecte": float(pre["nombre"]) * float(pre["capacite_kg_jour"]),
        "prob_apport": min(1.0, float(s.get("prob_apport_volontaire", 0.6)) / float(saison.get("coef_depots_sauvages", 1.0))),
        "seuil_nouveau": float(s.get("seuil_nouveau_depotoir_kg", 1500)),
        "prob_reapparition": float(s.get("prob_reapparition", 0.05)),
        "prob_tentative": float(s.get("prob_tentative_depot_surveille", 0.1)),
        "jours_par_mois": float(s.get("jours_par_mois", 30)),
        "eradications": int(laabal.get("nombre_brigades", 0)) * int(laabal.get("capacite_eradication_par_jour", 0)),
        "dissuasion": float(laabal.get("effet_dissuasion", 0.0)),
        "taux_controle": float(laabal.get("taux_controle", 0.0)),
        "amende": float(laabal.get("montant_amende_xof", 0.0)),
        "budget_mensuel": config.get("mairie", {}).get("budget_mensuel_xof"),
        "distance_marche": float(config["points_regroupement"]["distance_max_a_pied_m"]),
        "pas_m": float(config["points_regroupement"].get("pas_echantillonnage_m", 100)),
        "jpp": jours_entre_passages(config),
        "pas_couverture": int(s.get("max_echantillons_couverture", 400)),
    }


def _couverture(zone: dict, points: Sequence[dict], p: dict) -> tuple[float, list]:
    """Part des ménages de la zone à distance de marche d'un point, et la grille utilisée."""
    grille = echantillonner(zone["geometrie"], p["pas_m"], p["pas_couverture"])
    proches = [pt for pt in points if pt.get("zone_id") == zone["id"]]
    if not proches:
        return 0.0, grille
    dedans = sum(
        1 for la, lo in grille
        if min(distance_m(la, lo, pt["latitude"], pt["longitude"]) for pt in proches) <= p["distance_marche"]
    )
    return dedans / len(grille), grille


def _jour_de_passage(jour: int, jpp: float) -> bool:
    return math.floor(jour / jpp) > math.floor((jour - 1) / jpp)


def simuler(donnees: dict, config: dict, jours: int = 30, graine: int | None = None, plan: dict | None = None) -> dict:
    """Simule `jours` jours. Renvoie `{"indicateurs": [par jour], "resume": {...}, "graine": int}`.

    `plan` (sortie de `calculer_plan` ou plan enregistré) est calculé s'il est absent.
    """
    if not 1 <= jours <= JOURS_MAX:
        raise ValueError(f"jours doit être entre 1 et {JOURS_MAX}")
    graine = int(config["scenario"].get("graine_aleatoire", 0) if graine is None else graine)
    rng = random.Random(graine)
    p = _parametres(config)
    if plan is None:
        plan = calculer_plan(donnees, config)
    # Mêmes zones et dépotoirs que le plan : nouveaux quartiers rattachés, périmètre appliqué (livrable 3).
    zones, depotoirs_scenario, _ = preparer(donnees, config)
    demandes = {d["zone_id"]: d["demande_kg_jour"] for d in estimer_demande(zones, config)}

    # État : copies, l'entrée n'est jamais modifiée.
    depotoirs = []
    for d in depotoirs_scenario:
        d = dict(d)
        d.setdefault("statut", "actif")
        d.setdefault("legalite", "illegal")
        d["kg"] = 0.0
        depotoirs.append(d)
    # Les nouveaux dépotoirs prennent des ids libres dans toute la commune, pas seulement le périmètre.
    prochain_id = max((d["id"] for d in donnees.get("depotoirs", [])), default=0) + 1

    points = [dict(pt, stock=0.0) for pt in plan["points_regroupement"]]
    desservis = {a["cible_id"] for t in plan["tournees"] if t["type"] == "collecte" for a in t["arrets"]}
    collecte = [t for t in plan["tournees"] if t["type"] == "collecte"]
    cout_passage = sum(t["cout_xof"] for t in collecte)
    distance_passage = sum(t["distance_km"] for t in collecte)

    par_zone = {}
    for z in zones:
        cov, grille = _couverture(z, points, p)
        pts = [pt for pt in points if pt.get("zone_id") == z["id"]]
        poids = [max(pt.get("charge_kg_jour") or 0.0, 0.0) for pt in pts]
        if pts and sum(poids) == 0:
            poids = [1.0] * len(pts)
        par_zone[z["id"]] = {"couverture": cov, "grille": grille, "points": pts, "poids": poids}

    abonnes_total = sum(demandes[z["id"]] * p["taux_abonnement"] for z in zones if par_zone[z["id"]]["points"])
    ratio_pre = min(1.0, p["capacite_precollecte"] / abonnes_total) if abonnes_total > 0 else 0.0

    indicateurs = []
    cout_cumule = amendes_cumulees = sauvage_cumule = 0.0
    passages = passages_suspendus = 0
    actifs_debut = sum(1 for d in depotoirs if d["statut"] == "actif")

    for jour in range(1, jours + 1):
        production = vers_points = sauvage_jour = 0.0

        # 1-3. Ménages, pré-collecteurs, points.
        for z in zones:
            P = demandes[z["id"]]
            if P <= 0:
                continue
            info = par_zone[z["id"]]
            production += P
            if not info["points"]:
                sauvage_zone = P
                apport = 0.0
            else:
                pre = P * p["taux_abonnement"] * ratio_pre
                autres = P - pre
                apport = autres * info["couverture"] * p["prob_apport"]
                sauvage_zone = autres - apport
                if any(d["statut"] == "sous_surveillance" and d.get("zone_id") == z["id"] for d in depotoirs):
                    dissuade = sauvage_zone * p["dissuasion"] * info["couverture"]
                    apport += dissuade
                    sauvage_zone -= dissuade
                arrive = pre + apport
                total_poids = sum(info["poids"])
                for pt, w in zip(info["points"], info["poids"]):
                    pt["stock"] += arrive * w / total_poids
                    if pt["stock"] > pt["capacite_kg"]:            # débordement
                        surplus = pt["stock"] - pt["capacite_kg"]
                        pt["stock"] = pt["capacite_kg"]
                        arrive -= surplus
                        sauvage_zone += surplus
                vers_points += arrive

            # 4. Dépôts sauvages : dépotoirs existants ou nouveaux.
            sauvage_jour += sauvage_zone
            actifs_zone = [d for d in depotoirs if d["statut"] == "actif" and d.get("zone_id") == z["id"]]
            if sauvage_zone > 0 and rng.random() < min(1.0, sauvage_zone / p["seuil_nouveau"]):
                la, lo = rng.choice(info["grille"])
                nouveau = {"id": prochain_id, "latitude": la, "longitude": lo, "zone_id": z["id"], "statut": "actif",
                           "legalite": "illegal", "volume_estime": "petit", "nb_signalements": 0,
                           "nb_reapparitions": 0, "kg": 0.0, "apparu_jour": jour}
                prochain_id += 1
                depotoirs.append(nouveau)
                actifs_zone.append(nouveau)
            for d in actifs_zone:
                d["kg"] += sauvage_zone / len(actifs_zone)

        # 5. Brigade Laabal : surveillance des sites éradiqués la veille, réapparitions, contrôles.
        amendes_jour = 0.0
        constats = reapparitions = 0
        for d in depotoirs:
            if d["statut"] == "eradique":
                d["statut"] = "sous_surveillance"
            elif d["statut"] == "sous_surveillance":
                if rng.random() < p["prob_tentative"] and rng.random() < p["taux_controle"]:
                    constats += 1
                    amendes_jour += p["amende"]
                elif rng.random() < p["prob_reapparition"] * (1 - p["dissuasion"]):
                    d["statut"] = "actif"
                    d["nb_reapparitions"] = d.get("nb_reapparitions", 0) + 1
                    reapparitions += 1
        a_traiter = sorted(
            (d for d in depotoirs if d["legalite"] == "illegal" and d["statut"] in ("actif", "intervention_planifiee")),
            key=lambda d: (-priorite_depotoir(d, config)[0], d["id"]),
        )
        eradiques = a_traiter[: p["eradications"]]
        for d in eradiques:
            d["statut"] = "eradique"
            d["kg"] = 0.0

        # 6. Mairie : collecte les jours de passage, dans la limite du budget.
        cout_jour = distance_jour = collecte_kg = 0.0
        suspendue = False
        if _jour_de_passage(jour, p["jpp"]) and collecte:
            budget_dispo = (
                math.inf if p["budget_mensuel"] is None
                else p["budget_mensuel"] * jour / p["jours_par_mois"] + amendes_cumulees + amendes_jour - cout_cumule
            )
            if cout_passage <= budget_dispo:
                for pt in points:
                    if pt["id"] in desservis:
                        collecte_kg += pt["stock"]
                        pt["stock"] = 0.0
                cout_jour, distance_jour = cout_passage, distance_passage
                passages += 1
            else:
                suspendue = True
                passages_suspendus += 1

        cout_cumule += cout_jour
        amendes_cumulees += amendes_jour
        sauvage_cumule += sauvage_jour
        budget_restant = (
            None if p["budget_mensuel"] is None
            else round(p["budget_mensuel"] * jour / p["jours_par_mois"] + amendes_cumulees - cout_cumule)
        )
        indicateurs.append(
            {
                "jour": jour,
                "pct_collecte": round(100 * vers_points / production, 1) if production else 100.0,
                "depotoirs_actifs": sum(1 for d in depotoirs if d["statut"] == "actif"),
                "cout_xof": round(cout_jour),
                "distance_km": round(distance_jour, 2),
                "production_kg": round(production, 1),
                "dechets_sauvages_kg": round(sauvage_jour, 1),
                "stock_points_kg": round(sum(pt["stock"] for pt in points), 1),
                "collecte_kg": round(collecte_kg, 1),
                "passage": cout_jour > 0,
                "collecte_suspendue": suspendue,
                "depotoirs_eradiques": len(eradiques),
                "depotoirs_sous_surveillance": sum(1 for d in depotoirs if d["statut"] == "sous_surveillance"),
                "reapparitions": reapparitions,
                "constats": constats,
                "amendes_xof": round(amendes_jour),
                "budget_restant_xof": budget_restant,
            }
        )

    n = len(indicateurs)
    resume = {
        "jours": n,
        "pct_collecte_moyen": round(sum(i["pct_collecte"] for i in indicateurs) / n, 1),
        "depotoirs_actifs_debut": actifs_debut,
        "depotoirs_actifs_fin": indicateurs[-1]["depotoirs_actifs"],
        "nouveaux_depotoirs": prochain_id - 1 - max((d["id"] for d in donnees.get("depotoirs", [])), default=0),
        "depotoirs_eradiques": sum(i["depotoirs_eradiques"] for i in indicateurs),
        "reapparitions": sum(i["reapparitions"] for i in indicateurs),
        "dechets_sauvages_kg": round(sauvage_cumule, 1),
        "passages_collecte": passages,
        "passages_suspendus_budget": passages_suspendus,
        "cout_total_xof": round(cout_cumule),
        "distance_totale_km": round(sum(i["distance_km"] for i in indicateurs), 2),
        "amendes_total_xof": round(amendes_cumulees),
        "constats": sum(i["constats"] for i in indicateurs),
        "budget_restant_xof": indicateurs[-1]["budget_restant_xof"],
    }
    return {"graine": graine, "indicateurs": indicateurs, "resume": resume}
