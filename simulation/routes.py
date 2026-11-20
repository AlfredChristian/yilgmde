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
import threading
from collections import OrderedDict
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
    """Réseau routier configuré (`collecte.reseau_routier`), ou None (ligne droite × coef_detour)."""
    collecte = config.get("collecte") or {}
    chemin = collecte.get("reseau_routier")
    if not chemin:
        return None
    p = Path(chemin)
    if not p.is_absolute():
        p = RACINE / p
    if not p.exists():
        raise ValueError(f"réseau routier introuvable : {p} (lancer scripts/telecharger_reseau_routier.py)")
    return _charger(str(p), p.stat().st_mtime)


_MEMOIRE_ITINERAIRES: "OrderedDict[tuple, Itineraires]" = OrderedDict()
_VERROU_ITINERAIRES = threading.Lock()


def itineraires(reseau: "Reseau", sites, max_sites_complet: int = 600, rayon_m: float = 5000.0,
                coef_lointain: float = 1.3, garder: int = 8) -> "Itineraires":
    """Comme `Itineraires(...)`, mais réutilise le calcul des mêmes sites sur le même réseau (D68).

    Le calcul des distances sur les routes est l'étape la plus longue d'un plan (≈ 1,6 s pour un
    arrondissement). Un recalcul qui garde les mêmes points (panne de camions, budget, nouveau
    scénario sur la même zone) retrouve ainsi le résultat au lieu de le refaire. Le résultat est
    identique : seuls les sites, le réseau et les réglages entrent dans la clé.
    """
    cle = (id(reseau), tuple((round(float(a), 7), round(float(b), 7)) for a, b in sites),
           int(max_sites_complet), float(rayon_m), float(coef_lointain))
    with _VERROU_ITINERAIRES:
        trouve = _MEMOIRE_ITINERAIRES.get(cle)
        if trouve is not None and trouve.reseau is reseau:
            _MEMOIRE_ITINERAIRES.move_to_end(cle)
            return trouve
    itin = Itineraires(reseau, sites, max_sites_complet=max_sites_complet, rayon_m=rayon_m,
                       coef_lointain=coef_lointain)
    with _VERROU_ITINERAIRES:
        _MEMOIRE_ITINERAIRES[cle] = itin
        while len(_MEMOIRE_ITINERAIRES) > garder:
            _MEMOIRE_ITINERAIRES.popitem(last=False)
    return itin


class Itineraires:
    """Distances routières entre des sites et tracé des trajets retenus.

    Jusqu'à `max_sites_complet` sites (un arrondissement), toutes les paires sont calculées sur
    les routes et les chemins sont gardés. Au-delà (toute la commune), Dijkstra est limité à
    `rayon_m` autour de chaque site : les paires proches, celles qu'une tournée enchaîne, sont
    sur les routes ; les paires lointaines, que le solveur écarte de toute façon, sont estimées
    (ligne droite × `coef_lointain`). Les trajets retenus sont ensuite tracés sur les routes un
    par un. Mémoire et temps restent ainsi bornés (≈ 1 ms par site au lieu de 13).
    """

    def __init__(self, reseau: Reseau, sites, max_sites_complet: int = 600, rayon_m: float = 5000.0,
                 coef_lointain: float = 1.3):
        self.reseau = reseau
        self.sites = [tuple(map(float, s)) for s in sites]
        self.noeuds, self.acces = reseau.rattacher(sites)
        if len(self.sites) > max_sites_complet:
            self._limite(rayon_m, coef_lointain)
            return
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

    def _limite(self, rayon_m: float, coef_lointain: float) -> None:
        uniques, self._rang = np.unique(self.noeuds, return_inverse=True)
        lignes = []
        for debut in range(0, len(uniques), 200):
            dist = dijkstra(self.reseau.graphe, directed=True, indices=uniques[debut:debut + 200], limit=rayon_m)
            lignes.append(dist[:, uniques])
        d = np.vstack(lignes)[self._rang][:, self._rang]
        d = d + self.acces[:, None] + self.acces[None, :]
        loin = ~np.isfinite(d)
        if loin.any():
            la = np.radians([s[0] for s in self.sites])
            lo = np.radians([s[1] for s in self.sites])
            a = (np.sin((la[:, None] - la[None, :]) / 2) ** 2
                 + np.cos(la[:, None]) * np.cos(la[None, :]) * np.sin((lo[:, None] - lo[None, :]) / 2) ** 2)
            droit = 2 * R_TERRE * np.arcsin(np.sqrt(np.minimum(a, 1.0)))
            d[loin] = droit[loin] * coef_lointain
        np.fill_diagonal(d, 0.0)
        self.matrice_m = d
        self._pred = None                  # chemins recalculés à la demande (trajet)

    def matrice_entiers(self) -> list[list[int]]:
        return np.rint(self.matrice_m).astype(np.int64).tolist()

    def trajet(self, i: int, j: int) -> list[tuple[float, float]]:
        """Polyligne du site i au site j, qui suit les voies (accès en ligne droite aux deux bouts)."""
        source, cible = self.noeuds[i], self.noeuds[j]
        if self._pred is not None:
            chemin = _remonter(self._pred[self._rang[i]], int(source), int(cible))
        elif j == 0:                       # retour au dépôt : arbre inverse calculé une fois
            chemin = _remonter(self._arbre_vers_depot(), int(cible), int(source))[::-1]
        elif i == 0:                       # départ du dépôt : arbre calculé une fois
            chemin = _remonter(self._arbre_depuis_depot(), int(source), int(cible))
        else:                              # mode limité : un Dijkstra borné juste pour ce trajet
            borne = float(self.matrice_m[i][j]) * 1.5 + 1000.0
            _, pred = dijkstra(self.reseau.graphe, directed=True, indices=int(source), limit=borne,
                               return_predecessors=True)
            chemin = _remonter(pred, int(source), int(cible))
        trace = [self.sites[i], *self.reseau.geometrie(chemin), self.sites[j]]   # accès aux deux bouts
        return [p for k, p in enumerate(trace) if k == 0 or tuple(p) != tuple(trace[k - 1])]

    def _arbre_depuis_depot(self):
        if getattr(self, "_depuis", None) is None:
            _, self._depuis = dijkstra(self.reseau.graphe, directed=True, indices=int(self.noeuds[0]),
                                       return_predecessors=True)
        return self._depuis

    def _arbre_vers_depot(self):
        """Prédécesseurs dans le graphe inversé : chemin de n'importe quel carrefour vers le dépôt."""
        if getattr(self, "_vers", None) is None:
            _, self._vers = dijkstra(self.reseau.graphe.T.tocsr(), directed=True, indices=int(self.noeuds[0]),
                                     return_predecessors=True)
        return self._vers

    def trace_tournee(self, route: list[int], arrondi: int = 5) -> list[list[list[float]]]:
        """Un tronçon par trajet : dépôt → 1er arrêt, …, dernier arrêt → dépôt (indices de sites)."""
        etapes = [0, *route, 0]
        return [
            [[round(la, arrondi), round(lo, arrondi)] for la, lo in _simplifier(self.trajet(a, b))]
            for a, b in zip(etapes, etapes[1:])
        ]


def _remonter(pred, source: int, cible: int) -> list[int]:
    """Chemin source → cible à partir d'un tableau de prédécesseurs (Dijkstra depuis `source`)."""
    chemin = [cible]
    while chemin[-1] != source and pred[chemin[-1]] >= 0:
        chemin.append(int(pred[chemin[-1]]))
    chemin.reverse()
    return chemin


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
