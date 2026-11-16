# HANDOFF

> À remplir **uniquement** quand on change de conversation avec l'IA ou qu'on passe la main. Une section par personne. Écraser l'ancien contenu.

## Christian (front)

- **Objectif en cours** : afficher la carte des dépotoirs (Leaflet) dans le front React, alimentée par les données d'exemple.
- **Fichiers modifiés** : `frontend/` créé avec Vite + React ; `leaflet` et `react-leaflet` installés (`package.json`). Branche `front/init-react`.
- **Bugs ouverts** : aucun.
- **Prochaine étape précise** :
  1. créer `frontend/.env.example` (`VITE_API_URL`, `VITE_USE_MOCK=true`) ;
  2. copier les fichiers de `data/sample/` dans `frontend/public/mock/` ;
  3. créer `frontend/src/api/client.js` avec `getDepotoirs()` ;
  4. créer un composant `Carte.jsx` (MapContainer centré sur 12.3714, -1.5197, importer le CSS de Leaflet) ;
  5. y afficher les dépotoirs d'exemple, puis l'utiliser dans `App.jsx`.

## Faissal (back / moteur)

- **Objectif en cours** : A3 terminé (branche `back/moderation`) : le parcours citoyen → modération → carte publique fonctionne de bout en bout. Ensuite : zones, demande, points de regroupement (C1/C2), puis tournées (C3).
- **Fichiers modifiés** : `backend/routes/admin_signalements.py` (`GET /admin/signalements`, `GET .../photo`, `POST .../valider`, `POST .../rejeter`), `backend/schemas.py` (`ValiderEntree`, `RejeterEntree`, `DepotoirSortie`, `ResultatValidation` ; `SignalementAdmin` gagne `motif` et `depotoir_id`), `backend/main.py`, `docs/api-contract.md`, `tests/test_moderation.py` (29 tests, 120 au total), `TODO.md`, `DECISIONS.md` (D22).
- **État des PR** : la #8 (auth) a été fusionnée dans `back/signalements`, pas dans `main`. Il faut fusionner la **#7** pour que A1 et l'authentification arrivent dans `main`. La PR de A3 vise `main` : elle contient A1 et l'authentification tant que la #7 n'est pas fusionnée.
- **Bugs ouverts** : aucun. Pas de limitation des tentatives de connexion. Pas de retrait des métadonnées EXIF des photos (A7, P2). L'alerte `volume_aberrant` n'est pas implémentée. `contributeur.score_confiance` n'est jamais mis à jour : valider ou rejeter pourrait l'ajuster pour que l'alerte `appareil_peu_fiable` serve vraiment.
- **Pour lancer en local** : `YILGMDE_ADMIN_EMAIL`, `YILGMDE_ADMIN_PASSWORD` (premier admin), `YILGMDE_JWT_SECRET`, puis `uvicorn backend.main:app --reload`. Parcours : `POST /signalements` (en-tête `X-Device-Token`) → `POST /auth/login` → `POST /admin/signalements/{id}/valider` → `GET /depotoirs`.
- **Prochaine étape précise** :
  1. zones : chargement des polygones et de la population depuis `data/` (table `zone`), rattachement d'un dépotoir à sa zone à la validation ;
  2. C1 : estimation de la demande par zone (population × `production_dechets_kg_hab_jour` × coefficient de saison), fonction pure dans `simulation/` ;
  3. C2 : points de regroupement (scikit-learn, `capacite_kg` et `distance_max_a_pied_m` de la config) ;
  4. script `scripts/charger_exemples.py` pour remplir `depotoir` avec `data/sample/`.

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
