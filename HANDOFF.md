# HANDOFF

> À remplir **uniquement** quand on change de conversation avec l'IA ou qu'on passe la main. Écraser l'ancien contenu.

## État au 2026-11-18 (version 1.0)

**L'application est terminée et gelée.** Toutes les branches sont fusionnées dans `main` ; on ne change plus le code sauf correctif.

**Ce qui marche, vérifié de bout en bout** (navigateur, téléphone Android et PC Windows de l'équipe) :
- signalement citoyen sans compte, hors ligne compris, photo masquée sur le téléphone puis sur le serveur, note vocale (https) ;
- vérification automatique et modération, suivi par code, zoom sur le dépotoir depuis le suivi ;
- plan de gestion par arrondissement ou commune (points, tournées sur les voies OSM, coût expliqué), PDF ;
- scénarios, simulation sur 30 jours, comparaison, simulation d'un quartier ;
- espaces chauffeur (tournée, arrêts, panne) et brigade Laabal (camion animé, suivi de l'éradication) ;
- suivi de la flotte ; gestion des comptes ; logo partout (D66) ; cartes animées sans clignotement (D67).

**Lancer** : `powershell -ExecutionPolicy Bypass -File scripts\lancer_demo.ps1` (Windows) ou la section « Démarrer » du README. Comptes dans le README.

**Tests** : `python -m pytest -q`, 355 verts ; `cd frontend && npm run build` sans avertissement.

**Limites connues** (à dire au jury si la question vient) :
- découpage des arrondissements relevé à la main sur la carte INSD ; secteurs approchés (Voronoï) ;
- dépotoirs et signalements de démo inventés ; parts des ménages estimées par l'équipe (D63) ;
- sur 30 jours, le nombre de dépotoirs actifs réagit peu aux scénarios ;
- fond « Satellite » d'Esri affiché mais pas ouvert (retirable).

**Reste à faire (hors code)** :
1. rapport (L5) à partir de `docs/rapport/` ;
2. scénario et tournage de la vidéo de 3 minutes (L6) ;
3. répétition chronométrée du pitch.
