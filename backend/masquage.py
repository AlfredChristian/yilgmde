"""Masquage automatique des visages et des plaques d'immatriculation (livrable 1, D36).

Filet de sécurité **côté serveur** : l'application floute déjà sur le téléphone
avant l'envoi quand elle le peut, mais aucune photo n'est enregistrée sans passer
ici. Ainsi, même une photo envoyée par un client qui ne floute pas n'est jamais
gardée en clair.

Méthode (OpenCV, sans service externe ni modèle à télécharger) :
1. décodage de l'image (une image illisible est refusée) et réduction si elle
   dépasse `masquage.cote_max_px` ;
2. détection en niveaux de gris égalisés, sur une copie réduite à
   `masquage.cote_detection_px` (rapide) :
   - visages : cascades de Haar de face (`frontalface_default`) et de profil
     (`profileface`, aussi sur l'image retournée pour l'autre profil) ;
   - plaques : cascades `russian_plate_number` et `license_plate_rus_16stages`
     (plaques rectangulaires à caractères sombres sur fond clair, proches des
     plaques burkinabè) ;
3. chaque zone, élargie de `marge`, est **pixelisée puis floutée** (irréversible) ;
4. ré-encodage en JPEG : les métadonnées EXIF (dont la position GPS de l'appareil
   et son modèle) disparaissent.

Limites connues : les cascades de Haar manquent des visages de trois quarts, très
petits ou dans l'ombre, et des plaques inclinées ou sales ; elles floutent parfois
un motif qui n'est ni un visage ni une plaque (on préfère flouter trop que pas
assez). C'est pourquoi le masquage côté téléphone reste souhaitable, et l'admin
peut toujours rejeter une photo.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    import cv2
except ImportError:   # pragma: no cover - dépend de l'environnement
    cv2 = None

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
        return {"visages": self.visages, "plaques": self.plaques, "methode": "opencv-haar"}


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
    }


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

    return {
        "visages": remettre(_detecter(gris, CASCADES_VISAGES, p["facteur"], p["voisins_visage"], taille_min, miroir=True)),
        "plaques": remettre(_detecter(gris, CASCADES_PLAQUES, p["facteur"], p["voisins_plaque"], taille_min)),
    }


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
    bloc = max(4, min(x1 - x0, y1 - y0) // 8)
    petite = cv2.resize(region, (max(1, (x1 - x0) // bloc), max(1, (y1 - y0) // bloc)), interpolation=cv2.INTER_LINEAR)
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
