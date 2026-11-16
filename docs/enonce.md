# Énoncé — Hackathon des Universités 2026 · Finale

> Transcription de la capture du sujet. **À vérifier par Cramer contre le sujet officiel** avant de s'y fier à la lettre.

**Thème de l'année : l'Open Source.** Proposition à valider par le jury.
16 finalistes · 8 équipes par sujet.

## Deux challenges pour la finale

### 01 — Assainissement de Ouaga *(notre challenge)*

Un outil libre d'aide à la décision, du signalement des dépotoirs sauvages jusqu'au plan de gestion de la ville, avec simulation de tous les acteurs.

**Ce que l'outil fait**
- Cartographie des dépotoirs et signalements vérifiés
- Plan de gestion : emplacement des points de regroupement, tournées optimisées
- Simulation multi-agents : ménages, pré-collecteurs, brigade Laabal, mairie
- Paramètres modifiables et mis à jour (population, abonnements, camions, fréquences, budget) pour comparer des scénarios

**Données**
Carte ouverte (OpenStreetMap, Open Buildings), signalements collectés par chaque équipe dans son secteur, paramètres de départ fixés avec la mairie. Le jury garde un jeu de test caché.

**Épreuve en direct**
Le jury injecte des signalements piégés, puis change les paramètres (camions en panne, saison des pluies, nouveau quartier). Le plan doit se recalculer et rester cohérent.

**Bien commun**
La première carte ouverte des dépotoirs de Ouaga, versée dans OpenStreetMap, et un simulateur réutilisable par d'autres communes.

*Tags : Cartographie · Optimisation · Simulation multi-agents · Mobile*

### 02 — « Dites-le-nous une fois » *(pour information)*

Faire circuler les pièces entre administrations plutôt que les usagers entre les guichets, dans le respect de leurs droits sur leurs données.

**Données** : registres simulés fournis par le jury (état civil, nationalité, casier), peuplés de citoyens fictifs.
**Épreuve en direct** : ne transmettre que l'utile (« majeur : oui »), montrer à l'usager qui a consulté ses données, et tenir quand un registre tombe en panne.
**Bien commun** : un socle d'interopérabilité libre, avec ses règles de consentement et de traçabilité, réutilisable par l'administration.

*Tags : Back-end · Architecture · Sécurité*
