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

- **Objectif en cours** : plan de bout en bout fait (PR #11, branche `back/regroupement`) : C2, C3, C7, C4 + scénarios (D1–D4), `/points-regroupement`. Vues de terrain faites (branche `back/chauffeur-laabal`, empilée sur la précédente) : C6 chauffeur, H1–H3 Laabal, affectation des tournées (D28). `main` contient A1, A2, A3, auth, C1. Ensuite : simulation (E1–E3) et export G1.
- **Fichiers modifiés** : `simulation/geometrie.py` (distances, projection locale, aire, grille d'échantillons), `simulation/regroupement.py` (`placer_points`, D24), `simulation/tournees.py` (`planifier_tournees`, `planifier_interventions`, moteur OR-Tools + repli, D25, D26), `simulation/plan.py` (`calculer_plan`, `zones_du_scenario`, D27), `backend/plans.py` (scénarios, enregistrement/lecture du plan, empreinte), `backend/routes/scenarios.py`, `backend/schemas.py` (ScenarioCreation/Sortie), `backend/db.py` (colonnes `details`, `signature`, `scenario.actif` + migration douce), `backend/main.py` (scénario base au démarrage), `config/default.yaml` (paramètres [H] de points, collecte, Laabal), `config/ouagadougou.yaml` (`collecte.depot`), `docs/api-contract.md`, tests `test_regroupement.py`, `test_tournees.py`, `test_plan.py`, `test_scenarios.py` ; puis `backend/routes/terrain.py`, reprise du travail du jour dans `backend/plans.py` (`_reprise`), `tests/test_terrain.py` (65 nouveaux tests au total ; suite complète : 213 verts).
- **Bugs ouverts / limites** : le **dépôt** de Ouaga (`collecte.depot`, Polesgo approximatif) est une hypothèse à confirmer (Cramer : mairie). Avec les zones d'exemple (7 km², 300 m à pied) il faut ~33 points par zone : ajuster `distance_max_a_pied_m`/`couverture_cible` selon la mairie. Un nouveau plan reprend les arrêts effectués et affectations du **même jour UTC** seulement. Toujours pas de vraies zones, pas de limitation des tentatives de connexion, `score_confiance` jamais mis à jour.
- **Pour lancer avec des données** : `python scripts/charger_exemples.py`, puis `uvicorn backend.main:app --reload` ; `GET /points-regroupement` renvoie le plan courant ; en admin, `PUT /scenarios/1/parametres` avec `{"camions": [{"id": "camion_2", "disponible": false}]}` ou `{"saison": "pluies"}` renvoie le plan recalculé.
- **Prochaine étape précise** :
  1. fusionner PR #11 puis la PR de `back/chauffeur-laabal` (relecture par Christian) ;
  2. E1–E3 : `simulation/agents.py`, boucle journalière (ménages, pré-collecteurs, Laabal, mairie) avec graine, indicateurs par jour, route `POST /scenarios/{id}/simuler` (table `indicateur_simulation`) ;
  3. G1 : `GET /admin/export/depotoirs.geojson` (dépotoirs vérifiés, propriétés prêtes pour OSM) ;
  4. P2 : `/scenarios/comparer`, `/laabal/constats`, passage `classe`, import par lot A4.

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
