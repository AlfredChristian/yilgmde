"""C1 — Estimation de la demande de collecte par zone.

Fonction pure (D09) : `demande = f(zones, config)`. Aucun paramètre en dur (D10) :
production par habitant et coefficient de saison viennent de la config, donc un
changement de saison ou de production recalcule la demande sans autre modification.

    demande_kg_jour = population × (1 + evolution_pct / 100) × production_dechets_kg_hab_jour × coef_production(saison)
"""

from __future__ import annotations

from typing import Sequence


def coefficient_production(config: dict) -> float:
    """Coefficient de production de déchets de la saison courante du scénario."""
    return config["saisons"][config["scenario"]["saison"]]["coef_production"]


def estimer_demande(zones: Sequence[dict], config: dict) -> list[dict]:
    """Demande journalière en kg pour chaque zone, dans l'ordre des zones.

    Une zone dont la population est inconnue (None) a une demande de 0 et
    `population_connue = False` : elle est signalée, jamais inventée.
    """
    par_habitant = config["population"]["production_dechets_kg_hab_jour"]
    coef = coefficient_production(config)
    # Scénario « la population évolue de x % » (D56) : appliqué à toutes les zones connues.
    evolution = 1 + float(config["population"].get("evolution_pct", 0) or 0) / 100
    resultat = []
    for zone in zones:
        population = zone.get("population")
        if population is not None and evolution != 1:
            population = round(population * evolution)
        connue = population is not None
        resultat.append(
            {
                "zone_id": zone["id"],
                "nom": zone.get("nom"),
                "population": population,
                "population_connue": connue,
                "demande_kg_jour": population * par_habitant * coef if connue else 0.0,
            }
        )
    return resultat


def demande_totale_kg_jour(zones: Sequence[dict], config: dict) -> float:
    return sum(z["demande_kg_jour"] for z in estimer_demande(zones, config))
