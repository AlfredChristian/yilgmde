"""Itinéraires sur le vrai réseau routier (D52), calculés hors ligne.

Le réseau vient d'OpenStreetMap (`scripts/telecharger_reseau_routier.py` →
`data/ouaga/reseau_routier.json.gz`) : voies carrossables, sens uniques respectés, sans
voies privées, camps militaires ni aéroport. Activé par `collecte.reseau_routier` (chemin
du fichier) ; sans lui, le moteur garde la ligne droite × `coef_detour`.

Méthode :
1. Le graphe est réduit aux carrefours (un nœud OSM partagé par deux voies, ou une extrémité) ;
   chaque tronçon garde sa longueur et sa géométrie pour le tracé. On ne garde que la plus
   grande composante fortement connexe : tout site y trouve un aller et un retour.
2. Chaque site (dépôt, point, dépotoir) est rattaché au carrefour le plus proche ; la petite
   distance d'accès en ligne droite est ajoutée à l'aller et au retour.
3. Dijkstra (SciPy) depuis chaque site donne la matrice des distances routières, utilisée par
   OR-Tools, et les prédécesseurs, gardés pour retracer les tronçons des tournées retenues.

Tout est déterministe. Le graphe est construit une fois par processus et mis en cache.
"""

from __future__ import annotations

import gzip
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

RACINE = Path(__file__).resolve().parent.parent
R_TERRE = 6_371_000.0


class Reseau:
    """Graphe routier réduit aux carrefours, en coordonnées métriques locales."""

    def __init__(self, donnees: dict):
        noeuds = {int(k): v for k, v in donnees["noeuds"].items()}
        voies = donnees["voies"]
        lat0 = math.radians(sum(v[0] for v in noeuds.values()) / len(noeuds))
        self._kx = math.cos(lat0) * math.pi / 180 * R_TERRE
        self._ky = math.pi / 180 * R_TERRE

        usage: dict[int, int] = {}
        for v in voies:
            for n in v["n"]:
                usage[n] = usage.get(n, 0) + 1
            usage[v["n"][0]] += 1
            usage[v["n"][-1]] += 1
        carrefour = {n for n, c in usage.items() if c >= 2}

        index: dict[int, int] = {}
        coords: list[tuple[float, float]] = []

        def idx(n: int) -> int:
            if n not in index:
                index[n] = len(coords)
                coords.append(noeuds[n])
            return index[n]

        # Tronçons entre carrefours : (u, v, longueur m, géométrie [(lat, lon)]).
        aretes: dict[tuple[int, int], tuple[float, list]] = {}

        def ajouter(u: int, v: int, longueur: float, geom: list) -> None:
            if u != v and ((u, v) not in aretes or longueur < aretes[(u, v)][0]):
                aretes[(u, v)] = (longueur, geom)

        for v in voies:
            morceau = [v["n"][0]]
            for n in v["n"][1:]:
                morceau.append(n)
                if n in carrefour:
                    geom = [noeuds[m] for m in morceau]
                    longueur = sum(self._m(geom[i], geom[i + 1]) for i in range(len(geom) - 1))
                    a, b = idx(morceau[0]), idx(morceau[-1])
                    if v["s"] >= 0:
                        ajouter(a, b, longueur, geom)
                    if v["s"] <= 0:
                        ajouter(b, a, longueur, geom[::-1])
                    morceau = [n]

        n = len(coords)
        cles = list(aretes)
        lignes = np.array([u for u, _ in cles], dtype=np.int64)
        colonnes = np.array([v for _, v in cles], dtype=np.int64)
        poids = np.array([aretes[c][0] for c in cles], dtype=float)
        graphe = csr_matrix((poids, (lignes, colonnes)), shape=(n, n))

        # Plus grande composante fortement connexe : on peut y aller et en revenir.
        _, etiquettes = connected_components(graphe, directed=True, connection="strong")
        principale = np.bincount(etiquettes).argmax()
        garde = np.flatnonzero(etiquettes == principale)
        nouvel = -np.ones(n, dtype=np.int64)
        nouvel[garde] = np.arange(len(garde))
        self.coords = np.array(coords)[garde]
        self._geom: dict[tuple[int, int], list] = {}
        l2, c2, p2 = [], [], []
        for (u, v), (longueur, geom) in aretes.items():
            if nouvel[u] >= 0 and nouvel[v] >= 0:
                l2.append(nouvel[u])
                c2.append(nouvel[v])
                p2.append(longueur)
                self._geom[(int(nouvel[u]), int(nouvel[v]))] = geom
        m = len(garde)
        self.graphe = csr_matrix((np.array(p2), (np.array(l2), np.array(c2))), shape=(m, m))
        xy = np.column_stack([self.coords[:, 1] * self._kx, self.coords[:, 0] * self._ky])
        self._arbre = cKDTree(xy)

    def _m(self, a, b) -> float:
        return math.hypot((a[1] - b[1]) * self._kx, (a[0] - b[0]) * self._ky)

    @property
    def nb_carrefours(self) -> int:
        return self.graphe.shape[0]

    def rattacher(self, sites) -> tuple[np.ndarray, np.ndarray]:
        """Carrefour le plus proche de chaque site et distance d'accès (m)."""
        xy = np.array([[lon * self._kx, lat * self._ky] for lat, lon in sites])
        dist, noeud = self._arbre.query(xy)
        return noeud.astype(np.int64), dist

    def geometrie(self, chemin: list[int]) -> list[tuple[float, float]]:
        """Suite de carrefours → polyligne (lat, lon) qui suit les voies."""
        if len(chemin) < 2:
            return [tuple(self.coords[chemin[0]])] if chemin else []
        trace: list = []
        for u, v in zip(chemin, chemin[1:]):
            geom = self._geom[(u, v)]
            trace.extend(geom if not trace else geom[1:])
        return trace


@lru_cache(maxsize=2)
def _charger(chemin: str, _mtime: float) -> Reseau:
    with gzip.open(chemin, "rt", encoding="utf-8") as f:
        return Reseau(json.load(f))


def reseau_de(config: dict, nb_sites: int = 0) -> Reseau | None:
    """Réseau routier configuré (`collecte.reseau_routier`), ou None (ligne droite × coef_detour).

    Au-delà de `collecte.reseau_routier_max_sites` sites (toute la commune), on garde la ligne
    droite : la matrice routière demanderait trop de mémoire et de temps pour un recalcul en direct.
    """
    collecte = config.get("collecte") or {}
    chemin = collecte.get("reseau_routier")
    if not chemin or nb_sites > int(collecte.get("reseau_routier_max_sites", 600)):
        return None
    p = Path(chemin)
    if not p.is_absolute():
        p = RACINE / p
    if not p.exists():
        raise ValueError(f"réseau routier introuvable : {p} (lancer scripts/telecharger_reseau_routier.py)")
    return _charger(str(p), p.stat().st_mtime)


class Itineraires:
    """Distances routières entre des sites et tracé des trajets retenus."""

    def __init__(self, reseau: Reseau, sites):
        self.reseau = reseau
        self.sites = [tuple(map(float, s)) for s in sites]
        self.noeuds, self.acces = reseau.rattacher(sites)
        uniques, self._rang = np.unique(self.noeuds, return_inverse=True)
        # Par lots, pour borner la mémoire : on ne garde que les colonnes des sites et des
        # prédécesseurs en int32 (≈ 0,36 Mo par site pour 90 000 carrefours).
        lignes, preds = [], []
        for debut in range(0, len(uniques), 100):
            dist, pred = dijkstra(reseau.graphe, directed=True, indices=uniques[debut:debut + 100], return_predecessors=True)
            lignes.append(dist[:, uniques])
            preds.append(pred.astype(np.int32))
        self._pred = np.vstack(preds)
        d = np.vstack(lignes)[self._rang][:, self._rang]          # site × site
        d = d + self.acces[:, None] + self.acces[None, :]
        np.fill_diagonal(d, 0.0)
        if not np.isfinite(d).all():                            # ne devrait pas arriver (composante unique)
            d[~np.isfinite(d)] = 1e9
        self.matrice_m = d

    def matrice_entiers(self) -> list[list[int]]:
        return np.rint(self.matrice_m).astype(np.int64).tolist()

    def trajet(self, i: int, j: int) -> list[tuple[float, float]]:
        """Polyligne du site i au site j, qui suit les voies (accès en ligne droite aux deux bouts)."""
        source, cible = self.noeuds[i], self.noeuds[j]
        pred = self._pred[self._rang[i]]
        chemin = [int(cible)]
        while chemin[-1] != source and pred[chemin[-1]] >= 0:
            chemin.append(int(pred[chemin[-1]]))
        chemin.reverse()
        trace = [self.sites[i], *self.reseau.geometrie(chemin), self.sites[j]]   # accès aux deux bouts
        return [p for k, p in enumerate(trace) if k == 0 or tuple(p) != tuple(trace[k - 1])]

    def trace_tournee(self, route: list[int], arrondi: int = 5) -> list[list[list[float]]]:
        """Un tronçon par trajet : dépôt → 1er arrêt, …, dernier arrêt → dépôt (indices de sites)."""
        etapes = [0, *route, 0]
        return [
            [[round(la, arrondi), round(lo, arrondi)] for la, lo in _simplifier(self.trajet(a, b))]
            for a, b in zip(etapes, etapes[1:])
        ]


def _simplifier(points: list, tolerance_m: float = 4.0) -> list:
    """Retire les points presque alignés (Douglas-Peucker simple) pour alléger le plan enregistré."""
    if len(points) <= 2:
        return points
    kx = math.cos(math.radians(points[0][0])) * math.pi / 180 * R_TERRE
    ky = math.pi / 180 * R_TERRE
    xy = [(p[1] * kx, p[0] * ky) for p in points]
    garder = [False] * len(points)
    garder[0] = garder[-1] = True
    pile = [(0, len(points) - 1)]
    while pile:
        a, b = pile.pop()
        (x1, y1), (x2, y2) = xy[a], xy[b]
        dx, dy = x2 - x1, y2 - y1
        norme = math.hypot(dx, dy) or 1e-9
        pire, k_pire = -1.0, -1
        for k in range(a + 1, b):
            d = abs(dy * (xy[k][0] - x1) - dx * (xy[k][1] - y1)) / norme
            if d > pire:
                pire, k_pire = d, k
        if pire > tolerance_m:
            garder[k_pire] = True
            pile += [(a, k_pire), (k_pire, b)]
    return [p for p, g in zip(points, garder) if g]
