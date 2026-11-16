# CONTEXT — yilgmde

> À coller au début de chaque nouvelle conversation avec une IA.
> Ce fichier est **stable** (projet, contraintes, stack). Le suivi (fait / en cours / à faire) est **uniquement** dans `TODO.md`.
> Le texte exact du sujet est dans `docs/enonce.md`. Les détails sont dans `docs/` (voir section 9).

## 1. Le projet

**yilgmde** est un outil libre d'aide à la décision pour l'assainissement de Ouagadougou. Il va du signalement citoyen des dépotoirs sauvages jusqu'au plan de gestion de la ville (points de regroupement, tournées), avec une simulation des acteurs.

Contexte : Hackathon des Universités 2026, **finale** (16 finalistes, 8 équipes par sujet). Thème de l'année : **l'Open Source**. Format : 3 jours pour produire un outil. Notre équipe de 3 a tiré au sort le **Challenge 01 — « Assainissement de Ouaga »**.

## 2. Ce que le sujet exige

Quatre modules :
1. **Cartographie** des dépotoirs et signalements **vérifiés**.
2. **Plan de gestion** : emplacement des points de regroupement, tournées optimisées.
3. **Simulation multi-agents** : ménages, pré-collecteurs, brigade Laabal, mairie.
4. **Paramètres modifiables** (population, abonnements, camions, fréquences, budget) pour comparer des scénarios.

**Données** : carte ouverte (OpenStreetMap, Open Buildings), signalements collectés par chaque équipe dans son secteur, paramètres de départ fixés avec la mairie. Le jury garde un jeu de test caché.

**Épreuve en direct** : le jury injecte des signalements piégés, puis change les paramètres (camions en panne, saison des pluies, nouveau quartier). Le plan doit se recalculer et rester cohérent.

**Bien commun attendu** : la première carte ouverte des dépotoirs de Ouaga (versable dans OSM) et un simulateur réutilisable par d'autres communes.

## 3. Contraintes qui en découlent

1. Le calcul du plan est une **fonction pure** : `plan = f(données, paramètres)`. Pas d'état caché, résultat reproductible.
2. **Rien en dur** : tous les paramètres viennent de `config/` (YAML) ou de l'interface.
3. **Recalcul rapide** (quelques secondes) quand un paramètre ou une donnée change. Si le calcul est long, on renvoie la meilleure solution trouvée dans un temps limite.
4. **Filtre anti-pièges** sur les signalements : doublons, hors zone, positions incohérentes, abus par appareil. Chaque rejet est **explicable** (motif affiché).
5. **Projet open source** : licence libre, README, données ouvertes, code générique séparé des données propres à Ouaga.
6. **Démo fiable** : doit marcher hors ligne ou avec une connexion instable ; prévoir un plan B (captures, vidéo).

## 4. Utilisateurs de l'application

| Utilisateur | Compte | Rôle |
|---|---|---|
| Citoyen | Non (anonyme : jeton d'appareil + code de suivi) | Consulte la carte, signale, suit son signalement |
| Administrateur (mairie) | Oui | Modère les signalements, gère paramètres/scénarios/plan, affecte les tournées, crée les comptes, consulte les indicateurs. Le jury utilisera ce rôle pour les tests |
| Chauffeur de camion | Oui | Voit sa tournée de collecte, marque les arrêts effectués, signale un incident |
| Brigade Laabal | Oui | Traite les dépotoirs illégaux (éradication), met sous surveillance, enregistre les constats d'infraction |

Les comptes sont créés par l'administrateur (pas d'inscription libre).
**À ne pas confondre** : les *agents de la simulation* (ménages, pré-collecteurs, Laabal, mairie) sont des acteurs virtuels du modèle, pas des utilisateurs de l'app.

## 5. Stack

- **Langage / API** : Python 3.12, FastAPI, Pydantic, PyYAML.
- **Calcul** : GeoPandas, Shapely, pyproj (géo) ; scikit-learn (regroupement) ; OR-Tools (tournées).
- **Simulation** : boucle Python maison ou Mesa (à décider, voir `DECISIONS.md`).
- **Base de données** : SQLite pour le MVP (proposé, voir `DECISIONS.md`).
- **Front** : PWA responsive, Leaflet + tuiles OpenStreetMap (framework à confirmer).
- **Une seule application front** avec des vues selon le rôle.
- **Licence** : Apache-2.0 pour le code (proposé) ; données dérivées d'OSM sous ODbL.

## 6. Structure du dépôt

```
backend/      API FastAPI (routes, auth, accès base)
simulation/   moteur de calcul indépendant de l'API : vérification, demande, regroupement, tournées, agents
frontend/     application web (PWA)
config/       default.yaml (générique) + ouagadougou.yaml (local) — hypothèses marquées [H]
data/sample/  petits jeux de données fictifs commités (pour développer sans attendre)
data/raw/     données brutes lourdes — NON commitées
docs/         enonce, fonctionnalites, modele-donnees, api-contract
scripts/      scripts utilitaires (préparation des données, etc.)
```

## 7. Équipe

- **Christian** : front-end (carte, formulaires, vues par rôle).
- **Faissal** : back-end et moteur de calcul (API, vérification, plan, tournées, simulation).
- **Cramer** : présentation, documentation, données de terrain et jeux de test, pitch et démo.

## 8. Règles de travail

1. `main` doit toujours fonctionner. Personne ne pousse dessus directement.
2. Une branche par tâche : `front/…`, `back/…`, `docs/…`. Pull Request relue par un autre membre, puis *Squash and merge*.
3. Toute décision technique est notée dans `DECISIONS.md` **le jour même**.
4. Toute modification d'API passe par une PR qui met aussi à jour `docs/api-contract.md`.
5. Pas de secrets, pas de photos ni de données personnelles réelles dans le dépôt.
6. Pas de paramètre en dur : tout passe par `config/`.
7. On met à jour `TODO.md` en cochant les tâches ; on remplit `HANDOFF.md` quand on change de conversation avec l'IA.

## 9. Où trouver quoi

- `docs/enonce.md` : texte exact du sujet.
- `docs/fonctionnalites.md` : modules A à H, priorités, user stories.
- `docs/modele-donnees.md` : entités, statuts, règles de cohérence.
- `docs/api-contract.md` : routes, formats JSON, droits par rôle.
- `TODO.md` : suivi par personne. `DECISIONS.md` : choix et raisons. `HANDOFF.md` : reprise de travail.

## 10. Consignes à l'IA

- Réponds en français, de façon concrète, avec du code qui tourne sous **Windows (PowerShell)** comme sous Linux.
- Respecte `docs/api-contract.md` et `docs/modele-donnees.md`. Ne change pas la stack sans passer par `DECISIONS.md`.
- Privilégie le simple : un MVP qui marche vaut mieux qu'un projet ambitieux à moitié fini.
- Signale toute hypothèse que tu fais (surtout chiffrée) et marque-la `[H]`.

## 11. Questions ouvertes

- Date et heure exactes de la finale et du rendu (pour caler `TODO.md`).
- Quel est **notre secteur** de collecte des signalements, et quand collecte-t-on ?
- Comment le jury injecte-t-il ses signalements piégés (formulaire, API, fichier) et dans quel format ?
- Les paramètres de départ de la mairie nous sont-ils fournis, et sous quelle forme ?
- Règles de rendu : dépôt public dès maintenant ? licence imposée ?
- Procédure et règles pour verser la carte dans OpenStreetMap (règles d'import de la communauté).
- Confirmer qu'on dispose de la version complète de l'énoncé.
