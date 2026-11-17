import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.main import app
from backend.schemas import Role
from backend.utilisateurs import creer_utilisateur

MDP = "motdepasse-solide"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CHEMIN_DB_DEFAUT", tmp_path / "test.sqlite3")
    monkeypatch.setenv("YILGMDE_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.delenv("YILGMDE_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("YILGMDE_ADMIN_PASSWORD", raising=False)
    with TestClient(app) as c:
        conn = app.state.db
        depotoirs = [
            (1, 12.3701, -1.5201, "actif", "illegal", 2),
            (2, 12.3802, -1.5102, "eradique", "illegal", 1),
            (3, 12.3903, -1.5003, "actif", "officiel", 1),
            (4, 12.3604, -1.5304, "intervention_planifiee", "illegal", 1),
            (5, 12.3505, -1.5405, "sous_surveillance", "illegal", 1),
        ]
        with conn:
            for id_, la, lo, statut, legalite, nb in depotoirs:
                conn.execute(
                    "INSERT INTO depotoir (id, latitude, longitude, volume_estime, statut, legalite, nb_signalements,"
                    " premiere_detection, derniere_maj) VALUES (?, ?, ?, 'moyen', ?, ?, ?, '2026-11-01T08:00:00+00:00',"
                    " '2026-11-15T10:30:00+00:00')",
                    (id_, la, lo, statut, legalite, nb),
                )
            signalements = [
                (1, "plastiques", "verifie", "Derrière la maison de M. Ouédraogo"),
                (1, "plastiques", "verifie", None),
                (1, "gravats", "verifie", None),
                (1, "organique", "rejete", None),          # non vérifié : ignoré
                (4, "encombrants", "verifie", None),
            ]
            for i, (dep, type_, statut, desc) in enumerate(signalements):
                conn.execute(
                    "INSERT INTO signalement (latitude, longitude, photo, description, type_dechet, volume_estime,"
                    " code_suivi, statut, depotoir_id, cree_le) VALUES (12.37, -1.52, 'photo.jpg', ?, ?, 'moyen', ?, ?, ?,"
                    " '2026-11-10T09:00:00+00:00')",
                    (desc, type_, f"YG-{i}", statut, dep),
                )
        yield c


def entetes(client, role=Role.admin):
    email = f"{role.value}@exemple.bf"
    if not app.state.db.execute("SELECT 1 FROM utilisateur WHERE email = ?", (email,)).fetchone():
        creer_utilisateur(app.state.db, role.value, email, MDP, role)
    jeton = client.post("/auth/login", json={"email": email, "mot_de_passe": MDP}).json()["access_token"]
    return {"Authorization": f"Bearer {jeton}"}


def export(client, **params):
    r = client.get("/admin/export/depotoirs.geojson", params=params, headers=entetes(client))
    assert r.status_code == 200, r.text
    return r


def test_reserve_a_l_admin(client):
    assert client.get("/admin/export/depotoirs.geojson").status_code == 401
    for role in (Role.chauffeur, Role.laabal):
        assert client.get("/admin/export/depotoirs.geojson", headers=entetes(client, role)).status_code == 403


def test_fichier_telechargeable(client):
    r = export(client)
    assert r.headers["content-type"].startswith("application/geo+json")
    assert "depotoirs_yilgmde.geojson" in r.headers["content-disposition"]
    corps = r.json()
    assert corps["type"] == "FeatureCollection" and corps["metadata"]["nombre"] == len(corps["features"])
    assert corps["metadata"]["commune"] == "Ouagadougou"


def test_seuls_les_depotoirs_sur_le_terrain_par_defaut(client):
    ids = [f["id"] for f in export(client).json()["features"]]
    assert ids == ["yilgmde/depotoir/1", "yilgmde/depotoir/3", "yilgmde/depotoir/4"]
    tous = export(client, statut=["actif", "eradique", "sous_surveillance"]).json()
    assert [f["id"] for f in tous["features"]] == ["yilgmde/depotoir/1", "yilgmde/depotoir/2",
                                                   "yilgmde/depotoir/3", "yilgmde/depotoir/5"]
    r = client.get("/admin/export/depotoirs.geojson", params={"statut": "inconnu"}, headers=entetes(client))
    assert r.status_code == 422


def test_etiquettes_osm(client):
    f = {x["id"]: x for x in export(client).json()["features"]}
    illegal = f["yilgmde/depotoir/1"]
    assert illegal["geometry"] == {"type": "Point", "coordinates": [-1.5201, 12.3701]}
    assert illegal["properties"] == {
        "amenity": "waste_dump_site",
        "waste": "plastic",                                 # gravats : pas de valeur OSM claire
        "description": "Déchets plastiques, gravats",       # le plus fréquent d'abord ; rejeté ignoré
        "check_date": "2026-11-15",
        "source": "survey;YilGmdé",
    }
    assert f["yilgmde/depotoir/3"]["properties"]["landuse"] == "landfill"
    assert "amenity" not in f["yilgmde/depotoir/3"]["properties"]
    assert "waste" not in f["yilgmde/depotoir/4"]["properties"]


def test_aucune_donnee_personnelle(client):
    texte = export(client).text
    for interdit in ("Ouédraogo", "photo", "contributeur", "code_suivi", "YG-", "nb_signalements"):
        assert interdit not in texte


def test_seuil_de_signalements_et_journal(client, monkeypatch):
    monkeypatch.setitem(app.state.config, "export_osm", dict(app.state.config["export_osm"], min_signalements=2))
    assert [f["id"] for f in export(client).json()["features"]] == ["yilgmde/depotoir/1"]
    actions = [l["action"] for l in app.state.db.execute("SELECT action FROM journal_audit")]
    assert actions.count("export_osm") == 1
