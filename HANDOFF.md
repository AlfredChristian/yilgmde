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

- **Objectif en cours** : F1/F2/F4 terminés (branche `back/auth`, empilée sur `back/signalements` / PR #7). Ensuite : modération admin (A3) et cycle de vie du dépotoir (B5/B6).
- **Fichiers modifiés** : `backend/securite.py` (bcrypt, JWT, dépendances `utilisateur_courant` et `exiger_role(Role...)`), `backend/utilisateurs.py` (`creer_utilisateur`, `creer_admin_si_absent`, `journaliser`), `backend/routes/auth.py` (`POST /auth/login`, `GET /auth/moi`), `backend/routes/admin_utilisateurs.py` (`POST` et `GET /admin/utilisateurs`), `backend/schemas.py` (`UtilisateurAdmin`, validation email et mot de passe), `config/default.yaml` (`securite.duree_token_min` [H]), `docs/api-contract.md`, `tests/test_auth.py` (31 tests, 91 au total), `TODO.md`, `DECISIONS.md` (D21).
- **Bugs ouverts** : aucun. Pas de limitation des tentatives de connexion (à faire si le temps le permet). Les photos de signalements ne sont servies par aucune route.
- **Pour lancer en local** : définir `YILGMDE_ADMIN_EMAIL` et `YILGMDE_ADMIN_PASSWORD` (et `YILGMDE_JWT_SECRET` pour garder les connexions entre redémarrages), puis `uvicorn backend.main:app --reload`.
- **Prochaine étape précise** :
  1. A3 : `GET /admin/signalements?statut=` (alertes, score, `photo_url`) protégé par `exiger_role(Role.admin)` ;
  2. `POST /admin/signalements/{id}/valider` (`fusionner_avec` nul : crée un dépotoir `actif`, sinon fusion dans le dépotoir existant ; si celui-ci est `eradique` ou `sous_surveillance`, repasse à `actif` et `nb_reapparitions` +1, règle B5) et `POST /admin/signalements/{id}/rejeter` (motif obligatoire) ; chaque action écrite via `journaliser` ;
  3. route admin qui sert les photos ;
  4. script `scripts/charger_exemples.py` pour remplir `depotoir` avec `data/sample/`.

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
