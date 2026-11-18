"""Plan de gestion en PDF (D65), à partir de la synthèse Markdown (`backend/synthese.py`).

La synthèse n'utilise qu'une petite partie du Markdown : titres `#` à `###`, paragraphes,
gras `**…**`, listes `- `, tableaux `| … |` et filets `---`. Ce module les met en page
avec ReportLab (licence BSD) : A4, en-tête vert, tableaux à lignes alternées, numéro de page.
"""

from __future__ import annotations

import io
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

VERT = colors.HexColor("#0e5a3a")
OR = colors.HexColor("#e9b824")
ENCRE = colors.HexColor("#1d2b24")
GRIS = colors.HexColor("#5a6a61")
FOND = colors.HexColor("#f4f6f3")

STYLES = {
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=VERT, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=VERT, spaceBefore=10, spaceAfter=4),
    "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=ENCRE, spaceBefore=8, spaceAfter=3),
    "p": ParagraphStyle("p", fontName="Helvetica", fontSize=9.5, leading=13, textColor=ENCRE, alignment=TA_LEFT, spaceAfter=4),
    "cellule": ParagraphStyle("cellule", fontName="Helvetica", fontSize=8, leading=10, textColor=ENCRE),
    "entete": ParagraphStyle("entete", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white),
}


def _texte(brut: str) -> str:
    """Markdown en ligne vers le balisage de ReportLab : échappement, gras, code."""
    t = escape(brut.replace(" ", " "))
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`(.+?)`", r'<font face="Courier">\1</font>', t)
    return t


def _cellules(ligne: str) -> list[str]:
    return [c.strip() for c in ligne.strip().strip("|").split("|")]


def _tableau(lignes: list[str], largeur: float) -> Table:
    entete = _cellules(lignes[0])
    corps = [_cellules(l) for l in lignes[2:]]           # lignes[1] = |---|---|
    n = len(entete)
    donnees = [[Paragraph(_texte(c), STYLES["entete"]) for c in entete]]
    donnees += [[Paragraph(_texte(c), STYLES["cellule"]) for c in (r + [""] * n)[:n]] for r in corps]
    # Colonnes à la mesure de leur texte le plus long, bornées pour rester lisibles.
    longueurs = [max(len(r[i]) if i < len(r) else 0 for r in [entete] + corps) for i in range(n)]
    poids = [min(max(x, 4), 60) for x in longueurs]
    total = sum(poids)
    t = Table(donnees, colWidths=[largeur * w / total for w in poids], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), VERT),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, OR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#dfe6e1")),
    ]
    style += [("BACKGROUND", (0, i), (-1, i), FOND) for i in range(2, len(donnees), 2)]
    t.setStyle(TableStyle(style))
    return t


def _pied(canvas, doc, titre: str) -> None:
    canvas.saveState()
    canvas.setFillColor(VERT)
    canvas.rect(0, A4[1] - 6 * mm, A4[0], 6 * mm, stroke=0, fill=1)
    canvas.setFillColor(OR)
    canvas.rect(0, A4[1] - 7.2 * mm, A4[0], 1.2 * mm, stroke=0, fill=1)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRIS)
    canvas.drawString(18 * mm, 10 * mm, f"Yilgmdé, {titre}")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def synthese_pdf(markdown: str) -> bytes:
    """Met en page la synthèse Markdown en PDF A4 et renvoie ses octets."""
    tampon = io.BytesIO()
    marge = 18 * mm
    doc = SimpleDocTemplate(tampon, pagesize=A4, leftMargin=marge, rightMargin=marge, topMargin=16 * mm,
                            bottomMargin=18 * mm, title="Plan de gestion des déchets", author="Yilgmdé")
    largeur = A4[0] - 2 * marge
    titre = next((l[2:].strip() for l in markdown.splitlines() if l.startswith("# ")), "Plan de gestion")
    elements, lignes, i = [], markdown.splitlines(), 0
    while i < len(lignes):
        l = lignes[i]
        if not l.strip():
            i += 1
        elif l.startswith("|"):
            bloc = []
            while i < len(lignes) and lignes[i].startswith("|"):
                bloc.append(lignes[i])
                i += 1
            if len(bloc) >= 2:
                elements += [_tableau(bloc, largeur), Spacer(1, 6)]
        elif l.startswith("- ") or l.startswith("* "):
            items = []
            while i < len(lignes) and (lignes[i].startswith("- ") or lignes[i].startswith("* ")):
                items.append(ListItem(Paragraph(_texte(lignes[i][2:]), STYLES["p"]), leftIndent=10))
                i += 1
            elements.append(ListFlowable(items, bulletType="bullet", bulletColor=VERT, leftIndent=12, bulletFontSize=7))
        elif re.match(r"^-{3,}\s*$", l):
            elements.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#cfdcd3"), spaceBefore=4, spaceAfter=6))
            i += 1
        elif l.startswith("#"):
            niveau = min(3, len(l) - len(l.lstrip("#")))
            titre_bloc = Paragraph(_texte(l.lstrip("#").strip()), STYLES[f"h{niveau}"])
            # Un titre ne reste jamais seul en bas de page.
            suivant = lignes[i + 1] if i + 1 < len(lignes) else ""
            elements.append(KeepTogether([titre_bloc]) if niveau == 1 or suivant.strip() else titre_bloc)
            i += 1
        else:
            paragraphe = [l.strip()]
            i += 1
            while i < len(lignes) and lignes[i].strip() and not re.match(r"^(#|\||- |\* |-{3,})", lignes[i]):
                paragraphe.append(lignes[i].strip())
                i += 1
            elements.append(Paragraph(_texte(" ".join(paragraphe)), STYLES["p"]))
    doc.build(elements, onFirstPage=lambda c, d: _pied(c, d, titre), onLaterPages=lambda c, d: _pied(c, d, titre))
    return tampon.getvalue()
