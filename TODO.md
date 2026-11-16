# TODO — suivi du projet

> **Seul fichier de suivi.** On coche en PR. Format : `- [ ] ID — tâche (priorité)`. Priorités : **P1** indispensable, **P2** si possible, **P3** bonus.
> Les IDs (A1, C3, H2…) renvoient à `docs/fonctionnalites.md`.
> Objectif : une **version de bout en bout** (signalement → modération → plan → carte), même simple et sur données factices, **dès la fin du jour 1 ou le début du jour 2**. Le temps gagné va à la robustesse et à la répétition de l'épreuve en direct, pas à de nouvelles fonctionnalités.

## Phase 0 — Squelette (jour 1)

- [x] Dépôt créé, structure en place, API `/health` qui tourne (Christian)
- [ ] Faissal et Cramer ont cloné le dépôt et lancé l'API
- [ ] Contrat d'API (`docs/api-contract.md`) relu et validé par Christian et Faissal
- [ ] Décisions ouvertes tranchées dans `DECISIONS.md` (framework front, base de données, simulation, licence)
- [ ] Jeux de données d'exemple dans `data/sample/` utilisés par le front et le back
- [ ] Questions ouvertes de `CONTEXT.md` posées aux organisateurs (Cramer)

## Faissal — back-end et moteur

**Socle**
- [ ] Charger la config : `default.yaml` fusionné avec `ouagadougou.yaml` (P1)
- [ ] Modèle de données SQLite + schémas Pydantic (P1)
- [ ] F1/F4 — Connexion (JWT) et création de comptes par l'admin (P1)
- [ ] F2 — Droits par rôle vérifiés côté serveur (P1)

**Signalements**
- [ ] A1 — `POST /signalements` + `GET /depotoirs` (données factices d'abord) (P1)
- [ ] A2 — Vérification automatique : doublon, hors zone, position incohérente, limite par appareil, score + motif (P1)
- [ ] A3 — Modération : valider, rejeter avec motif, fusionner (P1)
- [ ] B5/B6 — Cycle de vie du dépotoir, légal/illégal, réapparition (P1)
- [ ] A4 — Import par lot CSV/GeoJSON pour l'admin (P2)

**Plan**
- [ ] C1 — Estimation de la demande par zone (P1)
- [ ] C2 — Points de regroupement (P1)
- [ ] C3 — Tournées de collecte (OR-Tools, repli plus proche voisin) (P1)
- [ ] C7 — Tournées d'intervention Laabal (P1)
- [ ] C4 — Recalcul automatique et rapide, plan = fonction pure (P1)
- [ ] D1–D4 — Scénarios : paramètres, camion en panne, saison des pluies, nouveau quartier (P1)
- [ ] C5 — Explication des choix (P2)

**Simulation et export**
- [ ] E1–E3 — Moteur journalier, 4 agents, indicateurs (P1)
- [ ] E4 — Reproductibilité par graine aléatoire (P2)
- [ ] G1 — Export GeoJSON des dépotoirs vérifiés (P1)
- [ ] H4/H5 — Constats d'infraction, détection de réapparition (P2)

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
- [ ] D6 — Comparaison de scénarios côte à côte (P2)
- [ ] A6 — Mode hors ligne : file d'attente d'envoi (P2)
- [ ] B3/B4 — Fiche dépotoir et filtres (P2)

## Cramer — présentation, documentation, données, tests

- [ ] README complété (présentation, installation, lancement, licence) (P1)
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
