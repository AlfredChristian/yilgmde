# HANDOFF

> À remplir **uniquement** quand on change de conversation avec l'IA ou qu'on passe la main. Une section par personne. Écraser l'ancien contenu.

## Christian (front)

- **Objectif en cours** : afficher la carte des dépotoirs (Leaflet) dans le front React, alimentée par les données d'exemple.
- **Fichiers modifiés** : `frontend/` créé avec Vite + React ; `leaflet` et `react-leaflet` installés (`package.json`). Branche `front/init-react`.
- **Bugs ouverts** : aucun.
- **Prochaine étape précise** :
  1. créer `frontend/.env.example` (`VITE_API_URL`, `VITE_USE_MOCK=true`) ;
  2. copier les fichiers de `data/sample/` dans `frontend/public/mock/` ;
  3. créer `frontend/src/api/client.js` avec `getDepotoirs()` ;
  4. créer un composant `Carte.jsx` (MapContainer centré sur 12.3714, -1.5197, importer le CSS de Leaflet) ;
  5. y afficher les dépotoirs d'exemple, puis l'utiliser dans `App.jsx`.

## Faissal (back / moteur)

- **Objectif en cours** : plan de bout en bout fait (branche `back/regroupement`) : C2 points de regroupement, C3 tournées de collecte, C7 tournées Laabal, C4 plan + scénarios (D1–D4) et `/points-regroupement`. `main` contient A1, A2, A3, auth, C1. Ensuite : vues chauffeur et Laabal (C6, H1–H3), puis simulation (E1–E3).
- **Fichiers modifiés** : `simulation/geometrie.py` (distances, projection locale, aire, grille d'échantillons), `simulation/regroupement.py` (`placer_points`, D24), `simulation/tournees.py` (`planifier_tournees`, `planifier_interventions`, moteur OR-Tools + repli, D25, D26), `simulation/plan.py` (`calculer_plan`, `zones_du_scenario`, D27), `backend/plans.py` (scénarios, enregistrement/lecture du plan, empreinte), `backend/routes/scenarios.py`, `backend/schemas.py` (ScenarioCreation/Sortie), `backend/db.py` (colonnes `details`, `signature`, `scenario.actif` + migration douce), `backend/main.py` (scénario base au démarrage), `config/default.yaml` (paramètres [H] de points, collecte, Laabal), `config/ouagadougou.yaml` (`collecte.depot`), `docs/api-contract.md`, tests `test_regroupement.py`, `test_tournees.py`, `test_plan.py`, `test_scenarios.py` (56 nouveaux tests ; suite complète : 204 verts).
- **Bugs ouverts / limites** : le **dépôt** de Ouaga (`collecte.depot`, Polesgo approximatif) est une hypothèse à confirmer (Cramer : mairie). Avec les zones d'exemple (7 km², 300 m à pied) il faut ~33 points par zone : ajuster `distance_max_a_pied_m`/`couverture_cible` selon la mairie. Les arrêts n'ont pas encore de route pour être cochés ; un nouveau plan crée de nouveaux arrêts (statuts `a_faire`) : la vue chauffeur devra lire le plan du scénario actif. Toujours pas de vraies zones, pas de limitation des tentatives de connexion, `score_confiance` jamais mis à jour.
- **Pour lancer avec des données** : `python scripts/charger_exemples.py`, puis `uvicorn backend.main:app --reload` ; `GET /points-regroupement` renvoie le plan courant ; en admin, `PUT /scenarios/1/parametres` avec `{"camions": [{"id": "camion_2", "disponible": false}]}` ou `{"saison": "pluies"}` renvoie le plan recalculé.
- **Prochaine étape précise** :
  1. C6 : `GET /chauffeur/tournee` (tournées de collecte du plan courant, affectées au chauffeur via `tournee.affectee_a`, sinon toutes), `POST /chauffeur/arrets/{id}/effectue`, `POST /chauffeur/incidents` (une `panne` met le camion `disponible: false` dans les paramètres du scénario actif, ce qui recalcule le plan) ; `POST /admin/tournees/{id}/affecter` ;
  2. H1–H3 : `GET /laabal/depotoirs-a-traiter` (réutiliser `depotoirs_a_traiter`), `GET /laabal/tournee`, `POST /laabal/depotoirs/{id}/intervention` et `/surveillance` (transitions B5, journal) ;
  3. E1–E3 : `simulation/agents.py`, boucle journalière avec graine, route `/scenarios/{id}/simuler` ;
  4. G1 : `GET /admin/export/depotoirs.geojson`.

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
