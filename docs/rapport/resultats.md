# Résultats des scénarios — arrondissement 9 de Ouagadougou

Généré par `scripts/resultats_scenarios.py` le 2026-11-17 : jeu `data/ouaga/`, config de Ouagadougou, simulation de 30 jours, graine 42. Arrondissement 9 : 336 483 habitants (RGPH 2019), secteurs 37 à 40. Relancer donne les mêmes chiffres.

## Scénarios

| Scénario | Ce qui change |
|---|---|
| Base | Paramètres de Ouagadougou, saison sèche |
| Pluies | Saison des pluies : +10 % de déchets, camions 30 % plus lents, moins d'apport volontaire |
| Panne | 60 camions sur 70 indisponibles (il en reste 10) |
| Sensibilisation | Apport volontaire aux points porté de 60 % à 80 % |
| Abonnements | Abonnement aux pré-collecteurs porté de 30 % à 50 % des ménages |
| Budget ÷ 2 | Budget mensuel de la commune réduit de moitié (90 000 000 XOF) |

## Plan de gestion (un passage de collecte)

- **Capacité de collecte** : part du stock des points que les camions peuvent vider.
- **Part captée estimée** : part des déchets produits qui arrive aux points (pré-collecte + apport volontaire).

| Scénario | Capacité de collecte | Part captée estimée | Points | Camions utilisés | Distance (km) | Coût mensuel (M XOF) | Budget de l'arr. (M XOF) | Calcul |
|---|---|---|---|---|---|---|---|---|
| Base | 100,0 % | 60,2 % | 240 | 13 | 2 497 | 18,8 | 25,1 | 0,4 s |
| Pluies | 100,0 % | 55,2 % | 240 | 15 | 2 767 | 21,2 | 25,1 | 0,4 s |
| Panne | 77,5 % | 60,2 % | 240 | 10 | 1 750 | 13,6 | 25,1 | 0,4 s |
| Sensibilisation | 100,0 % | 70,3 % | 240 | 13 | 2 497 | 18,8 | 25,1 | 0,3 s |
| Abonnements | 100,0 % | 71,6 % | 240 | 13 | 2 497 | 18,8 | 25,1 | 0,4 s |
| Budget ÷ 2 | 100,0 % | 60,2 % | 240 | 13 | 2 497 | 18,8 | 12,5 | 0,4 s |

## Simulation sur 30 jours

| Scénario | Part captée moyenne | Déchets sauvages | Dépotoirs actifs (début → fin) | Éradications (cumul) | Passages faits / annulés | Coût (M XOF) | Amendes (XOF) |
|---|---|---|---|---|---|---|---|
| Base | 68,3 % | 1 921 t | 25 → 5 | 210 | 8 / 0 | 17,3 | 650 k |
| Pluies | 64,3 % | 2 382 t | 25 → 5 | 210 | 8 / 0 | 19,6 | 650 k |
| Panne | 59,4 % | 2 457 t | 25 → 5 | 210 | 8 / 0 | 12,5 | 650 k |
| Sensibilisation | 75,6 % | 1 477 t | 25 → 5 | 210 | 8 / 0 | 17,3 | 650 k |
| Abonnements | 76,4 % | 1 429 t | 25 → 5 | 210 | 8 / 0 | 17,3 | 650 k |
| Budget ÷ 2 | 62,4 % | 2 276 t | 25 → 5 | 210 | 5 / 3 | 10,8 | 650 k |

Les dépotoirs suivent le même chemin dans tous les scénarios : dès qu'une zone produit des déchets sauvages au-delà de `seuil_nouveau_depotoir_kg`, un nouveau dépotoir y apparaît chaque jour (c'est le cas des 4 secteurs dans tous les scénarios), et les brigades Laabal, dont la capacité dépasse ces apparitions, ne dépendent pas des camions. L'effet des scénarios se lit donc sur les tonnes de déchets sauvages, pas sur le nombre de dépotoirs.

Courbes : `courbes_part_captee.png`, `courbes_dechets_sauvages.png`, `courbes_cout.png`. Plan de base détaillé : `plan_de_gestion.md`, carte : `carte_plan.png`.

Les hypothèses `[H]` sont listées dans `docs/parametres.md` ; les sources dans `data/ouaga/LISEZMOI.md`.
