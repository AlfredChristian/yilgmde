"""Scénarios et plans en base (C4, D1–D4).

- Un **scénario** = des surcharges partielles (`parametres`, JSON) fusionnées sur la
  config de l'application. Le scénario `actif` donne le « plan courant »
  (`GET /points-regroupement`, vues chauffeur et Laabal). Le scénario « base »
  (sans surcharge) est créé et activé au démarrage s'il n'y en a aucun.
- Un **plan** = la sortie de `simulation.plan.calculer_plan`, enregistrée dans
  `plan`, `point_regroupement`, `tournee`, `arret_tournee` ; ce qui n'a pas de
  colonne va dans `details` (JSON).
- **Recalcul automatique** : chaque plan garde l'empreinte (`signature`) de ses
  entrées (données lues en base + config effective). `plan_a_jour` recalcule
  seulement si l'empreinte a changé : un signalement validé, une intervention ou
  un paramètre modifié donnent un nouveau plan à la lecture suivante.

Le calcul (≈ 0,5 s) se fait **hors du verrou** de la base : on lit les données
sous verrou, on calcule, puis on enregistre sous verrou.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone

from backend import db
from backend.config import ConfigError, appliquer_surcharges, fusion_profonde
from backend.zones import lire_zones
from simulation.plan import calculer_plan

NOM_SCENARIO_BASE = "base"


# --- Scénarios -------------------------------------------------------------------------

def normaliser_parametres(parametres: dict) -> dict:
    """Raccourcis du contrat d'API → structure de la config.

    - `{"saison": "pluies"}` → `{"scenario": {"saison": "pluies"}}` ;
    - `zones_ajoutees` : une chaîne JSON est décodée.
    """
    if not isinstance(parametres, dict):
        raise ConfigError("parametres : objet JSON attendu")
    resultat = dict(parametres)
    if "saison" in resultat:
        resultat["scenario"] = dict(resultat.get("scenario") or {}, saison=resultat.pop("saison"))
    if "zones_ajoutees" in resultat:
        zones = resultat["zones_ajoutees"]
        if not isinstance(zones, list):
            raise ConfigError("zones_ajoutees : liste attendue")
        decodees = []
        for z in zones:
            if isinstance(z, str):
                try:
                    z = json.loads(z)
                except json.JSONDecodeError as e:
                    raise ConfigError(f"zones_ajoutees : GeoJSON illisible ({e})") from e
            decodees.append(z)
        resultat["zones_ajoutees"] = decodees
    return resultat


def fusionner_parametres(anciens: dict, nouveaux: dict) -> dict:
    """Fusion partielle ; `zones_ajoutees` s'**ajoute** aux zones déjà ajoutées (D4)."""
    nouveaux = normaliser_parametres(nouveaux)
    zones = list(anciens.get("zones_ajoutees") or [])
    for z in nouveaux.pop("zones_ajoutees", None) or []:
        if z not in zones:
            zones.append(z)
    resultat = fusion_profonde(anciens, nouveaux)
    if zones:
        resultat["zones_ajoutees"] = zones
    return resultat


def _scenario_sortie(ligne) -> dict:
    return {
        "id": ligne["id"],
        "nom": ligne["nom"],
        "parametres": db.depuis_json(ligne["parametres"], {}),
        "actif": bool(ligne["actif"]),
        "cree_par": ligne["cree_par"],
        "cree_le": ligne["cree_le"],
    }


def lister_scenarios(conn: sqlite3.Connection) -> list[dict]:
    return [_scenario_sortie(l) for l in conn.execute("SELECT * FROM scenario ORDER BY id")]


def lire_scenario(conn: sqlite3.Connection, scenario_id: int) -> dict | None:
    ligne = conn.execute("SELECT * FROM scenario WHERE id = ?", (scenario_id,)).fetchone()
    return _scenario_sortie(ligne) if ligne else None


def scenario_actif(conn: sqlite3.Connection) -> dict | None:
    ligne = conn.execute("SELECT * FROM scenario WHERE actif = 1 ORDER BY id LIMIT 1").fetchone()
    return _scenario_sortie(ligne) if ligne else None


def creer_scenario(conn: sqlite3.Connection, nom: str, parametres: dict, cree_par: int | None, actif: bool = False) -> int:
    curseur = conn.execute(
        "INSERT INTO scenario (nom, parametres, cree_par, cree_le, actif) VALUES (?, ?, ?, ?, ?)",
        (nom, db.en_json(parametres), cree_par, datetime.now(timezone.utc).isoformat(), int(actif)),
    )
    return curseur.lastrowid


def creer_scenario_base_si_absent(conn: sqlite3.Connection) -> None:
    with db.transaction(conn):
        if conn.execute("SELECT 1 FROM scenario LIMIT 1").fetchone() is None:
            creer_scenario(conn, NOM_SCENARIO_BASE, {}, None, actif=True)


def activer_scenario(conn: sqlite3.Connection, scenario_id: int) -> None:
    conn.execute("UPDATE scenario SET actif = CASE WHEN id = ? THEN 1 ELSE 0 END", (scenario_id,))


def config_effective(config_app: dict, scenario: dict) -> dict:
    """Config de l'application + surcharges du scénario. Lève ConfigError si invalide."""
    return appliquer_surcharges(config_app, scenario["parametres"])


# --- Données d'entrée et empreinte ---------------------------------------------------------

def lire_donnees(conn: sqlite3.Connection) -> dict:
    depotoirs = [
        dict(l)
        for l in conn.execute(
            "SELECT id, latitude, longitude, zone_id, volume_estime, statut, legalite,"
            " nb_signalements, nb_reapparitions FROM depotoir ORDER BY id"
        )
    ]
    return {"zones": lire_zones(conn), "depotoirs": depotoirs}


def signature(donnees: dict, config: dict) -> str:
    texte = json.dumps({"donnees": donnees, "config": config}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()


# --- Enregistrement et lecture d'un plan ---------------------------------------------------

_CLES_POINT = ("latitude", "longitude", "capacite_kg", "zone_id", "explication", "id")
_CLES_TOURNEE = ("type", "camion_id", "distance_km", "duree_min", "cout_xof", "arrets", "id")
_CLES_ARRET = ("ordre", "cible_type", "cible_id", "latitude", "longitude", "statut")


def cle_tournee(t: dict) -> tuple:
    """Identité d'une tournée d'un plan à l'autre : camion, jour du passage et rotation, ou brigade."""
    return (t["type"], t.get("camion_id"), t.get("jour"), t.get("rotation"), t.get("brigade"))


def cle_arret(a: dict) -> tuple:
    """Identité d'un arrêt d'un plan à l'autre : position du point, ou id du dépotoir."""
    if a["cible_type"] == "depotoir":
        return ("depotoir", a["cible_id"])
    return ("point_regroupement", round(a["latitude"], 6), round(a["longitude"], 6))


def _reprise(conn: sqlite3.Connection, scenario_id: int, jour: str) -> tuple[dict, set]:
    """Affectations et arrêts effectués du dernier plan du scénario calculé le même jour.

    Un recalcul (signalement validé, panne…) ne doit pas effacer le travail du jour :
    une tournée garde son chauffeur ou sa brigade, un point déjà vidé reste `effectue`.
    """
    dernier = dernier_plan_id(conn, scenario_id)
    if dernier is None:
        return {}, set()
    precedent = lire_plan(conn, dernier[0])
    if not precedent["calcule_le"].startswith(jour):
        return {}, set()
    affectations = {cle_tournee(t): t["affectee_a"] for t in precedent["tournees"] if t.get("affectee_a")}
    effectues = {cle_arret(a) for t in precedent["tournees"] for a in t["arrets"] if a["statut"] == "effectue"}
    return affectations, effectues


def enregistrer_plan(conn: sqlite3.Connection, scenario_id: int, plan: dict, sig: str, duree_ms: int) -> int:
    """Écrit le plan ; les ids locaux des points (1..n) deviennent des ids de base."""
    maintenant = datetime.now(timezone.utc).isoformat()
    affectations, effectues = _reprise(conn, scenario_id, maintenant[:10])
    curseur = conn.execute(
        "INSERT INTO plan (scenario_id, calcule_le, duree_calcul_ms, indicateurs, non_couverts, signature, details)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            scenario_id,
            maintenant,
            duree_ms,
            db.en_json(plan["indicateurs"]),
            "[]",   # réécrit plus bas avec les ids de base
            sig,
            db.en_json({"laabal_en_attente": plan.get("laabal_en_attente", []), "zones_ajoutees": plan.get("zones_ajoutees", [])}),
        ),
    )
    plan_id = curseur.lastrowid

    ids_points = {}
    for p in plan["points_regroupement"]:
        c = conn.execute(
            "INSERT INTO point_regroupement (plan_id, latitude, longitude, capacite_kg, zone_id, explication, details)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (plan_id, p["latitude"], p["longitude"], p["capacite_kg"], p["zone_id"], p["explication"],
             db.en_json({k: v for k, v in p.items() if k not in _CLES_POINT})),
        )
        ids_points[p["id"]] = c.lastrowid

    for t in plan["tournees"]:
        c = conn.execute(
            "INSERT INTO tournee (plan_id, type, camion_id, affectee_a, distance_km, duree_min, cout_xof, details)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (plan_id, t["type"], t["camion_id"], affectations.get(cle_tournee(t)),
             t["distance_km"], t["duree_min"], t["cout_xof"],
             db.en_json({k: v for k, v in t.items() if k not in _CLES_TOURNEE})),
        )
        tournee_id = c.lastrowid
        for a in t["arrets"]:
            cible = ids_points[a["cible_id"]] if a["cible_type"] == "point_regroupement" else a["cible_id"]
            conn.execute(
                "INSERT INTO arret_tournee (tournee_id, ordre, cible_type, cible_id, statut, details)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (tournee_id, a["ordre"], a["cible_type"], cible,
                 "effectue" if cle_arret(a) in effectues else a["statut"],
                 db.en_json({k: v for k, v in a.items() if k not in _CLES_ARRET} | {
                     "latitude": a["latitude"], "longitude": a["longitude"]})),
            )

    non_couverts = [
        dict(nc, point_regroupement_id=ids_points[nc["point_regroupement_id"]]) if "point_regroupement_id" in nc else nc
        for nc in plan["non_couverts"]
    ]
    conn.execute("UPDATE plan SET non_couverts = ? WHERE id = ?", (db.en_json(non_couverts), plan_id))
    return plan_id


def lire_plan(conn: sqlite3.Connection, plan_id: int) -> dict | None:
    ligne = conn.execute("SELECT * FROM plan WHERE id = ?", (plan_id,)).fetchone()
    if ligne is None:
        return None
    details = db.depuis_json(ligne["details"], {})
    points = [
        {"id": p["id"], "latitude": p["latitude"], "longitude": p["longitude"], "capacite_kg": p["capacite_kg"],
         "zone_id": p["zone_id"], "explication": p["explication"], **db.depuis_json(p["details"], {})}
        for p in conn.execute("SELECT * FROM point_regroupement WHERE plan_id = ? ORDER BY id", (plan_id,))
    ]
    tournees = []
    for t in conn.execute("SELECT * FROM tournee WHERE plan_id = ? ORDER BY id", (plan_id,)):
        arrets = [
            {"id": a["id"], "ordre": a["ordre"], "cible_type": a["cible_type"], "cible_id": a["cible_id"],
             "statut": a["statut"], **db.depuis_json(a["details"], {})}
            for a in conn.execute("SELECT * FROM arret_tournee WHERE tournee_id = ? ORDER BY ordre", (t["id"],))
        ]
        tournees.append(
            {"id": t["id"], "type": t["type"], "camion_id": t["camion_id"], "affectee_a": t["affectee_a"],
             "distance_km": t["distance_km"], "duree_min": t["duree_min"], "cout_xof": t["cout_xof"],
             **db.depuis_json(t["details"], {}), "arrets": arrets}
        )
    return {
        "id": ligne["id"],
        "scenario_id": ligne["scenario_id"],
        "calcule_le": ligne["calcule_le"],
        "duree_calcul_ms": ligne["duree_calcul_ms"],
        "points_regroupement": points,
        "tournees": tournees,
        "indicateurs": db.depuis_json(ligne["indicateurs"], {}),
        "non_couverts": db.depuis_json(ligne["non_couverts"], []),
        **details,
    }


def dernier_plan_id(conn: sqlite3.Connection, scenario_id: int) -> tuple[int, str | None] | None:
    ligne = conn.execute(
        "SELECT id, signature FROM plan WHERE scenario_id = ? ORDER BY id DESC LIMIT 1", (scenario_id,)
    ).fetchone()
    return (ligne["id"], ligne["signature"]) if ligne else None


# --- Calcul ------------------------------------------------------------------------------

def calculer_et_enregistrer(acces, config_app: dict, scenario_id: int, forcer: bool = False) -> dict:
    """Plan à jour du scénario. `acces()` est un gestionnaire de contexte qui donne la connexion.

    Sans `forcer`, le dernier plan est renvoyé tel quel si ses entrées n'ont pas changé.
    Lève LookupError (scénario inconnu), ConfigError ou ValueError (paramètres invalides).
    """
    with acces() as conn:
        scenario = lire_scenario(conn, scenario_id)
        if scenario is None:
            raise LookupError(scenario_id)
        donnees = lire_donnees(conn)
        dernier = dernier_plan_id(conn, scenario_id)
    config = config_effective(config_app, scenario)
    sig = signature(donnees, config)
    if dernier and dernier[1] == sig and not forcer:
        with acces() as conn:
            return lire_plan(conn, dernier[0])

    debut = time.perf_counter()
    plan = calculer_plan(donnees, config)
    duree_ms = int((time.perf_counter() - debut) * 1000)

    with acces() as conn:
        with db.transaction(conn):
            plan_id = enregistrer_plan(conn, scenario_id, plan, sig, duree_ms)
        return lire_plan(conn, plan_id)
