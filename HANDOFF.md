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
4. Masquage visages/plaques : fait côté serveur (D36) ; sur l'appareil, à décider (D47).
5. Brancher les routes réelles `/chauffeur/*` et `/laabal/*` avec Faissal (noms marqués [H]).

## Faissal (back / moteur)

- **Objectif en cours** : livrables du 2026-11-17. L1, L3, L4 fusionnés (PR #19, #20, #21). Contour OSM et indicateurs « capacité de collecte » / « part captée » fusionnés (PR #22, D41). Vrais arrondissements et 55 secteurs (carte INSD, D42) fusionnés (PR #23). Fait sur `back/parametres` : L2, `docs/parametres.md` (chaque paramètre : rôle, unité, défaut, Ouaga, source / [H] / technique / informatif), vérifié par un test ; `scenario.horizon_jours` sert maintenant de durée par défaut aux simulations. L2 fusionné (PR #24). Fait sur `back/rapport` : L5 côté back, `scripts/resultats_scenarios.py` → `docs/rapport/` (6 scénarios, tableaux, CSV, courbes, carte, synthèse) ; journées de collecte étalées sur les jours du passage (D43, 13 camions au lieu de 39 pour l'arr. 9). Réparé au passage : la PR #25 avait fusionné des marqueurs de conflit dans DECISIONS, HANDOFF et TODO ; les décisions front D20–D23 (doublons de numéros) sont devenues D44–D47.
- **Fichiers modifiés** : `scripts/generer_donnees_ouaga.py`, `data/ouaga/` (zones, dépotoirs, signalements, `LISEZMOI.md`), `config/ouagadougou.yaml` (paramètres sourcés ou [H], 70 camions, budget 180 M), `config/default.yaml` (`donnees_ouvertes:`, `max_arrets_recherche_locale`), `simulation/tournees.py` (D38, D39 jours par passage), `simulation/plan.py` et `simulation/agents.py` (budget du périmètre), `backend/plans.py` (jour dans la clé de reprise), `backend/synthese.py`, `backend/exemples.py` et `scripts/charger_exemples.py` (`--ouaga`), `backend/routes/donnees_ouvertes.py` (nouveau) ; tests : `test_donnees_ouaga.py` (8), compléments dans `test_tournees.py`, `test_plan.py` ; les tests du **moteur** utilisent maintenant la config générique (`charger_config(None)`), les tests de routes la config de Ouaga. Suite complète : **307 verts**.
- **Bugs ouverts / limites** : découpage relevé à la main sur la carte INSD (précision : quelques centaines de mètres ; arr. 8, 10, 11 à −20/+26/+19 % de la superficie INSD) ; limites entre secteurs approchées (Voronoï) ; population par secteur au prorata de la superficie. Si la mairie fournit les limites officielles, remplacer `data/ouaga/arrondissements.geojson` et `zones.geojson` ; position de Polesgo approximative ; un plan d'arrondissement dispose de toute la flotte (pas d'affectation de camions par arrondissement) ; plan de toute la commune ≈ 5 s (2 100 points).
- **Pour lancer avec des données** : `python scripts/charger_exemples.py --ouaga` sur une base vide, `uvicorn backend.main:app --reload`, puis en admin `PUT /scenarios/1/parametres` `{"perimetre": {"arrondissements": [9]}}` et `GET /scenarios/1/plan/synthese`. Scénarios marquants (arr. 9, secteurs 37 à 40, 30 jours, graine 42 ; capacité des camions / part captée estimée / part captée simulée) : base 100 / 60,2 / 68,3 % ; pluies 100 / 55,2 / 64,3 % ; 60 camions en panne 77,5 / 60,2 / 59,4 % ; apport volontaire porté à 0,8 : 100 / 70,3 / 75,6 %. Commune entière : 2 032 points, 6 s.
- **Prochaine étape précise** :
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
