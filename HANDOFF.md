# HANDOFF

> À remplir **uniquement** quand on change de conversation avec l'IA ou qu'on passe la main. Une section par personne. Écraser l'ancien contenu.

# HANDOFF (Christian, front)

**Branche** : `front/design-moderne` (à jour sur GitHub).

**Fait**
- Carte, légende (couleurs dans `config/couleurs.js`), proxy `/api`, mode mock.
- Accueil, en-tête, modèle de cartes, drapeau BF.
- `/signaler` (position, pictogrammes, note vocale), `/suivi`.
- Hors ligne : file IndexedDB avec `id_client` et `capture_le`, PWA.
- Connexion, routes protégées, `/admin` (modération), `/admin/plan`, `/chauffeur`, `/laabal`.

<<<<<<< HEAD
**À faire**
1. `npm run build`, puis PR vers `main`.
2. Vérifier le contrat (`id_client`, `capture_le`, `note_vocale`, `X-Device-Token`).
3. Comparaison de scénarios (D6).
4. Masquage visages/plaques (D23, à décider).
5. Brancher les routes réelles `/chauffeur/*` et `/laabal/*` avec Faissal (noms marqués [H]).
=======
- **Objectif en cours** : livrables du 2026-11-17. L1, L3, L4 fusionnés (PR #19, #20, #21). Contour OSM et indicateurs « capacité de collecte » / « part captée » fusionnés (PR #22, D41). Vrais arrondissements et 55 secteurs (carte INSD, D42) fusionnés (PR #23). Fait sur `back/parametres` : L2, `docs/parametres.md` (chaque paramètre : rôle, unité, défaut, Ouaga, source / [H] / technique / informatif), vérifié par un test ; `scenario.horizon_jours` sert maintenant de durée par défaut aux simulations. Reste : L5 (chiffres du rapport).
- **Fichiers modifiés** : `scripts/generer_donnees_ouaga.py`, `data/ouaga/` (zones, dépotoirs, signalements, `LISEZMOI.md`), `config/ouagadougou.yaml` (paramètres sourcés ou [H], 70 camions, budget 180 M), `config/default.yaml` (`donnees_ouvertes:`, `max_arrets_recherche_locale`), `simulation/tournees.py` (D38, D39 jours par passage), `simulation/plan.py` et `simulation/agents.py` (budget du périmètre), `backend/plans.py` (jour dans la clé de reprise), `backend/synthese.py`, `backend/exemples.py` et `scripts/charger_exemples.py` (`--ouaga`), `backend/routes/donnees_ouvertes.py` (nouveau) ; tests : `test_donnees_ouaga.py` (8), compléments dans `test_tournees.py`, `test_plan.py` ; les tests du **moteur** utilisent maintenant la config générique (`charger_config(None)`), les tests de routes la config de Ouaga. Suite complète : **301 verts**.
- **Bugs ouverts / limites** : découpage relevé à la main sur la carte INSD (précision : quelques centaines de mètres ; arr. 8, 10, 11 à −20/+26/+19 % de la superficie INSD) ; limites entre secteurs approchées (Voronoï) ; population par secteur au prorata de la superficie. Si la mairie fournit les limites officielles, remplacer `data/ouaga/arrondissements.geojson` et `zones.geojson` ; position de Polesgo approximative ; un plan d'arrondissement dispose de toute la flotte (pas d'affectation de camions par arrondissement) ; plan de toute la commune ≈ 5 s (2 100 points).
- **Pour lancer avec des données** : `python scripts/charger_exemples.py --ouaga` sur une base vide, `uvicorn backend.main:app --reload`, puis en admin `PUT /scenarios/1/parametres` `{"perimetre": {"arrondissements": [9]}}` et `GET /scenarios/1/plan/synthese`. Scénarios marquants (arr. 9, secteurs 37 à 40, 30 jours, graine 42 ; capacité des camions / part captée estimée / part captée simulée) : base 100 / 60,2 / 68,3 % ; pluies 100 / 55,2 / 64,3 % ; 60 camions en panne 77,5 / 60,2 / 59,4 % ; apport volontaire porté à 0,8 : 100 / 70,3 / 75,6 %. Commune entière : 2 032 points, 6 s.
- **Prochaine étape précise** :
  2. L5 : `scripts/resultats_scenarios.py` qui calcule les scénarios du rapport sur `data/ouaga/` et écrit tableaux (Markdown/CSV) et courbes ;
  3. aider Christian (tableau de bord) et Cramer (rapport, vidéo).

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
>>>>>>> origin/main
