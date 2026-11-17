# HANDOFF

> À remplir **uniquement** quand on change de conversation avec l'IA ou qu'on passe la main. Une section par personne. Écraser l'ancien contenu.

# HANDOFF (Christian, front)

**Objectif en cours** : mode hors ligne (file d'attente IndexedDB), puis PWA.

**Fait (branche `front/design-moderne`)**
- Carte Leaflet (dépotoirs + signalements de test, légende), proxy Vite `/api`, mode mock (`VITE_USE_MOCK`).
- Identité visuelle, accueil, en-tête, drapeau BF, `src/config/projet.js` (nom « Yilgamdé »).
- `/signaler` : position (clic, glisser, GPS), pictogrammes type et volume, note vocale (`EnregistreurVocal`), envoi, écran de confirmation avec code ou motif de rejet.
- `/suivi` : suivi par code.
- Hors ligne (à tester) : `src/api/fileAttente.js`, `signalerAvecFile`, `viderFile`, `BandeauReseau`.
- PR contrat `docs/api-audio` (note_vocale, X-Device-Token) ouverte.
- Pages Laabal (2 colonnes en grand écran), Chauffeur, Plan, routes et client API commités en local sur front/design-moderne. Push en attente : réseau coupé le 17/11 vers 11h45.
- viderFile : envoie id_client (= clé de file) et capture_le ; garde l'élément sur 429/503 et coupure réseau, le retire sur 200/201 et sur erreur définitive (413/422). Étape 2 sur 3.
- File d'attente conforme au contrat (3/3) : id_client et capture_le fixés dès le premier essai (nouvelleCle, ajouter accepte clé et date) ; seules 400/413/422 retirent l'élément, tout le reste le garde (aReessayer / estDefinitive).

**Bugs ouverts** : ucun connu ; hors ligne testé seulement avec la file, pas encore avec l'API.

**À vérifier**
- Orthographe du nom (Yilgamdé ou autre).
- Contrat : `GET /signalements` n'existe pas ; la couche « Signalements (test) » de la carte devra passer côté admin.
- Décision photo : masquage visages/plaques, ou pas de photo au MVP (D23).

**Prochaine étape**
0. Hors ligne : test complet avec l'API de Faissal (201 retire l'élément, deja_recu sur 200). P2 : montrer au citoyen les refus définitifs (413/422), respecter Retry-After, floutage des photos sur le téléphone, vérifier le message affiché par Signaler.jsx quand le serveur répond 429/503.
1. Tester le hors ligne (F12 > Network > Offline, avec `VITE_USE_MOCK=false`).
2. PWA : manifeste et service worker.
3. Connexion (`/auth/login`) et vue admin : modération.
4. Tableau de bord des scénarios, tournées sur la carte.