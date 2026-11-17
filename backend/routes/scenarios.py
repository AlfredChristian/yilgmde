"""C4, D1–D4 — Scénarios et plan de gestion (admin), points de regroupement (public).

Un scénario surcharge la config de façon partielle ; toute modification renvoie le
plan recalculé. Le plan est recalculé aussi, à la lecture, dès que les données
(dépotoirs, zones) ont changé depuis le dernier calcul (`backend/plans.py`).
Chaque création, modification ou activation est écrite dans `journal_audit` (règle 5).
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from backend import db, plans
from backend.config import ConfigError
from backend.deps import acces_db
from backend.synthese import synthese_markdown
from backend.zones import lire_zones
from backend.schemas import Role, ScenarioCreation, ScenarioSortie, SimulationEntree
from backend.securite import exiger_role
from backend.utilisateurs import journaliser
from simulation.agents import simuler
from simulation.plan import restreindre_perimetre, zones_du_scenario

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
    """422 si la config effective, un nouveau quartier ou le périmètre est invalide (rien n'est enregistré)."""
    try:
        config = plans.config_effective(request.app.state.config, {"parametres": parametres})
        zones_du_scenario([], config)
        if config.get("perimetre"):
            with acces_db(request) as conn:
                restreindre_perimetre(plans.lire_donnees(conn), config)
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


# Indicateurs comparés (D6) : chemin dans la réponse, et sens « meilleur ».
INDICATEURS_COMPARES = [
    ("plan", "capacite_collecte_pct", "plus"),
    ("plan", "part_captee_estimee_pct", "plus"),
    ("plan", "nb_points_regroupement", None),
    ("plan", "distance_totale_km", "moins"),
    ("plan", "cout_total_xof", "moins"),
    ("plan", "cout_mensuel_estime_xof", "moins"),
    ("simulation", "part_captee_moyenne_pct", "plus"),
    ("simulation", "depotoirs_actifs_fin", "moins"),
    ("simulation", "dechets_sauvages_kg", "moins"),
    ("simulation", "cout_total_xof", "moins"),
    ("simulation", "passages_suspendus_budget", "moins"),
]


@router.get("/scenarios/comparer")
def comparer(
    request: Request,
    ids: str = Query(..., description="ids séparés par des virgules, ex. 1,2"),
    jours: int | None = Query(None, ge=1, le=365, description="par défaut : scenario.horizon_jours"),
    graine: int | None = None,
    _=Depends(admin),
):
    """D6 : plan et simulation de 2 à 4 scénarios côte à côte, **même graine** pour une comparaison juste.

    Pour chaque indicateur : valeur par scénario, écart au premier scénario (la référence)
    et scénario le meilleur quand le sens est clair.
    """
    try:
        liste = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(422, "ids : entiers séparés par des virgules")
    if not 2 <= len(liste) <= 4 or len(set(liste)) != len(liste):
        raise HTTPException(422, "comparer 2 à 4 scénarios distincts")
    graine = int(request.app.state.config["scenario"].get("graine_aleatoire", 0) if graine is None else graine)
    jours = jours or int(request.app.state.config["scenario"].get("horizon_jours", 30))

    colonnes = []
    for sid in liste:
        plan = _plan(request, sid)
        with acces_db(request) as conn:
            scenario = plans.lire_scenario(conn, sid)
            donnees = plans.lire_donnees(conn)
        config = plans.config_effective(request.app.state.config, scenario)
        sim = simuler(donnees, config, jours, graine, plan=plan)
        colonnes.append({"scenario": scenario, "plan_id": plan["id"], "plan": plan["indicateurs"],
                         "simulation": sim["resume"]})

    lignes = []
    for source, cle, sens in INDICATEURS_COMPARES:
        valeurs = [c[source].get(cle) for c in colonnes]
        ref = valeurs[0]
        ecarts = [None if v is None or ref is None else round(v - ref, 2) for v in valeurs]
        meilleur = None
        if sens and all(v is not None for v in valeurs) and len(set(valeurs)) > 1:
            choisi = max(valeurs) if sens == "plus" else min(valeurs)
            meilleur = [c["scenario"]["id"] for c, v in zip(colonnes, valeurs) if v == choisi]
        lignes.append({"source": source, "indicateur": cle, "valeurs": valeurs, "ecart_a_la_reference": ecarts,
                       "sens": sens, "meilleur": meilleur})

    return {
        "jours": jours,
        "graine": graine,
        "scenarios": [{"id": c["scenario"]["id"], "nom": c["scenario"]["nom"], "parametres": c["scenario"]["parametres"],
                       "plan_id": c["plan_id"]} for c in colonnes],
        "indicateurs": lignes,
        "details": [{"scenario_id": c["scenario"]["id"], "plan": c["plan"], "simulation": c["simulation"]} for c in colonnes],
    }


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


@router.get("/scenarios/{scenario_id}/plan/synthese", response_class=PlainTextResponse)
def synthese(request: Request, scenario_id: int, _=Depends(admin)):
    """Livrable 3 : plan de gestion lisible (Markdown), pour l'arrondissement du scénario ou la commune."""
    plan = _plan(request, scenario_id)
    with acces_db(request) as conn:
        scenario = plans.lire_scenario(conn, scenario_id)
        zones = lire_zones(conn)
    config = plans.config_effective(request.app.state.config, scenario)
    texte = synthese_markdown(plan, scenario, zones, config)
    return PlainTextResponse(texte, media_type="text/markdown; charset=utf-8",
                             headers={"Content-Disposition": f'inline; filename="plan_scenario_{scenario_id}.md"'})


@router.post("/scenarios/{scenario_id}/simuler")
def simuler_scenario(request: Request, scenario_id: int, entree: SimulationEntree | None = None, _=Depends(admin)):
    """E1–E3 : simule `jours` jours sur le plan à jour du scénario (même graine = mêmes résultats).

    Les indicateurs journaliers sont enregistrés dans `indicateur_simulation` (une
    simulation par plan : la précédente est remplacée).
    """
    entree = entree or SimulationEntree()
    plan = _plan(request, scenario_id)
    with acces_db(request) as conn:
        scenario = plans.lire_scenario(conn, scenario_id)
        donnees = plans.lire_donnees(conn)
    config = plans.config_effective(request.app.state.config, scenario)
    jours = entree.jours or int(config["scenario"].get("horizon_jours", 30))
    resultat = simuler(donnees, config, jours, entree.graine, plan=plan)
    with acces_db(request) as conn:
        with db.transaction(conn):
            conn.execute("DELETE FROM indicateur_simulation WHERE plan_id = ?", (plan["id"],))
            conn.executemany(
                "INSERT INTO indicateur_simulation (plan_id, jour, pct_collecte, depotoirs_actifs, cout_xof, distance_km)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [(plan["id"], i["jour"], i["part_captee_pct"], i["depotoirs_actifs"], i["cout_xof"], i["distance_km"])
                 for i in resultat["indicateurs"]],
            )
    return {"scenario_id": scenario_id, "plan_id": plan["id"], **resultat}


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
