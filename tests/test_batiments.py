"""D58 : ménages situés d'après les bâtiments Open Buildings."""

import csv
import gzip

import numpy as np
import pytest

from backend.config import charger_config
from simulation.batiments import batiments_de, menages_dans_zone
from simulation.captage import couverture, parametres_captage
from simulation.regroupement import placer_points

ZONE = {"id": 1, "nom": "A", "population": 6000, "geometrie": {"type": "Polygon", "coordinates": [[
    [-1.53, 12.36], [-1.52, 12.36], [-1.52, 12.37], [-1.53, 12.37], [-1.53, 12.36]]]}}


def ecrire(chemin, batiments):
    with gzip.open(chemin, "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["latitude", "longitude", "surface_m2", "confiance"])
        w.writerows((la, lo, s, 0.8) for la, lo, s in batiments)


@pytest.fixture
def quartier_nord_est(tmp_path):
    """Toutes les maisons dans le quart nord-est de la zone, plus quelques-unes hors zone."""
    rng = np.random.default_rng(0)
    maisons = [(12.3655 + rng.random() * 0.0045, -1.5245 + rng.random() * 0.0045, 80 + rng.random() * 120)
               for _ in range(3000)]
    hors = [(12.40, -1.50, 100.0)] * 50
    chemin = tmp_path / "batiments.csv.gz"
    ecrire(chemin, maisons + hors)
    return chemin


def config_avec(chemin):
    c = charger_config("ouagadougou")
    c["population"]["batiments"] = str(chemin) if chemin else None
    return c


def test_paquets_dans_la_zone_et_bornes(quartier_nord_est):
    b = batiments_de(config_avec(quartier_nord_est))
    assert b.shape == (3050, 3)
    pos, surf = menages_dans_zone(b, ZONE["geometrie"], 100, 2000)
    assert all(12.36 <= la <= 12.37 and -1.53 <= lo <= -1.52 for la, lo in pos)   # les 50 hors zone écartés
    assert surf.sum() == pytest.approx(b[:3000, 2].sum())                          # aucune surface perdue
    pos_borne, surf_borne = menages_dans_zone(b, ZONE["geometrie"], 10, 30)
    assert len(pos_borne) <= 30 and surf_borne.sum() == pytest.approx(surf.sum())


def test_points_places_la_ou_sont_les_maisons(quartier_nord_est):
    uniforme = placer_points([], [ZONE], config_avec(None))["points"]
    reel = placer_points([], [ZONE], config_avec(quartier_nord_est))["points"]
    # Le quart nord-est commence à 12,3655 / -1,5245 : les points s'y concentrent.
    dans_ne = lambda pts: sum(p["latitude"] > 12.364 and p["longitude"] > -1.526 for p in pts) / len(pts)
    assert dans_ne(reel) >= 0.8 > dans_ne(uniforme)
    assert sum(p["charge_kg_jour"] for p in reel) == pytest.approx(sum(p["charge_kg_jour"] for p in uniforme), rel=0.01)
    assert "Open Buildings" in reel[0]["explication"] and "uniformément" in uniforme[0]["explication"]


def test_couverture_ponderee_par_les_maisons(quartier_nord_est):
    p = parametres_captage(config_avec(quartier_nord_est))
    un_point_ne = [{"zone_id": 1, "latitude": 12.3678, "longitude": -1.5222}]
    cov_reelle, _ = couverture(ZONE, un_point_ne, p)
    cov_uniforme, _ = couverture(ZONE, un_point_ne, parametres_captage(config_avec(None)))
    assert cov_reelle > 0.9 and cov_uniforme < 0.4      # un seul point suffit là où tout le monde habite


def test_fichier_absent_ou_zone_vide_retombe_sur_la_grille(tmp_path, quartier_nord_est):
    assert batiments_de(config_avec(tmp_path / "absent.csv.gz")) is None
    vide = dict(ZONE, geometrie={"type": "Polygon", "coordinates": [[
        [-1.60, 12.30], [-1.59, 12.30], [-1.59, 12.31], [-1.60, 12.31], [-1.60, 12.30]]]})
    pts = placer_points([], [vide], config_avec(quartier_nord_est))["points"]
    assert pts and "uniformément" in pts[0]["explication"]
