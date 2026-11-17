"""Livrable 1 : signalement hors connexion (envoi différé), note vocale, photo masquée (D36)."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import db, masquage
from backend.main import app
from backend.schemas import Role
from backend.utilisateurs import creer_utilisateur

JETON = "appareil-hors-ligne-01"
PORTRAIT = (Path(__file__).parent / "fixtures" / "portrait_domaine_public.jpg").read_bytes()
WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 200
M4A = b"\x00\x00\x00\x20ftypM4A " + b"\x00" * 200


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CHEMIN_DB_DEFAUT", tmp_path / "test.sqlite3")
    monkeypatch.setenv("YILGMDE_UPLOADS", str(tmp_path / "uploads"))
    monkeypatch.delenv("YILGMDE_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("YILGMDE_ADMIN_PASSWORD", raising=False)
    with TestClient(app) as c:
        yield c


def envoyer(client, jeton=JETON, fichiers=None, **champs):
    donnees = {"latitude": "12.3714", "longitude": "-1.5197", "type_dechet": "menager", "volume_estime": "moyen"}
    donnees.update(champs)
    return client.post("/signalements", data=donnees, files=fichiers, headers={"X-Device-Token": jeton})


def il_y_a(**duree):
    return (datetime.now(timezone.utc) - timedelta(**duree)).isoformat()


def admin(client):
    creer_utilisateur(app.state.db, "Awa", "awa@exemple.bf", "motdepasse-solide", Role.admin)
    jeton = client.post("/auth/login", json={"email": "awa@exemple.bf", "mot_de_passe": "motdepasse-solide"}).json()
    return {"Authorization": f"Bearer {jeton['access_token']}"}


def nb_signalements():
    return app.state.db.execute("SELECT COUNT(*) FROM signalement").fetchone()[0]


# --- Renvois (idempotence) ------------------------------------------------------------

def test_renvoi_du_meme_signalement_sans_doublon(client):
    premier = envoyer(client, id_client="file-1700000000-a1b2")
    assert premier.status_code == 201 and premier.json()["deja_recu"] is False
    renvoi = envoyer(client, id_client="file-1700000000-a1b2")   # réponse perdue, la file réessaie
    assert renvoi.status_code == 200
    assert renvoi.json() == dict(premier.json(), deja_recu=True)
    assert nb_signalements() == 1


def test_meme_id_client_sur_un_autre_appareil_est_un_autre_signalement(client):
    envoyer(client, id_client="file-commune-0001")
    autre = envoyer(client, jeton="autre-appareil-02", id_client="file-commune-0001", latitude="12.40")
    assert autre.status_code == 201 and nb_signalements() == 2


def test_id_client_invalide(client):
    assert envoyer(client, id_client="court").status_code == 422
    assert envoyer(client, id_client="avec espace interdit").status_code == 422


def test_index_unique_en_base(client):
    envoyer(client, id_client="file-unique-0001")
    ligne = app.state.db.execute("SELECT contributeur_id FROM signalement").fetchone()
    with pytest.raises(Exception):
        with app.state.db:
            app.state.db.execute(
                "INSERT INTO signalement (contributeur_id, latitude, longitude, type_dechet, volume_estime,"
                " code_suivi, statut, cree_le, id_client) VALUES (?, 12, -1, 'menager', 'moyen', 'AAA-AAA',"
                " 'soumis', '2026', 'file-unique-0001')", (ligne[0],))


# --- Date de prise de vue --------------------------------------------------------------

def test_capture_le_enregistree(client):
    quand = il_y_a(hours=3)
    sid = envoyer(client, capture_le=quand).json()["id"]
    stocke = app.state.db.execute("SELECT capture_le, cree_le FROM signalement WHERE id = ?", (sid,)).fetchone()
    assert datetime.fromisoformat(stocke["capture_le"]) == datetime.fromisoformat(quand)
    assert stocke["cree_le"] > stocke["capture_le"]


def test_capture_dans_le_futur_refusee_mais_tolerance(client):
    assert envoyer(client, capture_le=il_y_a(hours=-1)).status_code == 422
    assert envoyer(client, capture_le=il_y_a(minutes=-2)).status_code == 201   # horloge un peu en avance
    sans_fuseau = (datetime.now(timezone.utc) - timedelta(hours=1)).replace(tzinfo=None).isoformat()
    assert envoyer(client, jeton="appareil-sans-fuseau", capture_le=sans_fuseau, latitude="12.40").status_code == 201


def test_capture_ancienne_signalee(client):
    sid = envoyer(client, capture_le=il_y_a(days=45)).json()["id"]
    alertes = db.depuis_json(app.state.db.execute("SELECT alertes FROM signalement WHERE id = ?", (sid,)).fetchone()[0])
    assert "capture_ancienne" in alertes


def test_synchronisation_d_une_matinee_n_est_pas_un_abus(client):
    """6 photos prises à 1 h d'intervalle, envoyées d'un coup au retour du réseau."""
    limite = app.state.config["verification"]["max_signalements_par_appareil_heure"]
    reponses = [envoyer(client, capture_le=il_y_a(hours=8 - i), latitude=str(12.30 + 0.01 * i), id_client=f"file-matin-{i:04d}")
                for i in range(limite + 1)]
    assert [r.json()["statut"] for r in reponses] == ["en_attente_revue"] * (limite + 1)


def test_rafale_de_prises_de_vue_reste_limitee(client):
    """6 photos prises dans la même heure : la 6e est arrêtée, même envoyée plus tard."""
    limite = app.state.config["verification"]["max_signalements_par_appareil_heure"]
    reponses = [envoyer(client, capture_le=il_y_a(hours=5, minutes=50 - 5 * i), latitude=str(12.30 + 0.01 * i))
                for i in range(limite + 1)]
    assert reponses[-1].json()["statut"] == "rejete_auto"


def test_plafond_de_reception(client):
    app.state.config["hors_ligne"]["max_envois_par_heure"] = 3
    try:
        for i in range(3):
            assert envoyer(client, capture_le=il_y_a(days=1 + i), latitude=str(12.30 + 0.01 * i)).status_code == 201
        r = envoyer(client, capture_le=il_y_a(days=5), latitude="12.39")
        assert r.status_code == 429 and r.headers["retry-after"]
        assert nb_signalements() == 3
    finally:
        app.state.config["hors_ligne"]["max_envois_par_heure"] = 30


# --- Photo masquée ----------------------------------------------------------------------

def test_photo_avec_visage_masquee_avant_stockage(client, tmp_path):
    r = envoyer(client, fichiers={"photo": ("p.jpg", PORTRAIT, "image/jpeg")})
    assert r.status_code == 201 and r.json()["photo_masquee"]["visages"] == 1
    stockee = (tmp_path / "uploads" / f"{r.json()['id']}.jpg").read_bytes()
    assert stockee != PORTRAIT
    import cv2
    import numpy as np
    from backend.masquage import detecter
    image = cv2.imdecode(np.frombuffer(stockee, np.uint8), cv2.IMREAD_COLOR)
    assert detecter(image, app.state.config)["visages"] == []


def test_masquage_indisponible_rien_n_est_garde(client, monkeypatch):
    monkeypatch.setattr(masquage, "cv2", None)
    r = envoyer(client, fichiers={"photo": ("p.jpg", PORTRAIT, "image/jpeg")})
    assert r.status_code == 503 and nb_signalements() == 0
    assert envoyer(client).status_code == 201          # sans photo : pas concerné


def test_photo_corrompue(client):
    r = envoyer(client, fichiers={"photo": ("p.jpg", b"\xff\xd8\xff" + b"\x00" * 50, "image/jpeg")})
    assert r.status_code == 422 and nb_signalements() == 0


# --- Note vocale ------------------------------------------------------------------------

def test_note_vocale_gardee_et_reservee_a_l_admin(client, tmp_path):
    r = envoyer(client, fichiers={"note_vocale": ("n.webm", WEBM, "audio/webm")})
    assert r.status_code == 201
    sid = r.json()["id"]
    assert (tmp_path / "uploads" / "audio" / f"{sid}.webm").read_bytes() == WEBM
    h = admin(client)
    ligne = client.get("/admin/signalements?statut=en_attente_revue", headers=h).json()[0]
    assert ligne["note_vocale_url"] == f"/admin/signalements/{sid}/note-vocale"
    son = client.get(ligne["note_vocale_url"], headers=h)
    assert son.status_code == 200 and son.content == WEBM and son.headers["content-type"] == "audio/webm"
    assert client.get(ligne["note_vocale_url"]).status_code == 401
    sans = envoyer(client, jeton="autre-appareil-03", latitude="12.40").json()["id"]
    assert client.get(f"/admin/signalements/{sans}/note-vocale", headers=h).status_code == 404


def test_formats_audio(client):
    assert envoyer(client, fichiers={"note_vocale": ("n.m4a", M4A, "audio/mp4")}).status_code == 201
    faux = envoyer(client, latitude="12.40", fichiers={"note_vocale": ("n.webm", b"<script>", "audio/webm")})
    assert faux.status_code == 422
    app.state.config["hors_ligne"]["note_vocale_taille_max_mo"] = 0.0001
    try:
        gros = envoyer(client, latitude="12.41", fichiers={"note_vocale": ("n.webm", WEBM * 10, "audio/webm")})
        assert gros.status_code == 413
    finally:
        app.state.config["hors_ligne"]["note_vocale_taille_max_mo"] = 2


def test_rejet_d_office_ne_garde_ni_photo_ni_note(client, tmp_path):
    r = envoyer(client, latitude="5.36", longitude="-4.0083",
                fichiers={"photo": ("p.jpg", PORTRAIT, "image/jpeg"), "note_vocale": ("n.webm", WEBM, "audio/webm")})
    assert r.json()["statut"] == "rejete_auto" and r.json()["photo_masquee"] is None
    ligne = app.state.db.execute("SELECT photo, note_vocale FROM signalement").fetchone()
    assert (ligne["photo"], ligne["note_vocale"]) == (None, None)
    assert not (tmp_path / "uploads" / "audio").exists()
