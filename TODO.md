# TODO — suivi du projet

> **Seul fichier de suivi.** On coche en PR. Format : `- [ ] ID — tâche (priorité)`. Priorités : **P1** indispensable, **P2** si possible, **P3** bonus.
> Les IDs (A1, C3, H2…) renvoient à `docs/fonctionnalites.md`.
> Objectif : une **version de bout en bout** (signalement → modération → plan → carte), même simple et sur données factices, **dès la fin du jour 1 ou le début du jour 2**. Le temps gagné va à la robustesse et à la répétition de l'épreuve en direct, pas à de nouvelles fonctionnalités.

## Phase 0 — Squelette (jour 1)

- [x] Dépôt créé, structure en place, API `/health` qui tourne (Christian)
- [ ] Faissal et Cramer ont cloné le dépôt et lancé l'API
- [ ] Contrat d'API (`docs/api-contract.md`) relu et validé par Christian et Faissal
- [ ] Décisions ouvertes tranchées dans `DECISIONS.md` (framework front, base de données, simulation, licence) — simulation (D18) et licence MIT (D16) tranchées
- [ ] Jeux de données d'exemple dans `data/sample/` utilisés par le front et le back
- [ ] Questions ouvertes de `CONTEXT.md` posées aux organisateurs (Cramer)

## Faissal — back-end et moteur

**Socle**
- [x] Charger la config : `default.yaml` fusionné avec `ouagadougou.yaml` (P1)
- [x] Modèle de données SQLite + schémas Pydantic (P1)
- [x] F1/F4 — Connexion (JWT) et création de comptes par l'admin (P1) — + limitation des tentatives (D32)
- [x] F2 — Droits par rôle vérifiés côté serveur (P1)

**Signalements**
- [x] A1 — `POST /signalements` + `GET /depotoirs` (données factices d'abord) (P1)
- [x] A2 — Vérification automatique : doublon, hors zone, position incohérente, limite par appareil, score + motif (P1)
- [x] A3 — Modération : valider, rejeter avec motif, fusionner (P1) — + score de confiance des appareils (D33)
- [x] B5/B6 — Cycle de vie du dépotoir, légal/illégal, réapparition (P1) — réapparition (A3), transitions Laabal (D28), sites officiels et `classe` par l'admin (D35)
- [x] A4 — Import par lot CSV/GeoJSON pour l'admin (P2) — GeoJSON seulement (D35) ; CSV à ajouter si Cramer en a besoin

**Plan**
- [x] C1 — Estimation de la demande par zone (P1) — fonction pure `simulation/demande.py`, intégrée au plan (C4)
- [x] C2 — Points de regroupement (P1) — fonction pure `simulation/regroupement.py` (D24) ; route `/points-regroupement` avec le plan (C4)
- [x] C3 — Tournées de collecte (OR-Tools, repli plus proche voisin) (P1) — `simulation/tournees.py` (D25) ; dépôt de Ouaga à confirmer
- [x] C7 — Tournées d'intervention Laabal (P1) — `planifier_interventions` (D26)
- [x] C6/H1–H3 (back) — Routes `/chauffeur/*`, `/laabal/*`, `POST /admin/tournees/{id}/affecter` (D28)
- [x] C4 — Recalcul automatique et rapide, plan = fonction pure (P1) — `simulation/plan.py`, routes `/scenarios/*` et `/points-regroupement` (D27)
- [x] D1–D4 — Scénarios : paramètres, camion en panne, saison des pluies, nouveau quartier (P1) — côté back, panne aussi déclarable par le chauffeur (D28)
- [ ] C5 — Explication des choix (P2) — `explication` par point (C2), `raison` des arrêts Laabal et des non couverts ; reste la vue front

**Simulation et export**
- [x] E1–E3 — Moteur journalier, 4 agents, indicateurs (P1) — `simulation/agents.py`, `POST /scenarios/{id}/simuler` (D29)
- [x] E4 — Reproductibilité par graine aléatoire (P2)
- [ ] G1 — Export GeoJSON des dépotoirs vérifiés (P1)
- [ ] H4/H5 — Constats d'infraction, détection de réapparition (P2) — H4 fait (D35) ; H5 : la réapparition est détectée (A3) mais pas encore signalée à Laabal

## Christian — front-end

- [ ] Choisir et initialiser le framework, Leaflet + OSM, proxy ou CORS vers l'API (P1)
- [ ] A1 — Formulaire de signalement mobile (position GPS ajustable, photo, type, volume) (P1)
- [ ] B1/B2 — Carte publique : dépotoirs vérifiés, couches zones/points/tournées (P1)
- [ ] F1/F2 — Connexion et vues selon le rôle (P1)
- [ ] A3 — File de modération administrateur avec alertes (P1)
- [ ] D1–D4 — Panneau de paramètres (camions, panne, saison, nouveau quartier) avec recalcul visible (P1)
- [ ] C3/C7 — Affichage du plan et des tournées sur la carte (P1)
- [ ] C6 — Vue chauffeur : tournée et arrêts à cocher (P1)
- [ ] H1–H3 — Vue Laabal : dépotoirs à traiter, intervention, surveillance (P1)
- [ ] E3 — Tableau de bord des indicateurs (P1)
- [ ] A5 — Suivi d'un signalement avec le code (P2)
- [x] D6 — Comparaison de scénarios côte à côte (P2) — `GET /scenarios/comparer` (D31) ; reste la vue front
- [ ] A6 — Mode hors ligne : file d'attente d'envoi (P2)
- [ ] B3/B4 — Fiche dépotoir et filtres (P2)

## Cramer — présentation, documentation, données, tests

- [x] README complété (présentation, installation, lancement, licence) (P1) — licence MIT (D16)
- [ ] `docs/enonce.md` vérifié contre le sujet officiel (P1)
- [ ] Collecte des signalements de notre secteur (une fois le secteur confirmé) (P1)
- [ ] Hypothèses de `config/ouagadougou.yaml` documentées avec leurs sources (P1)
- [ ] Jeu de test maison : signalements valides + pièges (doublons, hors zone…) pour tester A2 (P1)
- [ ] Scénario de test de l'épreuve en direct (panne, pluies, nouveau quartier) (P1)
- [ ] Se renseigner sur la procédure de versement dans OSM (P2)
- [ ] Script de démo et pitch de 3 à 5 minutes : problème, solution, démo, impact (P1)
- [ ] Plan B de démo : captures d'écran et vidéo (P1)

## Jour 3 — Gel et répétition

- [ ] Gel du code (plus de nouvelle fonctionnalité)
- [ ] Répétition complète de l'épreuve en direct, de bout en bout, hors ligne comprise
- [ ] Répétition du pitch, chronométrée
- [ ] Dépôt propre : README, licence, pas de secret, données ouvertes

## Livrables ajoutés le 2026-11-17

- [x] L1 (back) — Signalement hors connexion : `id_client`, `capture_le`, plafond de réception, note vocale ; masquage serveur des visages et plaques (D36)
- [ ] L1 (front) — File d'attente : envoyer `id_client` et `capture_le`, garder l'élément sur `429`/`503` ; masquage sur le téléphone avant envoi (Christian)
- [x] L2 — Fichier de paramètres documenté (`docs/parametres.md`, test de complétude `tests/test_parametres_doc.py`)
- [x] L3 (back) — Plan, simulation et comparaison d'un arrondissement (`perimetre`), `GET /arrondissements`, synthèse Markdown du plan (D37)
- [ ] L3 (front) — Tableau de bord des scénarios : choix de l'arrondissement, plan sur la carte, indicateurs, simulation, comparaison, synthèse (Christian)
- [x] L4 — Données réalistes de Ouaga (12 arrondissements, paramètres sourcés) et jeu de signalements GeoJSON sous ODbL — `data/ouaga/`, `GET /donnees/signalements.geojson` (D38–D40)
- [ ] L5 — Rapport : démarche, paramètres, scénarios, résultats, plan de gestion (Cramer)
  - [x] chiffres, tableaux, courbes et carte : `python scripts/resultats_scenarios.py` → `docs/rapport/` (D43)
- [ ] L6 — Vidéo de 3 min : du signalement à la tournée, puis un changement de paramètres et le plan recalculé
