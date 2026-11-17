import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.exemples import charger_exemples
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
        charger_exemples(app.state.db)
        yield c


def entetes(client, role=Role.admin):
    email = f"{role.value}@exemple.bf"
    if not app.state.db.execute("SELECT 1 FROM utilisateur WHERE email = ?", (email,)).fetchone():
        creer_utilisateur(app.state.db, role.value, email, MDP, role)
    jeton = client.post("/auth/login", json={"email": email, "mot_de_passe": MDP}).json()["access_token"]
    return {"Authorization": f"Bearer {jeton}"}


def actions():
    return [l["action"] for l in app.state.db.execute("SELECT action FROM journal_audit ORDER BY id")]


def point(lat, lon, **props):
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {"type_dechet": "menager", "volume_estime": "moyen", **props}}


def test_droits(client):
    h = entetes(client, Role.laabal)
    assert client.post("/admin/depotoirs", json={"latitude": 12.37, "longitude": -1.52}, headers=h).status_code == 403
    assert client.patch("/admin/depotoirs/1", json={"legalite": "officiel"}, headers=h).status_code == 403
    assert client.post("/admin/signalements/import", json={"type": "FeatureCollection", "features": []},
                       headers=h).status_code == 403
    assert client.post("/admin/depotoirs", json={"latitude": 12.37, "longitude": -1.52}).status_code == 401


# --- B6 : site officiel --------------------------------------------------------------

def test_saisir_un_site_officiel(client):
    h = entetes(client)
    r = client.post("/admin/depotoirs", json={"latitude": 12.37, "longitude": -1.52, "volume_estime": "gros"}, headers=h)
    assert r.status_code == 201, r.text
    d = r.json()
    assert (d["legalite"], d["statut"], d["volume_estime"], d["nb_signalements"]) == ("officiel", "actif", "gros", 0)
    assert actions() == ["creer_depotoir"]
    # un site officiel n'est pas proposé à la brigade Laabal
    a_traiter = client.get("/laabal/depotoirs-a-traiter", headers=entetes(client, Role.laabal)).json()
    assert d["id"] not in [x["id"] for x in a_traiter]
    assert client.post("/admin/depotoirs", json={"latitude": 95, "longitude": -1.52}, headers=h).status_code == 422


def test_changer_la_legalite(client):
    h = entetes(client)
    r = client.patch("/admin/depotoirs/1", json={"legalite": "officiel"}, headers=h)
    assert r.status_code == 200 and r.json()["legalite"] == "officiel"
    assert actions() == ["legalite_officiel"]
    client.patch("/admin/depotoirs/1", json={"legalite": "officiel"}, headers=h)    # sans changement : rien
    assert actions() == ["legalite_officiel"]
    assert client.patch("/admin/depotoirs/999", json={"legalite": "illegal"}, headers=h).status_code == 404
    assert client.patch("/admin/depotoirs/1", json={}, headers=h).status_code == 422


# --- B5 : classement ------------------------------------------------------------------

def test_classer_seulement_sous_surveillance(client):
    h = entetes(client)
    assert client.patch("/admin/depotoirs/1", json={"statut": "classe"}, headers=h).status_code == 409
    assert client.patch("/admin/depotoirs/1", json={"statut": "eradique"}, headers=h).status_code == 422
    with app.state.db:
        app.state.db.execute("UPDATE depotoir SET statut = 'sous_surveillance' WHERE id = 1")
    r = client.patch("/admin/depotoirs/1", json={"statut": "classe"}, headers=h)
    assert r.status_code == 200 and r.json()["statut"] == "classe"
    assert actions() == ["classer_depotoir"]


# --- A4 : import par lot -------------------------------------------------------------

def test_import_passe_par_la_verification(client):
    h = entetes(client)
    lot = {"type": "FeatureCollection", "features": [
        point(12.375, -1.525, description="marché"),
        point(12.37501, -1.52501),                         # doublon du précédent, dans le même lot
        point(12.40, -1.48, type_dechet="plastiques"),
        point(0.0, 0.0),                                   # hors de la commune
        {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": []}, "properties": {}},
        point(12.38, -1.50, type_dechet="nucleaire"),
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": ["a", "b"]}, "properties": {}},
    ]}
    r = client.post("/admin/signalements/import", json=lot, headers=h)
    assert r.status_code == 200, r.text
    corps = r.json()
    assert corps["importes"] == 4 and sum(corps["par_statut"].values()) == 4
    assert [e["index"] for e in corps["erreurs"]] == [4, 5, 6]
    assert "type_dechet" in corps["erreurs"][1]["raison"]
    par_index = {s["index"]: s for s in corps["signalements"]}
    assert par_index[0]["statut"] == "en_attente_revue" and par_index[0]["alertes"] == []
    assert par_index[1]["alertes"] == [f"doublon_probable:{par_index[0]['id']}"]   # doublon dans le même lot
    assert par_index[3]["statut"] == "rejete_auto"         # hors zone
    assert all(s["code_suivi"] for s in corps["signalements"])
    assert actions() == ["importer_signalements"]
    # plus de 5 signalements sans être bloqué par la limite par appareil
    gros = {"type": "FeatureCollection", "features": [point(12.361 + 0.002 * i, -1.535) for i in range(8)]}
    assert client.post("/admin/signalements/import", json=gros, headers=h).json()["par_statut"] == {"en_attente_revue": 8}


def test_import_refuse(client):
    h = entetes(client)
    assert client.post("/admin/signalements/import", json={"type": "Feature"}, headers=h).status_code == 422
    assert client.post("/admin/signalements/import", json={"type": "FeatureCollection", "features": "x"},
                       headers=h).status_code == 422
    app.state.config["import"]["max_par_lot"] = 2
    try:
        lot = {"type": "FeatureCollection", "features": [point(12.37, -1.52)] * 3}
        assert client.post("/admin/signalements/import", json=lot, headers=h).status_code == 413
    finally:
        app.state.config["import"]["max_par_lot"] = 1000
    vide = client.post("/admin/signalements/import", json={"type": "FeatureCollection", "features": []}, headers=h)
    assert vide.json()["importes"] == 0 and actions() == []


def test_import_du_jeu_de_signalements_pieges(client):
    """Le jeu piégé de data/sample/ : chaque entrée finit comme le dit sa colonne `attendu`."""
    import json
    from pathlib import Path

    lot = json.loads(Path("data/sample/signalements_pieges.geojson").read_text(encoding="utf-8"))
    r = client.post("/admin/signalements/import", json=lot, headers=entetes(client))
    assert r.status_code == 200, r.text
    corps = r.json()
    par_index = {s["index"]: s for s in corps["signalements"]}
    en_erreur = {e["index"] for e in corps["erreurs"]}
    id_base = {f["properties"]["id"]: par_index[i]["id"] for i, f in enumerate(lot["features"]) if i in par_index}

    for i, f in enumerate(lot["features"]):
        attendu = f["properties"]["attendu"]
        s = par_index.get(i)
        message = f"entrée {f['properties']['id']} ({f['properties']['categorie']}) : attendu « {attendu} », obtenu {s}"
        if attendu.startswith("rejete:"):                      # entrée invalide : refusée sans planter
            assert i in en_erreur, message
        elif attendu.startswith("rejete_auto:"):
            motifs = {m.strip(" ()") for m in attendu.split(":", 1)[1].replace("ou", " ").split()}
            assert s and s["statut"] == "rejete_auto" and motifs & set(s["alertes"]), message
        elif attendu.startswith("alerte doublon_probable:"):
            ref = int(attendu.split(":")[1].split()[0])
            assert s and s["statut"] == "en_attente_revue", message
            assert f"doublon_probable:{id_base[ref]}" in s["alertes"], message
        elif attendu.startswith("alerte appareil_suspect"):    # 6e signalement en moins d'une heure
            assert s and "limite_appareil" in s["alertes"], message
        else:
            assert attendu.startswith("en_attente_revue"), message
            assert s and s["statut"] == "en_attente_revue", message
            # Importée avec tout le lot, l'entrée 6 (à 40 m de la 1) est à 15 m de la 5 : alerte légitime.
            # On vérifie seulement qu'elle n'est pas prise pour un doublon de la référence (entrée 1).
            if f["properties"]["categorie"] == "non_doublon_limite":
                assert f"doublon_probable:{id_base[1]}" not in s["alertes"], message
