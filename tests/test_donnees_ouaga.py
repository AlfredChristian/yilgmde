"""Livrable 4 : jeu réaliste de Ouagadougou (data/ouaga/) et jeu de signalements ouvert (ODbL)."""

import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.config import charger_config, appliquer_surcharges
from backend.exemples import DOSSIER_OUAGA, charger_exemples
from backend.main import app
from backend.schemas import Role
from backend.utilisateurs import creer_utilisateur
from simulation.geometrie import emprise, point_dans_geometrie
from simulation.plan import calculer_plan

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import generer_donnees_ouaga as gen  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def lire(nom):
    return json.loads((DOSSIER_OUAGA / nom).read_text(encoding="utf-8"))


ZONES, DEPOTOIRS, SIGNALEMENTS = lire("zones.geojson"), lire("depotoirs.geojson"), lire("signalements.geojson")


def test_fichiers_a_jour_avec_le_generateur():
    """Les fichiers commités sont exactement ceux que produit le générateur (déterministe)."""
    rng = random.Random(gen.GRAINE)
    zones = gen.generer_zones()
    depotoirs = gen.generer_depotoirs(rng, zones)
    signalements = gen.generer_signalements(rng, zones, depotoirs)
    assert zones == ZONES["features"] and depotoirs == DEPOTOIRS["features"] and signalements == SIGNALEMENTS["features"]


def test_population_du_recensement_2019():
    par_arr = Counter()
    for f in ZONES["features"]:
        par_arr[f["properties"]["arrondissement"]] += f["properties"]["population"]
    assert dict(par_arr) == gen.POPULATION_2019
    assert sum(par_arr.values()) == 2_415_266
    assert len(ZONES["features"]) == 52


def test_geometrie_coherente():
    config = charger_config("ouagadougou")
    bbox = config["zone_etude"]["bbox"]
    geometries = {f["properties"]["id"]: f["geometry"] for f in ZONES["features"]}
    for g in geometries.values():
        min_lat, min_lon, max_lat, max_lon = emprise(g)
        assert bbox["min_lat"] <= min_lat and max_lat <= bbox["max_lat"]
        assert bbox["min_lon"] <= min_lon and max_lon <= bbox["max_lon"]
    for f in DEPOTOIRS["features"]:
        lon, lat = f["geometry"]["coordinates"]
        assert point_dans_geometrie(lat, lon, geometries[f["properties"]["zone_id"]])
    # chaque secteur est dans le contour réel de la commune (OpenStreetMap), et ils le remplissent
    from shapely.geometry import shape
    from shapely.ops import unary_union
    commune = shape(lire("commune_ouagadougou.geojson")["features"][0]["geometry"])
    secteurs = [shape(g) for g in geometries.values()]
    assert all(commune.buffer(1e-6).contains(s) for s in secteurs)
    assert unary_union(secteurs).area == pytest.approx(commune.area, rel=0.01)
    officiels = [f for f in DEPOTOIRS["features"] if f["properties"]["legalite"] == "officiel"]
    assert len(officiels) == 35                                    # centres de collecte (UN-Habitat)


def test_signalements_anonymes_et_licence():
    assert SIGNALEMENTS["metadata"]["licence"] == "ODbL-1.0" and SIGNALEMENTS["metadata"]["fictif"] is True
    interdits = {"jeton_appareil", "photo", "note_vocale", "description", "code_suivi", "contributeur_id"}
    for f in SIGNALEMENTS["features"]:
        assert not interdits & set(f["properties"])
    nb_par_depotoir = Counter(f["properties"]["depotoir_id"] for f in SIGNALEMENTS["features"]
                              if f["properties"]["statut"] == "verifie")
    for d in DEPOTOIRS["features"]:
        if d["properties"]["legalite"] == "illegal":
            assert nb_par_depotoir[d["properties"]["id"]] == d["properties"]["nb_signalements"]


def test_plan_d_un_arrondissement_rapide_a_l_echelle_reelle():
    config = appliquer_surcharges(charger_config("ouagadougou"), {"perimetre": {"arrondissements": [9]}})
    zones = [{**{k: f["properties"][k] for k in ("id", "nom", "population", "densite", "arrondissement")},
              "geometrie": f["geometry"]} for f in ZONES["features"]]
    depotoirs = [dict(f["properties"], latitude=f["geometry"]["coordinates"][1],
                      longitude=f["geometry"]["coordinates"][0]) for f in DEPOTOIRS["features"]]
    debut = time.perf_counter()
    plan = calculer_plan({"zones": zones, "depotoirs": depotoirs}, config)
    assert time.perf_counter() - debut < 20                         # ~0,5 s en pratique
    ind = plan["indicateurs"]
    assert ind["perimetre"]["population"] == 336_483
    assert ind["nb_points_regroupement"] > 200 and ind["capacite_collecte_pct"] > 90
    assert ind["budget_mensuel_xof"] < config["mairie"]["budget_mensuel_xof"]


# --- Chargement et export public ------------------------------------------------------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CHEMIN_DB_DEFAUT", tmp_path / "test.sqlite3")
    monkeypatch.setenv("YILGMDE_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.delenv("YILGMDE_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("YILGMDE_ADMIN_PASSWORD", raising=False)
    with TestClient(app) as c:
        yield c


def test_chargement_idempotent(client):
    n = charger_exemples(app.state.db, DOSSIER_OUAGA)
    assert n == {"zones": 52, "depotoirs": 215, "signalements": len(SIGNALEMENTS["features"])}
    assert charger_exemples(app.state.db, DOSSIER_OUAGA) == {"zones": 0, "depotoirs": 0, "signalements": 0}
    arr = client.get("/arrondissements").json()
    assert [a["arrondissement"] for a in arr] == list(range(1, 13))
    assert sum(a["population"] for a in arr) == 2_415_266


def test_jeu_ouvert_de_signalements(client):
    charger_exemples(app.state.db, DOSSIER_OUAGA)
    r = client.get("/donnees/signalements.geojson")                 # public, sans connexion
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/geo+json")
    corps = r.json()
    verifies = sum(1 for f in SIGNALEMENTS["features"] if f["properties"]["statut"] == "verifie")
    assert corps["metadata"]["licence"] == "ODbL-1.0" and corps["metadata"]["nombre"] == verifies
    for f in corps["features"]:
        lon, lat = f["geometry"]["coordinates"]
        assert round(lat, 4) == lat and round(lon, 4) == lon           # position arrondie (~11 m)
        assert set(f["properties"]) == {"id", "type_dechet", "volume_estime", "date", "depotoir_id", "zone_id",
                                        "arrondissement"}
        assert len(f["properties"]["date"]) == 10


def test_jeu_ouvert_sans_signalement_non_verifie_ni_donnee_personnelle(client):
    creer_utilisateur(app.state.db, "a", "a@e.bf", "motdepasse-solide", Role.admin)
    r = client.post("/signalements", data={"latitude": "12.371234", "longitude": "-1.519876", "type_dechet": "menager",
                                           "volume_estime": "moyen", "description": "devant chez M. Ouédraogo"},
                    headers={"X-Device-Token": "appareil-ouvert-01"})
    sid = r.json()["id"]
    assert client.get("/donnees/signalements.geojson").json()["features"] == []   # en attente : pas publié
    jeton = client.post("/auth/login", json={"email": "a@e.bf", "mot_de_passe": "motdepasse-solide"}).json()
    client.post(f"/admin/signalements/{sid}/valider", json={}, headers={"Authorization": f"Bearer {jeton['access_token']}"})
    texte = client.get("/donnees/signalements.geojson").text
    assert "Ouédraogo" not in texte and "appareil-ouvert-01" not in texte and "12.371234" not in texte
    f = json.loads(texte)["features"][0]
    assert f["geometry"]["coordinates"] == [-1.5199, 12.3712]
