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

- **Objectif en cours** : sécurité de la connexion et score de confiance faits (branche `back/securite-login`). `main` contient tout le back P1 : signalements et modération (A1–A3), plan (C1–C4, C7), scénarios et comparaison (D1–D4, D6), terrain (C6, H1–H3), simulation (E1–E4), export OSM (G1).
- **Fichiers modifiés** : `backend/limitation.py` (D32), `backend/routes/auth.py`, `backend/main.py` (limiteurs remis à zéro au démarrage), `backend/confiance.py` (D33), `backend/routes/admin_signalements.py`, `config/default.yaml` (`securite:` et `verification:`), `tests/test_limitation.py` (9 tests), `tests/test_confiance.py` (4 tests) ; suite complète : **249 verts**. Docs : `docs/api-contract.md`, `DECISIONS.md` (D32, D33), `TODO.md`.
- **Bugs ouverts / limites** : compteurs de connexion en mémoire (un seul processus ; remis à zéro au redémarrage) ; derrière un proxy, l'IP vue est celle du proxy (à traiter si déploiement derrière nginx). À valider : étiquettes OSM et licence des données (D16, D30), `collecte.depot`, coefficients [H] de simulation.
- **Pour lancer avec des données** : `python scripts/charger_exemples.py`, `uvicorn backend.main:app --reload`. Essai : 5 mauvais mots de passe sur `POST /auth/login` → `429` avec `Retry-After`.
- **Prochaine étape précise** :
  1. P2 : `/laabal/constats` (amende réelle, preuves en multipart, table à créer), passage `classe` et saisie d'un site officiel par l'admin (B5/B6) ;
  2. A4 : import par lot de signalements (GeoJSON/CSV) passant par la même vérification (A2) ;
  3. aider Christian à brancher le front sur les routes du plan, de la simulation et de la comparaison ;
  4. README (installation, lancement, licence) avant la démo.

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
