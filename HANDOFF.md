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

- **Objectif en cours** : A1 terminé (branche `back/signalements`) : le citoyen peut signaler et suivre. A2 était déjà sur `main` (PR #4). Ensuite : modération admin (A3), avec connexion JWT (F1/F2) en prérequis.
- **Fichiers modifiés** : `backend/routes/signalements.py` (`POST /signalements`, `GET /signalements/suivi/{code}`), `backend/routes/depotoirs.py` (`GET /depotoirs` en GeoJSON, filtres `statut` et `zone_id`), `backend/deps.py` (verrou d'accès à la base), `backend/main.py` (routeurs branchés), `config/default.yaml` (`photo_taille_max_mo` [H]), `tests/test_routes_publiques.py` (21 tests), `TODO.md`, `DECISIONS.md` (D20).
- **Bugs ouverts** : aucun. 60 tests passent. Limites connues : les photos sont enregistrées dans `uploads/` mais aucune route ne les sert encore (à faire avec A3, derrière le rôle admin) ; pas de retrait des métadonnées EXIF (A7, P2) ; l'alerte `volume_aberrant` du modèle de données n'est pas implémentée.
- **Prochaine étape précise** :
  1. F1/F4 : `POST /auth/login` (JWT, `pyjwt` + `bcrypt`), `GET /auth/moi`, `POST /admin/utilisateurs`, et une dépendance qui vérifie le rôle côté serveur (F2) ;
  2. A3 : `GET /admin/signalements`, `POST /admin/signalements/{id}/valider` (création ou fusion dans un dépotoir, détection de réapparition B5, écriture dans `journal_audit`) et `/rejeter` ;
  3. servir les photos aux admins ;
  4. script `scripts/charger_exemples.py` pour remplir `depotoir` avec `data/sample/` (la carte de Christian pourra alors quitter le mode mock).

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
