# DECISIONS

> Une ligne par choix, avec sa raison. Toute décision technique importante se note **le jour même**.
> Statuts : **Validé** (acté par l'équipe), **Retenu** (en place dans le code), **Proposé** (à confirmer), **À décider**.

| ID | Date | Décision | Raison | Statut |
|---|---|---|---|---|
| D01 | 2026-11-16 | Travail centralisé sur Git : branches par tâche, Pull Requests, `main` toujours fonctionnel | Avancer vite à trois sans se marcher dessus | Validé |
| D02 | 2026-11-16 | Rôles : Christian front ; Faissal back et moteur ; Cramer présentation, docs, données, tests | Forces de chacun | Validé |
| D03 | 2026-11-16 | Calendrier en 3 jours, avec objectif de version de bout en bout au plus tôt | Garder du temps pour la robustesse et la répétition de l'épreuve en direct | Validé |
| D04 | 2026-11-16 | Citoyens sans compte (jeton d'appareil anonyme + code de suivi) ; comptes créés par l'admin pour les autres rôles | Moins de friction pour signaler, surtout sur mobile | Validé |
| D05 | 2026-11-16 | Utilisateurs : citoyen, administrateur, chauffeur, brigade Laabal. Retirés : agent de terrain, jury (accès admin sur place), réutilisateur | Périmètre réaliste en 3 jours | Validé |
| D06 | 2026-11-16 | Brigade Laabal : éradication des dépotoirs illégaux, surveillance, constats d'infraction | Précisé par l'équipe | Validé (détail des amendes à préciser) |
| D07 | 2026-11-16 | Python + FastAPI pour l'API et le moteur de calcul | Rapide à écrire, docs auto, même langage que le calcul | Retenu |
| D08 | 2026-11-16 | OR-Tools pour les tournées, scikit-learn pour le regroupement, GeoPandas/Shapely pour le géo | Standards open source du domaine | Retenu |
| D09 | 2026-11-16 | Le plan est une fonction pure de (données, paramètres), recalculé à chaque changement | Exigé par l'épreuve en direct | Retenu |
| D10 | 2026-11-16 | Paramètres dans `config/*.yaml`, jamais en dur ; hypothèses marquées `[H]` | Épreuve en direct + simulateur réutilisable | Retenu |
| D11 | 2026-11-16 | Pas de secrets, de photos ni de données personnelles réelles dans le dépôt | Dépôt open source | Retenu |
| D12 | 2026-11-16 | Front en PWA avec Leaflet + tuiles OpenStreetMap | « Mobile » est un tag du sujet ; open source | Proposé |
| D13 | 2026-11-16 | Une seule application front avec des vues selon le rôle | Moins de code à maintenir que trois applications | Proposé |
| D14 | 2026-11-16 | Base SQLite pour le MVP (opérations spatiales faites en Python) ; PostGIS écarté pour l'instant | Moins de configuration, pas de Docker obligatoire | Retenu (`backend/db.py`) |
| D15 | 2026-11-16 | Le constat d'infraction enregistre et trace, il ne décide jamais d'une sanction ; accès réservé à Laabal et admin ; la carte publique montre le dépotoir, pas la personne | Données personnelles sensibles | Proposé |
| D16 | 2026-11-16 | Licence du code : Apache-2.0 ; données dérivées d'OSM sous ODbL | Réutilisation facile par d'autres communes ; compatibilité OSM | Proposé |
| D17 | — | Framework front (React, Vue, Angular…) | À choisir selon ce que Christian maîtrise | À décider |
| D18 | — | Simulation : boucle Python maison ou Mesa | À choisir par Faissal | À décider |
