import json

import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.exemples import DOSSIER_SAMPLE, charger_exemples
from backend.main import app
from backend.schemas import Role
from backend.utilisateurs import creer_utilisateur
from backend.zones import importer_zones_geojson, lire_zones, zone_id_pour_point

MDP = "motdepasse-solide"


@pytest.fixture
def conn():
    c = db.connecter(":memory:")
    db.initialiser(c)
    return c


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CHEMIN_DB_DEFAUT", tmp_path / "test.sqlite3")
    monkeypatch.setenv("YILGMDE_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.delenv("YILGMDE_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("YILGMDE_ADMIN_PASSWORD", raising=False)
    with TestClient(app) as c:
        yield c


def carre(lon0, lat0, lon1, lat1):
    return {"type": "Polygon", "coordinates": [[[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]]}


def collection(*features):
    return {"type": "FeatureCollection", "features": list(features)}


def zone(nom="Z", geometrie=None, **props):
    return {"type": "Feature", "properties": {"nom": nom, **props}, "geometry": geometrie or carre(-1.54, 12.36, -1.51, 12.38)}


# ---------- import ----------

def test_import_et_lecture(conn):
    n = importer_zones_geojson(conn, collection(zone("A", id=5, population=1000, densite=50.0)))
    assert n == 1
    (z,) = lire_zones(conn)
    assert (z["id"], z["nom"], z["population"], z["densite"]) == (5, "A", 1000, 50.0)
    assert z["geometrie"]["type"] == "Polygon"


@pytest.mark.parametrize(
    "mauvaise",
    [
        {"type": "Feature"},                                                    # pas une collection
        collection(zone(nom="")),                                               # nom vide
        collection({"type": "Feature", "properties": {"nom": "X"}, "geometry": {"type": "Point", "coordinates": [0, 0]}}),
        collection({"type": "Feature", "properties": {"nom": "X"}, "geometry": None}),
    ],
)
def test_import_invalide_leve_une_erreur(conn, mauvaise):
    with pytest.raises(ValueError):
        importer_zones_geojson(conn, mauvaise)
    assert conn.execute("SELECT COUNT(*) FROM zone").fetchone()[0] == 0


def test_import_tout_ou_rien(conn):
    mauvaise = collection(zone("Bonne"), zone(nom=""))
    with pytest.raises(ValueError):
        importer_zones_geojson(conn, mauvaise)
    assert conn.execute("SELECT COUNT(*) FROM zone").fetchone()[0] == 0


def test_zone_id_pour_point(conn):
    importer_zones_geojson(conn, collection(zone("A", id=1), zone("B", carre(-1.51, 12.39, -1.48, 12.41), id=2)))
    assert zone_id_pour_point(conn, 12.37, -1.525) == 1
    assert zone_id_pour_point(conn, 12.40, -1.495) == 2
    assert zone_id_pour_point(conn, 5.36, -4.0) is None


# ---------- données d'exemple ----------

def test_charger_exemples_est_idempotent(conn):
    assert charger_exemples(conn) == {"zones": 2, "depotoirs": 3, "signalements": 0}
    assert charger_exemples(conn) == {"zones": 0, "depotoirs": 0, "signalements": 0}
    assert conn.execute("SELECT COUNT(*) FROM depotoir").fetchone()[0] == 3


def test_les_depotoirs_d_exemple_sont_dans_leur_zone(conn):
    charger_exemples(conn)
    for ligne in conn.execute("SELECT latitude, longitude, zone_id FROM depotoir"):
        assert zone_id_pour_point(conn, ligne["latitude"], ligne["longitude"]) == ligne["zone_id"]


def test_la_carte_n_est_plus_vide_apres_chargement(client):
    charger_exemples(app.state.db)
    assert len(client.get("/depotoirs").json()["features"]) == 3
    assert len(client.get("/zones").json()["features"]) == 2


def test_fichiers_d_exemple_presents():
    assert (DOSSIER_SAMPLE / "zones_exemple.geojson").is_file()
    json.loads((DOSSIER_SAMPLE / "zones_exemple.geojson").read_text(encoding="utf-8"))


# ---------- GET /zones ----------

def test_zones_vides_au_depart(client):
    assert client.get("/zones").json() == {"type": "FeatureCollection", "features": []}


def test_zones_avec_demande_selon_la_saison(client):
    importer_zones_geojson(app.state.db, collection(zone("A", id=1, population=10000)))
    par_hab = app.state.config["population"]["production_dechets_kg_hab_jour"]
    f = client.get("/zones").json()["features"][0]
    assert f["geometry"]["type"] == "Polygon"
    assert set(f["properties"]) == {"id", "nom", "population", "densite", "arrondissement", "demande_kg_jour"}
    assert f["properties"]["demande_kg_jour"] == pytest.approx(10000 * par_hab)
    app.state.config["scenario"]["saison"] = "pluies"
    coef = app.state.config["saisons"]["pluies"]["coef_production"]
    assert client.get("/zones").json()["features"][0]["properties"]["demande_kg_jour"] == pytest.approx(10000 * par_hab * coef, abs=0.1)


def test_zone_sans_population_a_une_demande_nulle(client):
    importer_zones_geojson(app.state.db, collection(zone("Sans données", id=1)))
    p = client.get("/zones").json()["features"][0]["properties"]
    assert p["population"] is None and p["demande_kg_jour"] == 0


# ---------- rattachement à la validation (A3) ----------

def _admin(client):
    creer_utilisateur(app.state.db, "Admin", "admin@exemple.bf", MDP, Role.admin)
    jeton = client.post("/auth/login", json={"email": "admin@exemple.bf", "mot_de_passe": MDP}).json()["access_token"]
    return {"Authorization": f"Bearer {jeton}"}


def _signaler_et_valider(client, h, lat, lon, jeton):
    sid = client.post(
        "/signalements",
        data={"latitude": lat, "longitude": lon, "type_dechet": "menager", "volume_estime": "petit"},
        headers={"X-Device-Token": jeton},
    ).json()["id"]
    return client.post(f"/admin/signalements/{sid}/valider", json={}, headers=h).json()["depotoir"]


def test_valider_rattache_le_depotoir_a_sa_zone(client):
    importer_zones_geojson(app.state.db, collection(zone("A", id=3, population=1000)))
    h = _admin(client)
    dans = _signaler_et_valider(client, h, "12.37", "-1.525", "appareil-zone-0001")
    hors = _signaler_et_valider(client, h, "12.45", "-1.40", "appareil-zone-0002")   # dans la ville, hors de toute zone
    assert dans["zone_id"] == 3
    assert hors["zone_id"] is None
    assert client.get("/depotoirs?zone_id=3").json()["features"][0]["properties"]["zone_id"] == 3
