"""Livrable 2 : chaque paramètre de config/ est documenté dans docs/parametres.md."""

from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent
DOC = (RACINE / "docs" / "parametres.md").read_text(encoding="utf-8")
# Valeurs composées documentées d'un bloc (pas paramètre par paramètre).
BLOCS = {"camions", "zone_etude.bbox", "collecte.depot", "laabal.priorite.poids_volume", "sources_donnees"}


def parametres(d, prefixe=""):
    for cle, valeur in d.items():
        chemin = f"{prefixe}.{cle}" if prefixe else cle
        if isinstance(valeur, dict) and chemin not in BLOCS:
            yield from parametres(valeur, chemin)
        else:
            yield chemin


def test_chaque_parametre_est_documente():
    manquants = []
    for nom in ("default.yaml", "ouagadougou.yaml"):
        config = yaml.safe_load((RACINE / "config" / nom).read_text(encoding="utf-8"))
        for chemin in parametres(config):
            attendu = "`camions[]`" if chemin == "camions" else f"`{chemin}`"
            if attendu not in DOC:
                manquants.append(f"{nom}: {chemin}")
    assert manquants == [], "paramètres absents de docs/parametres.md : " + ", ".join(manquants)


def test_chaque_parametre_a_un_statut():
    statuts = ("source", "[H]", "technique", "informatif", "choix", "levier de scénario", "référence")
    for ligne in DOC.splitlines():
        if ligne.startswith("| `"):
            assert any(s in ligne for s in statuts), ligne
