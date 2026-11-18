"""Exporte le modèle YuNet (ONNX) pour le moteur JavaScript du téléphone (masquage avant envoi).

    python scripts/exporter_yunet_web.py

Écrit `frontend/public/modeles/yunet.json` (graphe : opérations, attributs, formes) et
`frontend/public/modeles/yunet.bin` (poids float32 bout à bout). Lu par
`frontend/src/masquage/reseau.js`. À relancer seulement si le modèle change.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import onnx
from onnx import numpy_helper

RACINE = Path(__file__).resolve().parent.parent
SOURCE = RACINE / "backend" / "modeles" / "face_detection_yunet_2023mar.onnx"
SORTIE = RACINE / "frontend" / "public" / "modeles"


def main() -> None:
    m = onnx.load(SOURCE)
    # Entrées « de réglage » (échelles de Resize, formes de Reshape) : gardées en clair dans le JSON.
    reglages = {e for n in m.graph.node if n.op_type in ("Resize", "Reshape") for e in n.input[1:]}
    poids, morceaux, decalage, constantes = {}, [], 0, {}
    for init in m.graph.initializer:
        a = numpy_helper.to_array(init)
        if init.name not in reglages:
            poids[init.name] = {"forme": list(a.shape), "debut": decalage, "taille": int(a.size)}
            morceaux.append(a.astype("<f4").ravel())
            decalage += int(a.size)
        else:
            constantes[init.name] = a.astype(float).ravel().tolist()
    noeuds = []
    for n in m.graph.node:
        attrs = {}
        for at in n.attribute:
            v = onnx.helper.get_attribute_value(at)
            attrs[at.name] = v.decode() if isinstance(v, bytes) else (list(v) if not isinstance(v, (int, float)) else v)
        noeuds.append({"op": n.op_type, "entrees": list(n.input), "sorties": list(n.output), "attrs": attrs})
    graphe = {
        "source": "face_detection_yunet_2023mar.onnx (OpenCV Zoo, licence MIT)",
        "entree": m.graph.input[0].name,
        "taille_entree": [d.dim_value for d in m.graph.input[0].type.tensor_type.shape.dim],
        "sorties": [o.name for o in m.graph.output],
        "poids": poids, "constantes": constantes, "noeuds": noeuds,
    }
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / "yunet.json").write_text(json.dumps(graphe, separators=(",", ":")), encoding="utf-8")
    np.concatenate(morceaux).tofile(SORTIE / "yunet.bin")
    print(f"{len(noeuds)} opérations, {decalage} poids, écrits dans {SORTIE}")


if __name__ == "__main__":
    main()
