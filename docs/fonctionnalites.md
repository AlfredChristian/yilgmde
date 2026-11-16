# Fonctionnalités et user stories

Priorités : **P1** indispensable (MVP) · **P2** si le temps le permet · **P3** bonus.

## Utilisateurs

Citoyen (anonyme) · Administrateur (mairie ; le jury utilisera ce rôle) · Chauffeur de camion · Brigade Laabal.
Les agents de la simulation (ménages, pré-collecteurs, Laabal, mairie) sont des acteurs virtuels du modèle, pas des utilisateurs.

## Modules et fonctionnalités

### A. Collecte et vérification
- A1 · Formulaire de signalement : position GPS automatique et ajustable, photo, type de déchet, volume estimé (P1)
- A2 · Vérification automatique : doublons, hors zone, position incohérente, limite par appareil, score et motif (P1)
- A3 · File de modération : valider, rejeter avec motif, fusionner avec un dépotoir existant (P1)
- A4 · Import par lot CSV/GeoJSON par l'administrateur, pour charger les signalements collectés et un jeu de test (P2)
- A5 · Code de suivi et consultation du statut (P2)
- A6 · Mode hors ligne : file d'attente puis envoi différé (P2)
- A7 · Retrait des métadonnées sensibles des photos (P2)

### B. Cartographie
- B1 · Carte publique des dépotoirs vérifiés (P1)
- B2 · Couches : zones, bâtiments, points de regroupement, tournées (P1)
- B3 · Fiche d'un dépotoir : photos, historique, statut (P2)
- B4 · Filtres (statut, type, volume, zone) (P2)
- B5 · Cycle de vie du dépotoir : actif → intervention planifiée → éradiqué → sous surveillance → classé ; réapparition détectée (P1)
- B6 · Distinction dépotoir illégal / point officiel (P1)

### C. Plan de gestion
- C1 · Estimation de la demande par zone (population × production de déchets) (P1)
- C2 · Placement des points de regroupement (P1)
- C3 · Tournées de collecte optimisées par camion (P1)
- C4 · Recalcul automatique quand données ou paramètres changent (P1)
- C5 · Explication des choix (« ce point est ici parce que… ») (P2)
- C6 · Vue chauffeur : liste ordonnée des arrêts (P1)
- C7 · Tournées d'intervention Laabal sur les dépotoirs illégaux (P1)
- C8 · Affectation des tournées par l'administrateur (P2)

### D. Paramètres et scénarios
- D1 · Paramètres modifiables : population, abonnements, camions, fréquences, budget, saison (P1)
- D2 · Camion en panne (P1)
- D3 · Saison des pluies (P1)
- D4 · Nouveau quartier (ajout d'une zone) (P1)
- D5 · Sauvegarde et duplication de scénarios (P2)
- D6 · Comparaison de scénarios côte à côte (P2)

### E. Simulation multi-agents
- E1 · Moteur par pas journalier (P1)
- E2 · Quatre agents : ménages, pré-collecteurs, brigade Laabal (éradication + dissuasion), mairie (P1)
- E3 · Indicateurs et courbes : % collecté, dépotoirs actifs, coût, distance (P1)
- E4 · Reproductibilité par graine aléatoire (P2)

### F. Administration et sécurité
- F1 · Connexion sécurisée (P1)
- F2 · Rôles admin, chauffeur, Laabal, droits vérifiés côté serveur (P1)
- F3 · Journal d'audit de chaque validation, rejet ou modification (P2)
- F4 · Création des comptes par l'administrateur (P1)

### G. Open source et bien commun
- G1 · Export GeoJSON des dépotoirs vérifiés, prêt pour OSM (P1)
- G2 · Séparation du code générique et des données de Ouaga (P1)
- G3 · Licence, README, guide d'installation, hypothèses documentées (P1)
- G4 · Docker et démo hors ligne (P2)

### H. Brigade Laabal
- H1 · Liste des dépotoirs à traiter, par priorité (P1)
- H2 · Marquer une intervention : en cours, éradiqué, avec photo (P1)
- H3 · Mise sous surveillance après éradication (P1)
- H4 · Enregistrement d'un constat d'infraction avec preuves et montant (P2)
- H5 · Détection de réapparition et alerte (P2)
- H6 · Paiement de l'amende par Mobile Money (P3)

## User stories

**Citoyen**
- US1 · Voir la carte des dépotoirs vérifiés afin de savoir où sont les problèmes. (B1)
- US2 · Signaler en moins de 30 secondes, sans compte, afin de ne pas me décourager. (A1)
- US3 · Signaler sans réseau et envoyer plus tard afin de ne pas perdre mon signalement. (A6)
- US4 · Suivre mon signalement avec un code afin de savoir s'il a été pris en compte. (A5)

**Administrateur**
- US5 · Une file de signalements triés avec alertes automatiques afin de traiter les cas incertains. (A2, A3)
- US6 · Valider, rejeter avec motif ou fusionner un signalement afin de garder une carte fiable. (A3)
- US7 · Modifier les paramètres afin de tester des hypothèses. (D1)
- US8 · Que le plan se recalcule seul afin de voir l'effet de mes changements. (C4)
- US9 · Consulter les indicateurs et comparer deux scénarios afin de choisir. (E3, D6)
- US10 · Comprendre pourquoi un point de regroupement est placé là afin de justifier la décision. (C5)
- US11 · Créer les comptes des chauffeurs et des brigadiers. (F4)
- US12 · Affecter les tournées. (C8)
- US13 · Consulter l'historique des actions. (F3)
- US14 · Exporter les dépotoirs vérifiés en GeoJSON afin de les verser dans OSM. (G1)

**Chauffeur de camion**
- US15 · Voir ma tournée du jour avec l'ordre des arrêts. (C6)
- US16 · Marquer chaque arrêt comme effectué afin que la mairie suive l'avancement. (C6)
- US17 · Signaler un problème (panne, route impraticable) afin que le plan s'adapte. (D2)

**Brigade Laabal**
- US18 · Voir la liste des dépotoirs illégaux à traiter, par priorité. (H1)
- US19 · Marquer un dépotoir comme éradiqué, avec photo. (H2)
- US20 · Mettre un dépotoir sous surveillance afin d'empêcher qu'on y rejette des ordures. (H3)
- US21 · Être alerté quand un dépotoir réapparaît. (H5)
- US22 · Enregistrer un constat d'infraction avec preuves afin de pouvoir sanctionner. (H4)
