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

- **Objectif en cours** : simulation multi-agents faite (branche `back/simulation`). `main` contient déjà tout le plan (PR #11 : C2, C3, C7, C4, D1–D4) et les vues de terrain (PR #12 : C6, H1–H3). Ensuite : export G1, puis les P2.
- **Fichiers modifiés** : `simulation/agents.py` (`simuler`, D29), `backend/routes/scenarios.py` (`POST /scenarios/{id}/simuler`), `backend/schemas.py` (`SimulationEntree`), `config/default.yaml` (bloc `simulation:` [H]), `tests/test_agents.py` (13 tests) et 2 tests dans `tests/test_scenarios.py` ; suite complète : **228 verts**. Docs : `docs/api-contract.md`, `DECISIONS.md` (D18 tranchée, D29), `TODO.md`.
- **Bugs ouverts / limites** : coefficients de simulation tous [H] (apport volontaire 0,6, seuil 1 500 kg, réapparition 5 %/jour…) : à caler avec la mairie ou des observations (Cramer). Les dépotoirs hors zone ne reçoivent pas de dépôts dans la simulation. La simulation suit le plan figé du jour 1 (pas de recalcul en cours de simulation). Toujours à confirmer : `collecte.depot` (Polesgo), vraies zones et populations. Pas de limitation des tentatives de connexion ; `score_confiance` jamais mis à jour.
- **Pour lancer avec des données** : `python scripts/charger_exemples.py`, `uvicorn backend.main:app --reload`, puis en admin `POST /scenarios/1/simuler` avec `{"jours": 30, "graine": 42}`. Pour comparer : créer un scénario (`POST /scenarios` avec `{"nom": "pluies", "parametres": {"saison": "pluies"}}`) et simuler les deux avec la même graine.
- **Prochaine étape précise** :
  1. G1 : `GET /admin/export/depotoirs.geojson` (dépotoirs vérifiés, propriétés prêtes pour OSM : `amenity=waste_disposal`? à vérifier avec Cramer, `source`, dates) ;
  2. D6 (P2) : `GET /scenarios/comparer?ids=1,2` (indicateurs du plan + résumé de simulation côte à côte, même graine) ;
  3. P2 : `/laabal/constats`, passage `classe`, import par lot A4, limitation des tentatives de connexion.

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
