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

- **Objectif en cours** : export OSM (G1) et comparaison de scénarios (D6) faits (branche `back/export-osm`). `main` contient tout le reste du back P1 : plan (C2–C4, C7), scénarios (D1–D4), terrain (C6, H1–H3), simulation (E1–E4). Reste surtout du P2 et l'aide au front.
- **Fichiers modifiés** : `backend/export_osm.py`, `backend/routes/admin_export.py`, `backend/routes/scenarios.py` (`/scenarios/comparer`, déclarée avant `/scenarios/{id}`), `backend/main.py`, `config/default.yaml` (bloc `export_osm:`), `tests/test_export_osm.py` (6 tests) et 2 tests dans `tests/test_scenarios.py` ; suite complète : **236 verts**. Docs : `docs/api-contract.md`, `DECISIONS.md` (D30, D31), `TODO.md`.
- **Bugs ouverts / limites** : étiquettes OSM et licence des données (D16 proposé, `export_osm.licence: null`) à valider avant tout versement ; un versement OSM = un import à annoncer à la communauté OSM du Burkina. `/scenarios/comparer` recalcule les simulations à chaque appel (~1 s par scénario). Coefficients `[H]` de simulation et `collecte.depot` toujours à confirmer. Pas de limitation des tentatives de connexion ; `score_confiance` jamais mis à jour.
- **Pour lancer avec des données** : `python scripts/charger_exemples.py`, `uvicorn backend.main:app --reload` ; en admin : `GET /admin/export/depotoirs.geojson`, `GET /scenarios/comparer?ids=1,2&jours=30&graine=42` (après avoir créé un 2e scénario).
- **Prochaine étape précise** :
  1. sécurité (P1 transverse) : limiter les tentatives de `POST /auth/login` (compteur par e-mail et IP, blocage temporaire, paramètres dans la config) ;
  2. `score_confiance` des contributeurs : monter à la validation, baisser au rejet (A3), et l'utiliser dans le score automatique (A2) ;
  3. P2 : `/laabal/constats` (amendes réelles), passage `classe`, saisie d'un site officiel par l'admin, import par lot A4 ;
  4. aider Christian à brancher le front sur `/points-regroupement`, `/scenarios/{id}/plan`, `/simuler`, `/comparer`.

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
