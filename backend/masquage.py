"""Masquage automatique des visages et des plaques d'immatriculation (livrable 1, D36).

Filet de sécurité **côté serveur** : l'application floute déjà sur le téléphone
avant l'envoi quand elle le peut, mais aucune photo n'est enregistrée sans passer
ici. Ainsi, même une photo envoyée par un client qui ne floute pas n'est jamais
gardée en clair.

Méthode (OpenCV, sans service externe ; D57) :
1. décodage de l'image (une image illisible est refusée) et réduction si elle
   dépasse `masquage.cote_max_px` ;
2. détection en niveaux de gris égalisés, sur une copie réduite à
   `masquage.cote_detection_px` (rapide) :
   - visages : **YuNet** (réseau de neurones léger fourni par OpenCV, modèle ONNX de
     230 Ko dans `backend/modeles/`, licence MIT), qui voit aussi les visages de trois
     quarts, petits ou dans l'ombre. Sans le modèle, retour aux cascades de Haar de
     face et de profil ;
   - plaques : **recherche par la forme**, valable quel que soit le pays (et, D59, un fond
     clair portant des caractères sur une ou deux lignes, comme les plaques de moto jaunes) : un rectangle
     plus clair que son entourage, 2 à 6,5 fois plus large que haut, qui contient une
     rangée de 4 à 12 caractères sombres de même hauteur (2 à 10 fois plus large que haute) ; complétée par les cascades
     `russian_plate_number` et `license_plate_rus_16stages` ;
3. chaque zone, élargie de `marge`, est **pixelisée puis floutée** (irréversible) ;
4. ré-encodage en JPEG : les métadonnées EXIF (dont la position GPS de l'appareil
   et son modèle) disparaissent.

Limites connues : un visage de moins de 10 pixels ou de dos, une plaque très inclinée,
sale ou à demi cachée peuvent échapper au floutage ; un panneau ou une inscription peut
être flouté à tort (on préfère flouter trop que pas assez). L'admin voit la photo avant
de valider et peut la rejeter.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    import cv2
except ImportError:   # pragma: no cover - dépend de l'environnement
    cv2 = None

from pathlib import Path

MODELE_YUNET = Path(__file__).resolve().parent / "modeles" / "face_detection_yunet_2023mar.onnx"
CASCADES_VISAGES = ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml")
CASCADES_PLAQUES = ("haarcascade_russian_plate_number.xml", "haarcascade_license_plate_rus_16stages.xml")

_cache: dict[str, object] = {}


class MasquageIndisponible(RuntimeError):
    """OpenCV absent : aucune photo ne doit être enregistrée sans masquage."""


@dataclass(frozen=True)
class Resultat:
    contenu: bytes            # JPEG masqué, sans métadonnées
    extension: str            # toujours ".jpg"
    visages: int
    plaques: int
    largeur: int
    hauteur: int

    def resume(self) -> dict:
        return {"visages": self.visages, "plaques": self.plaques, "methode": "opencv-yunet" if MODELE_YUNET.exists() else "opencv-haar"}


def disponible() -> bool:
    return cv2 is not None


def _cascade(nom: str):
    if nom not in _cache:
        c = cv2.CascadeClassifier(cv2.data.haarcascades + nom)
        if c.empty():
            raise MasquageIndisponible(f"détecteur OpenCV introuvable : {nom} (opencv-python-headless < 5 requis)")
        _cache[nom] = c
    return _cache[nom]


def _parametres(config: dict) -> dict:
    m = config.get("masquage", {})
    return {
        "cote_max": int(m.get("cote_max_px", 1600)),
        "cote_detection": int(m.get("cote_detection_px", 800)),
        "facteur": float(m.get("facteur_echelle", 1.1)),
        "voisins_visage": int(m.get("voisins_min_visage", 5)),
        "voisins_plaque": int(m.get("voisins_min_plaque", 4)),
        "taille_min": int(m.get("taille_min_px", 20)),
        "marge": float(m.get("marge", 0.25)),
        "qualite": int(m.get("qualite_jpeg", 85)),
        "seuil_yunet": float(m.get("seuil_visage", 0.6)),
    }


CONTRASTE_MIN_VISAGE = 6.0   # écart type des gris en dessous duquel une zone est jugée unie


def _visages_yunet(image, seuil: float) -> list[tuple[int, int, int, int]] | None:
    """Visages par YuNet, ou None si le modèle est absent."""
    if not MODELE_YUNET.exists() or not hasattr(cv2, "FaceDetectorYN"):
        return None
    h, w = image.shape[:2]
    cle = f"yunet-{seuil}"
    if cle not in _cache:
        _cache[cle] = cv2.FaceDetectorYN.create(str(MODELE_YUNET), "", (w, h), seuil, 0.3, 5000)
    detecteur = _cache[cle]
    detecteur.setInputSize((w, h))
    _, visages = detecteur.detect(image)
    if visages is None:
        return []
    gris = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    sortie = []
    for v in visages:
        x, y, vw, vh = (int(v[0]), int(v[1]), int(v[2]), int(v[3]))
        zone = gris[max(0, y):max(0, y + vh), max(0, x):max(0, x + vw)]
        # Un vrai visage a du relief (yeux, nez, bouche). Certaines versions d'OpenCV (vu sous
        # Windows, 4.14) voient un « visage » dans une zone unie : on l'écarte.
        if zone.size and float(zone.std()) >= CONTRASTE_MIN_VISAGE:
            sortie.append((x, y, vw, vh))
    return sortie


def _plaques_par_forme(gris) -> list[tuple[int, int, int, int]]:
    """Rectangles clairs contenant une rangée de caractères sombres (plaques de tout pays)."""
    h, w = gris.shape[:2]
    kx = max(9, (w // 45) | 1)
    noir_sur_clair = cv2.morphologyEx(gris, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (kx, max(5, kx // 3))))
    grad = np.absolute(cv2.Sobel(noir_sur_clair, cv2.CV_32F, 1, 0, ksize=3))
    grad = cv2.normalize(grad, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    grad = cv2.morphologyEx(cv2.GaussianBlur(grad, (5, 5), 0), cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_RECT, (kx * 2 + 1, max(3, kx // 3))))
    _, masque = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    masque = cv2.dilate(cv2.erode(masque, None, iterations=2), None, iterations=2)
    contours, _ = cv2.findContours(masque, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    plaques = []
    for c in contours:
        # La zone trouvée est la rangée de caractères : 2 à 10 fois plus large que haute.
        x, y, cw, ch = cv2.boundingRect(c)
        if ch < 8 or not 2.0 <= cw / ch <= 10 or not 0.0003 * w * h <= cw * ch <= 0.06 * w * h:
            continue
        dy = int(ch * 0.5)                             # la plaque déborde la rangée de caractères
        y0, y1 = max(0, y - dy), min(h, y + ch + dy)
        region = gris[y0:y1, x:x + cw]
        _, encre = cv2.threshold(region, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        if encre.mean() / 255 > 0.6:          # surtout sombre : pas un fond clair à caractères
            continue
        n, _, stats, _ = cv2.connectedComponentsWithStats(encre)
        caracteres = [s for s in stats[1:] if 0.6 * ch <= s[cv2.CC_STAT_HEIGHT] <= 1.2 * ch
                      and s[cv2.CC_STAT_WIDTH] <= 0.3 * cw and s[cv2.CC_STAT_AREA] >= 6]
        if 4 <= len(caracteres) <= 12:
            hauteurs = [s[cv2.CC_STAT_HEIGHT] for s in caracteres]
            if max(hauteurs) <= 1.6 * min(hauteurs):      # caractères de même taille
                plaques.append((x, y0, cw, y1 - y0))
    return plaques


def _plaques_dans_masque(gris, masque) -> list[tuple[int, int, int, int]]:
    """Zones du masque (fond de plaque supposé) à peu près rectangulaires, portant 4 à 16
    caractères sombres sur une ou deux lignes."""
    h, w = gris.shape[:2]
    m = max(3, (w // 100) | 1)
    masque = cv2.morphologyEx(masque, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (m, m)))
    n, etiquettes, stats, _ = cv2.connectedComponentsWithStats(masque)
    plaques = []
    for i in range(1, n):
        x, y, cw, ch, aire = (int(v) for v in stats[i])
        if not (0.0005 * w * h <= aire <= 0.08 * w * h and 0.8 <= cw / ch <= 5 and aire >= 0.5 * cw * ch and ch >= 12):
            continue
        region = gris[y:y + ch, x:x + cw]
        # Seul l'intérieur de la plaque compte (une plaque penchée laisse des coins sombres dans sa boîte).
        pts = np.column_stack(np.nonzero(etiquettes[y:y + ch, x:x + cw] == i))[:, ::-1].astype(np.int32)
        coque = np.zeros((ch, cw), np.uint8)
        cv2.fillConvexPoly(coque, cv2.convexHull(pts), 1)
        coque = cv2.erode(coque, np.ones((3, 3), np.uint8), iterations=2)
        dedans = region[coque > 0]
        if dedans.size < 20:
            continue
        seuil, _ = cv2.threshold(dedans.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        encre = ((region <= seuil) & (coque > 0)).astype(np.uint8)
        nn, _, s2, c2 = cv2.connectedComponentsWithStats(encre)
        caracteres = sorted(
            ((s2[j], c2[j]) for j in range(1, nn)
             if 0.15 * ch <= s2[j][3] <= 0.85 * ch and s2[j][2] <= 0.35 * cw and s2[j][4] >= 6),
            key=lambda t: t[1][1])
        rangees = []          # caractères de même hauteur, centres alignés
        for st, centre in caracteres:
            for r in rangees:
                if abs(centre[1] - r["y"]) <= 0.5 * r["h"] and 0.6 <= st[3] / r["h"] <= 1.6:
                    r["n"] += 1
                    break
            else:
                rangees.append({"y": centre[1], "h": int(st[3]), "n": 1})
        bonnes = [r for r in rangees if r["n"] >= 3]
        if 1 <= len(bonnes) <= 2 and 4 <= sum(r["n"] for r in bonnes) <= 16:
            plaques.append((x, y, cw, ch))
    return plaques


def _plaques_fond_clair(gris, image=None) -> list[tuple[int, int, int, int]]:
    """Plaques vues par leur fond (D59) : un fond **plus clair que son entourage** (plaque
    blanche, ou jaune éclairée par le flash), ou un fond **jaune** (plaques de moto burkinabè,
    qui sans flash ont la même luminosité que la latérite mais pas la même couleur). Le fond
    doit porter 4 à 16 caractères sombres sur une ou deux lignes."""
    h, w = gris.shape[:2]
    k = max(15, (w // 20) | 1)
    fond = cv2.blur(gris, (k * 3, k * 3))
    masques = [((gris.astype(np.int16) - fond > 25) & (gris > 110)).astype(np.uint8)]
    if image is not None:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        jaune = ((hsv[..., 0] >= 20) & (hsv[..., 0] <= 40) & (hsv[..., 1] >= 40) & (hsv[..., 2] >= 80)).astype(np.uint8)
        # Points jaunes isolés (grain du sol, herbe sèche) retirés : ils relieraient la plaque au décor.
        masques.append(cv2.morphologyEx(jaune, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)))
    plaques = []
    for masque in masques:
        plaques += [z for z in _plaques_dans_masque(gris, masque) if z not in plaques]
    return plaques


def _detecter(gris, cascades, facteur, voisins, taille_min, miroir=False) -> list[tuple[int, int, int, int]]:
    zones = []
    largeur = gris.shape[1]
    for nom in cascades:
        c = _cascade(nom)
        for x, y, w, h in c.detectMultiScale(gris, scaleFactor=facteur, minNeighbors=voisins,
                                             minSize=(taille_min, taille_min)):
            zones.append((int(x), int(y), int(w), int(h)))
        if miroir and "profile" in nom:   # la cascade de profil ne voit qu'un côté
            for x, y, w, h in c.detectMultiScale(cv2.flip(gris, 1), scaleFactor=facteur, minNeighbors=voisins,
                                                 minSize=(taille_min, taille_min)):
                zones.append((int(largeur - x - w), int(y), int(w), int(h)))
    return zones


def detecter(image, config: dict) -> dict[str, list[tuple[int, int, int, int]]]:
    """Zones (x, y, largeur, hauteur) des visages et des plaques, en pixels de `image`."""
    p = _parametres(config)
    h, w = image.shape[:2]
    echelle = min(1.0, p["cote_detection"] / max(h, w))
    petite = cv2.resize(image, (max(1, int(w * echelle)), max(1, int(h * echelle))), interpolation=cv2.INTER_AREA) \
        if echelle < 1 else image
    gris = cv2.equalizeHist(cv2.cvtColor(petite, cv2.COLOR_BGR2GRAY))
    taille_min = max(8, int(p["taille_min"] * echelle))

    def remettre(zones):
        return [(int(x / echelle), int(y / echelle), int(zw / echelle), int(zh / echelle)) for x, y, zw, zh in zones]

    yunet = _visages_yunet(petite, p["seuil_yunet"])
    if yunet is None:          # modèle absent : anciennes cascades de face et de profil
        visages = _detecter(gris, CASCADES_VISAGES, p["facteur"], p["voisins_visage"], taille_min, miroir=True)
    else:
        visages = yunet
    gris_brut = cv2.cvtColor(petite, cv2.COLOR_BGR2GRAY)
    plaques = _detecter(gris, CASCADES_PLAQUES, p["facteur"], p["voisins_plaque"], taille_min) + _plaques_par_forme(gris_brut) \
        + _plaques_fond_clair(gris_brut, petite)
    return {"visages": remettre(visages), "plaques": remettre(plaques)}


def _fusionner(zones: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    """Retire les zones entièrement contenues dans une autre (doublons des cascades)."""
    garde = []
    for z in sorted(zones, key=lambda r: -r[2] * r[3]):
        x, y, w, h = z
        if not any(x >= gx and y >= gy and x + w <= gx + gw and y + h <= gy + gh for gx, gy, gw, gh in garde):
            garde.append(z)
    return garde


def flouter(image, zone: tuple[int, int, int, int], marge: float) -> None:
    """Pixelise puis floute la zone élargie de `marge`, en place. Irréversible."""
    x, y, w, h = zone
    dx, dy = int(w * marge), int(h * marge)
    x0, y0 = max(0, x - dx), max(0, y - dy)
    x1, y1 = min(image.shape[1], x + w + dx), min(image.shape[0], y + h + dy)
    if x1 <= x0 or y1 <= y0:
        return
    region = image[y0:y1, x0:x1]
    # Blocs de 1/5 de la zone : même un détecteur moderne (YuNet) n'y retrouve plus de visage.
    bloc = max(4, min(x1 - x0, y1 - y0) // 5)
    petite = cv2.resize(region, (max(1, (x1 - x0) // bloc), max(1, (y1 - y0) // bloc)), interpolation=cv2.INTER_AREA)
    pixel = cv2.resize(petite, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
    noyau = max(3, (bloc * 2) | 1)
    image[y0:y1, x0:x1] = cv2.GaussianBlur(pixel, (noyau, noyau), 0)


def masquer_photo(contenu: bytes, config: dict) -> Resultat:
    """Photo (JPEG, PNG ou WebP) → JPEG masqué sans métadonnées.

    Lève MasquageIndisponible si OpenCV manque, ValueError si l'image est illisible.
    """
    if cv2 is None:
        raise MasquageIndisponible("OpenCV n'est pas installé : photo refusée plutôt que gardée en clair")
    p = _parametres(config)
    image = cv2.imdecode(np.frombuffer(contenu, np.uint8), cv2.IMREAD_COLOR)   # applique l'orientation EXIF
    if image is None:
        raise ValueError("image illisible")
    h, w = image.shape[:2]
    if max(h, w) > p["cote_max"]:
        e = p["cote_max"] / max(h, w)
        image = cv2.resize(image, (int(w * e), int(h * e)), interpolation=cv2.INTER_AREA)

    zones = detecter(image, config)
    visages, plaques = _fusionner(zones["visages"]), _fusionner(zones["plaques"])
    for z in visages + plaques:
        flouter(image, z, p["marge"])
    ok, tampon = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, p["qualite"]])
    if not ok:   # pragma: no cover
        raise ValueError("ré-encodage impossible")
    return Resultat(tampon.tobytes(), ".jpg", len(visages), len(plaques), image.shape[1], image.shape[0])
