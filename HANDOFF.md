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

- **Objectif en cours** : livrables du 2026-11-17. L1, L3, L4 fusionnés (PR #19, #20, #21). Fait sur `back/carte-reelle` : vrai contour de Ouagadougou (OpenStreetMap) et indicateurs « capacité de collecte » / « part captée » distingués (D41). Reste : L2 (paramètres documentés) et L5 (chiffres du rapport).
- **Fichiers modifiés** : `scripts/generer_donnees_ouaga.py`, `data/ouaga/` (zones, dépotoirs, signalements, `LISEZMOI.md`), `config/ouagadougou.yaml` (paramètres sourcés ou [H], 70 camions, budget 180 M), `config/default.yaml` (`donnees_ouvertes:`, `max_arrets_recherche_locale`), `simulation/tournees.py` (D38, D39 jours par passage), `simulation/plan.py` et `simulation/agents.py` (budget du périmètre), `backend/plans.py` (jour dans la clé de reprise), `backend/synthese.py`, `backend/exemples.py` et `scripts/charger_exemples.py` (`--ouaga`), `backend/routes/donnees_ouvertes.py` (nouveau) ; tests : `test_donnees_ouaga.py` (8), compléments dans `test_tournees.py`, `test_plan.py` ; les tests du **moteur** utilisent maintenant la config générique (`charger_config(None)`), les tests de routes la config de Ouaga. Suite complète : **301 verts**.
- **Bugs ouverts / limites** : vrai contour de la commune, mais limites des **arrondissements schématiques** : elles ne sont ni dans OpenStreetMap ni sur HDX/geoBoundaries (niveau commune seulement). Si la mairie fournit un fichier, le mettre dans `data/ouaga/zones.geojson` avec les mêmes propriétés. Depuis la session de Claude, Overpass et les fichiers HDX (stockés sur `s3.us-east-1.amazonaws.com`) restaient bloqués malgré l'autorisation demandée ; position de Polesgo approximative ; un plan d'arrondissement dispose de toute la flotte (pas d'affectation de camions par arrondissement) ; plan de toute la commune ≈ 5 s (2 100 points).
- **Pour lancer avec des données** : `python scripts/charger_exemples.py --ouaga` sur une base vide, `uvicorn backend.main:app --reload`, puis en admin `PUT /scenarios/1/parametres` `{"perimetre": {"arrondissements": [9]}}` et `GET /scenarios/1/plan/synthese`. Scénarios marquants (arr. 9, 30 jours, graine 42 ; capacité des camions / part captée estimée / part captée simulée) : base 100 / 67,6 / 75,7 % ; pluies 73,5 / 61,3 / 56,6 % avec 3 passages annulés (budget) ; 60 camions en panne 81,0 / 67,6 / 66,3 % ; apport volontaire porté à 0,8 : 100 / 80,1 / 85,0 %.
- **Prochaine étape précise** :
  1. L2 : `docs/parametres.md` (chaque paramètre : rôle, unité, valeur, source ou [H]), vérifié par un test contre `config/default.yaml` et `config/ouagadougou.yaml` ;
  2. L5 : `scripts/resultats_scenarios.py` qui calcule les scénarios du rapport sur `data/ouaga/` et écrit tableaux (Markdown/CSV) et courbes ;
  3. aider Christian (tableau de bord) et Cramer (rapport, vidéo).

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
