# HANDOFF

> À remplir **uniquement** quand on change de conversation avec l'IA ou qu'on passe la main. Une section par personne. Écraser l'ancien contenu.

## Christian (front)

**Branche** : `front/design-moderne` (à jour sur GitHub).

**Fait**
- Carte, légende (couleurs dans `config/couleurs.js`), proxy `/api`, mode mock.
- Accueil, en-tête, modèle de cartes, drapeau BF.
- `/signaler` (position, pictogrammes, note vocale), `/suivi`.
- Hors ligne : file IndexedDB avec `id_client` et `capture_le`, PWA.
- Connexion, routes protégées, `/admin` (modération), `/admin/plan`, `/chauffeur`, `/laabal`.

**À faire**
1. `npm run build`, puis PR vers `main`.
2. Vérifier le contrat (`id_client`, `capture_le`, `note_vocale`, `X-Device-Token`).
3. Comparaison de scénarios (D6).
4. Masquage visages/plaques : fait sur le serveur (D36, D57) **et sur le téléphone avant l'envoi** (D59, `src/masquage/`, branche `front/masquage-appareil`). Le modèle est dans `public/modeles/` ; s'il change, relancer `python scripts/exporter_yunet_web.py` puis `python scripts/verifier_masquage_web.py`.
5. Brancher les routes réelles `/chauffeur/*` et `/laabal/*` avec Faissal (noms marqués [H]).

## Faissal (back / moteur)

- **Objectif en cours** : livrables du 2026-11-17. L1, L3, L4 fusionnés (PR #19, #20, #21). Contour OSM et indicateurs « capacité de collecte » / « part captée » fusionnés (PR #22, D41). Vrais arrondissements et 55 secteurs (carte INSD, D42) fusionnés (PR #23). Fait sur `back/parametres` : L2, `docs/parametres.md` (chaque paramètre : rôle, unité, défaut, Ouaga, source / [H] / technique / informatif), vérifié par un test ; `scenario.horizon_jours` sert maintenant de durée par défaut aux simulations. L2 fusionné (PR #24). Fait sur `back/rapport` : L5 côté back, `scripts/resultats_scenarios.py` → `docs/rapport/` (6 scénarios, tableaux, CSV, courbes, carte, synthèse) ; journées de collecte étalées sur les jours du passage (D43, 13 camions au lieu de 39 pour l'arr. 9). Réparé au passage : la PR #25 avait fusionné des marqueurs de conflit dans DECISIONS, HANDOFF et TODO ; les décisions front D20–D23 (doublons de numéros) sont devenues D44–D47.
- **Fichiers modifiés** : `scripts/generer_donnees_ouaga.py`, `data/ouaga/` (zones, dépotoirs, signalements, `LISEZMOI.md`), `config/ouagadougou.yaml` (paramètres sourcés ou [H], 70 camions, budget 180 M), `config/default.yaml` (`donnees_ouvertes:`, `max_arrets_recherche_locale`), `simulation/tournees.py` (D38, D39 jours par passage), `simulation/plan.py` et `simulation/agents.py` (budget du périmètre), `backend/plans.py` (jour dans la clé de reprise), `backend/synthese.py`, `backend/exemples.py` et `scripts/charger_exemples.py` (`--ouaga`), `backend/routes/donnees_ouvertes.py` (nouveau) ; tests : `test_donnees_ouaga.py` (8), compléments dans `test_tournees.py`, `test_plan.py` ; les tests du **moteur** utilisent maintenant la config générique (`charger_config(None)`), les tests de routes la config de Ouaga. Suite complète : **307 verts**.
- **Bugs ouverts / limites** : découpage relevé à la main sur la carte INSD (précision : quelques centaines de mètres ; arr. 8, 10, 11 à −20/+26/+19 % de la superficie INSD) ; limites entre secteurs approchées (Voronoï) ; population par secteur au prorata de la superficie. Si la mairie fournit les limites officielles, remplacer `data/ouaga/arrondissements.geojson` et `zones.geojson` ; position de Polesgo approximative ; un plan d'arrondissement dispose de toute la flotte (pas d'affectation de camions par arrondissement) ; plan de toute la commune ≈ 5 s (2 100 points).
- **Pour lancer avec des données** : `python scripts/charger_exemples.py --ouaga` sur une base vide, `uvicorn backend.main:app --reload`, puis en admin `PUT /scenarios/1/parametres` `{"perimetre": {"arrondissements": [9]}}` et `GET /scenarios/1/plan/synthese`. Scénarios marquants (arr. 9, secteurs 37 à 40, 30 jours, graine 42 ; capacité des camions / part captée estimée / part captée simulée) : base 100 / 60,2 / 68,3 % ; pluies 100 / 55,2 / 64,3 % ; 60 camions en panne 77,5 / 60,2 / 59,4 % ; apport volontaire porté à 0,8 : 100 / 70,3 / 75,6 %. Commune entière : 2 032 points, 6 s.
- **Prochaine étape précise** :
  0. Fait sur `back/retours-tests` : D65, cartes sur Leaflet seul (`src/carte/`, react-leaflet retiré pour sa licence), plan de gestion en PDF, coût expliqué, zoom sur le dépotoir depuis le suivi, tableau des licences dans le README ;
  0. Fait sur `front/https-telephone` : D64, `npm run dev:telephone` (https sur le réseau local, note vocale sur téléphone), `npm run essai:installable`, `scripts/lancer_demo.ps1` ;
  0. Fait sur `back/parts-menages` : D63, parts des ménages 35 % abonnés / 15 % apport / 50 % sauvage (`config/ouagadougou.yaml`), rapport régénéré (part captée du plan de base 47,9 %, 60,6 % sur 30 jours). Les chiffres plus anciens cités plus bas (66 %, 72 %) sont dépassés ;
  0. Fait sur `front/simulation-quartier` : D62, Plan > « Simulation d'un quartier » (`src/components/SimulationQuartier.jsx`, `simulation/quartier.py`, `backend/routes/quartier.py`, illustrations `src/components/iconesQuartier.js`) ;
  0. Fait sur `front/laabal-camion` : D61, camion de la brigade animé sur `/laabal` (`src/components/CamionEnRoute.jsx`, `GET /laabal/depotoirs/{id}/itineraire`) ;
  0. Fait sur `front/camera-camions-eradication` : D60. Plan > « Suivi de l'éradication » (`src/components/SuiviEradication.jsx`, `GET /admin/suivi-depotoirs`, `backend/routes/eradication.py`), webcam en fenêtre sur ordinateur (`src/components/PriseDeVue.jsx`, ne marche que sur https ou localhost), camions en SVG (`src/components/iconeCamion.js`). Relancer `python scripts/charger_exemples.py --ouaga --demo` pour avoir l'historique d'éradication ;
  0. Fait sur `back/floutage-batiments` : D57 (visages par YuNet, plaques par la forme quel que soit le pays, pixellisation plus forte), D58 (ménages situés d'après les bâtiments Open Buildings, `simulation/batiments.py`, poids par surface bâtie pour les points, la charge et la couverture). Fichier `data/ouaga/batiments.csv.gz` poussé par Faissal (2 029 837 bâtiments, 16 Mo, chargé en 2 s). Arr. 9 : 228 points au lieu de 240, part captée estimée 66,3 % au lieu de 60,2 %, aucun point à plus de 150 m d'une maison (11 avant) ; commune : 1 920 points, 66,0 %, 9 s. `docs/rapport/` régénéré ; 333 tests ;
  0. Fait sur `front/parametres-quartier-synthese` : D56, nouveau quartier dessiné sur la carte du plan (retirable), leviers population / abonnements / fréquence / apport volontaire, lecture et téléchargement du plan de gestion ; 326 tests ;
  0. Fait sur `back/commune-routes-moderation` : D53 (commune entière sur les routes, ~10 s), D54 (fiche de modération avant décision, correctif du bouton Fusionner) ; explication des jours retirée du suivi ; 323 tests ;
  0. Fait sur `back/reseau-routier` : D52, tournées sur les vraies voies OSM (fichier téléchargé par Faissal), sur toutes les cartes et dans le rapport ; 321 tests ;
  0. Fait sur `back/suivi-flotte` : D51, suivi de la flotte en 2D réel (`GET /admin/suivi` + `components/SuiviFlotte.jsx`, plein écran), remplace la scène isométrique ;
  0. Fait sur `back/finitions-demo` : D50 (calibrage des nouveaux dépotoirs pour Ouaga, rapport régénéré), D49 (gestion des comptes, API + page Comptes), `--demo` (comptes, scénarios pluies/panne/sensibilisation, tournées affectées), variante nommée et activée à la création, tonnes et % dans la comparaison. 315 tests ;
  0. Fait sur `front/branchement-api` (avec Christian) : le front parle à la vraie API, vérifié de bout en bout dans un navigateur (signalement en ligne et hors ligne, suivi, modération, plan par arrondissement, panne, chauffeur, Laabal). Corrigés : longitude jamais envoyée (tous les signalements refusés en 422 puis supprimés de la file), `vite-plugin-pwa` absent de `package.json` (build cassé), photo et note vocale de modération chargées avec le jeton, paramètres du plan traduits en surcharges de scénario, nouveaux indicateurs (D41), routes réelles chauffeur et Laabal. Ajouté : `indicateurs.camions_flotte`. Reste au front : écran d'affectation des tournées, simulation et comparaison (L3) ;
  1. Cramer reprend `docs/rapport/resultats.md` et les images dans le rapport ; autre arrondissement : `--arrondissement N` ;
  2. limite connue : sur 30 jours le nombre de dépotoirs actifs est le même dans tous les scénarios (un nouveau dépotoir par secteur et par jour dès que le seuil est dépassé) ; à revoir si on veut que la courbe des dépotoirs réagisse aux scénarios ;
  3. aider Christian (tableau de bord) et Cramer (rapport, vidéo).

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
