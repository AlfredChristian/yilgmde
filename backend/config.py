"""Chargement et fusion de la configuration.

Principe (D10) : aucun paramètre en dur, tout vient de `config/`.
Ordre de priorité, du plus faible au plus fort :
    default.yaml  <  <ville>.yaml  <  surcharges du scénario

Les fonctions sont pures : elles ne modifient jamais leurs arguments, ce qui
permet de calculer un plan comme `plan = f(données, paramètres)` (D09).
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml

DOSSIER_CONFIG_DEFAUT = Path(__file__).resolve().parent.parent / "config"
SAISONS_VALIDES = ("seche", "pluies")


class ConfigError(ValueError):
    """Configuration invalide ou introuvable."""


def dossier_config() -> Path:
    """Dossier de config, surchargeable par la variable YILGMDE_CONFIG_DIR."""
    return Path(os.environ.get("YILGMDE_CONFIG_DIR", DOSSIER_CONFIG_DEFAUT))


def _liste_avec_ids(valeur: Any) -> bool:
    return (
        isinstance(valeur, list)
        and len(valeur) > 0
        and all(isinstance(x, dict) and "id" in x for x in valeur)
    )


def fusion_profonde(base: Any, surcharge: Any) -> Any:
    """Fusionne `surcharge` sur `base` sans modifier ni l'un ni l'autre.

    - dict : fusion récursive clé par clé ;
    - liste d'objets ayant tous un `id` : fusion par `id` (un camion existant est
      mis à jour, un nouveau est ajouté, l'ordre d'origine est conservé) ;
    - tout le reste (scalaires, autres listes) : la surcharge remplace la base.
    """
    if isinstance(base, dict) and isinstance(surcharge, dict):
        resultat = copy.deepcopy(base)
        for cle, valeur in surcharge.items():
            if cle in resultat:
                resultat[cle] = fusion_profonde(resultat[cle], valeur)
            else:
                resultat[cle] = copy.deepcopy(valeur)
        return resultat

    if _liste_avec_ids(base) and _liste_avec_ids(surcharge):
        resultat = copy.deepcopy(base)
        index = {element["id"]: i for i, element in enumerate(resultat)}
        for element in surcharge:
            if element["id"] in index:
                i = index[element["id"]]
                resultat[i] = fusion_profonde(resultat[i], element)
            else:
                index[element["id"]] = len(resultat)
                resultat.append(copy.deepcopy(element))
        return resultat

    return copy.deepcopy(surcharge)


def _lire_yaml(chemin: Path) -> dict:
    if not chemin.is_file():
        raise ConfigError(f"Fichier de configuration introuvable : {chemin}")
    with chemin.open(encoding="utf-8") as f:
        contenu = yaml.safe_load(f)
    if contenu is None:
        return {}
    if not isinstance(contenu, dict):
        raise ConfigError(f"{chemin.name} doit contenir un dictionnaire YAML")
    return contenu


def valider_config(config: dict) -> dict:
    """Vérifie les invariants dont le reste du code dépend. Renvoie la config."""
    saison = config.get("scenario", {}).get("saison")
    if saison not in SAISONS_VALIDES:
        raise ConfigError(f"saison invalide : {saison!r} (attendu : {', '.join(SAISONS_VALIDES)})")
    if saison not in config.get("saisons", {}):
        raise ConfigError(f"coefficients manquants pour la saison {saison!r}")

    bbox = config.get("zone_etude", {}).get("bbox")
    if bbox is not None:
        for cle in ("min_lat", "max_lat", "min_lon", "max_lon"):
            if cle not in bbox:
                raise ConfigError(f"zone_etude.bbox : clé manquante {cle!r}")
        if bbox["min_lat"] >= bbox["max_lat"] or bbox["min_lon"] >= bbox["max_lon"]:
            raise ConfigError("zone_etude.bbox : minimum supérieur ou égal au maximum")

    ids = [c.get("id") for c in config.get("camions", [])]
    if len(ids) != len(set(ids)):
        raise ConfigError("camions : identifiants en double")
    return config


def charger_config(
    ville: str | None = "ouagadougou",
    surcharges: dict | None = None,
    dossier: Path | None = None,
) -> dict:
    """Construit la configuration effective.

    `ville=None` charge uniquement `default.yaml` (utile pour les tests ou pour
    une commune qui n'a pas encore son fichier).
    """
    racine = Path(dossier) if dossier is not None else dossier_config()
    config = _lire_yaml(racine / "default.yaml")
    if ville:
        config = fusion_profonde(config, _lire_yaml(racine / f"{ville}.yaml"))
    if surcharges:
        config = fusion_profonde(config, surcharges)
    return valider_config(config)


def appliquer_surcharges(config: dict, surcharges: dict) -> dict:
    """Applique une modification partielle (PUT /scenarios/{id}/parametres)."""
    return valider_config(fusion_profonde(config, surcharges))


def camions_disponibles(config: dict) -> list[dict]:
    """Règle de cohérence 4 : un camion indisponible n'est jamais utilisé."""
    return [c for c in config.get("camions", []) if c.get("disponible", True)]


def coefficients_saison(config: dict) -> dict:
    """Coefficients de la saison courante du scénario."""
    return config["saisons"][config["scenario"]["saison"]]
