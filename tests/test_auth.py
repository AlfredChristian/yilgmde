import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.main import app
from backend.schemas import Role
from backend.securite import creer_token, hasher_mot_de_passe, verifier_mot_de_passe
from backend.utilisateurs import EmailDejaUtilise, creer_admin_si_absent, creer_utilisateur

MDP = "motdepasse-solide"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CHEMIN_DB_DEFAUT", tmp_path / "test.sqlite3")
    monkeypatch.setenv("YILGMDE_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.delenv("YILGMDE_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("YILGMDE_ADMIN_PASSWORD", raising=False)
    with TestClient(app) as c:
        yield c


def compte(role=Role.admin, email=None):
    return creer_utilisateur(app.state.db, f"Test {role.value}", email or f"{role.value}@exemple.bf", MDP, role)


def connexion(client, email, mdp=MDP):
    return client.post("/auth/login", json={"email": email, "mot_de_passe": mdp})


def entetes(client, email):
    return {"Authorization": f"Bearer {connexion(client, email).json()['access_token']}"}


# ---------- mots de passe et jetons ----------

def test_mot_de_passe_hache_et_verifie():
    h = hasher_mot_de_passe(MDP)
    assert h != MDP and verifier_mot_de_passe(MDP, h)
    assert not verifier_mot_de_passe("autre-mot-de-passe", h)
    assert not verifier_mot_de_passe(MDP, None)           # utilisateur inconnu
    assert not verifier_mot_de_passe("x" * 100, h)        # > 72 octets : refus propre, pas d'exception


# ---------- POST /auth/login ----------

def test_connexion_reussie(client):
    compte(Role.chauffeur)
    r = connexion(client, "chauffeur@exemple.bf")
    assert r.status_code == 200
    assert r.json()["role"] == "chauffeur" and r.json()["token_type"] == "bearer"


def test_email_insensible_a_la_casse(client):
    compte(Role.admin, "Admin@Exemple.BF")
    assert connexion(client, "  ADMIN@exemple.bf ").status_code == 200


def test_mauvais_mot_de_passe_et_email_inconnu_donnent_la_meme_reponse(client):
    compte()
    faux = connexion(client, "admin@exemple.bf", "mauvais-mot-de-passe")
    inconnu = connexion(client, "personne@exemple.bf")
    assert faux.status_code == inconnu.status_code == 401
    assert faux.json() == inconnu.json() == {"detail": "identifiants invalides"}


def test_compte_desactive_ne_peut_pas_se_connecter(client):
    u = compte()
    app.state.db.execute("UPDATE utilisateur SET actif = 0 WHERE id = ?", (u["id"],))
    app.state.db.commit()
    assert connexion(client, "admin@exemple.bf").status_code == 401


# ---------- GET /auth/moi ----------

def test_moi(client):
    compte(Role.laabal)
    r = client.get("/auth/moi", headers=entetes(client, "laabal@exemple.bf"))
    assert r.status_code == 200
    assert r.json()["role"] == "laabal" and r.json()["nom"] == "Test laabal"
    assert "email" not in r.json() and "mot_de_passe_hash" not in r.json()


@pytest.mark.parametrize("entete", [None, "Bearer", "Bearer jeton-bidon", "Basic abc", "abc"])
def test_moi_refuse_sans_jeton_valide(client, entete):
    headers = {"Authorization": entete} if entete else {}
    r = client.get("/auth/moi", headers=headers)
    assert r.status_code == 401


def test_jeton_expire_est_refuse(client):
    u = compte()
    expire = creer_token(u["id"], "admin", duree_min=-1)
    assert client.get("/auth/moi", headers={"Authorization": f"Bearer {expire}"}).status_code == 401


def test_jeton_signe_avec_un_autre_secret_est_refuse(client):
    import jwt
    u = compte()
    faux = jwt.encode({"sub": str(u["id"]), "exp": 9999999999}, "autre-secret-32-octets-minimum-ok!!", algorithm="HS256")
    assert client.get("/auth/moi", headers={"Authorization": f"Bearer {faux}"}).status_code == 401


def test_compte_desactive_apres_connexion_perd_l_acces_tout_de_suite(client):
    u = compte()
    h = entetes(client, "admin@exemple.bf")
    assert client.get("/auth/moi", headers=h).status_code == 200
    app.state.db.execute("UPDATE utilisateur SET actif = 0 WHERE id = ?", (u["id"],))
    app.state.db.commit()
    assert client.get("/auth/moi", headers=h).status_code == 401


def test_le_role_est_relu_en_base_pas_dans_le_jeton(client):
    u = compte(Role.admin)
    h = entetes(client, "admin@exemple.bf")                # jeton émis quand il était admin
    app.state.db.execute("UPDATE utilisateur SET role = 'chauffeur' WHERE id = ?", (u["id"],))
    app.state.db.commit()
    r = client.post("/admin/utilisateurs", headers=h, json={"nom": "X", "email": "x@exemple.bf", "mot_de_passe": MDP, "role": "chauffeur"})
    assert r.status_code == 403


# ---------- /admin/utilisateurs : F2 (droits) et F4 (création) ----------

def corps(**s):
    return {"nom": "Awa Ouédraogo", "email": "awa@exemple.bf", "mot_de_passe": MDP, "role": "chauffeur", **s}


def test_admin_cree_un_compte_qui_peut_se_connecter(client):
    compte()
    r = client.post("/admin/utilisateurs", headers=entetes(client, "admin@exemple.bf"), json=corps())
    assert r.status_code == 201
    assert r.json()["role"] == "chauffeur" and r.json()["actif"] is True
    assert "mot_de_passe" not in r.json() and "mot_de_passe_hash" not in r.json()
    assert connexion(client, "awa@exemple.bf").json()["role"] == "chauffeur"


def test_le_mot_de_passe_n_est_jamais_stocke_en_clair(client):
    compte()
    client.post("/admin/utilisateurs", headers=entetes(client, "admin@exemple.bf"), json=corps())
    h = app.state.db.execute("SELECT mot_de_passe_hash FROM utilisateur WHERE email = 'awa@exemple.bf'").fetchone()[0]
    assert MDP not in h and h.startswith("$2")


def test_creation_sans_jeton_401(client):
    assert client.post("/admin/utilisateurs", json=corps()).status_code == 401


@pytest.mark.parametrize("role", [Role.chauffeur, Role.laabal])
def test_creation_par_un_non_admin_403(client, role):
    compte(role)
    r = client.post("/admin/utilisateurs", headers=entetes(client, f"{role.value}@exemple.bf"), json=corps())
    assert r.status_code == 403
    assert app.state.db.execute("SELECT COUNT(*) FROM utilisateur WHERE email = 'awa@exemple.bf'").fetchone()[0] == 0


def test_email_en_double_409(client):
    compte()
    h = entetes(client, "admin@exemple.bf")
    assert client.post("/admin/utilisateurs", headers=h, json=corps()).status_code == 201
    assert client.post("/admin/utilisateurs", headers=h, json=corps(email="AWA@exemple.bf")).status_code == 409


@pytest.mark.parametrize(
    "surcharge",
    [{"mot_de_passe": "court"}, {"mot_de_passe": "é" * 40}, {"email": "pas-un-email"}, {"role": "citoyen"}, {"nom": ""}],
)
def test_creation_entrees_invalides_422(client, surcharge):
    compte()
    r = client.post("/admin/utilisateurs", headers=entetes(client, "admin@exemple.bf"), json=corps(**surcharge))
    assert r.status_code == 422


def test_liste_des_comptes_reservee_a_l_admin(client):
    compte(Role.admin)
    compte(Role.chauffeur)
    assert client.get("/admin/utilisateurs").status_code == 401
    assert client.get("/admin/utilisateurs", headers=entetes(client, "chauffeur@exemple.bf")).status_code == 403
    r = client.get("/admin/utilisateurs", headers=entetes(client, "admin@exemple.bf"))
    assert r.status_code == 200
    assert [u["role"] for u in r.json()] == ["admin", "chauffeur"]
    assert all("mot_de_passe_hash" not in u for u in r.json())


def test_creation_de_compte_est_tracee_dans_le_journal(client):
    admin = compte()
    client.post("/admin/utilisateurs", headers=entetes(client, "admin@exemple.bf"), json=corps())
    ligne = app.state.db.execute("SELECT * FROM journal_audit").fetchone()
    assert ligne["action"] == "creer_utilisateur" and ligne["utilisateur_id"] == admin["id"]


def test_routes_publiques_restent_ouvertes(client):
    assert client.get("/health").status_code == 200
    assert client.get("/depotoirs").status_code == 200


# ---------- amorçage du premier admin ----------

def test_creer_admin_depuis_l_environnement(monkeypatch):
    conn = db.connecter(":memory:")
    db.initialiser(conn)
    assert creer_admin_si_absent(conn) is False            # variables absentes
    monkeypatch.setenv("YILGMDE_ADMIN_EMAIL", "boss@exemple.bf")
    monkeypatch.setenv("YILGMDE_ADMIN_PASSWORD", MDP)
    assert creer_admin_si_absent(conn) is True
    assert creer_admin_si_absent(conn) is False            # idempotent : un admin existe déjà
    assert conn.execute("SELECT COUNT(*) FROM utilisateur").fetchone()[0] == 1


def test_creer_utilisateur_refuse_un_doublon():
    conn = db.connecter(":memory:")
    db.initialiser(conn)
    creer_utilisateur(conn, "A", "a@exemple.bf", MDP, Role.admin)
    with pytest.raises(EmailDejaUtilise):
        creer_utilisateur(conn, "B", "A@exemple.bf", MDP, Role.chauffeur)
