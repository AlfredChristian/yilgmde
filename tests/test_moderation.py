import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.main import app
from backend.schemas import Role
from backend.utilisateurs import creer_utilisateur

MDP = "motdepasse-solide"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CHEMIN_DB_DEFAUT", tmp_path / "test.sqlite3")
    monkeypatch.setenv("YILGMDE_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.delenv("YILGMDE_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("YILGMDE_ADMIN_PASSWORD", raising=False)
    with TestClient(app) as c:
        yield c


def entetes(client, role=Role.admin):
    email = f"{role.value}@exemple.bf"
    existe = app.state.db.execute("SELECT 1 FROM utilisateur WHERE email = ?", (email,)).fetchone()
    if not existe:
        creer_utilisateur(app.state.db, role.value, email, MDP, role)
    jeton = client.post("/auth/login", json={"email": email, "mot_de_passe": MDP}).json()["access_token"]
    return {"Authorization": f"Bearer {jeton}"}


_compteur = {"n": 0}


def signaler(client, lat="12.3714", lon="-1.5197", volume="moyen", photo=False):
    """Envoie un signalement citoyen avec un appareil neuf (évite la limite par appareil)."""
    _compteur["n"] += 1
    r = client.post(
        "/signalements",
        data={"latitude": lat, "longitude": lon, "type_dechet": "menager", "volume_estime": volume},
        files={"photo": ("p.png", PNG, "image/png")} if photo else None,
        headers={"X-Device-Token": f"appareil-moderation-{_compteur['n']:04d}"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def valider(client, sid, fusionner_avec=None, role=Role.admin):
    corps = {"fusionner_avec": fusionner_avec}
    return client.post(f"/admin/signalements/{sid}/valider", json=corps, headers=entetes(client, role))


def rejeter(client, sid, motif="photo sans rapport", role=Role.admin):
    return client.post(f"/admin/signalements/{sid}/rejeter", json={"motif": motif}, headers=entetes(client, role))


def depotoir_en_base(did):
    return app.state.db.execute("SELECT * FROM depotoir WHERE id = ?", (did,)).fetchone()


# ---------- droits ----------

@pytest.mark.parametrize(
    "methode, url",
    [
        ("get", "/admin/signalements"),
        ("get", "/admin/signalements/1/photo"),
        ("post", "/admin/signalements/1/valider"),
        ("post", "/admin/signalements/1/rejeter"),
    ],
)
def test_sans_jeton_401(client, methode, url):
    assert getattr(client, methode)(url).status_code == 401


@pytest.mark.parametrize("role", [Role.chauffeur, Role.laabal])
def test_roles_non_admin_403(client, role):
    sid = signaler(client)["id"]
    h = entetes(client, role)
    assert client.get("/admin/signalements", headers=h).status_code == 403
    assert client.get(f"/admin/signalements/{sid}/photo", headers=h).status_code == 403
    assert valider(client, sid, role=role).status_code == 403
    assert rejeter(client, sid, role=role).status_code == 403
    # rien n'a changé
    assert app.state.db.execute("SELECT statut FROM signalement WHERE id = ?", (sid,)).fetchone()[0] == "en_attente_revue"
    assert app.state.db.execute("SELECT COUNT(*) FROM depotoir").fetchone()[0] == 0


# ---------- GET /admin/signalements ----------

def test_file_de_moderation(client):
    premier = signaler(client, lat="12.30")["id"]
    second = signaler(client, lat="12.40")["id"]
    rejete = signaler(client, lat="5.36", lon="-4.0083")["id"]    # rejeté d'office
    h = entetes(client)

    attente = client.get("/admin/signalements?statut=en_attente_revue", headers=h).json()
    assert [s["id"] for s in attente] == [premier, second]         # les plus anciens d'abord
    ligne = attente[0]
    assert set(ligne) >= {"id", "latitude", "longitude", "type_dechet", "volume_estime", "photo_url",
                          "statut", "score_auto", "alertes", "cree_le", "motif", "depotoir_id"}
    assert ligne["photo_url"] is None and ligne["score_auto"] == 1.0

    auto = client.get("/admin/signalements?statut=rejete_auto", headers=h).json()
    assert [s["id"] for s in auto] == [rejete] and auto[0]["motif"] == "hors zone d'étude"
    assert len(client.get("/admin/signalements", headers=h).json()) == 3
    assert client.get("/admin/signalements?statut=bidon", headers=h).status_code == 422


def test_la_file_montre_les_alertes_de_la_verification(client):
    signaler(client)
    doublon = signaler(client)                                       # même endroit
    liste = client.get("/admin/signalements?statut=en_attente_revue", headers=entetes(client)).json()
    assert liste[1]["id"] == doublon["id"]
    assert liste[1]["alertes"] == ["doublon_probable:1"] and liste[1]["score_auto"] < 1


# ---------- valider : création ----------

def test_valider_cree_un_depotoir_actif(client):
    sid = signaler(client, volume="gros")["id"]
    r = valider(client, sid)
    assert r.status_code == 200
    corps = r.json()
    assert corps["signalement"]["statut"] == "verifie"
    d = corps["depotoir"]
    assert (d["statut"], d["legalite"], d["nb_signalements"], d["nb_reapparitions"]) == ("actif", "illegal", 1, 0)
    assert (d["latitude"], d["longitude"], d["volume_estime"]) == (12.3714, -1.5197, "gros")
    assert corps["signalement"]["depotoir_id"] == d["id"]


def test_valider_est_visible_sur_la_carte_publique_et_au_suivi(client):
    r = signaler(client)
    assert client.get("/depotoirs").json()["features"] == []         # pas public tant que non vérifié
    valider(client, r["id"])
    features = client.get("/depotoirs").json()["features"]
    assert len(features) == 1 and features[0]["properties"]["statut"] == "actif"
    suivi = client.get(f"/signalements/suivi/{r['code_suivi']}").json()
    assert suivi["statut"] == "verifie" and suivi["depotoir_id"] == features[0]["properties"]["id"]


def test_valider_sans_corps(client):
    sid = signaler(client)["id"]
    r = client.post(f"/admin/signalements/{sid}/valider", headers=entetes(client))
    assert r.status_code == 200 and r.json()["depotoir"]["nb_signalements"] == 1


# ---------- valider : fusion et réapparition ----------

def test_fusion_ne_duplique_pas(client):
    a = signaler(client)["id"]
    did = valider(client, a).json()["depotoir"]["id"]
    b = signaler(client)["id"]                                       # même endroit
    r = valider(client, b, fusionner_avec=did)
    assert r.status_code == 200
    assert r.json()["depotoir"]["id"] == did
    assert r.json()["depotoir"]["nb_signalements"] == 2 and r.json()["depotoir"]["statut"] == "actif"
    assert r.json()["depotoir"]["nb_reapparitions"] == 0
    assert app.state.db.execute("SELECT COUNT(*) FROM depotoir").fetchone()[0] == 1


@pytest.mark.parametrize("ancien_statut", ["eradique", "sous_surveillance", "classe"])
def test_fusion_dans_un_depotoir_traite_est_une_reapparition(client, ancien_statut):
    did = valider(client, signaler(client)["id"]).json()["depotoir"]["id"]
    app.state.db.execute("UPDATE depotoir SET statut = ? WHERE id = ?", (ancien_statut, did))
    app.state.db.commit()
    r = valider(client, signaler(client)["id"], fusionner_avec=did)
    d = r.json()["depotoir"]
    assert d["statut"] == "actif" and d["nb_reapparitions"] == 1 and d["nb_signalements"] == 2


def test_fusion_dans_un_depotoir_planifie_ne_change_pas_son_statut(client):
    did = valider(client, signaler(client)["id"]).json()["depotoir"]["id"]
    app.state.db.execute("UPDATE depotoir SET statut = 'intervention_planifiee' WHERE id = ?", (did,))
    app.state.db.commit()
    d = valider(client, signaler(client)["id"], fusionner_avec=did).json()["depotoir"]
    assert d["statut"] == "intervention_planifiee" and d["nb_reapparitions"] == 0


def test_fusion_avec_un_depotoir_inconnu_404_sans_effet(client):
    sid = signaler(client)["id"]
    assert valider(client, sid, fusionner_avec=999).status_code == 404
    assert app.state.db.execute("SELECT statut FROM signalement WHERE id = ?", (sid,)).fetchone()[0] == "en_attente_revue"
    assert app.state.db.execute("SELECT COUNT(*) FROM depotoir").fetchone()[0] == 0


# ---------- rejeter ----------

def test_rejeter_avec_motif(client):
    r = signaler(client)
    rep = rejeter(client, r["id"], motif="  photo sans rapport  ")
    assert rep.status_code == 200
    assert rep.json()["statut"] == "rejete" and rep.json()["motif"] == "photo sans rapport"
    suivi = client.get(f"/signalements/suivi/{r['code_suivi']}").json()
    assert suivi["statut"] == "rejete" and suivi["motif"] == "photo sans rapport"
    assert client.get("/depotoirs").json()["features"] == []
    assert app.state.db.execute("SELECT COUNT(*) FROM depotoir").fetchone()[0] == 0


@pytest.mark.parametrize("corps", [{}, {"motif": ""}, {"motif": "   "}, {"motif": "x" * 301}])
def test_rejeter_exige_un_motif(client, corps):
    sid = signaler(client)["id"]
    r = client.post(f"/admin/signalements/{sid}/rejeter", json=corps, headers=entetes(client))
    assert r.status_code == 422
    assert app.state.db.execute("SELECT statut FROM signalement WHERE id = ?", (sid,)).fetchone()[0] == "en_attente_revue"


# ---------- états et identifiants ----------

def test_un_signalement_ne_se_traite_qu_une_fois(client):
    a, b, c = (signaler(client, lat=f"12.{30 + i}")["id"] for i in range(3))
    valider(client, a)
    rejeter(client, b)
    for sid in (a, b):
        assert valider(client, sid).status_code == 409
        assert rejeter(client, sid).status_code == 409
    rejete_auto = signaler(client, lat="5.36", lon="-4.0083")["id"]
    assert valider(client, rejete_auto).status_code == 409           # déjà rejeté d'office
    assert app.state.db.execute("SELECT COUNT(*) FROM depotoir").fetchone()[0] == 1
    assert app.state.db.execute("SELECT statut FROM signalement WHERE id = ?", (c,)).fetchone()[0] == "en_attente_revue"


def test_signalement_inconnu_404(client):
    assert valider(client, 999).status_code == 404
    assert rejeter(client, 999).status_code == 404


# ---------- journal d'audit (règle 5) ----------

def test_actions_tracees_dans_le_journal(client):
    a, b = signaler(client, lat="12.30")["id"], signaler(client, lat="12.40")["id"]
    valider(client, a)
    rejeter(client, b)
    lignes = app.state.db.execute(
        "SELECT action, objet_type, objet_id, utilisateur_id FROM journal_audit ORDER BY id"
    ).fetchall()
    assert [(l["action"], l["objet_type"], l["objet_id"]) for l in lignes] == [
        ("valider_signalement", "signalement", a),
        ("rejeter_signalement", "signalement", b),
    ]
    assert all(l["utilisateur_id"] is not None for l in lignes)
    assert app.state.db.execute("SELECT valide_par FROM signalement WHERE id = ?", (a,)).fetchone()[0] is not None


def test_echec_n_ecrit_rien_dans_le_journal(client):
    sid = signaler(client)["id"]
    valider(client, sid, fusionner_avec=999)
    rejeter(client, 999)
    assert app.state.db.execute("SELECT COUNT(*) FROM journal_audit").fetchone()[0] == 0


# ---------- photos ----------

def test_l_admin_peut_voir_la_photo(client):
    sid = signaler(client, photo=True)["id"]
    h = entetes(client)
    ligne = client.get("/admin/signalements?statut=en_attente_revue", headers=h).json()[0]
    assert ligne["photo_url"] == f"/admin/signalements/{sid}/photo"
    r = client.get(ligne["photo_url"], headers=h)
    assert r.status_code == 200 and r.content == PNG and r.headers["content-type"] == "image/png"


def test_pas_de_photo_404(client):
    sid = signaler(client)["id"]
    assert client.get(f"/admin/signalements/{sid}/photo", headers=entetes(client)).status_code == 404
    assert client.get("/admin/signalements/999/photo", headers=entetes(client)).status_code == 404


def test_les_photos_ne_sont_pas_servies_publiquement(client):
    sid = signaler(client, photo=True)["id"]
    for url in (f"/uploads/{sid}.png", f"/admin/signalements/{sid}/photo"):
        assert client.get(url).status_code in (401, 404)
