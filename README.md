# yilgmde

Outil libre d'aide à la décision pour l'assainissement de Ouagadougou, du signalement des dépotoirs sauvages jusqu'au plan de gestion de la ville, avec simulation des acteurs.

Projet du **Hackathon des Universités 2026 — Finale**, Challenge 01 « Assainissement de Ouaga » (thème : l'Open Source).

## Ce que fait l'outil

- **Carte ouverte des dépotoirs** : signalements citoyens (sans compte), vérifiés par la mairie.
- **Plan de gestion** : points de regroupement et tournées de collecte optimisés.
- **Brigade Laabal** : tournées d'éradication des dépotoirs illégaux, surveillance, constats.
- **Simulation multi-agents** : ménages, pré-collecteurs, brigade Laabal, mairie.
- **Scénarios** : paramètres modifiables (camions, budget, fréquences, saison…) avec recalcul du plan.

## Installation

Prérequis : Python 3.11+ et Node.js 20+.

### Back-end

Windows (PowerShell) :
```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Linux / macOS :
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

L'API tourne sur http://localhost:8000 (documentation interactive : http://localhost:8000/docs).

### Front-end

```bash
cd frontend
npm install
npm run dev
```

## Configuration

Les paramètres sont dans `config/` : `default.yaml` (générique) et `ouagadougou.yaml` (propre à Ouaga). Les valeurs marquées `[H]` sont des hypothèses à ajuster.

## Réutiliser pour une autre commune

Le moteur (`simulation/`) est indépendant des données de Ouaga. Pour une autre commune : remplacer `config/ouagadougou.yaml` et fournir ses propres données (zones, signalements).

## Organisation du dépôt

Voir `CONTEXT.md` (vue d'ensemble), `docs/` (fonctionnalités, modèle de données, contrat d'API), `DECISIONS.md` (choix techniques).

## Licence

Code : Apache-2.0 (à confirmer, voir `DECISIONS.md`). Données dérivées d'OpenStreetMap : ODbL.

## Équipe

Christian, Faissal, Cramer.
