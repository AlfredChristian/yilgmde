# HANDOFF

> À remplir **uniquement** quand on change de conversation avec l'IA ou qu'on passe la main. Une section par personne. Écraser l'ancien contenu.

# HANDOFF (Christian, front)

**Branche** : `front/design-moderne` (à jour sur GitHub).

**Fait**
- Carte, légende (couleurs dans `config/couleurs.js`), proxy `/api`, mode mock.
- Accueil, en-tête, modèle de cartes, drapeau BF.
- `/signaler` (position, pictogrammes, note vocale), `/suivi`.
- Hors ligne : file IndexedDB avec `id_client` et `capture_le`, PWA.
- Connexion, routes protégées, `/admin` (modération), `/admin/plan`, `/chauffeur`, `/laabal`.

**À faire**
1. `npm run build`, puis PR vers `main`.
2. Vérifier le contrat (`id_client`, `capture_le`, `note_vocale`, `X-Device-Token`).
3. Comparaison de scénarios (D6).
4. Masquage visages/plaques (D23, à décider).
5. Brancher les routes réelles `/chauffeur/*` et `/laabal/*` avec Faissal (noms marqués [H]).