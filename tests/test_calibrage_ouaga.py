"""D50 : sur le jeu de Ouaga, les nouveaux dépotoirs réagissent aux scénarios (D48 ne sature pas)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import appliquer_surcharges, charger_config  # noqa: E402
from scripts.resultats_scenarios import lire_donnees  # noqa: E402
from simulation.agents import simuler  # noqa: E402
from simulation.plan import calculer_plan  # noqa: E402


def test_moins_de_dechets_sauvages_moins_de_nouveaux_depotoirs():
    donnees = lire_donnees()
    base = appliquer_surcharges(charger_config("ouagadougou"), {"perimetre": {"arrondissements": [9]}})
    plan = calculer_plan(donnees, base)
    sensibilisation = appliquer_surcharges(base, {"simulation": {"prob_apport_volontaire": 0.8}})
    r_base = simuler(donnees, base, 30, 42, plan=plan)["resume"]
    r_sens = simuler(donnees, sensibilisation, 30, 42, plan=plan)["resume"]
    assert r_sens["dechets_sauvages_kg"] < r_base["dechets_sauvages_kg"]
    assert r_sens["nouveaux_depotoirs"] < 0.75 * r_base["nouveaux_depotoirs"]
