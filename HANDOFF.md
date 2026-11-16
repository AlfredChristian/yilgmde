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

**Bugs ouverts**: aucun

**Décisions à noter dans DECISIONS.md (si pas déjà fait)**
- D17 React + Vite + Leaflet (Retenu) ; D19 mode mock (Retenu).
- D20 : police installée via npm (hors ligne), palette verte + jaune, rouge réservé aux dépotoirs actifs.

**À vérifier / en suspens**
- Orthographe du nom : j'ai mis « Yilgamdé » (confirmer avec l'équipe ; sinon changer `NOM` dans `src/config/projet.js`). Remplacer le nom affiché dans README, DECISIONS, TODO et `frontend/index.html` (`<title>`), sans renommer le dépôt ni les dossiers.
- Demandes de Christian : pas d'emojis, drapeau du Burkina en haut à droite (fait), style inspiré de Sherbrooke sans copie.
- TODO : ajouter « Identité visuelle et page d'accueil attrayante » (P1) ; découper la tâche front « framework / Leaflet / proxy » (framework et Leaflet faits).

**Prochaine étape précise**
1. Corriger l'import, vérifier `/` et `/carte`, commit, PR relue par Faissal ou Cramer.
2. Légende de la carte (rouge actif, vert éradiqué ; signalements orange, violet, gris).
3. Formulaire de signalement mobile (A1) : position GPS ajustable, type, volume, photo ; page `/signaler`.
4. Vérifier dans `docs/api-contract.md` la route et le droit d'accès pour `GET /signalements` (probablement admin).
5. Plus tard : connexion et vues par rôle, panneau de paramètres, tournées sur la carte.

## Faissal (back / moteur)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
