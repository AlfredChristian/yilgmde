import re

import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.main import app

JETON = "appareil-test-0001"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CHEMIN_DB_DEFAUT", tmp_path / "test.sqlite3")
    monkeypatch.setenv("YILGMDE_UPLOADS", str(tmp_path / "uploads"))
    with TestClient(app) as c:
        yield c


def formulaire(**surcharges):
    donnees = {
        "latitude": "12.3714",
        "longitude": "-1.5197",
        "type_dechet": "menager",
        "volume_estime": "moyen",
    }
    donnees.update(surcharges)
    return donnees


def envoyer(client, jeton=JETON, fichiers=None, **surcharges):
    return client.post(
        "/signalements",
        data=formulaire(**surcharges),
        files=fichiers,
        headers={"X-Device-Token": jeton},
    )


# ---------- POST /signalements ----------

def test_creation_valide_va_en_revue(client):
    r = envoyer(client)
    assert r.status_code == 201
    corps = r.json()
    assert corps["statut"] == "en_attente_revue"
    assert corps["motif"] is None
    assert re.fullmatch(r"[A-Z2-9]{3}-[A-Z2-9]{3}", corps["code_suivi"])


def test_hors_zone_est_rejete_avec_motif(client):
    r = envoyer(client, latitude="5.36", longitude="-4.0083")
    assert r.status_code == 201
    assert r.json()["statut"] == "rejete_auto"
    assert r.json()["motif"] == "hors zone d'étude"


def test_jeton_d_appareil_obligatoire(client):
    r = client.post("/signalements", data=formulaire())
    assert r.status_code == 422


def test_jeton_d_appareil_mal_forme(client):
    assert envoyer(client, jeton="court").status_code == 422


@pytest.mark.parametrize(
    "surcharge",
    [{"latitude": "120"}, {"type_dechet": "inconnu"}, {"volume_estime": "énorme"}, {"description": "x" * 501}],
)
def test_entrees_invalides_sont_refusees(client, surcharge):
    assert envoyer(client, **surcharge).status_code == 422


def test_limite_par_appareil_vient_de_la_config(client):
    limite = app.state.config["verification"]["max_signalements_par_appareil_heure"]
    # positions distinctes pour ne pas dépendre des alertes de doublon
    for i in range(limite):
        assert envoyer(client, latitude=str(12.30 + i * 0.01)).json()["statut"] == "en_attente_revue"
    r = envoyer(client, latitude="12.45")
    assert r.json()["statut"] == "rejete_auto"
    assert "trop de signalements" in r.json()["motif"]
    # un autre appareil n'est pas concerné
    assert envoyer(client, jeton="autre-appareil-02", latitude="12.46").json()["statut"] == "en_attente_revue"


def test_doublon_reste_en_revue_avec_alerte(client):
    envoyer(client)
    envoyer(client, jeton="autre-appareil-02")  # même endroit, autre appareil
    ligne = app.state.db.execute(
        "SELECT statut, alertes FROM signalement ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert ligne["statut"] == "en_attente_revue"
    assert db.depuis_json(ligne["alertes"]) == ["doublon_probable:1"]


def test_contributeur_cree_et_compte(client):
    envoyer(client)
    envoyer(client, latitude="12.40")
    ligne = app.state.db.execute(
        "SELECT nb_signalements FROM contributeur WHERE jeton_appareil = ?", (JETON,)
    ).fetchone()
    assert ligne["nb_signalements"] == 2


# ---------- photo ----------

def test_photo_valide_est_enregistree(client, tmp_path):
    r = envoyer(client, fichiers={"photo": ("p.png", PNG, "image/png")})
    assert r.status_code == 201
    sid = r.json()["id"]
    assert (tmp_path / "uploads" / f"{sid}.png").read_bytes() == PNG
    nom = app.state.db.execute("SELECT photo FROM signalement WHERE id = ?", (sid,)).fetchone()["photo"]
    assert nom == f"{sid}.png"


def test_photo_qui_n_est_pas_une_image_est_refusee(client):
    r = envoyer(client, fichiers={"photo": ("p.png", b"<?php echo 1; ?>", "image/png")})
    assert r.status_code == 422


def test_photo_trop_grosse_est_refusee(client):
    app.state.config["verification"]["photo_taille_max_mo"] = 0.0001  # ~ 100 octets
    r = envoyer(client, fichiers={"photo": ("p.png", PNG + b"\x00" * 500, "image/png")})
    assert r.status_code == 413


def test_photo_d_un_signalement_rejete_n_est_pas_gardee(client, tmp_path):
    r = envoyer(client, latitude="5.36", longitude="-4.0083", fichiers={"photo": ("p.png", PNG, "image/png")})
    assert r.json()["statut"] == "rejete_auto"
    assert not (tmp_path / "uploads").exists() or not list((tmp_path / "uploads").iterdir())


def test_photo_requise_selon_la_config(client):
    app.state.config["verification"]["photo_requise"] = True
    assert envoyer(client).json()["motif"] == "photo requise manquante"
    ok = envoyer(client, jeton="autre-appareil-02", latitude="12.40", fichiers={"photo": ("p.png", PNG, "image/png")})
    assert ok.json()["statut"] == "en_attente_revue"


# ---------- GET /signalements/suivi/{code} ----------

def test_suivi_d_un_signalement(client):
    code = envoyer(client).json()["code_suivi"]
    r = client.get(f"/signalements/suivi/{code}")
    assert r.status_code == 200
    assert r.json() == {"code_suivi": code, "statut": "en_attente_revue", "motif": None, "depotoir_id": None}
    # insensible à la casse et aux espaces
    assert client.get(f"/signalements/suivi/{code.lower()}").status_code == 200


def test_suivi_montre_le_motif_de_rejet(client):
    code = envoyer(client, latitude="5.36", longitude="-4.0083").json()["code_suivi"]
    r = client.get(f"/signalements/suivi/{code}")
    assert r.json()["statut"] == "rejete_auto" and r.json()["motif"] == "hors zone d'étude"


def test_suivi_code_inconnu(client):
    assert client.get("/signalements/suivi/ZZZ-999").status_code == 404


# ---------- GET /depotoirs ----------

def _depotoir(statut="actif", zone_id=1, lat=12.37, lon=-1.52):
    app.state.db.execute(
        "INSERT OR IGNORE INTO zone (id, nom, geometrie) VALUES (?, ?, '{}')",
        (zone_id, f"zone {zone_id}"),
    )
    app.state.db.execute(
        "INSERT INTO depotoir (latitude, longitude, zone_id, volume_estime, statut,"
        " nb_signalements, premiere_detection, derniere_maj) VALUES (?, ?, ?, 'moyen', ?, 2, 'x', 'x')",
        (lat, lon, zone_id, statut),
    )
    app.state.db.commit()


def test_depotoirs_vide_au_depart(client):
    r = client.get("/depotoirs")
    assert r.status_code == 200
    assert r.json() == {"type": "FeatureCollection", "features": []}


def test_depotoirs_geojson(client):
    _depotoir(lat=12.3714, lon=-1.5197)
    f = client.get("/depotoirs").json()["features"][0]
    assert f["geometry"] == {"type": "Point", "coordinates": [-1.5197, 12.3714]}  # [lon, lat]
    assert set(f["properties"]) == {
        "id", "statut", "legalite", "volume_estime", "nb_signalements", "zone_id", "derniere_maj",
    }


def test_depotoirs_filtres(client):
    _depotoir(statut="actif", zone_id=1)
    _depotoir(statut="eradique", zone_id=2)
    assert len(client.get("/depotoirs?statut=eradique").json()["features"]) == 1
    assert len(client.get("/depotoirs?zone_id=1").json()["features"]) == 1
    assert len(client.get("/depotoirs?statut=actif&zone_id=2").json()["features"]) == 0
    assert client.get("/depotoirs?statut=bidon").status_code == 422


def test_un_signalement_non_verifie_n_apparait_pas_sur_la_carte(client):
    envoyer(client)
    assert client.get("/depotoirs").json()["features"] == []
