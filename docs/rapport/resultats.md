# Résultats des scénarios — arrondissement 9 de Ouagadougou

Généré par `scripts/resultats_scenarios.py` le 2026-11-18 : jeu `data/ouaga/`, config de Ouagadougou, simulation de 30 jours, graine 42. Arrondissement 9 : 336 483 habitants (RGPH 2019), secteurs 37 à 40. Relancer donne les mêmes chiffres.

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
| Base | 100,0 % | 66,3 % | 228 | 13 | 2 478 | 18,5 | 25,1 | 8,6 s |
| Pluies | 100,0 % | 60,3 % | 228 | 14 | 2 686 | 20,2 | 25,1 | 3,6 s |
| Panne | 80,2 % | 66,3 % | 228 | 10 | 1 850 | 14,0 | 25,1 | 3,4 s |
| Sensibilisation | 100,0 % | 78,5 % | 228 | 13 | 2 478 | 18,5 | 25,1 | 3,8 s |
| Abonnements | 100,0 % | 76,0 % | 228 | 13 | 2 478 | 18,5 | 25,1 | 3,7 s |
| Budget ÷ 2 | 100,0 % | 66,3 % | 228 | 13 | 2 478 | 18,5 | 12,5 | 3,5 s |

## Simulation sur 30 jours

| Scénario | Part captée moyenne | Déchets sauvages | Nouveaux dépotoirs | Dépotoirs actifs (début → fin) | Éradications (cumul) | Passages faits / annulés | Coût (M XOF) | Amendes (XOF) |
|---|---|---|---|---|---|---|---|---|
| Base | 72,2 % | 1 682 t | 15 | 25 → 5 | 63 | 8 / 0 | 17,1 | 260 k |
| Pluies | 67,4 % | 2 169 t | 14 | 25 → 6 | 66 | 8 / 0 | 18,7 | 280 k |
| Panne | 63,9 % | 2 184 t | 21 | 25 → 5 | 74 | 8 / 0 | 12,9 | 250 k |
| Sensibilisation | 79,0 % | 1 273 t | 8 | 25 → 5 | 51 | 8 / 0 | 17,1 | 290 k |
| Abonnements | 77,5 % | 1 361 t | 8 | 25 → 5 | 51 | 8 / 0 | 17,1 | 290 k |
| Budget ÷ 2 | 63,3 % | 2 224 t | 22 | 25 → 5 | 78 | 5 / 3 | 10,7 | 310 k |

Lecture : plus il reste de déchets sauvages, plus il apparaît de **nouveaux dépotoirs** (probabilité lissée et plafonnée, D48, calibrée pour Ouaga en D50). Le nombre de dépotoirs **actifs** en fin de période varie peu : les brigades Laabal de la commune (12 éradications par jour) suffisent à traiter un arrondissement. Sur toute la commune, elles deviendraient la contrainte.

Courbes : `courbes_part_captee.png`, `courbes_dechets_sauvages.png`, `courbes_cout.png`. Plan de base détaillé : `plan_de_gestion.md`, carte : `carte_plan.png`.

Les hypothèses `[H]` sont listées dans `docs/parametres.md` ; les sources dans `data/ouaga/LISEZMOI.md`.
