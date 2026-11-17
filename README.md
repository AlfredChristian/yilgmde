# yilgmde

Outil libre d'aide à la décision pour l'assainissement de Ouagadougou, du signalement des dépotoirs sauvages jusqu'au plan de gestion de la ville, avec simulation des acteurs.

Projet du **Hackathon des Universités 2026 — Finale**, Challenge 01 « Assainissement de Ouaga » (thème : l'Open Source).

## Ce que fait l'outil

| Besoin | Ce que fait l'outil | Où |
|---|---|---|
| Savoir où sont les dépotoirs | Signalement citoyen **sans compte**, même **hors connexion** (position, photo aux visages et plaques floutés, note vocale, type de déchets), vérification automatique (doublons, hors zone, limite par appareil, appareil peu fiable), puis modération par la mairie | `POST /signalements`, `/admin/signalements` |
| Organiser la collecte | Demande par zone, **points de regroupement** à distance de marche, **tournées** de camions optimisées (OR-Tools), coûts et budget | `GET /points-regroupement`, `/scenarios/{id}/plan` |
| Éradiquer les dépotoirs illégaux | Tournées de la **brigade Laabal** par priorité, intervention, surveillance, réapparition | `/laabal/*` |
| Guider le terrain | Tournée du chauffeur, arrêts à cocher, déclaration de panne (le plan se recalcule) | `/chauffeur/*` |
| Décider | **Scénarios** (camion en panne, saison des pluies, nouveau quartier, budget…), **simulation multi-agents** sur 30 jours, **comparaison** côte à côte | `/scenarios/*` |
| Partager | **Jeu ouvert** des signalements vérifiés (ODbL, anonymisé) ; **export GeoJSON** des dépotoirs prêt pour OpenStreetMap | `GET /donnees/signalements.geojson`, `GET /admin/export/depotoirs.geojson` |

Chaque choix du moteur est **expliqué** (pourquoi ce point, pourquoi ce dépotoir d'abord, pourquoi une zone n'est pas couverte), et **reproductible** : mêmes données et mêmes paramètres donnent le même plan ; même graine donne la même simulation.

## Installation

Prérequis : **Python 3.11+** (back-end) et **Node.js 20+** (front-end).

### Back-end

Windows (PowerShell) :
```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Linux / macOS :
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Front-end

```bash
cd frontend
npm install
```

## Lancement

### 1. Créer le compte administrateur (première fois)

Le compte admin est créé au démarrage s'il n'existe pas, à partir de deux variables d'environnement.

Windows (PowerShell) :
```powershell
$env:YILGMDE_ADMIN_EMAIL = "admin@mairie.bf"
$env:YILGMDE_ADMIN_PASSWORD = "un-mot-de-passe-solide"
$env:YILGMDE_JWT_SECRET = "une-longue-chaine-aleatoire"
```
Linux / macOS :
```bash
export YILGMDE_ADMIN_EMAIL=admin@mairie.bf
export YILGMDE_ADMIN_PASSWORD=un-mot-de-passe-solide
export YILGMDE_JWT_SECRET=une-longue-chaine-aleatoire
```

### 2. Charger des données (facultatif)

```bash
python scripts/charger_exemples.py --ouaga   # démo : 12 arrondissements de Ouaga, 215 dépotoirs, 930 signalements
python scripts/charger_exemples.py           # ou le petit jeu de data/sample/ (2 zones)
```
Le jeu de Ouaga (`data/ouaga/`, licence ODbL) a un **découpage réel** (12 arrondissements et 55 secteurs relevés sur la carte de l'INSD) et la population réelle par arrondissement (recensement 2019) ; les dépotoirs et signalements sont inventés. Sources et limites : `data/ouaga/LISEZMOI.md`. Sans effet si la base est déjà remplie.

### 3. Démarrer

```bash
uvicorn backend.main:app --reload          # API : http://localhost:8000, documentation : http://localhost:8000/docs
cd frontend && npm run dev                 # interface : http://localhost:5173
```

### 4. Essayer (épreuve en direct)

Depuis http://localhost:8000/docs, après `POST /auth/login` avec le compte admin (bouton « Authorize ») :

1. `PUT /scenarios/1/parametres` avec `{"perimetre": {"arrondissements": [9]}}` : plan de l'arrondissement 9 (336 000 habitants, secteurs 37 à 40) en moins d'une seconde ; `GET /scenarios/1/plan/synthese` le donne en texte lisible.
2. `GET /points-regroupement` : les points du plan courant, chacun avec son explication.
3. `PUT /scenarios/1/parametres` avec `{"camions": [{"id": "camion_2", "disponible": false}]}` : le plan est recalculé sans ce camion ; ce qui n'est plus desservi est listé avec la raison.
4. `PUT /scenarios/1/parametres` avec `{"saison": "pluies"}` : plus de déchets, camions plus lents ; le budget de l'arrondissement est dépassé.
5. `POST /scenarios/1/simuler` avec `{"jours": 30, "graine": 42}` : évolution jour par jour (% collecté, dépotoirs actifs, coût).
6. `POST /scenarios` avec `{"nom": "budget serré", "parametres": {"mairie": {"budget_mensuel_xof": 300000}}}`, puis `GET /scenarios/comparer?ids=1,2` : comparaison côte à côte.

### Tests

```bash
python -m pytest -q
```
Environ 250 tests. Pour aller vite, lancez seulement le fichier concerné : `python -m pytest -q tests/test_plan.py`.

## Configuration

Tous les paramètres sont dans `config/`, **aucun n'est écrit dans le code** :

- `default.yaml` : paramètres génériques, valables pour n'importe quelle commune (production de déchets, capacités, camions, simulation…) ;
- `ouagadougou.yaml` : ce qui est propre à Ouaga (nom, dépôt des camions…), fusionné par-dessus ;
- un **scénario** surcharge ensuite quelques valeurs, sans modifier les fichiers.

Les valeurs marquées **`[H]`** sont des **hypothèses de départ**, sans source établie : à ajuster avec la mairie ou des données réelles.

| Variable d'environnement | Rôle | Par défaut |
|---|---|---|
| `YILGMDE_VILLE` | fichier `config/<ville>.yaml` à charger (vide : `default.yaml` seul) | `ouagadougou` |
| `YILGMDE_CONFIG_DIR` | dossier de configuration | `config/` |
| `YILGMDE_DB` | fichier de base SQLite | `data/processed/yilgmde.sqlite3` |
| `YILGMDE_UPLOADS` | dossier des photos (jamais publiques, ignoré par git) | `uploads/` |
| `YILGMDE_JWT_SECRET` | secret des jetons de connexion ; **obligatoire en production** (sinon les connexions expirent à chaque redémarrage) | secret aléatoire par processus |
| `YILGMDE_ADMIN_EMAIL`, `YILGMDE_ADMIN_PASSWORD`, `YILGMDE_ADMIN_NOM` | compte admin créé au démarrage s'il n'existe pas | — |

## Réutiliser pour une autre commune

Le moteur (`simulation/`) ne dépend ni de la base ni de Ouaga : ce sont des fonctions pures qui prennent des données et une configuration.

1. Copier `config/ouagadougou.yaml` en `config/<commune>.yaml` et l'adapter (nom, `collecte.depot`, camions, budget…).
2. Lancer avec `YILGMDE_VILLE=<commune>`.
3. Fournir ses zones (GeoJSON avec population) et ses dépotoirs, ou les laisser venir des signalements.

## Architecture

```
backend/        API FastAPI : routes, base SQLite, sécurité, stockage du plan et des scénarios
simulation/     moteur pur : demande (C1), points (C2), tournées (C3, C7), plan (C4), simulation (E1–E4)
config/         paramètres (default.yaml + <ville>.yaml)
data/sample/    données fictives et signalements piégés pour les tests
frontend/       interface React + Vite (carte Leaflet)
tests/          tests pytest
docs/           fonctionnalités, modèle de données, contrat d'API
```

Pour aller plus loin : `CONTEXT.md` (vue d'ensemble et règles de cohérence), `docs/api-contract.md` (toutes les routes), `docs/modele-donnees.md`, `DECISIONS.md` (choix techniques et hypothèses).

## Données et vie privée

- Les citoyens signalent **sans compte** ; un appareil est reconnu par un jeton anonyme.
- Les **visages et les plaques d'immatriculation sont floutés automatiquement** sur le serveur, et les métadonnées des photos (position GPS de l'appareil, modèle) supprimées, avant tout enregistrement.
- Les **photos et notes vocales ne sont jamais publiques** : seule l'administration les voit, pour vérifier.
- L'**export OpenStreetMap** ne contient que des étiquettes OSM (type de site, type de déchets, date), sans photo, ni contributeur, ni texte libre.
- Verser ces données dans OpenStreetMap est un **import** : il faut l'annoncer et le faire valider par la communauté OSM du Burkina, avec une licence compatible ODbL.

## Licence

Code : **MIT** (voir `LICENSE`, décision D16). Réutilisable librement, y compris par d'autres communes.

Données (signalements publiés, jeu de démonstration `data/ouaga/`, données dérivées d'OpenStreetMap) : **ODbL 1.0** (D40).

## Équipe

Christian (front-end), Faissal (back-end, moteur), Cramer (docs, données, présentation).
