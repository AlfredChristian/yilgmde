"""D52 : itinéraires sur le réseau routier (petit réseau fictif, sans dépendre du fichier OSM)."""

import gzip
import json

import pytest

from backend.config import appliquer_surcharges, charger_config
from simulation.geometrie import distance_m
from simulation.routes import Itineraires, Reseau, itineraires, reseau_de
from simulation.tournees import planifier_tournees

# Grille 3 × 3 de carrefours (~110 m d'écart) :
#   7 - 8 - 9
#   |       |      la rue 4-5-6 est à sens unique (vers l'est) ;
#   4 → 5 → 6      il n'y a pas de voie au centre entre 2 et 8 (un « camp »).
#   |       |
#   1 - 2 - 3
D = 0.001
NOEUDS = {str(i): (12.0 + D * ((i - 1) // 3), -1.0 + D * ((i - 1) % 3)) for i in range(1, 10)}
VOIES = [
    {"n": [1, 2, 3], "h": "residential", "s": 0},
    {"n": [7, 8, 9], "h": "residential", "s": 0},
    {"n": [1, 4, 7], "h": "residential", "s": 0},
    {"n": [3, 6, 9], "h": "residential", "s": 0},
    {"n": [4, 5, 6], "h": "residential", "s": 1},
]


@pytest.fixture
def reseau():
    return Reseau({"noeuds": NOEUDS, "voies": VOIES})


def test_les_distances_suivent_les_voies(reseau):
    sites = [NOEUDS["2"], NOEUDS["8"]]                  # séparés par le « camp » : pas de ligne droite
    it = Itineraires(reseau, sites)
    droit = distance_m(*sites[0], *sites[1])
    assert it.matrice_m[0][1] > 1.9 * droit             # contournement par 1-4-7 ou 3-6-9
    trace = it.trajet(0, 1)
    assert tuple(trace[0]) == NOEUDS["2"] and tuple(trace[-1]) == NOEUDS["8"]
    assert all(tuple(p) in set(NOEUDS.values()) for p in trace)    # que des points de voies (le site 2 est sur la rue 1-2-3)
    assert NOEUDS["5"] not in [tuple(p) for p in trace]            # jamais par le centre


def test_le_sens_unique_est_respecte(reseau):
    it = Itineraires(reseau, [NOEUDS["4"], NOEUDS["6"]])
    aller, retour = it.matrice_m[0][1], it.matrice_m[1][0]
    assert aller == pytest.approx(distance_m(*NOEUDS["4"], *NOEUDS["6"]), rel=0.01)   # tout droit, dans le sens
    assert retour > 1.9 * aller                                                       # à contresens : détour


def test_un_site_hors_voie_est_rattache_au_carrefour_le_plus_proche(reseau):
    hors = (12.0 + D * 0.1, -1.0 - D * 0.2)             # à ~25 m du carrefour 1
    it = Itineraires(reseau, [hors, NOEUDS["3"]])
    assert 0 < it.acces[0] < 40 and it.acces[1] == pytest.approx(0, abs=0.01)
    assert it.matrice_m[0][1] == pytest.approx(it.acces[0] + distance_m(*NOEUDS["1"], *NOEUDS["3"]), rel=0.01)


def test_tournees_tracees_sur_le_reseau(tmp_path):
    chemin = tmp_path / "reseau.json.gz"
    with gzip.open(chemin, "wt", encoding="utf-8") as f:
        json.dump({"noeuds": NOEUDS, "voies": VOIES}, f)
    config = appliquer_surcharges(charger_config(None), {
        "collecte": {"reseau_routier": str(chemin), "depot": {"latitude": NOEUDS["1"][0], "longitude": NOEUDS["1"][1]}},
    })
    assert reseau_de(config) is not None
    points = [{"id": i, "latitude": NOEUDS[n][0], "longitude": NOEUDS[n][1], "capacite_kg": 500,
               "stock_entre_passages_kg": 500} for i, n in enumerate(["8", "9", "6"], start=1)]
    r = planifier_tournees(points, config)
    t = r["tournees"][0]
    assert len(t["trace"]) == len(t["arrets"]) + 1                  # dépôt → arrêts → dépôt
    assert t["trace"][0][0] == [round(NOEUDS["1"][0], 5), round(NOEUDS["1"][1], 5)]
    sans = planifier_tournees(points, appliquer_surcharges(config, {"collecte": {"reseau_routier": None}}))
    assert "trace" not in sans["tournees"][0]


def test_mode_limite_pour_beaucoup_de_sites(reseau):
    """Commune entière : paires proches sur les routes, paires lointaines estimées, trajets tracés sur les routes."""
    sites = [NOEUDS["1"], NOEUDS["2"], NOEUDS["8"], NOEUDS["6"]]
    complet = Itineraires(reseau, sites)
    limite = Itineraires(reseau, sites, max_sites_complet=1, rayon_m=150, coef_lointain=1.3)
    assert limite.matrice_m[0][1] == pytest.approx(complet.matrice_m[0][1])          # proche : identique
    droit = distance_m(*NOEUDS["2"], *NOEUDS["8"])
    assert limite.matrice_m[1][2] == pytest.approx(droit * 1.3, rel=0.01)            # lointain : estimé
    for i, j in [(0, 2), (1, 2), (2, 0), (3, 1)]:                                     # dépôt, retour, autres
        assert limite.trajet(i, j) == complet.trajet(i, j)
    assert NOEUDS["5"] not in [tuple(p) for p in limite.trajet(1, 2)]


def test_reseau_introuvable():
    config = appliquer_surcharges(charger_config(None), {"collecte": {"reseau_routier": "nimporte.json.gz"}})
    with pytest.raises(ValueError, match="introuvable"):
        reseau_de(config)


def test_itineraires_reutilise_le_calcul_des_memes_sites(reseau):
    """D68 : mêmes sites, même réseau, mêmes réglages => même objet, mêmes distances."""
    sites = [NOEUDS["1"], NOEUDS["3"], NOEUDS["4"]]
    a = itineraires(reseau, sites)
    b = itineraires(reseau, [tuple(x) for x in sites])
    assert a is b
    assert (a.matrice_m == Itineraires(reseau, sites).matrice_m).all()
    assert itineraires(reseau, sites[:2]) is not a                    # autres sites : nouveau calcul
    assert itineraires(reseau, sites, max_sites_complet=1) is not a   # autres réglages aussi
    autre = Reseau({"noeuds": NOEUDS, "voies": VOIES})
    assert itineraires(autre, sites) is not a                        # autre réseau aussi
