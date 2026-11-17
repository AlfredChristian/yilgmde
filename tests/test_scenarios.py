import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.exemples import charger_exemples
from backend.main import app
from backend.schemas import Role
from backend.utilisateurs import creer_utilisateur

MDP = "motdepasse-solide"
NOUVEAU_QUARTIER = {
    "type": "Feature",
    "properties": {"nom": "Extension nord", "population": 3000},
    "geometry": {"type": "Polygon", "coordinates": [[[-1.50, 12.42], [-1.49, 12.42], [-1.49, 12.43], [-1.50, 12.43], [-1.50, 12.42]]]},
}


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


def nb_plans():
    return app.state.db.execute("SELECT COUNT(*) FROM plan").fetchone()[0]


def test_scenario_base_actif_au_demarrage(client):
    r = client.get("/scenarios", headers=entetes(client))
    assert r.status_code == 200
    assert [(s["nom"], s["actif"], s["parametres"]) for s in r.json()] == [("base", True, {})]


def test_droits(client):
    assert client.get("/scenarios").status_code == 401
    for role in (Role.chauffeur, Role.laabal):
        assert client.get("/scenarios", headers=entetes(client, role)).status_code == 403
        assert client.put("/scenarios/1/parametres", json={}, headers=entetes(client, role)).status_code == 403
    assert client.get("/points-regroupement").status_code == 200       # public


def test_points_regroupement_public_et_plan_courant(client):
    r = client.get("/points-regroupement").json()
    assert r["type"] == "FeatureCollection" and r["features"]
    p = r["features"][0]
    assert p["geometry"]["type"] == "Point"
    assert {"id", "capacite_kg", "zone_id", "explication"} <= set(p["properties"])
    plan = client.get("/scenarios/1/plan", headers=entetes(client)).json()
    assert plan["id"] == r["plan_id"]
    assert [f["properties"]["id"] for f in r["features"]] == [x["id"] for x in plan["points_regroupement"]]


def test_plan_conforme_au_contrat(client):
    plan = client.post("/scenarios/1/calculer", headers=entetes(client)).json()
    assert {"id", "scenario_id", "calcule_le", "duree_calcul_ms", "points_regroupement", "tournees",
            "indicateurs", "non_couverts"} <= set(plan)
    ids_points = {p["id"] for p in plan["points_regroupement"]}
    collecte = [t for t in plan["tournees"] if t["type"] == "collecte"]
    assert collecte and {t["type"] for t in plan["tournees"]} == {"collecte", "intervention"}
    for t in plan["tournees"]:
        assert {"id", "camion_id", "distance_km", "duree_min", "cout_xof", "arrets"} <= set(t)
        for a in t["arrets"]:
            assert {"id", "ordre", "cible_type", "cible_id", "latitude", "longitude", "statut"} <= set(a)
            if a["cible_type"] == "point_regroupement":
                assert a["cible_id"] in ids_points            # ids de base, pas les ids locaux


def test_pas_de_recalcul_inutile_mais_calcul_force(client):
    h = entetes(client)
    a = client.get("/scenarios/1/plan", headers=h).json()
    b = client.get("/scenarios/1/plan", headers=h).json()
    assert a["id"] == b["id"] and nb_plans() == 1
    c = client.post("/scenarios/1/calculer", headers=h).json()
    assert c["id"] != a["id"] and nb_plans() == 2


def test_recalcul_automatique_quand_les_donnees_changent(client):
    h = entetes(client)
    avant = client.get("/scenarios/1/plan", headers=h).json()
    with app.state.db:
        app.state.db.execute("UPDATE depotoir SET statut = 'eradique' WHERE id = 1")
    apres = client.get("/scenarios/1/plan", headers=h).json()
    assert apres["id"] != avant["id"]
    assert apres["indicateurs"]["depotoirs_actifs"] == avant["indicateurs"]["depotoirs_actifs"] - 1


def test_camion_en_panne(client):
    h = entetes(client)
    r = client.put("/scenarios/1/parametres", json={"camions": [{"id": "camion_2", "disponible": False}]}, headers=h)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert "camion_2" not in {t["camion_id"] for t in plan["tournees"]}
    assert plan["indicateurs"]["camions_indisponibles"] == ["camion_2"]
    scenario = client.get("/scenarios/1", headers=h).json()
    assert scenario["parametres"] == {"camions": [{"id": "camion_2", "disponible": False}]}
    journal = app.state.db.execute("SELECT action FROM journal_audit WHERE objet_type = 'scenario'").fetchall()
    assert [j["action"] for j in journal] == ["modifier_parametres"]


def test_saison_des_pluies_par_raccourci(client):
    h = entetes(client)
    seche = client.get("/scenarios/1/plan", headers=h).json()["indicateurs"]
    pluies = client.put("/scenarios/1/parametres", json={"saison": "pluies"}, headers=h).json()["indicateurs"]
    assert pluies["saison"] == "pluies"
    assert pluies["demande_totale_kg_jour"] > seche["demande_totale_kg_jour"]
    assert client.get("/scenarios/1", headers=h).json()["parametres"] == {"scenario": {"saison": "pluies"}}


def test_nouveau_quartier_s_ajoute(client):
    h = entetes(client)
    plan = client.put("/scenarios/1/parametres", json={"zones_ajoutees": [NOUVEAU_QUARTIER]}, headers=h).json()
    zone = plan["zones_ajoutees"][0]
    assert any(p["zone_id"] == zone for p in plan["points_regroupement"])
    deuxieme = dict(NOUVEAU_QUARTIER, properties={"nom": "Extension sud", "population": 1000})
    import json
    plan = client.put("/scenarios/1/parametres", json={"zones_ajoutees": [json.dumps(deuxieme)]}, headers=h).json()
    assert len(plan["zones_ajoutees"]) == 2                             # ajout, pas remplacement


def test_parametres_invalides_rien_n_est_enregistre(client):
    h = entetes(client)
    for corps in ({"saison": "hiver"},
                  {"zones_ajoutees": [{"type": "Point", "coordinates": [0, 0]}]},
                  {"zones_ajoutees": ["{pas du json"]},
                  {"zones_ajoutees": "pas une liste"}):
        r = client.put("/scenarios/1/parametres", json=corps, headers=h)
        assert r.status_code == 422, corps
    assert client.get("/scenarios/1", headers=h).json()["parametres"] == {}
    assert client.put("/scenarios/99/parametres", json={}, headers=h).status_code == 404
    assert client.get("/scenarios/99/plan", headers=h).status_code == 404


def test_creer_base_sur_et_activer(client):
    h = entetes(client)
    client.put("/scenarios/1/parametres", json={"saison": "pluies"}, headers=h)
    r = client.post("/scenarios", json={"nom": "2 camions en moins", "base_sur": 1,
                                         "parametres": {"camions": [{"id": "camion_1", "disponible": False},
                                                                    {"id": "camion_2", "disponible": False}]}},
                    headers=h)
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["actif"] is False and s["parametres"]["scenario"] == {"saison": "pluies"}
    assert client.post("/scenarios", json={"nom": "x", "base_sur": 42}, headers=h).status_code == 404
    assert client.post("/scenarios", json={"nom": "x", "parametres": {"saison": "hiver"}}, headers=h).status_code == 422

    actif = client.post(f"/scenarios/{s['id']}/activer", headers=h).json()
    assert actif["actif"] is True
    assert [x["actif"] for x in client.get("/scenarios", headers=h).json()] == [False, True]
    points = client.get("/points-regroupement").json()
    assert points["scenario_id"] == s["id"]
    plan = client.get(f"/scenarios/{s['id']}/plan", headers=h).json()
    assert {t["camion_id"] for t in plan["tournees"] if t["type"] == "collecte"} <= {"camion_3"}


def test_scenarios_independants(client):
    h = entetes(client)
    s2 = client.post("/scenarios", json={"nom": "pluies", "parametres": {"saison": "pluies"}}, headers=h).json()
    p1 = client.get("/scenarios/1/plan", headers=h).json()
    p2 = client.get(f"/scenarios/{s2['id']}/plan", headers=h).json()
    assert p1["indicateurs"]["saison"] == "seche" and p2["indicateurs"]["saison"] == "pluies"


def test_simuler(client):
    h = entetes(client)
    r = client.post("/scenarios/1/simuler", json={"jours": 10, "graine": 42}, headers=h)
    assert r.status_code == 200, r.text
    corps = r.json()
    assert corps["graine"] == 42 and len(corps["indicateurs"]) == 10
    assert {"jour", "pct_collecte", "depotoirs_actifs", "cout_xof", "distance_km"} <= set(corps["indicateurs"][0])
    assert client.post("/scenarios/1/simuler", json={"jours": 10, "graine": 42}, headers=h).json() == corps
    lignes = app.state.db.execute("SELECT COUNT(*) FROM indicateur_simulation WHERE plan_id = ?", (corps["plan_id"],)).fetchone()[0]
    assert lignes == 10                                                  # remplacée, pas doublée
    defaut = client.post("/scenarios/1/simuler", headers=h).json()
    assert len(defaut["indicateurs"]) == 30
    assert client.post("/scenarios/1/simuler", json={"jours": 0}, headers=h).status_code == 422
    assert client.post("/scenarios/99/simuler", json={}, headers=h).status_code == 404
    assert client.post("/scenarios/1/simuler", json={}, headers=entetes(client, Role.chauffeur)).status_code == 403


def test_comparer_deux_scenarios_par_simulation(client):
    h = entetes(client)
    s2 = client.post("/scenarios", json={"nom": "pluies", "parametres": {"saison": "pluies"}}, headers=h).json()
    base = client.post("/scenarios/1/simuler", json={"jours": 30, "graine": 1}, headers=h).json()["resume"]
    pluies = client.post(f"/scenarios/{s2['id']}/simuler", json={"jours": 30, "graine": 1}, headers=h).json()["resume"]
    assert pluies["dechets_sauvages_kg"] > base["dechets_sauvages_kg"]
