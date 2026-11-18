"""Bâtiments (Google Open Buildings v3), pour savoir où vivent les ménages (D58).

Le fichier `population.batiments` (CSV gzip : latitude, longitude, surface_m2, confiance),
produit par `scripts/telecharger_batiments.py`, est lu une fois puis gardé en mémoire.
`menages_dans_zone` renvoie, pour une zone, des « paquets » de bâtiments regroupés sur une
grille de `pas_m` : position moyenne et surface bâtie totale. La surface bâtie sert de poids :
un secteur dense pèse plus qu'un terrain vague, et les points de regroupement vont là où
sont les maisons. Sans fichier, l'appelant garde la grille uniforme (hypothèse [H]).
"""

from __future__ import annotations

import csv
import gzip
from functools import lru_cache
from pathlib import Path

import numpy as np

from simulation.geometrie import _polygones, emprise

RACINE = Path(__file__).resolve().parent.parent
M_PAR_DEGRE = 111_320.0


@lru_cache(maxsize=2)
def _charger(chemin: str, _mtime: float) -> np.ndarray:
    lignes = []
    with gzip.open(chemin, "rt", encoding="utf-8", newline="") as f:
        for r in csv.reader(f):
            try:
                lignes.append((float(r[0]), float(r[1]), float(r[2])))
            except (ValueError, IndexError):
                continue          # en-tête ou ligne abîmée
    tableau = np.array(lignes, dtype=float).reshape(-1, 3)
    return tableau[np.argsort(tableau[:, 0], kind="stable")]   # trié par latitude : découpe rapide


def batiments_de(config: dict) -> np.ndarray | None:
    """Tableau (lat, lon, surface) des bâtiments configurés, ou None (fichier absent ou non configuré)."""
    chemin = (config.get("population") or {}).get("batiments")
    if not chemin:
        return None
    p = Path(chemin)
    if not p.is_absolute():
        p = RACINE / p
    if not p.exists():
        return None
    return _charger(str(p), p.stat().st_mtime)


def _dans_anneau(lon: np.ndarray, lat: np.ndarray, anneau) -> np.ndarray:
    dedans = np.zeros(len(lon), dtype=bool)
    xs = [c[0] for c in anneau]
    ys = [c[1] for c in anneau]
    j = len(anneau) - 1
    for i in range(len(anneau)):
        xi, yi, xj, yj = xs[i], ys[i], xs[j], ys[j]
        if yi != yj:
            croise = (yi > lat) != (yj > lat)
            x_inter = (xj - xi) * (lat - yi) / (yj - yi) + xi
            dedans ^= croise & (lon < x_inter)
        j = i
    return dedans


def _dans_geometrie(lat: np.ndarray, lon: np.ndarray, geometrie: dict) -> np.ndarray:
    resultat = np.zeros(len(lat), dtype=bool)
    for anneaux in _polygones(geometrie):
        if not anneaux:
            continue
        dedans = _dans_anneau(lon, lat, anneaux[0])
        for trou in anneaux[1:]:
            dedans &= ~_dans_anneau(lon, lat, trou)
        resultat |= dedans
    return resultat


def batiments_dans_zone(batiments: np.ndarray, geometrie: dict) -> np.ndarray:
    """Bâtiments (lat, lon, surface) situés dans la zone, un par ligne."""
    min_lat, min_lon, max_lat, max_lon = emprise(geometrie)
    debut = int(np.searchsorted(batiments[:, 0], min_lat, side="left"))
    fin = int(np.searchsorted(batiments[:, 0], max_lat, side="right"))
    b = batiments[debut:fin]
    b = b[(b[:, 1] >= min_lon) & (b[:, 1] <= max_lon)]
    return b[_dans_geometrie(b[:, 0], b[:, 1], geometrie)] if len(b) else b


def menages_dans_zone(batiments: np.ndarray, geometrie: dict, pas_m: float, max_paquets: int
                      ) -> tuple[list[tuple[float, float]], np.ndarray]:
    """Paquets de bâtiments de la zone : positions (lat, lon) et surface bâtie de chacun (m²).

    Listes vides si la zone ne contient aucun bâtiment. Le pas est agrandi si besoin pour
    ne pas dépasser `max_paquets`.
    """
    min_lat, min_lon, max_lat, max_lon = emprise(geometrie)
    b = batiments_dans_zone(batiments, geometrie)
    if not len(b):
        return [], np.array([])

    lat0 = (min_lat + max_lat) / 2
    m_lon = M_PAR_DEGRE * np.cos(np.radians(lat0))
    pas = max(float(pas_m), 1.0)
    while True:
        ix = np.floor((b[:, 1] - min_lon) * m_lon / pas).astype(np.int64)
        iy = np.floor((b[:, 0] - min_lat) * M_PAR_DEGRE / pas).astype(np.int64)
        cle = iy * (int(1e7)) + ix
        cles, inverse = np.unique(cle, return_inverse=True)
        if len(cles) <= max_paquets:
            break
        pas *= 1.25
    poids = np.maximum(b[:, 2], 1.0)          # un bâtiment de surface inconnue compte 1 m²
    surface = np.bincount(inverse, weights=poids)
    lat = np.bincount(inverse, weights=b[:, 0] * poids) / surface
    lon = np.bincount(inverse, weights=b[:, 1] * poids) / surface
    return list(zip(lat.tolist(), lon.tolist())), surface
