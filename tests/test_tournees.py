import copy
import json

import pytest

from backend.config import appliquer_surcharges, charger_config
from simulation import tournees as module_tournees
from simulation.tournees import matrice_distances_m, planifier_tournees, vitesse_m_par_min


@pytest.fixture
def config():
    # Configuration générique : on teste le moteur, pas les valeurs de Ouaga (70 camions, etc.).
    return charger_config(None, surcharges={"collecte": {"depot": {"latitude": 12.37, "longitude": -1.52}}})


def point(id_, lat, lon, stock=1000.0, capacite=3000.0):
    return {"id": id_, "latitude": lat, "longitude": lon, "capacite_kg": capacite, "stock_entre_passages_kg": stock}


# 8 points autour du dépôt, 1 t chacun : 8 t pour 3 camions de 6 t.
POINTS = [point(i, 12.37 + 0.01 * (i % 3), -1.52 + 0.01 * (i // 3)) for i in range(1, 9)]


def ids_desservis(resultat):
    return sorted(a["cible_id"] for t in resultat["tournees"] for a in t["arrets"])


def test_tous_les_points_desservis_une_seule_fois(config):
    r = planifier_tournees(POINTS, config)
    assert r["methode"] == "ortools"
    assert ids_desservis(r) == [p["id"] for p in POINTS]
    assert r["non_couverts"] == []
    for t in r["tournees"]:
        assert t["type"] == "collecte"
        assert [a["ordre"] for a in t["arrets"]] == list(range(1, len(t["arrets"]) + 1))
        assert all(a["cible_type"] == "point_regroupement" and a["statut"] == "a_faire" for a in t["arrets"])
    assert [t["id"] for t in r["tournees"]] == list(range(1, len(r["tournees"]) + 1))


def test_capacite_et_duree_respectees(config):
    r = planifier_tournees(POINTS, config)
    capacites = {c["id"]: c["capacite_kg"] for c in config["camions"]}
    duree_rotation = config["collecte"]["duree_max_tournee_min"] / config["collecte"]["rotations_max_par_jour"]
    for t in r["tournees"]:
        assert t["charge_kg"] <= capacites[t["camion_id"]]
        assert t["duree_min"] <= duree_rotation + 1


def test_reproductible_et_pur(config):
    avant = json.dumps([POINTS, config], sort_keys=True)
    a = planifier_tournees(POINTS, config)
    b = planifier_tournees(copy.deepcopy(POINTS), copy.deepcopy(config))
    assert a == b
    assert json.dumps([POINTS, config], sort_keys=True) == avant


def test_camion_en_panne_jamais_utilise(config):
    panne = appliquer_surcharges(config, {"camions": [{"id": "camion_2", "disponible": False}]})
    r = planifier_tournees(POINTS, panne)
    assert "camion_2" not in {t["camion_id"] for t in r["tournees"]}
    assert ids_desservis(r) == [p["id"] for p in POINTS]   # les deux autres suffisent ici


def test_capacite_insuffisante_explique_la_panne(config):
    gros = [point(i, 12.37 + 0.002 * i, -1.52, stock=5000) for i in range(1, 6)]   # 25 t
    un_camion = appliquer_surcharges(config, {
        "camions": [{"id": "camion_2", "disponible": False}, {"id": "camion_3", "disponible": False}],
    })
    r = planifier_tournees(gros, un_camion)
    rotations = config["collecte"]["rotations_max_par_jour"]
    assert len(ids_desservis(r)) == rotations      # 1 point de 5 t par rotation d'un camion de 6 t
    assert len(r["non_couverts"]) == 5 - rotations
    assert "camion_2, camion_3 indisponibles" in r["non_couverts"][0]["raison"]


def test_aucun_camion(config):
    tous_hs = appliquer_surcharges(config, {"camions": [{"id": c["id"], "disponible": False} for c in config["camions"]]})
    r = planifier_tournees(POINTS, tous_hs)
    assert r["tournees"] == [] and len(r["non_couverts"]) == len(POINTS)
    assert r["non_couverts"][0]["raison"].startswith("aucun camion disponible")


def test_point_trop_gros_pour_un_camion(config):
    r = planifier_tournees([point(1, 12.371, -1.52, stock=9000)], config)
    assert r["tournees"] == []
    assert "supérieur à la capacité" in r["non_couverts"][0]["raison"]


def test_stock_inconnu_suppose_point_plein(config):
    r = planifier_tournees([dict(point(1, 12.371, -1.52), stock_entre_passages_kg=None)], config)
    assert r["tournees"][0]["charge_kg"] == 3000


def test_saison_des_pluies_ralentit(config):
    pluies = appliquer_surcharges(config, {"scenario": {"saison": "pluies"}})
    assert vitesse_m_par_min(pluies) < vitesse_m_par_min(config)
    seche = sum(t["duree_min"] for t in planifier_tournees(POINTS, config)["tournees"])
    humide = sum(t["duree_min"] for t in planifier_tournees(POINTS, pluies)["tournees"])
    assert humide > seche


def test_cout_km_et_journalier(config):
    r = planifier_tournees(POINTS[:1], config)
    t = r["tournees"][0]
    camion = next(c for c in config["camions"] if c["id"] == t["camion_id"])
    assert t["cout_xof"] == pytest.approx(t["distance_km"] * camion["cout_km_xof"] + camion["cout_jour_xof"], abs=3)


def test_repli_plus_proche_voisin(config, monkeypatch):
    forcee = planifier_tournees(POINTS, config, methode="plus_proche_voisin")
    assert forcee["methode"] == "plus_proche_voisin"
    assert ids_desservis(forcee) == [p["id"] for p in POINTS]
    monkeypatch.setattr(module_tournees, "pywrapcp", None)   # OR-Tools absent
    auto = planifier_tournees(POINTS, config)
    assert auto["methode"] == "plus_proche_voisin" and ids_desservis(auto) == ids_desservis(forcee)


def test_ortools_pas_pire_que_le_repli(config):
    ortools = planifier_tournees(POINTS, config)
    glouton = planifier_tournees(POINTS, config, methode="plus_proche_voisin")
    total = lambda r: sum(t["distance_km"] for t in r["tournees"])
    assert total(ortools) <= total(glouton) + 0.01


def test_sans_point_et_erreurs(config):
    assert planifier_tournees([], config) == {"tournees": [], "non_couverts": [], "methode": "aucune"}
    with pytest.raises(ValueError):
        planifier_tournees(POINTS, config, methode="magie")
    sans_depot = charger_config(None)
    with pytest.raises(ValueError):
        planifier_tournees(POINTS, sans_depot)


def test_matrice_symetrique_avec_detour():
    sites = [(12.37, -1.52), (12.38, -1.52)]
    m1 = matrice_distances_m(sites, 1.0)
    m2 = matrice_distances_m(sites, 1.3)
    assert m1[0][1] == m1[1][0] and m1[0][0] == 0
    assert m2[0][1] == pytest.approx(m1[0][1] * 1.3, abs=1)


# --- C7 : tournées Laabal -------------------------------------------------------------

from simulation.tournees import depotoirs_a_traiter, planifier_interventions, priorite_depotoir  # noqa: E402


def depotoir(id_, lat, lon, volume="moyen", statut="actif", legalite="illegal", reap=0, sig=1):
    return {"id": id_, "latitude": lat, "longitude": lon, "volume_estime": volume, "statut": statut,
            "legalite": legalite, "nb_reapparitions": reap, "nb_signalements": sig}


DEPOTOIRS = [
    depotoir(1, 12.371, -1.521),
    depotoir(2, 12.372, -1.525, volume="gros"),
    depotoir(3, 12.375, -1.519, reap=2),                       # revient : prioritaire
    depotoir(4, 12.369, -1.530, volume="petit"),
    depotoir(5, 12.380, -1.510, statut="eradique"),            # déjà traité
    depotoir(6, 12.381, -1.511, legalite="officiel"),          # site officiel : pas d'éradication
    depotoir(7, 12.374, -1.522, statut="intervention_planifiee"),
]


def test_priorite_et_raison(config):
    score, raison = priorite_depotoir(DEPOTOIRS[2], config)
    p = config["laabal"]["priorite"]
    assert score == p["poids_volume"]["moyen"] + 2 * p["poids_reapparition"] + p["poids_signalement"]
    assert "2 réapparition(s)" in raison


def test_seuls_les_illegaux_actifs_sont_a_traiter(config):
    ids = [d["id"] for d in depotoirs_a_traiter(DEPOTOIRS, config)]
    assert set(ids) == {1, 2, 3, 4, 7}
    assert ids[0] == 3 and ids[-1] == 4                         # réapparition d'abord, petit en dernier


def test_capacite_laabal_et_en_attente(config):
    r = planifier_interventions(DEPOTOIRS, config)
    capacite = config["laabal"]["nombre_brigades"] * config["laabal"]["capacite_eradication_par_jour"]
    traites = [a["cible_id"] for t in r["tournees"] for a in t["arrets"]]
    assert len(traites) == capacite
    assert set(traites) == {d["id"] for d in depotoirs_a_traiter(DEPOTOIRS, config)[:capacite]}
    assert {x["depotoir_id"] for x in r["en_attente"]} == {1, 2, 3, 4, 7} - set(traites)
    assert all("capacité Laabal" in x["motif"] for x in r["en_attente"])
    t = r["tournees"][0]
    assert t["type"] == "intervention" and t["camion_id"] is None and t["cout_xof"] == 0
    assert all(a["cible_type"] == "depotoir" and a["raison"] for a in t["arrets"])


def test_plus_de_brigades_traitent_plus(config):
    deux = appliquer_surcharges(config, {"laabal": {"nombre_brigades": 2, "capacite_eradication_par_jour": 3}})
    r = planifier_interventions(DEPOTOIRS, deux)
    assert sum(len(t["arrets"]) for t in r["tournees"]) == 5 and r["en_attente"] == []
    assert planifier_interventions(DEPOTOIRS, deux) == r          # reproductible


def test_sans_brigade(config):
    zero = appliquer_surcharges(config, {"laabal": {"nombre_brigades": 0}})
    r = planifier_interventions(DEPOTOIRS, zero)
    assert r["tournees"] == [] and len(r["en_attente"]) == 5


def test_grande_instance_solution_de_depart_deterministe(config):
    """Au-delà de max_arrets_recherche_locale : solution de départ seule, rapide et reproductible (D38)."""
    petit_seuil = appliquer_surcharges(config, {"collecte": {"max_arrets_recherche_locale": 3}})
    a = planifier_tournees(POINTS, petit_seuil)
    assert a["methode"] == "ortools_rapide"
    assert ids_desservis(a) == [p["id"] for p in POINTS]
    assert planifier_tournees(POINTS, petit_seuil) == a
    complet = planifier_tournees(POINTS, config)
    total = lambda r: sum(t["distance_km"] for t in r["tournees"])
    assert total(complet) <= total(a) + 0.01                      # la recherche locale ne fait pas pire


def test_passage_etale_sur_plusieurs_jours(config):
    """Collecte 2 fois par semaine sur 6 jours ouvrés : 3 jours pour faire le tour des points (D39)."""
    from simulation.tournees import jours_par_passage
    assert jours_par_passage(config) == 1                                      # sans le paramètre
    six = appliquer_surcharges(config, {"collecte": {"jours_ouvres_par_semaine": 6}})
    assert jours_par_passage(six) == 3
    assert jours_par_passage(appliquer_surcharges(six, {"collecte": {"frequence_passages_par_semaine": 7}})) == 1
    gros = [point(i, 12.37 + 0.002 * i, -1.52, stock=5000) for i in range(1, 7)]   # 30 t, 1 camion de 6 t
    un_camion = appliquer_surcharges(six, {"camions": [{"id": "camion_2", "disponible": False},
                                                       {"id": "camion_3", "disponible": False}]})
    r = planifier_tournees(gros, un_camion)
    assert len(ids_desservis(r)) == 6 and r["non_couverts"] == []               # 3 jours × 2 rotations
    assert sorted({t["jour"] for t in r["tournees"]}) == [1, 2, 3]
    c = next(x for x in config["camions"] if x["id"] == "camion_1")
    km = sum(t["distance_km"] for t in r["tournees"])
    assert sum(t["cout_xof"] for t in r["tournees"]) == pytest.approx(km * c["cout_km_xof"] + 3 * c["cout_jour_xof"], abs=10)
