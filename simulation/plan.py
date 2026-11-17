"""C4 — Plan de gestion : `plan = calculer_plan(donnees, config)` (D09).

Fonction pure qui assemble :
- C1 demande par zone (`simulation/demande.py`) ;
- C2 points de regroupement (`simulation/regroupement.py`) ;
- C3 tournées de collecte et C7 tournées Laabal (`simulation/tournees.py`).

`donnees` = `{"zones": [...], "depotoirs": [...]}` lus en base par l'appelant (tous
statuts : le plan ne garde que les dépotoirs `actif` pour les points, règle 3, et
les dépotoirs illégaux à traiter pour Laabal). Les scénarios agissent uniquement
par la config (D1–D4) :
- `camions[].disponible = false` : camion en panne (D2) ;
- `scenario.saison = pluies` : production et vitesse changent (D3) ;
- `zones_ajoutees` : nouveaux quartiers en GeoJSON (D4), ajoutés aux zones lues en
  base ; les dépotoirs sans zone qu'ils contiennent leur sont rattachés.

Le résultat ne contient ni id de plan ni date ni durée : c'est l'appelant qui les
ajoute en l'enregistrant (la date et la durée ne sont pas des fonctions des entrées).
"""

from __future__ import annotations

from typing import Sequence

from simulation.demande import estimer_demande
from simulation.geometrie import point_dans_geometrie, zone_pour_point
from simulation.regroupement import placer_points
from simulation.tournees import planifier_interventions, planifier_tournees

SEMAINES_PAR_MOIS = 52 / 12


def zones_du_scenario(zones: Sequence[dict], config: dict) -> list[dict]:
    """Zones en base + `zones_ajoutees` du scénario (Feature ou géométrie GeoJSON).

    Une zone ajoutée sans `id` reçoit un id au-delà du plus grand id existant.
    """
    resultat = [dict(z) for z in zones]
    prochain = max((z["id"] for z in zones), default=0) + 1
    for i, ajout in enumerate(config.get("zones_ajoutees") or [], start=1):
        if not isinstance(ajout, dict):
            raise ValueError(f"zones_ajoutees[{i}] : objet GeoJSON attendu")
        if ajout.get("type") == "Feature":
            geometrie, proprietes = ajout.get("geometry") or {}, ajout.get("properties") or {}
        else:
            geometrie, proprietes = ajout, {}
        try:
            point_dans_geometrie(0.0, 0.0, geometrie)   # valide Polygon / MultiPolygon
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise ValueError(f"zones_ajoutees[{i}] : géométrie invalide ({e})") from e
        zone_id = proprietes.get("id")
        if zone_id is None or any(z["id"] == zone_id for z in resultat):
            zone_id = prochain
        prochain = max(prochain, zone_id) + 1
        resultat.append(
            {
                "id": zone_id,
                "nom": proprietes.get("nom") or f"Nouveau quartier {i}",
                "geometrie": geometrie,
                "population": proprietes.get("population"),
                "densite": proprietes.get("densite"),
                "ajoutee": True,
            }
        )
    return resultat


def _rattacher(depotoirs: Sequence[dict], zones: Sequence[dict]) -> list[dict]:
    """Copie des dépotoirs ; ceux sans zone connue sont rattachés à une zone ajoutée qui les contient."""
    ids = {z["id"] for z in zones}
    ajoutees = [z for z in zones if z.get("ajoutee")]
    resultat = []
    for d in depotoirs:
        d = dict(d)
        if d.get("zone_id") not in ids and ajoutees:
            d["zone_id"] = zone_pour_point(d["latitude"], d["longitude"], ajoutees)
        resultat.append(d)
    return resultat


def preparer(donnees: dict, config: dict) -> tuple[list[dict], list[dict], dict | None]:
    """Zones et dépotoirs du scénario, dans son périmètre (livrable 3).

    1. ajoute les nouveaux quartiers (D4) à **toutes** les zones de la commune, pour
       qu'ils reçoivent un identifiant libre ; rattache les dépotoirs sans zone ;
    2. applique `config["perimetre"]` = `{"arrondissements": [4], "zones": [12]}` (union ;
       absent ou vide = toute la commune) : garde les zones choisies, **toujours** les
       nouveaux quartiers, et les dépotoirs de ces zones.

    Renvoie `(zones, depotoirs, resume_du_perimetre)` ; le résumé vaut None sans périmètre.
    Lève ValueError si le périmètre ne contient aucune zone.
    """
    zones = zones_du_scenario(donnees.get("zones", []), config)
    depotoirs = _rattacher(donnees.get("depotoirs", []), zones)

    perimetre = config.get("perimetre") or {}
    if not isinstance(perimetre, dict):
        raise ValueError("perimetre : objet attendu, ex. {\"arrondissements\": [4]}")
    arrondissements = set(perimetre.get("arrondissements") or [])
    ids_demandes = set(perimetre.get("zones") or [])
    if not arrondissements and not ids_demandes:
        return zones, depotoirs, None

    choisies = [z for z in zones if not z.get("ajoutee")
                and (z.get("arrondissement") in arrondissements or z["id"] in ids_demandes)]
    if not choisies:
        raise ValueError(
            f"périmètre vide : aucune zone pour les arrondissements {sorted(arrondissements)}"
            f" ni les zones {sorted(ids_demandes)}"
        )
    gardees = [z for z in zones if z in choisies or z.get("ajoutee")]
    ids = {z["id"] for z in gardees}
    population = sum(z.get("population") or 0 for z in choisies)
    population_commune = sum(z.get("population") or 0 for z in zones if not z.get("ajoutee"))
    resume = {
        "arrondissements": sorted(arrondissements),
        "zones": sorted(z["id"] for z in choisies),
        "population": population,
        # Part du budget communal revenant au périmètre, au prorata de la population (D39).
        "part_budget": round(population / population_commune, 4) if population_commune else 1.0,
    }
    return gardees, [d for d in depotoirs if d.get("zone_id") in ids], resume


def budget_du_perimetre(config: dict, perimetre: dict | None) -> float | None:
    """Budget mensuel de la commune, ou sa part pour le périmètre (au prorata de la population)."""
    budget = config.get("mairie", {}).get("budget_mensuel_xof")
    if budget is None or not perimetre:
        return budget
    return round(budget * perimetre["part_budget"])


def restreindre_perimetre(donnees: dict, config: dict) -> dict | None:
    """Vérifie le périmètre sur les données (ValueError s'il est vide) ; renvoie son résumé."""
    return preparer(donnees, config)[2]


def calculer_plan(donnees: dict, config: dict) -> dict:
    zones, depotoirs, perimetre = preparer(donnees, config)
    actifs = [d for d in depotoirs if d.get("statut", "actif") == "actif"]   # règle 3

    demandes = estimer_demande(zones, config)
    regroupement = placer_points(actifs, zones, config)
    points = regroupement["points"]
    collecte = planifier_tournees(points, config)
    laabal = planifier_interventions(depotoirs, config)

    tournees = collecte["tournees"] + laabal["tournees"]
    for i, t in enumerate(tournees, start=1):
        t["id"] = i

    # Non couverts : zones (C2), points (C3) et, pour l'utilisateur, les dépotoirs concernés.
    points_par_id = {p["id"]: p for p in points}
    non_couverts = list(regroupement["non_couverts"]) + list(collecte["non_couverts"])
    for nc in collecte["non_couverts"]:
        for dep_id in points_par_id[nc["point_regroupement_id"]]["depotoirs_desservis"]:
            non_couverts.append({"depotoir_id": dep_id, "raison": nc["raison"]})

    a_collecter = sum(a for a in (_stock(p) for p in points))
    collecte_kg = sum(t["charge_kg"] for t in collecte["tournees"])
    camions_utilises = sorted({t["camion_id"] for t in collecte["tournees"]})
    cout_passage = sum(t["cout_xof"] for t in collecte["tournees"])
    passages_mois = config["collecte"]["frequence_passages_par_semaine"] * SEMAINES_PAR_MOIS
    cout_mensuel = cout_passage * passages_mois
    budget = budget_du_perimetre(config, perimetre)

    indicateurs = {
        "demande_totale_kg_jour": round(sum(d["demande_kg_jour"] for d in demandes), 1),
        "zones_population_inconnue": [d["zone_id"] for d in demandes if not d["population_connue"]],
        "nb_points_regroupement": len(points),
        "stock_a_collecter_kg": round(a_collecter, 1),
        "dechets_collectes_pct": round(100 * collecte_kg / a_collecter, 1) if a_collecter else 100.0,
        "depotoirs_actifs": len(actifs),
        "depotoirs_planifies_laabal": sum(len(t["arrets"]) for t in laabal["tournees"]),
        "depotoirs_en_attente_laabal": len(laabal["en_attente"]),
        "camions_utilises": camions_utilises,
        "camions_indisponibles": [c["id"] for c in config.get("camions", []) if not c.get("disponible", True)],
        "distance_totale_km": round(sum(t["distance_km"] for t in tournees), 2),
        "cout_total_xof": round(cout_passage),
        "cout_mensuel_estime_xof": round(cout_mensuel),
        "budget_mensuel_xof": budget,
        "budget_depasse": bool(budget is not None and cout_mensuel > budget),
        "saison": config["scenario"]["saison"],
        "methode_tournees": collecte["methode"],
        "perimetre": perimetre,
    }
    return {
        "points_regroupement": points,
        "tournees": tournees,
        "laabal_en_attente": laabal["en_attente"],
        "indicateurs": indicateurs,
        "non_couverts": non_couverts,
        "zones_ajoutees": [z["id"] for z in zones if z.get("ajoutee")],
    }


def _stock(point: dict) -> float:
    s = point.get("stock_entre_passages_kg")
    return float(point["capacite_kg"] if s is None else s)
