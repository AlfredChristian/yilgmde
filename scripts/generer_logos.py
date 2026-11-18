"""Logos et icônes de l'application à partir des sources de docs/marque/sources (D66).

    python scripts/generer_logos.py

Détoure les logos (le fond crème devient transparent, bords adoucis), les recadre, puis
écrit les versions utilisées par l'interface (frontend/public/marque/), les icônes de
l'application installable et du navigateur (frontend/public/), et le logo du PDF
(backend/ressources/). À relancer seulement si les sources changent.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

RACINE = Path(__file__).resolve().parent.parent
SOURCES = RACINE / "docs" / "marque" / "sources"
PUBLIC = RACINE / "frontend" / "public"
CREME = (246, 242, 231)        # fond des sources, gardé pour les icônes pleines


def detourer(chemin: Path) -> Image.Image:
    """Fond uni → transparent. L'alpha croît avec l'écart à la couleur du fond, et la couleur
    des bords est dé-mélangée du fond pour éviter un liseré crème sur fond sombre."""
    im = np.asarray(Image.open(chemin).convert("RGB")).astype(np.float32)
    fond = np.median(np.concatenate([im[:8].reshape(-1, 3), im[-8:].reshape(-1, 3)]), axis=0)
    ecart = np.linalg.norm(im - fond, axis=2)
    alpha = np.clip((ecart - 10) / 60, 0, 1)
    a = np.maximum(alpha, 1e-3)[..., None]
    couleur = np.clip((im - (1 - a) * fond) / a, 0, 255)
    rgba = np.dstack([couleur, alpha * 255]).astype(np.uint8)
    img = Image.fromarray(rgba, "RGBA")
    boite = Image.fromarray((alpha > 0.04).astype(np.uint8) * 255).getbbox()
    return img.crop(boite)


def version_claire(img: Image.Image) -> Image.Image:
    """Pour les fonds sombres (pied de page vert) : les verts deviennent crème, l'or reste."""
    a = np.asarray(img).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    vert = (g > r + 12) & (g > b)                    # l'or a r > g ; le vert a g > r
    a[vert, :3] = CREME
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def a_hauteur(img: Image.Image, h: int) -> Image.Image:
    return img.resize((round(img.width * h / img.height), h), Image.LANCZOS)


def carre(img: Image.Image, cote: int, marge: float, fond=None) -> Image.Image:
    """Le dessin centré dans un carré, avec `marge` (fraction du côté) tout autour."""
    utile = round(cote * (1 - 2 * marge))
    e = utile / max(img.width, img.height)
    petit = img.resize((max(1, round(img.width * e)), max(1, round(img.height * e))), Image.LANCZOS)
    toile = Image.new("RGBA", (cote, cote), (*fond, 255) if fond else (0, 0, 0, 0))
    toile.alpha_composite(petit, ((cote - petit.width) // 2, (cote - petit.height) // 2))
    return toile


def main() -> None:
    (PUBLIC / "marque").mkdir(parents=True, exist_ok=True)
    symbole = detourer(SOURCES / "symbole.png")
    horizontal = detourer(SOURCES / "logo-horizontal.png")
    vertical = detourer(SOURCES / "logo-carre.png")

    # Interface : deux fois la taille affichée, pour les écrans à haute densité.
    a_hauteur(horizontal, 96).save(PUBLIC / "marque" / "logo-horizontal.png", optimize=True)
    version_claire(a_hauteur(horizontal, 96)).save(PUBLIC / "marque" / "logo-horizontal-clair.png", optimize=True)
    a_hauteur(vertical, 480).save(PUBLIC / "marque" / "logo-vertical.png", optimize=True)
    a_hauteur(symbole, 256).save(PUBLIC / "marque" / "symbole.png", optimize=True)

    # Icônes : sur fond crème (lisibles sur un écran d'accueil sombre ou clair).
    carre(symbole, 64, 0.06).save(PUBLIC / "pwa-64x64.png", optimize=True)
    carre(symbole, 192, 0.08, CREME).save(PUBLIC / "pwa-192x192.png", optimize=True)
    carre(symbole, 512, 0.08, CREME).save(PUBLIC / "pwa-512x512.png", optimize=True)
    carre(symbole, 512, 0.2, CREME).save(PUBLIC / "maskable-icon-512x512.png", optimize=True)   # zone sûre : 80 %
    carre(symbole, 180, 0.1, CREME).convert("RGB").save(PUBLIC / "apple-touch-icon-180x180.png", optimize=True)
    carre(symbole, 32, 0.02).save(PUBLIC / "favicon-32x32.png", optimize=True)
    carre(symbole, 256, 0.02).save(PUBLIC / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])

    # PDF du plan de gestion.
    a_hauteur(horizontal, 120).save(RACINE / "backend" / "ressources" / "logo.png", optimize=True)
    print("Logos et icônes écrits.")


if __name__ == "__main__":
    main()
