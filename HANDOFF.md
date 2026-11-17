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

**Bugs ouverts** : aucun connu. Hors ligne non encore testé.

**À vérifier**
- Orthographe du nom (Yilgamdé ou autre).
- Contrat : `GET /signalements` n'existe pas ; la couche « Signalements (test) » de la carte devra passer côté admin.
- Décision photo : masquage visages/plaques, ou pas de photo au MVP (D23).

**Prochaine étape**
1. Tester le hors ligne (F12 > Network > Offline, avec `VITE_USE_MOCK=false`).
2. PWA : manifeste et service worker.
3. Connexion (`/auth/login`) et vue admin : modération.
4. Tableau de bord des scénarios, tournées sur la carte.