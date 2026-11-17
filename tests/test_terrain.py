import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.exemples import charger_exemples
from backend.main import app
from backend.schemas import Role
from backend.utilisateurs import creer_utilisateur

MDP = "motdepasse-solide"
import cv2 as _cv2
import numpy as _np

PNG = _cv2.imencode(".png", _np.full((32, 32, 3), 180, _np.uint8))[1].tobytes()   # vraie image (masquage, D36)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CHEMIN_DB_DEFAUT", tmp_path / "test.sqlite3")
    monkeypatch.setenv("YILGMDE_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.delenv("YILGMDE_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("YILGMDE_ADMIN_PASSWORD", raising=False)
    with TestClient(app) as c:
        charger_exemples(app.state.db)
        yield c


def compte(client, role, nom=None):
    nom = nom or role.value
    email = f"{nom}@exemple.bf"
    ligne = app.state.db.execute("SELECT id FROM utilisateur WHERE email = ?", (email,)).fetchone()
    uid = ligne["id"] if ligne else creer_utilisateur(app.state.db, nom, email, MDP, role)["id"]
    jeton = client.post("/auth/login", json={"email": email, "mot_de_passe": MDP}).json()["access_token"]
    return uid, {"Authorization": f"Bearer {jeton}"}


def plan(client):
    _, h = compte(client, Role.admin)
    return client.get("/scenarios/1/plan", headers=h).json()


def premiere(plan_, type_):
    return next(t for t in plan_["tournees"] if t["type"] == type_)


def affecter(client, tournee_id, uid):
    _, h = compte(client, Role.admin)
    return client.post(f"/admin/tournees/{tournee_id}/affecter", json={"utilisateur_id": uid}, headers=h)


def test_droits(client):
    _, hc = compte(client, Role.chauffeur)
    _, hl = compte(client, Role.laabal)
    assert client.get("/chauffeur/tournee").status_code == 401
    assert client.get("/chauffeur/tournee", headers=hl).status_code == 403
    assert client.get("/laabal/tournee", headers=hc).status_code == 403
    assert client.post("/admin/tournees/1/affecter", json={"utilisateur_id": 1}, headers=hc).status_code == 403


def test_affectation_et_vue_chauffeur(client):
    uid, hc = compte(client, Role.chauffeur)
    assert client.get("/chauffeur/tournee", headers=hc).json()["tournees"] == []
    t = premiere(plan(client), "collecte")
    r = affecter(client, t["id"], uid)
    assert r.status_code == 200 and r.json()["affectee_a"] == uid
    vue = client.get("/chauffeur/tournee", headers=hc).json()
    assert [x["id"] for x in vue["tournees"]] == [t["id"]] and vue["tournees"][0]["arrets"]


def test_affectation_refusee(client):
    p = plan(client)
    uid_laabal, _ = compte(client, Role.laabal)
    assert affecter(client, premiere(p, "collecte")["id"], uid_laabal).status_code == 422   # mauvais rôle
    assert affecter(client, premiere(p, "collecte")["id"], 999).status_code == 404
    assert affecter(client, 99999, uid_laabal).status_code == 404


def test_cocher_un_arret(client):
    uid, hc = compte(client, Role.chauffeur)
    t = premiere(plan(client), "collecte")
    arret = t["arrets"][0]
    assert client.post(f"/chauffeur/arrets/{arret['id']}/effectue", headers=hc).status_code == 403   # pas affectée
    affecter(client, t["id"], uid)
    r = client.post(f"/chauffeur/arrets/{arret['id']}/effectue", headers=hc)
    assert r.status_code == 200 and r.json()["statut"] == "effectue"
    assert client.post("/chauffeur/arrets/999999/effectue", headers=hc).status_code == 404
    autre_uid, h_autre = compte(client, Role.chauffeur, "autre-chauffeur")
    assert client.post(f"/chauffeur/arrets/{t['arrets'][1]['id']}/effectue", headers=h_autre).status_code == 403


def test_le_travail_du_jour_survit_au_recalcul(client):
    uid, hc = compte(client, Role.chauffeur)
    t = premiere(plan(client), "collecte")
    affecter(client, t["id"], uid)
    arret = t["arrets"][0]
    client.post(f"/chauffeur/arrets/{arret['id']}/effectue", headers=hc)
    with app.state.db:                                   # les données changent : nouveau plan
        app.state.db.execute("UPDATE depotoir SET nb_signalements = nb_signalements + 1 WHERE id = 1")
    nouveau = plan(client)
    assert nouveau["id"] != t["id"]
    mien = [x for x in nouveau["tournees"] if x.get("affectee_a") == uid]
    assert mien and (mien[0]["camion_id"], mien[0]["rotation"]) == (t["camion_id"], t["rotation"])
    effectues = [(a["latitude"], a["longitude"]) for x in nouveau["tournees"] for a in x["arrets"] if a["statut"] == "effectue"]
    assert (arret["latitude"], arret["longitude"]) in effectues


def test_panne_declaree_par_le_chauffeur(client):
    uid, hc = compte(client, Role.chauffeur)
    t = premiere(plan(client), "collecte")
    assert client.post("/chauffeur/incidents", json={"type": "panne"}, headers=hc).status_code == 422   # aucun camion
    affecter(client, t["id"], uid)
    r = client.post("/chauffeur/incidents", json={"type": "panne", "description": "moteur"}, headers=hc)
    assert r.status_code == 200, r.text
    corps = r.json()
    assert corps["camion_id"] == t["camion_id"]
    assert t["camion_id"] in corps["plan"]["indicateurs"]["camions_indisponibles"]
    assert t["camion_id"] not in {x["camion_id"] for x in corps["plan"]["tournees"]}
    assert client.post("/chauffeur/incidents", json={"type": "panne", "camion_id": "camion_99"}, headers=hc).status_code == 404
    r = client.post("/chauffeur/incidents", json={"type": "route_impraticable"}, headers=hc)
    assert r.status_code == 200 and r.json()["plan"] is None
    actions = [l["action"] for l in app.state.db.execute("SELECT action FROM journal_audit ORDER BY id")]
    assert "incident_panne" in actions and "incident_route_impraticable" in actions


def test_laabal_a_traiter_et_tournee(client):
    uid, hl = compte(client, Role.laabal)
    liste = client.get("/laabal/depotoirs-a-traiter", headers=hl).json()
    assert liste and all({"priorite", "raison"} <= set(d) for d in liste)
    assert [d["priorite"] for d in liste] == sorted((d["priorite"] for d in liste), reverse=True)
    t = premiere(plan(client), "intervention")
    affecter(client, t["id"], uid)
    vue = client.get("/laabal/tournee", headers=hl).json()
    assert vue["tournees"][0]["id"] == t["id"] and "en_attente" in vue
    arret = t["arrets"][0]
    assert client.post(f"/laabal/arrets/{arret['id']}/effectue", headers=hl).status_code == 200


def test_cycle_intervention_surveillance(client):
    _, hl = compte(client, Role.laabal)
    did = client.get("/laabal/depotoirs-a-traiter", headers=hl).json()[0]["id"]
    assert client.post(f"/laabal/depotoirs/{did}/surveillance", headers=hl).status_code == 409   # pas éradiqué
    r = client.post(f"/laabal/depotoirs/{did}/intervention", data={"statut": "en_cours"}, headers=hl)
    assert r.status_code == 200 and r.json()["statut_depotoir"] == "intervention_planifiee"
    r = client.post(f"/laabal/depotoirs/{did}/intervention", data={"statut": "eradique"},
                    files={"photo": ("p.png", PNG, "image/png")}, headers=hl)
    assert r.status_code == 200 and r.json() == {"intervention_id": 2, "depotoir_id": did,
                                                 "statut_depotoir": "eradique", "photo": True}
    assert client.post(f"/laabal/depotoirs/{did}/intervention", data={"statut": "eradique"}, headers=hl).status_code == 409
    r = client.post(f"/laabal/depotoirs/{did}/surveillance", headers=hl)
    assert r.status_code == 200 and r.json()["statut_depotoir"] == "sous_surveillance"
    assert did not in [d["id"] for d in client.get("/laabal/depotoirs-a-traiter", headers=hl).json()]
    assert client.post("/laabal/depotoirs/999/surveillance", headers=hl).status_code == 404
    mauvaise = client.post(f"/laabal/depotoirs/{did}/intervention", data={"statut": "en_cours"},
                           files={"photo": ("p.png", b"pas une image", "image/png")}, headers=hl)
    assert mauvaise.status_code == 422


def test_site_officiel_pas_eradique(client):
    _, hl = compte(client, Role.laabal)
    with app.state.db:
        app.state.db.execute("UPDATE depotoir SET legalite = 'officiel' WHERE id = 1")
    assert client.post("/laabal/depotoirs/1/intervention", data={"statut": "en_cours"}, headers=hl).status_code == 409


# --- Constats ---------------------------------------------------------------------------

def test_constat_avec_preuves_et_amende_par_defaut(client):
    uid, hl = compte(client, Role.laabal)
    r = client.post("/laabal/constats", data={"depotoir_id": "1", "description": "dépôt d'un tricycle"},
                    files=[("preuves", ("a.png", PNG, "image/png")), ("preuves", ("b.png", PNG, "image/png"))],
                    headers=hl)
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["preuves"] == 2 and c["montant_xof"] == app.state.config["laabal"]["montant_amende_xof"]
    assert c["laabal_id"] == uid and c["statut"] == "enregistre"
    r2 = client.post("/laabal/constats", data={"depotoir_id": "1", "montant_xof": "2500"}, headers=hl)
    assert r2.status_code == 201 and r2.json()["preuves"] == 0 and r2.json()["montant_xof"] == 2500
    assert [x["id"] for x in client.get("/laabal/constats", headers=hl).json()] == [r2.json()["id"], c["id"]]
    _, h_autre = compte(client, Role.laabal, "autre-laabal")
    assert client.get("/laabal/constats", headers=h_autre).json() == []
    _, ha = compte(client, Role.admin)
    total = client.get("/admin/constats", headers=ha).json()
    assert total["nombre"] == 2 and total["montant_total_xof"] == c["montant_xof"] + 2500
    actions = [l["action"] for l in app.state.db.execute("SELECT action FROM journal_audit")]
    assert actions.count("creer_constat") == 2


def test_constat_refuse(client):
    _, hl = compte(client, Role.laabal)
    assert client.post("/laabal/constats", data={"depotoir_id": "999"}, headers=hl).status_code == 404
    assert client.post("/laabal/constats", data={"depotoir_id": "1", "montant_xof": "-5"}, headers=hl).status_code == 422
    trop = [("preuves", (f"{i}.png", PNG, "image/png")) for i in range(6)]
    assert client.post("/laabal/constats", data={"depotoir_id": "1"}, files=trop, headers=hl).status_code == 422
    faux = [("preuves", ("x.png", b"pas une image", "image/png"))]
    assert client.post("/laabal/constats", data={"depotoir_id": "1"}, files=faux, headers=hl).status_code == 422
    with app.state.db:
        app.state.db.execute("UPDATE depotoir SET legalite = 'officiel' WHERE id = 1")
    assert client.post("/laabal/constats", data={"depotoir_id": "1"}, headers=hl).status_code == 409
    _, hc = compte(client, Role.chauffeur)
    assert client.post("/laabal/constats", data={"depotoir_id": "1"}, headers=hc).status_code == 403
    assert client.get("/admin/constats", headers=hl).status_code == 403


def test_suivi_de_la_flotte(client):
    """D51 : l'admin voit l'avancement réel (arrêts cochés, heure, agent), réservé à l'admin."""
    uid, hc = compte(client, Role.chauffeur)
    _, ha = compte(client, Role.admin)
    assert client.get("/admin/suivi", headers=hc).status_code == 403
    t = premiere(plan(client), "collecte")
    affecter(client, t["id"], uid)
    client.post(f"/chauffeur/arrets/{t['arrets'][0]['id']}/effectue", headers=hc)
    suivi = client.get("/admin/suivi", headers=ha).json()
    assert suivi["depot"]["latitude"] is not None and suivi["jours"]
    vue = next(x for x in suivi["tournees"] if x["id"] == t["id"])
    assert vue["affectee_nom"] == "chauffeur" and vue["arrets_effectues"] == 1
    assert vue["arrets"][0]["statut"] == "effectue" and vue["arrets"][0]["effectue_le"]
    assert vue["arrets"][0]["latitude"] is not None and vue["derniere_activite"] == vue["arrets"][0]["effectue_le"]
    assert all(a["effectue_le"] is None for a in vue["arrets"][1:])
    assert suivi["resume"]["arrets_effectues"] == 1 and suivi["resume"]["tournees_affectees"] == 1
