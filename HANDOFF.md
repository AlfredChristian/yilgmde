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

- **Objectif en cours** : A2 terminé (branche `back/verification`). Ensuite : `POST /signalements` et `GET /depotoirs` (A1).
- **Fichiers modifiés** : `backend/verification.py` (`verifier`, `contexte_depuis_db`, `distance_m`), `config/default.yaml` (pénalités de score `[H]`), `tests/test_verification.py` (25 tests), `TODO.md`, `DECISIONS.md` (D19).
- **Bugs ouverts** : aucun. `fastapi`, `httpx`, `bcrypt`, `shapely` absents de l'environnement de travail de l'IA (réseau coupé) : `tests/test_db.py` n'y a pas été relancé, les tests de vérification et de config passent.
- **Prochaine étape précise** :
  1. `backend/routes/signalements.py` : `POST /signalements` (multipart, en-tête `X-Device-Token`). Créer ou retrouver le `contributeur`, appeler `contexte_depuis_db` puis `verifier`, générer `code_suivi` (format `K7M-4QD`), insérer le signalement avec `statut`, `motif`, `score_auto`, `alertes` (JSON), incrémenter `nb_signalements` ;
  2. `GET /signalements/suivi/{code}` ;
  3. `GET /depotoirs` en GeoJSON (seuls les `verifie`, contrat d'API) ;
  4. brancher le routeur dans `main.py`, tests avec `TestClient`.

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
