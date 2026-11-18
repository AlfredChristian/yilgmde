"""Vérifie que le moteur JavaScript du téléphone (frontend/src/masquage) donne les mêmes
sorties qu'onnxruntime et les mêmes visages qu'OpenCV (serveur), sur une photo.

    python scripts/verifier_masquage_web.py [photo.jpg]

Demande Node.js, onnxruntime et opencv-python-headless.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

RACINE = Path(__file__).resolve().parent.parent
MODELE = RACINE / "backend" / "modeles" / "face_detection_yunet_2023mar.onnx"
HARNAIS = """
import fs from 'node:fs'
import { Reseau } from '%(uri)s/frontend/src/masquage/reseau.js'
import { decoder } from '%(uri)s/frontend/src/masquage/visages.js'
const g = JSON.parse(fs.readFileSync('%(racine)s/frontend/public/modeles/yunet.json'))
const bin = fs.readFileSync('%(racine)s/frontend/public/modeles/yunet.bin')
const r = new Reseau(g, bin.buffer.slice(bin.byteOffset, bin.byteOffset + bin.length))
const b = fs.readFileSync(process.argv[2])
const entree = new Float32Array(b.buffer.slice(b.byteOffset, b.byteOffset + b.length))
const t = performance.now()
const s = r.executer(entree, 640, 640)
const out = { ms: performance.now() - t }
for (const [k, v] of Object.entries(s)) out[k] = Array.from(v.donnees)
out.visages = decoder(s, 0.6)
fs.writeFileSync(process.argv[3], JSON.stringify(out))
"""


def main() -> None:
    photo = Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE / "tests" / "fixtures" / "portrait_domaine_public.jpg"
    image = cv2.imread(str(photo))
    e = 640 / max(image.shape[:2])
    image = cv2.resize(image, (int(image.shape[1] * e), int(image.shape[0] * e)), interpolation=cv2.INTER_AREA)
    toile = np.zeros((640, 640, 3), np.uint8)
    toile[: image.shape[0], : image.shape[1]] = image
    entree = toile.transpose(2, 0, 1)[None].astype(np.float32)

    reference = dict(zip([o.name for o in ort.InferenceSession(str(MODELE)).get_outputs()],
                         ort.InferenceSession(str(MODELE)).run(None, {"input": entree})))
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "h.mjs").write_text(HARNAIS % {"racine": RACINE.as_posix(), "uri": RACINE.as_uri()}, encoding="utf-8")
        entree.tofile(Path(d) / "e.bin")
        subprocess.run(["node", str(Path(d) / "h.mjs"), str(Path(d) / "e.bin"), str(Path(d) / "s.json")], check=True)
        js = json.loads((Path(d) / "s.json").read_text())

    ecart = max(float(np.abs(np.array(js[k]) - v.ravel()).max()) for k, v in reference.items())
    det = cv2.FaceDetectorYN.create(str(MODELE), "", (640, 640), 0.6, 0.3, 5000)
    _, v = det.detect(toile)
    opencv = [] if v is None else [list(map(float, x[:5])) for x in v]
    print(f"temps JS : {js['ms']:.0f} ms ; écart max avec onnxruntime : {ecart:.2e}")
    print("visages JS     :", [[round(c, 1) for c in f] for f in js["visages"]])
    print("visages OpenCV :", [[round(c, 1) for c in f] for f in opencv])
    assert ecart < 1e-3, "le moteur JS s'écarte d'onnxruntime"
    assert len(js["visages"]) == len(opencv), "nombre de visages différent d'OpenCV"


if __name__ == "__main__":
    main()
