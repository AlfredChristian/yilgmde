"""D65 : mise en page du plan de gestion en PDF."""

from backend.synthese_pdf import synthese_pdf


def test_markdown_de_la_synthese_mis_en_page():
    texte = ("# Plan de gestion\n\nScénario **Base** & <test>, 1 000 habitants.\n\n- périmètre : arrondissement 9\n\n"
             "---\n\n## En bref\n\n| Indicateur | Valeur |\n|---|---|\n| Points | 228 |\n| Ligne incomplète |\n")
    pdf = synthese_pdf(texte)
    assert pdf.startswith(b"%PDF") and len(pdf) > 1500
