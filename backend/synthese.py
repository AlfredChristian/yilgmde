"""Livrable 3 : plan de gestion lisible (Markdown) d'un scénario, pour un arrondissement ou la commune.

À afficher dans le tableau de bord, coller dans le rapport ou imprimer. Construit
uniquement à partir du plan enregistré et du scénario : aucune nouvelle décision ici.
"""

from __future__ import annotations

import json
from collections import defaultdict


def _xof(v) -> str:
    return f"{round(v or 0):,}".replace(",", " ") + " XOF"


def _nb(v, decimales=0) -> str:
    """Nombre à la française : espace pour les milliers, virgule pour les décimales."""
    return f"{v:,.{decimales}f}".replace(",", " ").replace(".", ",")


def synthese_markdown(plan: dict, scenario: dict, zones: list[dict], config: dict) -> str:
    ind = plan["indicateurs"]
    perimetre = ind.get("perimetre")
    noms = {z["id"]: z["nom"] for z in zones}
    if perimetre:
        arr = ", ".join(str(a) for a in perimetre["arrondissements"]) or "aucun"
        titre = f"Plan de gestion des déchets de l’arrondissement {arr}" if perimetre["arrondissements"] else \
            "Plan de gestion des déchets des zones choisies"
        lieu = f"{len(perimetre['zones'])} zone(s), {_nb(perimetre['population'])} habitants"
    else:
        titre = f"Plan de gestion des déchets de {config.get('ville') or 'la commune'}"
        lieu = f"{len(zones)} zone(s)"
    collecte = [t for t in plan["tournees"] if t["type"] == "collecte"]
    laabal = [t for t in plan["tournees"] if t["type"] == "intervention"]
    freq = config["collecte"]["frequence_passages_par_semaine"]

    l = [f"# {titre}", "",
         f"Scénario **{scenario['nom']}**, plan n° {plan['id']} calculé le {plan['calcule_le'][:16].replace('T', ' ')} UTC"
         f" en {plan['duree_calcul_ms']} ms, saison {'des pluies' if ind['saison'] == 'pluies' else 'sèche'}, {lieu}.", ""]
    resume = _parametres_lisibles(scenario.get("parametres") or {})
    if resume:
        l += ["Paramètres modifiés par rapport à la configuration de base :", "", *[f"- {x}" for x in resume], ""]

    l += ["## En bref", "",
          "| Indicateur | Valeur |", "|---|---|",
          f"| Déchets produits | {_nb(ind['demande_totale_kg_jour'])} kg/jour |",
          f"| Points de regroupement | {ind['nb_points_regroupement']} |",
          f"| Collecte | {freq} passage(s) par semaine, {len(collecte)} rotation(s) sur"
          f" {max((t.get('jour', 1) for t in collecte), default=0)} jour(s) par passage |",
          f"| Capacité de collecte des camions (part du stock des points vidée à chaque passage)"
          f" | {_nb(ind['capacite_collecte_pct'], 1)} % |",
          f"| Part des déchets captée, estimée (arrive aux points : pré-collecte {_nb(ind['precollecte_pct'], 1)} %"
          f" + apport volontaire {_nb(ind['apport_volontaire_pct'], 1)} %) | {_nb(ind['part_captee_estimee_pct'], 1)} % |",
          f"| Camions utilisés | {', '.join(ind['camions_utilises']) or 'aucun'} |",
          f"| Camions indisponibles | {', '.join(ind['camions_indisponibles']) or 'aucun'} |",
          f"| Distance d'un passage | {_nb(ind['distance_totale_km'], 1)} km |",
          f"| Coût d'un passage | {_xof(ind['cout_total_xof'])} |",
          f"| Coût mensuel estimé | {_xof(ind['cout_mensuel_estime_xof'])}"
          + (f" (budget {_xof(ind['budget_mensuel_xof'])}{', **dépassé**' if ind['budget_depasse'] else ''})"
             if ind.get("budget_mensuel_xof") else "") + " |",
          f"| Dépotoirs actifs | {ind['depotoirs_actifs']} ({ind['depotoirs_planifies_laabal']} traités aujourd'hui"
          f" par Laabal, {ind['depotoirs_en_attente_laabal']} en attente) |", ""]

    # Points par zone
    par_zone = defaultdict(list)
    for p in plan["points_regroupement"]:
        par_zone[p["zone_id"]].append(p)
    l += ["## Points de regroupement", "",
          "| Zone | Points | Déchets (kg/jour) | Points saturés |", "|---|---|---|---|"]
    for zid in sorted(par_zone, key=lambda z: (z is None, z or 0)):
        pts = par_zone[zid]
        charge = sum(p.get("charge_kg_jour") or 0 for p in pts)
        l.append(f"| {noms.get(zid, 'Nouveau quartier ' + str(zid) if zid else 'Hors zone connue')} | {len(pts)}"
                 f" | {_nb(charge)} | {sum(1 for p in pts if p.get('sature'))} |")
    exemple = next((p for p in plan["points_regroupement"] if p.get("explication")), None)
    if exemple:
        l += ["", f"Pourquoi ces points ? Exemple (point n° {exemple['id']}) : {exemple['explication']}"]
    l.append("")

    # Tournées
    l += ["## Tournées de collecte (un passage)", ""]
    if collecte:
        l += ["| Jour | Camion | Rotation | Arrêts | Charge (kg) | Distance (km) | Durée (min) | Coût |",
              "|---|---|---|---|---|---|---|---|"]
        for t in sorted(collecte, key=lambda t: (t.get("jour", 1), t["camion_id"], t.get("rotation", 1))):
            l.append(f"| {t.get('jour', 1)} | {t['camion_id']} | {t.get('rotation', 1)} | {len(t['arrets'])}"
                     f" | {_nb(t.get('charge_kg', 0))}"
                     f" | {_nb(t['distance_km'], 1)} | {_nb(t['duree_min'])} | {_xof(t['cout_xof'])} |")
    else:
        l.append("Aucune tournée de collecte possible (aucun camion disponible).")
    l.append("")

    l += ["## Brigade Laabal (aujourd'hui)", ""]
    if laabal:
        for t in laabal:
            l.append(f"- Brigade {t.get('brigade', '?')} : {len(t['arrets'])} dépotoir(s), {_nb(t['distance_km'], 1)} km, "
                     f"{_nb(t['duree_min'])} min : " + " ; ".join(
                         f"n° {a['cible_id']} ({a.get('raison', '')})" for a in t["arrets"]))
    else:
        l.append("- Aucun dépotoir illégal à traiter aujourd'hui.")
    if plan.get("laabal_en_attente"):
        l.append(f"- En attente : {len(plan['laabal_en_attente'])} dépotoir(s) "
                 f"({plan['laabal_en_attente'][0]['motif']}).")
    l.append("")

    l += ["## Ce qui n'est pas couvert", ""]
    if plan["non_couverts"]:
        for nc in plan["non_couverts"]:
            if "zone_id" in nc:
                cible = f"Zone {noms.get(nc['zone_id'], nc['zone_id'])}"
            elif "point_regroupement_id" in nc:
                cible = f"Point n° {nc['point_regroupement_id']}"
            else:
                cible = f"Dépotoir n° {nc['depotoir_id']}"
            l.append(f"- {cible} : {nc['raison']}")
    else:
        l.append("Tout est couvert.")
    l += ["", "---", "",
          "Plan calculé par yilgmde (code MIT). Les valeurs marquées [H] dans la configuration sont des hypothèses "
          "de départ ; voir `docs/parametres.md`.", ""]
    return "\n".join(l)


def _parametres_lisibles(p: dict) -> list[str]:
    """Paramètres du scénario en phrases, pour la mairie (le détail technique reste dans l'API)."""
    lignes = []
    arr = (p.get("perimetre") or {}).get("arrondissements")
    if arr:
        lignes.append(f"périmètre : arrondissement{'s' if len(arr) > 1 else ''} {', '.join(map(str, arr))}")
    saison = (p.get("scenario") or {}).get("saison") or p.get("saison")
    if saison:
        lignes.append(f"saison : {'des pluies' if saison == 'pluies' else 'sèche'}")
    pannes = [c["id"] for c in p.get("camions") or [] if c.get("disponible") is False]
    if pannes:
        lignes.append(f"camions en panne : {len(pannes)}")
    budget = (p.get("mairie") or {}).get("budget_mensuel_xof")
    if budget is not None:
        lignes.append(f"budget mensuel de la commune : {_xof(budget)}")
    pop = p.get("population") or {}
    if pop.get("evolution_pct"):
        lignes.append(f"évolution de la population : {pop['evolution_pct']:+g} %")
    if pop.get("taux_abonnement_precollecteurs") is not None:
        lignes.append(f"ménages abonnés aux pré-collecteurs : {_nb(pop['taux_abonnement_precollecteurs'] * 100)} %")
    freq = (p.get("collecte") or {}).get("frequence_passages_par_semaine")
    if freq is not None:
        lignes.append(f"passages de collecte : {freq} par semaine")
    apport = (p.get("simulation") or {}).get("prob_apport_volontaire")
    if apport is not None:
        lignes.append(f"apport volontaire aux points : {_nb(apport * 100)} %")
    for z in p.get("zones_ajoutees") or []:
        props = (json.loads(z) if isinstance(z, str) else z).get("properties") or {}
        lignes.append(f"nouveau quartier : {props.get('nom', 'sans nom')}"
                      + (f", {_nb(props['population'])} habitants" if props.get("population") else ""))
    return lignes
