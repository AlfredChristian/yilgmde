"""D59 : le masquage du téléphone (frontend/src/masquage, JavaScript) donne les mêmes
visages et les mêmes plaques que le serveur. Demande Node.js ; sinon le test est sauté."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from backend import masquage

RACINE = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js absent")

HARNAIS = """
import fs from 'node:fs'
import { Reseau } from '%(r)s/frontend/src/masquage/reseau.js'
import { detecterVisages } from '%(r)s/frontend/src/masquage/visages.js'
import { plaquesFondClair, plaquesParForme } from '%(r)s/frontend/src/masquage/plaques.js'
import { flouterPixels } from '%(r)s/frontend/src/masquage/flou.js'
const [, , fichier, w, h] = process.argv
const W = +w, H = +h
const rgba = new Uint8ClampedArray(fs.readFileSync(fichier))
const g = JSON.parse(fs.readFileSync('%(r)s/frontend/public/modeles/yunet.json'))
const b = fs.readFileSync('%(r)s/frontend/public/modeles/yunet.bin')
const reseau = new Reseau(g, b.buffer.slice(b.byteOffset, b.byteOffset + b.length))
const visages = detecterVisages(reseau, { width: W, height: H, data: rgba }, 0.6).map((v) => v.slice(0, 4))
const gris = new Uint8Array(W * H)
for (let i = 0; i < W * H; i++) gris[i] = Math.round(0.299 * rgba[i * 4] + 0.587 * rgba[i * 4 + 1] + 0.114 * rgba[i * 4 + 2])
const plaques = plaquesParForme(gris, W, H)
const fondClair = plaquesFondClair(gris, W, H, rgba)
for (const [x, y, zw, zh] of visages) {
  const x0 = Math.max(0, Math.floor(x - zw / 4)), y0 = Math.max(0, Math.floor(y - zh / 4))
  const x1 = Math.min(W, Math.ceil(x + zw * 1.25)), y1 = Math.min(H, Math.ceil(y + zh * 1.25))
  const zone = new Uint8ClampedArray((x1 - x0) * (y1 - y0) * 4)
  for (let j = 0; j < y1 - y0; j++) zone.set(rgba.subarray(((y0 + j) * W + x0) * 4, ((y0 + j) * W + x1) * 4), j * (x1 - x0) * 4)
  flouterPixels(zone, x1 - x0, y1 - y0)
  for (let j = 0; j < y1 - y0; j++) rgba.set(zone.subarray(j * (x1 - x0) * 4, (j + 1) * (x1 - x0) * 4), ((y0 + j) * W + x0) * 4)
}
fs.writeFileSync(fichier + '.floue', rgba)
console.log(JSON.stringify({ visages, plaques, fondClair }))
"""


def executer(image_bgr, tmp_path):
    h, w = image_bgr.shape[:2]
    (tmp_path / "h.mjs").write_text(HARNAIS % {"r": RACINE.as_posix()})
    rgba = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGBA)
    rgba.tofile(tmp_path / "img.rgba")
    sortie = subprocess.check_output(["node", str(tmp_path / "h.mjs"), str(tmp_path / "img.rgba"), str(w), str(h)])
    floue = np.fromfile(tmp_path / "img.rgba.floue", np.uint8).reshape(h, w, 4)
    return json.loads(sortie), cv2.cvtColor(floue, cv2.COLOR_RGBA2BGR)


def yunet(image):
    d = cv2.FaceDetectorYN.create(str(masquage.MODELE_YUNET), "", (image.shape[1], image.shape[0]), 0.6, 0.3, 5000)
    _, v = d.detect(image)
    return [] if v is None else [list(map(float, x[:4])) for x in v]


def test_meme_visage_que_le_serveur_et_floutage_efficace(tmp_path):
    image = cv2.imread(str(RACINE / "tests" / "fixtures" / "portrait_domaine_public.jpg"))
    js, floue = executer(image, tmp_path)
    serveur = yunet(image)
    assert len(js["visages"]) == len(serveur) == 1
    assert np.allclose(js["visages"][0], serveur[0], atol=1.0)
    assert yunet(floue) == []                     # le visage flouté par le téléphone n'est plus reconnu


def test_meme_plaque_que_le_serveur(tmp_path):
    sys.path.insert(0, str(Path(__file__).parent))
    from test_masquage import _photo_avec_plaque

    image = _photo_avec_plaque()
    js, _ = executer(image, tmp_path)
    serveur = masquage._plaques_par_forme(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
    assert [tuple(p) for p in js["plaques"]] == [tuple(int(v) for v in p) for p in serveur]


def test_meme_plaque_de_moto_que_le_serveur(tmp_path):
    sys.path.insert(0, str(Path(__file__).parent))
    from test_masquage import _photo_avec_plaque_moto

    image = _photo_avec_plaque_moto()
    js, _ = executer(image, tmp_path)
    serveur = masquage._plaques_fond_clair(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
    assert len(serveur) == 1
    assert [tuple(p) for p in js["fondClair"]] == serveur


def test_meme_plaque_sans_flash_que_le_serveur(tmp_path):
    sys.path.insert(0, str(Path(__file__).parent))
    from test_masquage import _photo_avec_plaque_moto_sans_flash

    image = _photo_avec_plaque_moto_sans_flash()
    js, _ = executer(image, tmp_path)
    serveur = masquage._plaques_fond_clair(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), image)
    assert len(serveur) == 1
    assert [tuple(p) for p in js["fondClair"]] == serveur
