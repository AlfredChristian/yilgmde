# HANDOFF

> À remplir **uniquement** quand on change de conversation avec l'IA ou qu'on passe la main. Une section par personne. Écraser l'ancien contenu.

## Christian (front)

**Objectif en cours** : finir l'habillage visuel du front (inspiré du site de la ville de Sherbrooke : bandeau vert, grille de services, bande de cartes sombres, pied de page sobre), puis le formulaire de signalement.

**Fait (branche `front/init-react`)**
- React + Vite + Leaflet/react-leaflet ; carte de Ouaga avec 2 couches (dépotoirs vérifiés, signalements de test) via `LayersControl`.
- `src/api/client.js` : `getDepotoirs()`, `getSignalements()` ; mode mock (`VITE_USE_MOCK=true`, fichiers dans `public/mock/`) ou API.
- Proxy Vite `/api` vers `http://localhost:8000` ; testé avec `uvicorn backend.main:app --reload` (lancé depuis la racine).
- Identité : palette verte (variables dans `src/index.css`), police Poppins via `@fontsource`, routage `react-router-dom`.
- Composants : `Entete`, `Icone` (SVG au trait), `DrapeauBF` ; pages : `Accueil` ; config : `src/config/projet.js` (nom + slogan).
- Légende branchée dans Carte.jsx, couleurs lues depuis config/couleurs.js (vérifié sur /carte).
**Bugs ouverts**: aucun

**Décisions à noter dans DECISIONS.md (si pas déjà fait)**
- D17 React + Vite + Leaflet (Retenu) ; D19 mode mock (Retenu).
- D20 : police installée via npm (hors ligne), palette verte + jaune, rouge réservé aux dépotoirs actifs.

**À vérifier / en suspens**
- Orthographe du nom : j'ai mis « Yilgamdé » (confirmer avec l'équipe ; sinon changer `NOM` dans `src/config/projet.js`). Remplacer le nom affiché dans README, DECISIONS, TODO et `frontend/index.html` (`<title>`), sans renommer le dépôt ni les dossiers.
- Demandes de Christian : pas d'emojis, drapeau du Burkina en haut à droite (fait), style inspiré de Sherbrooke sans copie.
- TODO : ajouter « Identité visuelle et page d'accueil attrayante » (P1) ; découper la tâche front « framework / Leaflet / proxy » (framework et Leaflet faits).
- Le remote est passé en HTTPS (le SSH n'arrivait pas à résoudre github.com sur ma machine). Garder HTTPS.

**Prochaine étape précise**
1. PR `front/init-react` ouverte, en attente de relecture par Faissal ou Cramer. `chore/regles-de-travail` est fusionnée, `main` fusionné dans la branche (conflit DECISIONS.md résolu).
2. Ouvrir la PR front/legende-carte une fois front/init-react fusionnée.
3. Formulaire de signalement mobile (A1) : position GPS ajustable, type, volume, photo ; page `/signaler`.
4. Vérifier dans `docs/api-contract.md` la route et le droit d'accès pour `GET /signalements` (probablement admin).
5. Plus tard : connexion et vues par rôle, panneau de paramètres, tournées sur la carte.

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
