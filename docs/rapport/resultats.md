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
| Base | 100,0 % | 60,2 % | 240 | 13 | 2 497 | 18,8 | 25,1 | 0,5 s |
| Pluies | 100,0 % | 55,2 % | 240 | 15 | 2 767 | 21,2 | 25,1 | 0,4 s |
| Panne | 77,5 % | 60,2 % | 240 | 10 | 1 750 | 13,6 | 25,1 | 0,5 s |
| Sensibilisation | 100,0 % | 70,3 % | 240 | 13 | 2 497 | 18,8 | 25,1 | 0,5 s |
| Abonnements | 100,0 % | 71,6 % | 240 | 13 | 2 497 | 18,8 | 25,1 | 0,5 s |
| Budget ÷ 2 | 100,0 % | 60,2 % | 240 | 13 | 2 497 | 18,8 | 12,5 | 0,4 s |

## Simulation sur 30 jours

| Scénario | Part captée moyenne | Déchets sauvages | Nouveaux dépotoirs | Dépotoirs actifs (début → fin) | Éradications (cumul) | Passages faits / annulés | Coût (M XOF) | Amendes (XOF) |
|---|---|---|---|---|---|---|---|---|
| Base | 68,3 % | 1 921 t | 21 | 25 → 6 | 73 | 8 / 0 | 17,3 | 290 k |
| Pluies | 64,1 % | 2 390 t | 24 | 25 → 7 | 84 | 8 / 0 | 19,6 | 270 k |
| Panne | 59,4 % | 2 462 t | 25 | 25 → 6 | 78 | 8 / 0 | 12,5 | 300 k |
| Sensibilisation | 75,6 % | 1 475 t | 10 | 25 → 5 | 56 | 8 / 0 | 17,3 | 240 k |
| Abonnements | 76,4 % | 1 427 t | 10 | 25 → 5 | 56 | 8 / 0 | 17,3 | 240 k |
| Budget ÷ 2 | 60,2 % | 2 409 t | 27 | 25 → 6 | 84 | 5 / 3 | 10,8 | 370 k |

Lecture : plus il reste de déchets sauvages, plus il apparaît de **nouveaux dépotoirs** (probabilité lissée et plafonnée, D48, calibrée pour Ouaga en D50). Le nombre de dépotoirs **actifs** en fin de période varie peu : les brigades Laabal de la commune (12 éradications par jour) suffisent à traiter un arrondissement. Sur toute la commune, elles deviendraient la contrainte.

Courbes : `courbes_part_captee.png`, `courbes_dechets_sauvages.png`, `courbes_cout.png`. Plan de base détaillé : `plan_de_gestion.md`, carte : `carte_plan.png`.

Les hypothèses `[H]` sont listées dans `docs/parametres.md` ; les sources dans `data/ouaga/LISEZMOI.md`.
