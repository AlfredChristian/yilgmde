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

- **Objectif en cours** : P2 du back faits (branche `back/p2-depotoirs`) : sites officiels et classement (B5/B6), import par lot (A4), constats Laabal (H4). En attente de fusion aussi : PR #16 (README, `YILGMDE_VILLE`). `main` contient tout le back P1.
- **Fichiers modifiés** : `backend/routes/admin_donnees.py` (nouveau), `backend/routes/terrain.py` (constats), `backend/main.py`, `config/default.yaml` (`import.max_par_lot`), `tests/test_admin_donnees.py` (6 tests), `tests/test_terrain.py` (+2) ; suite complète : **257 verts**. Docs : `docs/api-contract.md`, `DECISIONS.md` (D35), `TODO.md`.
- **Bugs ouverts / limites** : import en GeoJSON seulement (pas de CSV) ; pour Cramer : dans le jeu piégé, l'entrée 6 (« non doublon », à 40 m de la 1) est à 15 m de l'entrée 5 : importée avec tout le lot, elle reçoit à juste titre une alerte doublon de la 5 ; H5 : la réapparition est détectée à la validation (A3) mais aucune alerte n'est envoyée à Laabal (elle remonte seulement dans `/laabal/depotoirs-a-traiter` avec priorité plus haute). **Licence à trancher** (`LICENSE` MIT, D16 Apache-2.0). Toujours à valider : étiquettes OSM, `collecte.depot`, coefficients [H].
- **Pour lancer avec des données** : `python scripts/charger_exemples.py`, `uvicorn backend.main:app --reload` ; en admin : `POST /admin/signalements/import` avec le contenu de `data/sample/signalements_pieges.geojson` (testé : les 23 entrées donnent leur `attendu`), `POST /admin/depotoirs` pour un site officiel.
- **Prochaine étape précise** :
  1. H5 : alerte de réapparition pour Laabal (`GET /laabal/alertes` : dépotoirs revenus `actif` depuis la dernière consultation, ou champ `reapparu_le`) ;
  2. import CSV (A4) si Cramer collecte en tableur ;
  3. brancher le front (avec Christian) sur plan, scénarios, simulation, comparaison, modération.

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
