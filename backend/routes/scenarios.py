"""C4, D1–D4 — Scénarios et plan de gestion (admin), points de regroupement (public).

Un scénario surcharge la config de façon partielle ; toute modification renvoie le
plan recalculé. Le plan est recalculé aussi, à la lecture, dès que les données
(dépotoirs, zones) ont changé depuis le dernier calcul (`backend/plans.py`).
Chaque création, modification ou activation est écrite dans `journal_audit` (règle 5).
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from backend import db, plans
from backend.config import ConfigError
from backend.deps import acces_db
from backend.schemas import Role, ScenarioCreation, ScenarioSortie
from backend.securite import exiger_role
from backend.utilisateurs import journaliser
from simulation.plan import zones_du_scenario

router = APIRouter(tags=["scenarios"])
admin = exiger_role(Role.admin)


def _acces(request: Request):
    return lambda: acces_db(request)


def _plan(request: Request, scenario_id: int, forcer: bool = False) -> dict:
    try:
        return plans.calculer_et_enregistrer(_acces(request), request.app.state.config, scenario_id, forcer)
    except LookupError:
        raise HTTPException(404, "scénario inconnu")
    except (ConfigError, ValueError) as e:
        raise HTTPException(422, f"paramètres invalides : {e}")


def _scenario_ou_404(conn, scenario_id: int) -> dict:
    scenario = plans.lire_scenario(conn, scenario_id)
    if scenario is None:
        raise HTTPException(404, "scénario inconnu")
    return scenario


def _valider(request: Request, parametres: dict) -> None:
    """422 si la config effective ou un nouveau quartier est invalide (rien n'est enregistré)."""
    try:
        config = plans.config_effective(request.app.state.config, {"parametres": parametres})
        zones_du_scenario([], config)
    except (ConfigError, ValueError) as e:
        raise HTTPException(422, f"paramètres invalides : {e}")


@router.get("/scenarios", response_model=list[ScenarioSortie])
def lister(request: Request, _=Depends(admin)):
    with acces_db(request) as conn:
        return plans.lister_scenarios(conn)


@router.post("/scenarios", response_model=ScenarioSortie, status_code=201)
def creer(request: Request, entree: ScenarioCreation, utilisateur=Depends(admin)):
    try:
        parametres = plans.normaliser_parametres(entree.parametres)
    except ConfigError as e:
        raise HTTPException(422, f"paramètres invalides : {e}")
    with acces_db(request) as conn:
        if entree.base_sur is not None:
            base = _scenario_ou_404(conn, entree.base_sur)
            parametres = plans.fusionner_parametres(base["parametres"], parametres)
    _valider(request, parametres)
    with acces_db(request) as conn:
        with db.transaction(conn):
            sid = plans.creer_scenario(conn, entree.nom.strip(), parametres, utilisateur["id"])
            journaliser(conn, utilisateur["id"], "creer_scenario", "scenario", sid)
            if entree.activer:
                plans.activer_scenario(conn, sid)
                journaliser(conn, utilisateur["id"], "activer_scenario", "scenario", sid)
        return plans.lire_scenario(conn, sid)


@router.get("/scenarios/{scenario_id}", response_model=ScenarioSortie)
def lire(request: Request, scenario_id: int, _=Depends(admin)):
    with acces_db(request) as conn:
        return _scenario_ou_404(conn, scenario_id)


@router.put("/scenarios/{scenario_id}/parametres")
def modifier_parametres(request: Request, scenario_id: int, modification: dict = Body(...), utilisateur=Depends(admin)):
    """Modification **partielle** fusionnée sur les paramètres du scénario ; renvoie le plan recalculé.

    `zones_ajoutees` s'ajoute aux nouveaux quartiers déjà présents ; `camions` se
    fusionne par `id` ; `saison` est un raccourci de `scenario.saison`.
    """
    with acces_db(request) as conn:
        scenario = _scenario_ou_404(conn, scenario_id)
    try:
        parametres = plans.fusionner_parametres(scenario["parametres"], modification)
    except ConfigError as e:
        raise HTTPException(422, f"paramètres invalides : {e}")
    _valider(request, parametres)
    with acces_db(request) as conn:
        with db.transaction(conn):
            conn.execute("UPDATE scenario SET parametres = ? WHERE id = ?", (db.en_json(parametres), scenario_id))
            journaliser(conn, utilisateur["id"], "modifier_parametres", "scenario", scenario_id)
    return _plan(request, scenario_id)


@router.post("/scenarios/{scenario_id}/activer", response_model=ScenarioSortie)
def activer(request: Request, scenario_id: int, utilisateur=Depends(admin)):
    with acces_db(request) as conn:
        _scenario_ou_404(conn, scenario_id)
        with db.transaction(conn):
            plans.activer_scenario(conn, scenario_id)
            journaliser(conn, utilisateur["id"], "activer_scenario", "scenario", scenario_id)
        return plans.lire_scenario(conn, scenario_id)


@router.post("/scenarios/{scenario_id}/calculer")
def calculer(request: Request, scenario_id: int, _=Depends(admin)):
    """Force un nouveau calcul (même si rien n'a changé)."""
    return _plan(request, scenario_id, forcer=True)


@router.get("/scenarios/{scenario_id}/plan")
def plan_du_scenario(request: Request, scenario_id: int, _=Depends(admin)):
    """Dernier plan, recalculé d'abord si les données ou les paramètres ont changé."""
    return _plan(request, scenario_id)


@router.get("/points-regroupement")
def points_regroupement(request: Request):
    """Points du plan courant (scénario actif) en GeoJSON. Vide s'il n'y a pas de scénario actif."""
    with acces_db(request) as conn:
        actif = plans.scenario_actif(conn)
    if actif is None:
        return {"type": "FeatureCollection", "features": []}
    plan = _plan(request, actif["id"])
    return {
        "type": "FeatureCollection",
        "plan_id": plan["id"],
        "scenario_id": actif["id"],
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [p["longitude"], p["latitude"]]},
                "properties": {k: v for k, v in p.items() if k not in ("latitude", "longitude")},
            }
            for p in plan["points_regroupement"]
        ],
    }
