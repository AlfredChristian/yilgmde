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

- **Objectif en cours** : socle du back-end terminé sur la branche `back/socle` (config, SQLite, schémas). Ensuite : signalements (A1, A2).
- **Fichiers modifiés** : `backend/config.py` (fusion default + ville + surcharges, fusion des camions par `id`), `backend/db.py` (schéma SQLite complet), `backend/schemas.py` (énumérations, signalements, auth), `backend/main.py` (config et base au démarrage), `requirements.txt` (python-multipart, pyjwt, bcrypt, pytest, httpx), `tests/` (16 tests).
- **Bugs ouverts** : aucun. Avertissement de test sans gravité sur `httpx` et `starlette.testclient`.
- **Prochaine étape précise** : écrire `backend/verification.py` (A2 : doublon dans `verification.rayon_doublon_m`, hors `zone_etude.bbox`, position incohérente, limite `max_signalements_par_appareil_heure`, score et motif lisible), avec ses tests, puis `POST /signalements` et `GET /depotoirs`.

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
