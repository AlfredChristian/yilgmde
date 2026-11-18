"""D62 : journée simulée d'un quartier (ménages, précollecteurs, points, camion)."""

import numpy as np
import pytest

from backend.config import charger_config
from backend.schemas import Role
from simulation.quartier import cercle, fenetre, journee_quartier
from tests.test_terrain import client, compte  # noqa: F401  (fixture réutilisée)

C = (12.37, -1.52)
ZONE = {"id": 7, "nom": "Secteur essai", "population": 6000, "geometrie": cercle(C[0], C[1], 600)}
POINTS = [{"id": 1, "latitude": C[0], "longitude": C[1]}, {"id": 2, "latitude": C[0] + 0.003, "longitude": C[1] + 0.002}]


@pytest.fixture
def config():
    c = charger_config("ouagadougou")
    c["quartier"]["maisons_affichees"] = 80
    return c


def maisons(n=400, graine=3):
    rng = np.random.default_rng(graine)
    return np.column_stack([C[0] + rng.normal(0, 0.002, n), C[1] + rng.normal(0, 0.002, n), rng.uniform(40, 200, n)])


def journee(config, graine=1, depotoirs=()):
    return journee_quartier(ZONE, maisons(), POINTS, list(depotoirs), (12.43, -1.47), config, graine)


def test_chaque_maison_a_un_role_et_les_parts_suivent_les_regles(config):
    j = journee(config)
    assert len(j["maisons"]) == 80
    r = j["resume"]
    assert r["abonnes"] + r["apport_volontaire"] + r["depot_sauvage"] == 80
    assert 0.1 < r["abonnes"] / 80 < 0.5            # taux d'abonnement 30 %
    assert j["echelle"]["menages_par_maison"] == pytest.approx(6000 / 6 / 80, rel=0.01)
    pietons = {p["maison_id"] for p in j["pietons"]}
    ramassees = {a["maison_id"] for t in j["tricycles"] for a in t["arrets"]}
    for m in j["maisons"]:
        assert (m["id"] in ramassees) == (m["mode"] == "abonne") and (m["id"] in pietons) == (m["mode"] != "abonne")


def test_horaires_coherents(config):
    j = journee(config)
    par_id = {m["id"]: m for m in j["maisons"]}
    for t in j["tricycles"]:
        temps = [s["t0"] for s in t["segments"]]
        assert temps == sorted(temps)
        for a in t["arrets"]:
            assert a["t"] >= par_id[a["maison_id"]]["sortie_min"]       # la poubelle était dehors
        assert t["vidage_min"] >= t["arrets"][-1]["t"]
    for p in j["pietons"]:
        aller, depose, retour = p["segments"]
        assert aller["t1"] == depose["t0"] and depose["t1"] == retour["t0"]
        assert aller["t0"] >= par_id[p["maison_id"]]["sortie_min"]
    for c in j["camions"]:
        dernier = max([t["vidage_min"] for t in j["tricycles"] if t["point_id"] == c["point_id"]]
                      + [p["segments"][1]["t0"] for p in j["pietons"]
                         if p["mode"] == "apport" and par_id[p["maison_id"]]["point_id"] == c["point_id"]])
        assert c["segments"][1]["t0"] > dernier                         # le camion passe après le dernier apport
    assert j["horaire"]["debut"] < j["horaire"]["fin"]


def test_meme_graine_meme_matinee_autre_graine_autre_matinee(config):
    a, b, c = journee(config, 1), journee(config, 1), journee(config, 2)
    assert a == b
    assert [m["mode"] for m in a["maisons"]] != [m["mode"] for m in c["maisons"]]


def test_depot_sauvage_au_depotoir_connu_sinon_sur_un_terrain_vague(config):
    j = journee(config)
    assert len(j["sauvages"]) == 1 and not j["sauvages"][0]["existant"]
    connu = {"id": 42, "latitude": C[0] - 0.003, "longitude": C[1] - 0.003, "statut": "actif"}
    j2 = journee(config, depotoirs=[connu])
    assert j2["sauvages"][0]["existant"] and j2["sauvages"][0]["depotoir_id"] == 42
    assert all(m["sauvage_id"] == "d42" for m in j2["maisons"] if m["mode"] == "sauvage")


def test_le_quartier_est_centre_sur_le_point_le_plus_habite():
    b = maisons()
    loin = {"id": 9, "latitude": C[0] + 0.02, "longitude": C[1] + 0.02}
    centre, sous, proches, part = fenetre(ZONE, b, [loin, *POINTS], 450)
    assert centre["id"] == 1 and proches[0]["id"] == 1 and 9 not in [p["id"] for p in proches]
    assert 0 < part <= 1 and len(sous) < len(b)


def test_api(client):
    _, hl = compte(client, Role.laabal)
    _, ha = compte(client, Role.admin)
    assert client.get("/admin/simulation-quartier/secteurs", headers=hl).status_code == 403
    secteurs = client.get("/admin/simulation-quartier/secteurs", headers=ha).json()
    assert secteurs and all(s["points"] > 0 for s in secteurs)
    r = client.get(f"/admin/simulation-quartier?zone_id={secteurs[0]['id']}", headers=ha)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["maisons"] and j["points"] and j["centre"]["point_id"] == j["points"][0]["id"]
    assert client.get("/admin/simulation-quartier?zone_id=999999", headers=ha).status_code == 404
