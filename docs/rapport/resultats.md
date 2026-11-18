# Résultats des scénarios — arrondissement 9 de Ouagadougou

Généré par `scripts/resultats_scenarios.py` le 2026-11-18 : jeu `data/ouaga/`, config de Ouagadougou, simulation de 30 jours, graine 42. Arrondissement 9 : 336 483 habitants (RGPH 2019), secteurs 37 à 40. Relancer donne les mêmes chiffres.

## Scénarios

| Scénario | Ce qui change |
|---|---|
| Base | Paramètres de Ouagadougou, saison sèche |
| Pluies | Saison des pluies : +10 % de déchets, camions 30 % plus lents, moins d'apport volontaire |
| Panne | 60 camions sur 70 indisponibles (il en reste 10) |
| Sensibilisation | Apport volontaire aux points porté de 23 % à 50 % des non-abonnés proches d'un point |
| Abonnements | Abonnement aux pré-collecteurs porté de 35 % à 50 % des ménages |
| Budget ÷ 2 | Budget mensuel de la commune réduit de moitié (90 000 000 XOF) |

## Plan de gestion (un passage de collecte)

- **Capacité de collecte** : part du stock des points que les camions peuvent vider.
- **Part captée estimée** : part des déchets produits qui arrive aux points (pré-collecte + apport volontaire).

| Scénario | Capacité de collecte | Part captée estimée | Points | Camions utilisés | Distance (km) | Coût mensuel (M XOF) | Budget de l'arr. (M XOF) | Calcul |
|---|---|---|---|---|---|---|---|---|
| Base | 100,0 % | 47,9 % | 228 | 13 | 2 478 | 18,5 | 25,1 | 9,1 s |
| Pluies | 100,0 % | 45,8 % | 228 | 14 | 2 686 | 20,2 | 25,1 | 3,8 s |
| Panne | 80,2 % | 47,9 % | 228 | 10 | 1 850 | 14,0 | 25,1 | 3,7 s |
| Sensibilisation | 100,0 % | 63,1 % | 228 | 13 | 2 478 | 18,5 | 25,1 | 3,9 s |
| Abonnements | 100,0 % | 60,0 % | 228 | 13 | 2 478 | 18,5 | 25,1 | 3,8 s |
| Budget ÷ 2 | 100,0 % | 47,9 % | 228 | 13 | 2 478 | 18,5 | 12,5 | 3,9 s |

## Simulation sur 30 jours

| Scénario | Part captée moyenne | Déchets sauvages | Nouveaux dépotoirs | Dépotoirs actifs (début → fin) | Éradications (cumul) | Passages faits / annulés | Coût (M XOF) | Amendes (XOF) |
|---|---|---|---|---|---|---|---|---|
| Base | 60,6 % | 2 388 t | 22 | 25 → 5 | 87 | 8 / 0 | 17,1 | 300 k |
| Pluies | 58,6 % | 2 757 t | 29 | 25 → 6 | 85 | 8 / 0 | 18,7 | 290 k |
| Panne | 53,6 % | 2 811 t | 18 | 25 → 5 | 75 | 8 / 0 | 12,9 | 320 k |
| Sensibilisation | 70,3 % | 1 798 t | 16 | 25 → 5 | 62 | 8 / 0 | 17,1 | 270 k |
| Abonnements | 68,3 % | 1 918 t | 18 | 25 → 6 | 70 | 8 / 0 | 17,1 | 280 k |
| Budget ÷ 2 | 55,2 % | 2 714 t | 19 | 25 → 6 | 74 | 5 / 3 | 10,7 | 320 k |

Lecture : plus il reste de déchets sauvages, plus il apparaît de **nouveaux dépotoirs** (probabilité lissée et plafonnée, D48, calibrée pour Ouaga en D50). Le nombre de dépotoirs **actifs** en fin de période varie peu : les brigades Laabal de la commune (12 éradications par jour) suffisent à traiter un arrondissement. Sur toute la commune, elles deviendraient la contrainte.

Courbes : `courbes_part_captee.png`, `courbes_dechets_sauvages.png`, `courbes_cout.png`. Plan de base détaillé : `plan_de_gestion.md`, carte : `carte_plan.png`.

Les hypothèses `[H]` sont listées dans `docs/parametres.md` ; les sources dans `data/ouaga/LISEZMOI.md`.
