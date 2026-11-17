"""Arrondissements et secteurs de Ouagadougou relevés sur la carte de l'INSD (D42).

Source : carte « Le nouveau découpage administratif de la Commune de Ouagadougou »
(12 arrondissements, 55 secteurs ; loi 066-2009/AN modifiée par la loi 026-2012/AN),
INSD, 5e RGPH 2019, *Monographie de la commune de Ouagadougou*.

La carte n'a pas de coordonnées. Méthode :
1. relevé **à la main**, en pixels (image de 656 × 472), du contour de la commune, des
   limites d'arrondissement (traits épais) et de la position des 55 numéros de secteur ;
2. échelle : barre d'échelle de la carte (5 km = 88 px, soit 56,8 m/px) ; un ajustement
   libre sur le contour OpenStreetMap trouve 56,6 m/px, à 0,5 % près ;
3. position : translation qui recouvre au mieux le contour OpenStreetMap de la commune
   (relation 5675756) ; carte orientée nord (une rotation n'améliore pas le recouvrement :
   83 % sans, 84 % avec) ;
4. arrondissements : polygones reconstruits à partir des limites relevées (shapely) ;
5. secteurs : diagrammes de Voronoï des numéros de secteur, dans leur arrondissement.

Précision : quelques centaines de mètres pour les limites d'arrondissement ; les
limites **entre secteurs** sont approchées (Voronoï), seuls leur numéro et leur
position sont relevés. Contrôle : superficie de chaque arrondissement comparée à
celle de l'INSD (population / densité, tableaux 2.2 et A 15) dans les tests.
"""

from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.ops import polygonize, unary_union, voronoi_diagram

from simulation.geometrie import depuis_metres

# --- Calage ---------------------------------------------------------------------------------

METRES_PAR_PIXEL = 5000 / 88                  # barre d'échelle de la carte
ORIGINE = (12.37, -1.53)                      # origine de la projection locale (lat, lon)
TRANSLATION_M = (-17783.0, 13241.0)           # ajustée sur le contour OpenStreetMap (recouvrement 83 %)


def vers_geo(x: float, y: float) -> tuple[float, float]:
    """Pixel de la carte → (longitude, latitude)."""
    lat, lon = depuis_metres(x * METRES_PAR_PIXEL + TRANSLATION_M[0], -y * METRES_PAR_PIXEL + TRANSLATION_M[1],
                             *ORIGINE)
    return lon, lat


# --- Relevés (pixels de la carte) ----------------------------------------------------------------

CONTOUR = [(340, 18), (360, 9), (380, 4), (420, 3), (450, 3), (455, 20), (460, 40), (466, 58), (474, 70),
           (478, 95), (482, 118), (482, 160), (485, 185), (483, 198), (492, 215), (500, 240), (507, 255),
           (512, 280), (518, 300), (520, 322), (519, 345), (514, 370), (510, 400), (505, 430), (500, 455),
           (495, 466), (470, 460), (440, 456), (420, 451), (400, 447), (360, 440), (340, 437), (320, 433),
           (300, 431), (280, 432), (260, 430), (240, 430), (200, 433), (160, 433), (140, 430), (130, 423),
           (122, 410), (117, 393), (110, 380), (100, 365), (92, 350), (80, 335), (75, 320), (70, 300), (68, 280),
           (70, 250), (75, 235), (80, 215), (88, 195), (97, 178), (105, 165), (115, 150), (130, 135), (145, 120),
           (160, 108), (175, 98), (185, 93), (200, 78), (210, 68), (225, 55), (240, 45), (262, 37), (282, 30),
           (300, 26), (320, 22)]

# Limites d'arrondissement (traits épais).
LIMITES = {
    "8|9 (secteurs 36|37)": [(100, 152), (111, 157), (140, 186), (160, 201), (185, 213)],
    "3 nord (15, 16 | 37, 38, 39, 17)": [(183, 222), (188, 200), (200, 190), (222, 178), (278, 178),
                                        (276, 193), (292, 207), (282, 223)],
    "3|8 (13, 14 | 34, 35)": [(183, 222), (184, 255), (186, 262), (178, 285), (180, 315), (183, 333)],
    "diagonale 8|7, 3|6, 2|1": [(92, 350), (140, 338), (183, 329), (200, 322), (240, 308),
                                (272, 292), (300, 276), (320, 258), (340, 253), (376, 222)],
    "centre ouest et nord (2 | 3, 4)": [(272, 292), (268, 270), (270, 240), (278, 225), (290, 222),
                                        (300, 220), (318, 226), (340, 222), (376, 222)],
    "centre sud (1 | 6, 12)": [(272, 292), (282, 312), (300, 322), (330, 324), (340, 325)],
    "1|5 (3, 4 | 22, 23, 24)": [(376, 222), (379, 262), (365, 285), (372, 290), (369, 300), (362, 300),
                                (355, 308), (340, 325)],
    "9|4 (40, 39 | 20, 17)": [(337, 15), (345, 70), (350, 140), (313, 173), (278, 172), (278, 178)],
    "4 | 5, 10": [(485, 115), (422, 168), (383, 200), (377, 222)],
    "5|10": [(422, 168), (428, 190), (435, 215), (440, 228)],
    "5|11": [(440, 228), (420, 260), (378, 325)],
    "10|11": [(420, 260), (475, 295), (500, 318), (520, 322)],
    "12 ouest (6, 7 | 12)": [(330, 324), (328, 380), (326, 435)],
    "12 nord (5 | 12)": [(330, 324), (340, 325), (378, 325)],
    "12 est (11 | 12)": [(378, 325), (440, 400), (495, 466)],
    "6|7": [(183, 333), (212, 331), (215, 340), (222, 355), (240, 372), (242, 385), (300, 387), (327, 390)],
}

# Position des numéros de secteur, et arrondissement de chaque secteur (55 au total).
SECTEURS = {
    1: (320, 272), 2: (334, 268), 3: (366, 248), 4: (355, 284), 5: (316, 301), 6: (289, 297),
    7: (286, 266), 8: (283, 244), 9: (300, 231), 10: (330, 245), 11: (332, 231),
    12: (246, 283), 13: (199, 287), 14: (228, 246), 15: (214, 208), 16: (261, 209),
    17: (320, 196), 18: (365, 202), 19: (426, 134), 20: (398, 65),
    21: (411, 202), 22: (394, 230), 23: (398, 259), 24: (371, 312),
    25: (305, 338), 26: (270, 318), 27: (236, 334), 28: (255, 363), 29: (300, 371),
    30: (300, 411), 31: (249, 408), 32: (194, 394), 33: (139, 368),
    34: (127, 308), 35: (127, 248), 36: (115, 202),
    37: (163, 153), 38: (243, 106), 39: (306, 153), 40: (324, 87),
    41: (463, 152), 42: (458, 185), 43: (466, 220), 44: (443, 253), 45: (484, 278),
    46: (439, 289), 47: (487, 326), 48: (472, 354), 49: (475, 399), 50: (438, 348), 51: (407, 319),
    52: (352, 341), 53: (394, 373), 54: (351, 376), 55: (390, 423),
}
ARRONDISSEMENT_DU_SECTEUR = {s: a for a, plage in {
    1: range(1, 7), 2: range(7, 12), 3: range(12, 17), 4: range(17, 21), 5: range(21, 25), 6: range(25, 30),
    7: range(30, 34), 8: range(34, 37), 9: range(37, 41), 10: range(41, 46), 11: range(46, 52), 12: range(52, 56),
}.items() for s in plage}

# Extrémités posées sur le contour : prolongées davantage pour bien le couper.
SUR_LE_CONTOUR = {"8|9 (secteurs 36|37)": "debut", "diagonale 8|7, 3|6, 2|1": "debut", "9|4 (40, 39 | 20, 17)": "debut",
                  "4 | 5, 10": "debut", "10|11": "fin", "12 ouest (6, 7 | 12)": "fin", "12 est (11 | 12)": "fin"}


def _prolonger(pts, contour: str | None = None, px=4.0, loin=12.0):
    """Prolonge les extrémités : deux limites qui se touchent presque se croisent bien."""
    def bout(a, b, d):
        dx, dy = a[0] - b[0], a[1] - b[1]
        n = math.hypot(dx, dy) or 1.0
        return (a[0] + dx / n * d, a[1] + dy / n * d)
    return [bout(pts[0], pts[1], loin if contour == "debut" else px), *pts,
            bout(pts[-1], pts[-2], loin if contour == "fin" else px)]


def _en_geo(geometrie):
    """Géométrie en pixels → géométrie en (lon, lat)."""
    return shapely.transform(geometrie, lambda xy: np.array([vers_geo(x, y) for x, y in xy]))


def arrondissements_pixels() -> dict[int, Polygon]:
    contour = Polygon(CONTOUR)
    lignes = [LineString(_prolonger(pts, SUR_LE_CONTOUR.get(nom))) for nom, pts in LIMITES.items()]
    morceaux = [m.intersection(contour) for m in polygonize(unary_union(lignes + [contour.exterior]))
                if m.representative_point().within(contour)]
    reperes: dict[int, list] = {}
    for s, xy in SECTEURS.items():
        reperes.setdefault(ARRONDISSEMENT_DU_SECTEUR[s], []).append(Point(xy))
    resultat: dict[int, list] = {a: [] for a in reperes}
    orphelins = []
    for m in morceaux:
        dedans = {a for a, pts in reperes.items() if any(m.contains(p) for p in pts)}
        if len(dedans) > 1:
            raise ValueError(f"un morceau contient des secteurs de plusieurs arrondissements : {sorted(dedans)}")
        (resultat[dedans.pop()] if dedans else orphelins).append(m)
    for m in orphelins:   # miettes entre deux limites : à l'arrondissement de plus longue frontière commune
        voisin = max(resultat, key=lambda a: unary_union(resultat[a]).boundary.intersection(m.boundary).length
                     if resultat[a] else 0)
        resultat[voisin].append(m)
    return {a: unary_union(ms) for a, ms in resultat.items()}


def secteurs_pixels(arrondissements: dict[int, Polygon]) -> dict[int, Polygon]:
    """Voronoï des numéros de secteur, découpé par leur arrondissement."""
    resultat = {}
    for a, poly in arrondissements.items():
        siens = [s for s, aa in ARRONDISSEMENT_DU_SECTEUR.items() if aa == a]
        for s in siens:
            if not poly.contains(Point(SECTEURS[s])):
                raise ValueError(f"secteur {s} hors de son arrondissement {a}")
        if len(siens) == 1:
            resultat[siens[0]] = poly
            continue
        cellules = voronoi_diagram(MultiPoint([SECTEURS[s] for s in siens]), envelope=poly.buffer(50))
        for s in siens:
            cellule = next(c for c in cellules.geoms if c.contains(Point(SECTEURS[s])))
            resultat[s] = cellule.intersection(poly)
    return resultat


def decoupage():
    """(arrondissements, secteurs, commune) en coordonnées géographiques (lon, lat)."""
    arr_px = arrondissements_pixels()
    sec_px = secteurs_pixels(arr_px)
    return ({a: _en_geo(g) for a, g in arr_px.items()},
            {s: _en_geo(g) for s, g in sec_px.items()},
            _en_geo(Polygon(CONTOUR)))
