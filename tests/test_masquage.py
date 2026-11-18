"""Masquage des visages et plaques (D36). Portrait : image « astronaut » (NASA, domaine public)."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from backend import masquage
from backend.config import charger_config
from backend.masquage import MasquageIndisponible, detecter, flouter, masquer_photo

PORTRAIT = (Path(__file__).parent / "fixtures" / "portrait_domaine_public.jpg").read_bytes()


@pytest.fixture
def config():
    return charger_config("ouagadougou")


def decoder(contenu):
    return cv2.imdecode(np.frombuffer(contenu, np.uint8), cv2.IMREAD_COLOR)


def test_visage_detecte_puis_floute(config):
    original = decoder(PORTRAIT)
    (x, y, w, h), = detecter(original, config)["visages"]
    r = masquer_photo(PORTRAIT, config)
    assert (r.visages, r.extension) == (1, ".jpg")
    masque = decoder(r.contenu)
    # le détail du visage a disparu (variance du laplacien effondrée) ...
    nettete = lambda img: cv2.Laplacian(cv2.cvtColor(img[y:y + h, x:x + w], cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
    assert nettete(masque) < nettete(original) / 10
    # ... et le visage n'est plus détectable
    assert detecter(masque, config)["visages"] == []
    # le reste de l'image est intact (coin opposé)
    assert np.abs(masque[-40:, -40:].astype(int) - original[-40:, -40:].astype(int)).mean() < 6


def test_image_sans_visage_ni_plaque_inchangee(config):
    uni = cv2.imencode(".png", np.full((120, 160, 3), 200, np.uint8))[1].tobytes()
    r = masquer_photo(uni, config)
    assert (r.visages, r.plaques, r.largeur, r.hauteur) == (0, 0, 160, 120)
    assert r.resume() == {"visages": 0, "plaques": 0, "methode": "opencv-yunet"}


def test_plaques_floutees(config, monkeypatch):
    """Les cascades de plaques sont branchées : on simule une détection pour vérifier le floutage."""
    image = np.zeros((200, 300, 3), np.uint8)
    cv2.putText(image, "11 GH 4242", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    contenu = cv2.imencode(".png", image)[1].tobytes()
    monkeypatch.setattr(masquage, "detecter", lambda img, cfg: {"visages": [], "plaques": [(15, 75, 270, 50)]})
    r = masquer_photo(contenu, config)
    assert r.plaques == 1
    zone = decoder(r.contenu)[80:120, 25:280]
    avant = image[80:120, 25:280]
    assert cv2.Laplacian(cv2.cvtColor(zone, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var() < \
        cv2.Laplacian(cv2.cvtColor(avant, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var() / 10


def test_cascades_de_plaques_chargees():
    for nom in masquage.CASCADES_PLAQUES + masquage.CASCADES_VISAGES:
        assert not masquage._cascade(nom).empty()


def test_exif_supprime_et_photo_reduite(config):
    grande = cv2.imencode(".jpg", np.full((2000, 3000, 3), 120, np.uint8))[1].tobytes()
    # Segment APP1 « Exif » inséré juste après le début du JPEG, comme le ferait un téléphone.
    charge = b"Exif\x00\x00" + b"MM\x00\x2a" + b"Fabricant GPS 12.37 -1.52"
    app1 = b"\xff\xe1" + (len(charge) + 2).to_bytes(2, "big") + charge
    avec_exif = grande[:2] + app1 + grande[2:]
    assert decoder(avec_exif) is not None and b"Fabricant" in avec_exif
    r = masquer_photo(avec_exif, config)
    assert b"Fabricant" not in r.contenu and b"Exif" not in r.contenu
    assert max(r.largeur, r.hauteur) == config["masquage"]["cote_max_px"]


def test_zone_en_bord_d_image(config):
    image = np.random.default_rng(0).integers(0, 255, (50, 50, 3), dtype=np.uint8)
    flouter(image, (40, 40, 30, 30), 0.25)     # déborde : découpée sans erreur
    flouter(image, (60, 60, 10, 10), 0.25)     # entièrement dehors : rien


def test_image_illisible_et_opencv_absent(config, monkeypatch):
    with pytest.raises(ValueError):
        masquer_photo(b"\xff\xd8\xff" + b"\x00" * 50, config)
    monkeypatch.setattr(masquage, "cv2", None)
    with pytest.raises(MasquageIndisponible):
        masquer_photo(PORTRAIT, config)



def test_yunet_utilise_et_haar_en_secours(config, monkeypatch):
    """D57 : YuNet trouve le visage ; sans le modèle, les cascades de Haar prennent le relais."""
    assert masquage.MODELE_YUNET.exists()
    assert len(detecter(decoder(PORTRAIT), config)["visages"]) == 1
    monkeypatch.setattr(masquage, "MODELE_YUNET", Path("/inexistant.onnx"))
    assert len(detecter(decoder(PORTRAIT), config)["visages"]) >= 1


def _photo_avec_plaque(texte="11 KJ 4521", echelle=1.1):
    rng = np.random.default_rng(3)
    fond = rng.normal(120, 25, (600, 900, 3)).clip(0, 255).astype(np.uint8)
    (tw, th), _ = cv2.getTextSize(texte, cv2.FONT_HERSHEY_SIMPLEX, echelle, 3)
    cv2.rectangle(fond, (288, 300 - th - 14), (312 + tw, 314), (235, 235, 235), -1)
    cv2.putText(fond, texte, (300, 300), cv2.FONT_HERSHEY_SIMPLEX, echelle, (15, 15, 15), 3)
    return fond


def test_plaque_trouvee_par_sa_forme_quel_que_soit_le_pays(config):
    """D57 : rectangle clair + rangée de caractères sombres, sans cascade entraînée sur un pays."""
    image = _photo_avec_plaque()
    zones = masquage._plaques_par_forme(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
    assert len(zones) == 1
    x, y, w, h = zones[0]
    assert x <= 310 and x + w >= 400 and y <= 290 <= y + h       # la plaque est couverte
    r = masquer_photo(cv2.imencode(".png", image)[1].tobytes(), config)
    assert r.plaques >= 1


def _photo_avec_plaque_moto(angle=8.0):
    """Plaque de moto burkinabè : fond jaune, deux lignes, presque carrée, un peu penchée."""
    rng = np.random.default_rng(5)
    fond = rng.normal(70, 20, (600, 900, 3)).clip(0, 255).astype(np.uint8)
    plaque = np.full((120, 150, 3), (40, 205, 235), np.uint8)          # jaune (BGR)
    cv2.putText(plaque, "4562", (18, 52), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (20, 20, 20), 4)
    cv2.putText(plaque, "4012", (18, 108), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (20, 20, 20), 4)
    rot = cv2.getRotationMatrix2D((75, 60), angle, 1.0)
    masque = cv2.warpAffine(np.full((120, 150), 255, np.uint8), rot, (150, 120))
    plaque = cv2.warpAffine(plaque, rot, (150, 120))
    zone = fond[380:500, 100:250]
    zone[masque > 0] = plaque[masque > 0]
    return fond


def _photo_avec_plaque_moto_sans_flash():
    """Même plaque, sans flash : jaune terne, aussi lumineuse que la latérite qui l'entoure."""
    rng = np.random.default_rng(6)
    fond = np.dstack([rng.normal(m, 8, (600, 900)) for m in (95, 110, 140)]).clip(0, 255).astype(np.uint8)   # latérite (BGR)
    plaque = np.full((120, 150, 3), (60, 125, 130), np.uint8)       # jaune terne, même gris que le sol
    cv2.putText(plaque, "7021", (18, 52), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (25, 25, 25), 4)
    cv2.putText(plaque, "2DR 09", (8, 108), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (25, 25, 25), 4)
    fond[380:500, 100:250] = plaque
    return fond


def test_plaque_de_moto_sans_flash_trouvee_par_sa_couleur():
    image = _photo_avec_plaque_moto_sans_flash()
    gris = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    assert masquage._plaques_fond_clair(gris) == []                 # pas plus claire que le sol
    zones = masquage._plaques_fond_clair(gris, image)               # mais jaune
    assert len(zones) == 1
    x, y, w, h = zones[0]
    assert x <= 110 and x + w >= 240 and y <= 390 and y + h >= 490


def test_plaque_de_moto_jaune_sur_deux_lignes(config):
    """D59 : sur une vraie photo, la recherche par rangée unique ne voit pas ces plaques presque carrées."""
    image = _photo_avec_plaque_moto()
    gris = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    zones = masquage._plaques_fond_clair(gris)
    assert len(zones) == 1
    x, y, w, h = zones[0]
    assert x <= 110 and x + w >= 240 and y <= 390 and y + h >= 490       # toute la plaque est couverte
    assert masquer_photo(cv2.imencode(".png", image)[1].tobytes(), config).plaques >= 1


def test_pas_de_fausse_plaque_sur_un_tas_de_dechets(config):
    rng = np.random.default_rng(7)
    for _ in range(10):
        image = rng.normal(110, 30, (600, 900, 3)).clip(0, 255).astype(np.uint8)
        for _ in range(60):
            couleur = tuple(int(c) for c in rng.integers(0, 255, 3))
            cv2.ellipse(image, (int(rng.integers(0, 900)), int(rng.integers(0, 600))),
                        (int(rng.integers(5, 60)), int(rng.integers(5, 40))), int(rng.integers(0, 180)), 0, 360, couleur, -1)
        assert detecter(image, config)["plaques"] == []
