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
    assert r.resume() == {"visages": 0, "plaques": 0, "methode": "opencv-haar"}


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
