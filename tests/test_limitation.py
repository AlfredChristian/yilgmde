import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.limitation import LimiteurTentatives, creer_limiteurs
from backend.main import app
from backend.schemas import Role
from backend.utilisateurs import creer_utilisateur

MDP = "motdepasse-solide"


class Horloge:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


# --- Limiteur seul -------------------------------------------------------------------

def test_blocage_apres_n_echecs_puis_deblocage():
    h = Horloge()
    lim = LimiteurTentatives(3, fenetre_s=60, blocage_s=120, horloge=h)
    assert not lim.echec("a") and not lim.echec("a")
    assert lim.attente_s("a") == 0
    assert lim.echec("a") is True
    assert lim.attente_s("a") == 120
    h.t += 119
    assert lim.attente_s("a") == pytest.approx(1)
    h.t += 1
    assert lim.attente_s("a") == 0
    assert not lim.echec("a")                       # compteur reparti de zéro après le blocage


def test_fenetre_glissante_et_succes():
    h = Horloge()
    lim = LimiteurTentatives(3, fenetre_s=60, blocage_s=120, horloge=h)
    lim.echec("a"); lim.echec("a")
    h.t += 61                                       # les deux échecs sortent de la fenêtre
    assert not lim.echec("a") and not lim.echec("a")
    lim.succes("a")
    assert not lim.echec("a") and not lim.echec("a")
    assert lim.attente_s("b") == 0                  # les clés sont indépendantes


def test_nettoyer_borne_la_memoire():
    h = Horloge()
    lim = LimiteurTentatives(2, fenetre_s=60, blocage_s=60, horloge=h)
    lim.echec("x"); lim.echec("y"); lim.echec("y")
    h.t += 61
    lim.nettoyer()
    assert lim._echecs == {} and lim._bloque_jusqu_a == {}


def test_parametres_de_la_config():
    lim = creer_limiteurs({"securite": {"max_echecs_par_email": 2, "max_echecs_par_ip": 7,
                                        "fenetre_echecs_min": 1, "blocage_min": 3}})
    assert (lim["email"].max_echecs, lim["ip"].max_echecs) == (2, 7)
    assert (lim["email"].fenetre_s, lim["email"].blocage_s) == (60, 180)


# --- Route /auth/login -----------------------------------------------------------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CHEMIN_DB_DEFAUT", tmp_path / "test.sqlite3")
    monkeypatch.setenv("YILGMDE_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.delenv("YILGMDE_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("YILGMDE_ADMIN_PASSWORD", raising=False)
    with TestClient(app) as c:
        creer_utilisateur(app.state.db, "Awa", "awa@exemple.bf", MDP, Role.admin)
        yield c


def login(client, email="awa@exemple.bf", mdp=MDP):
    return client.post("/auth/login", json={"email": email, "mot_de_passe": mdp})


def test_email_bloque_meme_avec_le_bon_mot_de_passe(client):
    n = app.state.config["securite"]["max_echecs_par_email"]
    for _ in range(n):
        assert login(client, mdp="mauvais-mot-de-passe").status_code == 401
    r = login(client)
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) == app.state.config["securite"]["blocage_min"] * 60
    assert "trop de tentatives" in r.json()["detail"]
    actions = [l["action"] for l in app.state.db.execute("SELECT action FROM journal_audit")]
    assert actions == ["connexion_bloquee_email"]


def test_succes_remet_a_zero(client):
    n = app.state.config["securite"]["max_echecs_par_email"]
    for _ in range(n - 1):
        login(client, mdp="mauvais-mot-de-passe")
    assert login(client).status_code == 200
    for _ in range(n - 1):
        assert login(client, mdp="mauvais-mot-de-passe").status_code == 401
    assert login(client).status_code == 200


def test_meme_traitement_pour_un_compte_inexistant(client):
    n = app.state.config["securite"]["max_echecs_par_email"]
    for _ in range(n):
        assert login(client, email="personne@exemple.bf", mdp="xxxxxxxx").status_code == 401
    assert login(client, email="personne@exemple.bf", mdp="xxxxxxxx").status_code == 429
    assert login(client).status_code == 200          # un autre e-mail n'est pas bloqué


def test_blocage_par_ip_sur_plusieurs_comptes(client):
    n = app.state.config["securite"]["max_echecs_par_ip"]
    for i in range(n):                               # e-mails tous différents : seul le compteur IP monte
        assert login(client, email=f"essai{i}@exemple.bf", mdp="xxxxxxxx").status_code == 401
    assert login(client).status_code == 429          # même le bon compte, depuis cette IP
    actions = [l["action"] for l in app.state.db.execute("SELECT action FROM journal_audit")]
    assert actions == ["connexion_bloquee_ip"]


def test_email_normalise(client):
    n = app.state.config["securite"]["max_echecs_par_email"]
    for i in range(n):
        login(client, email="AWA@exemple.bf" if i % 2 else " awa@exemple.bf ", mdp="mauvais-mot-de-passe")
    assert login(client).status_code == 429
