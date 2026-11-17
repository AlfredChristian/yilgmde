import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.config import charger_config
from backend.confiance import nouveau_score
from backend.main import app
from backend.schemas import Role
from backend.utilisateurs import creer_utilisateur

MDP = "motdepasse-solide"


@pytest.fixture
def config():
    return charger_config("ouagadougou")


def test_formules(config):
    g = config["verification"]["gain_confiance_validation"]
    p = config["verification"]["perte_confiance_rejet"]
    assert nouveau_score(0.5, "valide", config) == pytest.approx(0.5 + g * 0.5)
    assert nouveau_score(0.5, "rejete", config) == pytest.approx(0.5 - p * 0.5)
    with pytest.raises(ValueError):
        nouveau_score(0.5, "peut-etre", config)


def test_toujours_entre_0_et_1_et_asymetrique(config):
    s = 0.5
    for _ in range(100):
        s = nouveau_score(s, "valide", config)
    assert 0.99 < s <= 1.0
    for _ in range(100):
        s = nouveau_score(s, "rejete", config)
    assert 0.0 <= s < 0.01
    un_rejet = nouveau_score(0.5, "rejete", config)
    assert nouveau_score(un_rejet, "valide", config) < 0.5            # une validation ne rattrape pas un rejet


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CHEMIN_DB_DEFAUT", tmp_path / "test.sqlite3")
    monkeypatch.setenv("YILGMDE_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.delenv("YILGMDE_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("YILGMDE_ADMIN_PASSWORD", raising=False)
    with TestClient(app) as c:
        creer_utilisateur(app.state.db, "Awa", "awa@exemple.bf", MDP, Role.admin)
        jeton = c.post("/auth/login", json={"email": "awa@exemple.bf", "mot_de_passe": MDP}).json()["access_token"]
        c.headers.update({"Authorization": f"Bearer {jeton}"})
        yield c


def signaler(client, appareil, lat):
    r = client.post("/signalements", data={"latitude": str(lat), "longitude": "-1.5197", "type_dechet": "menager",
                                            "volume_estime": "moyen"}, headers={"X-Device-Token": appareil})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def score(appareil):
    return app.state.db.execute("SELECT score_confiance FROM contributeur WHERE jeton_appareil = ?", (appareil,)).fetchone()[0]


def test_moderation_fait_evoluer_le_score(client):
    cfg = app.state.config
    a = signaler(client, "appareil-fiable-0001", 12.3714)
    b = signaler(client, "appareil-douteux-0001", 12.3814)
    assert client.post(f"/admin/signalements/{a}/valider", json={}).status_code == 200
    assert client.post(f"/admin/signalements/{b}/rejeter", json={"motif": "faux"}).status_code == 200
    assert score("appareil-fiable-0001") == nouveau_score(0.5, "valide", cfg)
    assert score("appareil-douteux-0001") == nouveau_score(0.5, "rejete", cfg)


def test_rejets_repetes_rendent_l_appareil_peu_fiable_pour_a2(client):
    cfg = app.state.config
    seuil = cfg["verification"]["seuil_confiance_appareil"]
    s, n = 0.5, 0
    while s >= seuil:
        s, n = nouveau_score(s, "rejete", cfg), n + 1
    for i in range(n):
        sid = signaler(client, "appareil-spam-0001", 12.30 + 0.01 * i)
        client.post(f"/admin/signalements/{sid}/rejeter", json={"motif": "faux"})
    assert score("appareil-spam-0001") < seuil
    nouveau = client.post("/signalements", data={"latitude": "12.45", "longitude": "-1.5197", "type_dechet": "menager",
                                                  "volume_estime": "moyen"}, headers={"X-Device-Token": "appareil-spam-0001"})
    sid = nouveau.json()["id"]
    alertes = client.get("/admin/signalements", params={"statut": "en_attente_revue"}).json()
    vu = [x for x in alertes if x["id"] == sid]
    assert vu and any("fiable" in a for a in vu[0]["alertes"])
