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

- **Objectif en cours** : nouveaux livrables du 2026-11-17 (voir `TODO.md`). L1 côté serveur fusionné (PR #19, D36). Fait sur `back/arrondissement` : L3 côté serveur (périmètre de scénario, `/arrondissements`, synthèse Markdown, D37). Ensuite : L4 (données réalistes + jeu GeoJSON ODbL), puis L2 et L5 (paramètres documentés, chiffres du rapport).
- **Fichiers modifiés** : `backend/masquage.py` (nouveau), `backend/routes/signalements.py` (`id_client`, `capture_le`, `note_vocale`, masquage), `backend/routes/admin_signalements.py` (`/note-vocale`, champs ajoutés), `backend/routes/terrain.py` (photos d'intervention masquées), `backend/verification.py` (limite comptée à la prise de vue), `backend/db.py` (4 colonnes + index unique), `backend/schemas.py`, `config/default.yaml` (`hors_ligne:`, `masquage:`), `requirements.txt` (`opencv-python-headless<5`), tests `test_masquage.py`, `test_hors_ligne.py`, fixture `tests/fixtures/portrait_domaine_public.jpg` (NASA, domaine public) ; suite complète : **282 verts**.
- **Bugs ouverts / limites** : cascades de Haar imparfaites (visages de trois quarts ou petits, plaques inclinées) : le masquage sur le téléphone reste utile ; durée des notes vocales non vérifiée (taille seulement). **Christian** : la file d'attente (`frontend/src/api/fileAttente.js`) doit envoyer `id_client` (sa `cle`) et `capture_le` (son `creeLe` en ISO), et garder l'élément sur `429` et `503` (voir `docs/api-contract.md`).
- **Pour lancer avec des données** : `pip install -r requirements.txt` (OpenCV ajouté), `python scripts/charger_exemples.py`, `uvicorn backend.main:app --reload` ; envoyer un signalement avec une photo de personne : la réponse donne `photo_masquee`, et `GET /admin/signalements/{id}/photo` montre la version floutée.
- **Prochaine étape précise** :
  1. L3 fait (back) : `perimetre`, `GET /arrondissements`, `GET /scenarios/{id}/plan/synthese` ; Christian branche le tableau de bord dessus ;
  2. L4 : 12 arrondissements réalistes (population RGPH 2019, contours approximatifs), paramètres sourcés, jeu de signalements fictifs réalistes, export public ODbL ;
  3. L2/L5 : `docs/parametres.md` généré depuis `config/default.yaml`, script `scripts/resultats_scenarios.py` pour le rapport.

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
