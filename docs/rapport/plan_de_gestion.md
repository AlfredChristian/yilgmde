# Plan de gestion des déchets — arrondissement 9

Scénario **Base — arrondissement 9** · plan n° 1 calculé le 2026-11-17 21:06 UTC en 477 ms · saison sèche · 4 zone(s), 336 483 habitants.

Paramètres modifiés par rapport à la configuration de base :

```json
{"perimetre": {"arrondissements": [9]}}
```

## En bref

| Indicateur | Valeur |
|---|---|
| Déchets produits | 201 890 kg/jour |
| Points de regroupement | 240 |
| Collecte | 2 passage(s) par semaine, 78 rotation(s) sur 3 jour(s) par passage |
| Capacité de collecte des camions (part du stock des points vidée à chaque passage) | 100,0 % |
| Part des déchets captée, estimée (arrive aux points : pré-collecte 30,0 % + apport volontaire 30,2 %) | 60,2 % |
| Camions utilisés | camion_1, camion_10, camion_11, camion_12, camion_13, camion_2, camion_3, camion_4, camion_5, camion_6, camion_7, camion_8, camion_9 |
| Camions indisponibles | aucun |
| Distance d'un passage | 2 497,2 km |
| Coût d'un passage | 2 165 715 XOF |
| Coût mensuel estimé | 18 769 530 XOF (budget 25 074 000 XOF) |
| Dépotoirs actifs | 25 (12 traités aujourd'hui par Laabal, 12 en attente) |

## Points de regroupement

| Zone | Points | Déchets (kg/jour) | Points saturés |
|---|---|---|---|
| Secteur 37 | 60 | 56 387 | 43 |
| Secteur 38 | 60 | 65 395 | 60 |
| Secteur 39 | 60 | 31 927 | 0 |
| Secteur 40 | 60 | 48 181 | 17 |

Pourquoi ces points ? Exemple (point n° 1) : Secteur 37 : 56387 kg/jour, 60 point(s) (capacité : 66, marche ≤ 300 m : 85) ; couverture 62 %. Ce point dessert environ 2 % des ménages de la zone, soit 958 kg/jour et 3352 kg entre deux passages (capacité 3000 kg). Attention : capacité dépassée entre deux passages, augmenter la fréquence de collecte.

## Tournées de collecte (un passage)

| Jour | Camion | Rotation | Arrêts | Charge (kg) | Distance (km) | Durée (min) | Coût |
|---|---|---|---|---|---|---|---|
| 1 | camion_1 | 1 | 2 | 6 900 | 45,9 | 158 | 47 966 XOF |
| 1 | camion_1 | 2 | 2 | 6 999 | 44,9 | 155 | 22 444 XOF |
| 1 | camion_10 | 1 | 3 | 9 643 | 22,9 | 99 | 36 466 XOF |
| 1 | camion_10 | 2 | 3 | 9 682 | 22,2 | 96 | 11 082 XOF |
| 1 | camion_11 | 1 | 3 | 8 756 | 21,0 | 93 | 35 490 XOF |
| 1 | camion_11 | 2 | 5 | 8 989 | 23,5 | 120 | 11 739 XOF |
| 1 | camion_12 | 1 | 5 | 9 566 | 20,8 | 112 | 35 404 XOF |
| 1 | camion_12 | 2 | 5 | 9 978 | 20,8 | 112 | 10 405 XOF |
| 1 | camion_13 | 1 | 4 | 9 766 | 18,0 | 94 | 33 993 XOF |
| 1 | camion_13 | 2 | 4 | 9 977 | 17,5 | 93 | 8 762 XOF |
| 1 | camion_2 | 1 | 2 | 7 689 | 40,9 | 143 | 45 430 XOF |
| 1 | camion_2 | 2 | 3 | 9 858 | 43,4 | 160 | 21 700 XOF |
| 1 | camion_3 | 1 | 3 | 9 858 | 38,5 | 145 | 44 224 XOF |
| 1 | camion_3 | 2 | 3 | 9 562 | 39,2 | 148 | 19 611 XOF |
| 1 | camion_4 | 1 | 3 | 9 966 | 35,9 | 138 | 42 934 XOF |
| 1 | camion_4 | 2 | 3 | 9 959 | 40,8 | 152 | 20 404 XOF |
| 1 | camion_5 | 1 | 3 | 9 810 | 34,4 | 133 | 42 200 XOF |
| 1 | camion_5 | 2 | 2 | 7 904 | 32,8 | 118 | 16 422 XOF |
| 1 | camion_6 | 1 | 2 | 8 935 | 30,6 | 112 | 40 286 XOF |
| 1 | camion_6 | 2 | 2 | 8 134 | 30,3 | 111 | 15 129 XOF |
| 1 | camion_7 | 1 | 2 | 7 675 | 28,1 | 104 | 39 036 XOF |
| 1 | camion_7 | 2 | 2 | 7 790 | 28,2 | 105 | 14 096 XOF |
| 1 | camion_8 | 1 | 2 | 7 561 | 26,2 | 99 | 38 125 XOF |
| 1 | camion_8 | 2 | 2 | 8 134 | 25,9 | 98 | 12 934 XOF |
| 1 | camion_9 | 1 | 3 | 9 865 | 28,1 | 114 | 39 066 XOF |
| 1 | camion_9 | 2 | 3 | 8 924 | 25,3 | 106 | 12 654 XOF |
| 2 | camion_1 | 1 | 3 | 9 858 | 46,0 | 168 | 47 996 XOF |
| 2 | camion_1 | 2 | 3 | 9 661 | 44,9 | 165 | 22 452 XOF |
| 2 | camion_10 | 1 | 3 | 9 092 | 22,2 | 97 | 36 123 XOF |
| 2 | camion_10 | 2 | 5 | 9 731 | 23,9 | 122 | 11 933 XOF |
| 2 | camion_11 | 1 | 4 | 9 818 | 28,9 | 127 | 39 470 XOF |
| 2 | camion_11 | 2 | 4 | 8 659 | 20,8 | 102 | 10 414 XOF |
| 2 | camion_12 | 1 | 3 | 8 756 | 18,1 | 84 | 34 054 XOF |
| 2 | camion_12 | 2 | 4 | 9 897 | 23,9 | 112 | 11 930 XOF |
| 2 | camion_13 | 1 | 4 | 9 850 | 15,4 | 86 | 32 727 XOF |
| 2 | camion_13 | 2 | 4 | 8 805 | 15,8 | 87 | 7 888 XOF |
| 2 | camion_2 | 1 | 2 | 7 985 | 40,5 | 142 | 45 278 XOF |
| 2 | camion_2 | 2 | 3 | 9 858 | 39,7 | 149 | 19 840 XOF |
| 2 | camion_3 | 1 | 2 | 7 295 | 37,2 | 132 | 43 616 XOF |
| 2 | camion_3 | 2 | 3 | 9 956 | 43,5 | 160 | 21 728 XOF |
| 2 | camion_4 | 1 | 3 | 9 863 | 39,2 | 148 | 44 622 XOF |
| 2 | camion_4 | 2 | 3 | 9 956 | 34,0 | 132 | 16 982 XOF |
| 2 | camion_5 | 1 | 3 | 9 945 | 34,7 | 134 | 42 369 XOF |
| 2 | camion_5 | 2 | 2 | 8 363 | 31,5 | 114 | 15 748 XOF |
| 2 | camion_6 | 1 | 2 | 7 904 | 29,9 | 110 | 39 941 XOF |
| 2 | camion_6 | 2 | 2 | 8 134 | 29,4 | 108 | 14 688 XOF |
| 2 | camion_7 | 1 | 2 | 8 019 | 28,1 | 104 | 39 057 XOF |
| 2 | camion_7 | 2 | 3 | 9 977 | 33,8 | 132 | 16 914 XOF |
| 2 | camion_8 | 1 | 5 | 9 154 | 28,4 | 135 | 39 202 XOF |
| 2 | camion_8 | 2 | 3 | 9 398 | 27,0 | 111 | 13 522 XOF |
| 2 | camion_9 | 1 | 3 | 9 598 | 24,3 | 103 | 37 144 XOF |
| 2 | camion_9 | 2 | 5 | 9 154 | 26,3 | 129 | 13 149 XOF |
| 3 | camion_1 | 1 | 3 | 9 956 | 44,6 | 164 | 47 327 XOF |
| 3 | camion_1 | 2 | 2 | 7 788 | 42,1 | 146 | 21 043 XOF |
| 3 | camion_10 | 1 | 5 | 8 906 | 23,5 | 120 | 36 752 XOF |
| 3 | camion_10 | 2 | 4 | 9 476 | 25,5 | 116 | 12 736 XOF |
| 3 | camion_11 | 1 | 3 | 8 924 | 19,5 | 88 | 34 755 XOF |
| 3 | camion_11 | 2 | 4 | 9 982 | 26,6 | 120 | 13 284 XOF |
| 3 | camion_12 | 1 | 4 | 9 818 | 19,7 | 99 | 34 855 XOF |
| 3 | camion_12 | 2 | 4 | 9 934 | 20,9 | 103 | 10 473 XOF |
| 3 | camion_13 | 1 | 4 | 9 658 | 31,1 | 133 | 40 553 XOF |
| 3 | camion_13 | 2 | 5 | 9 071 | 16,4 | 99 | 8 224 XOF |
| 3 | camion_2 | 1 | 3 | 9 759 | 40,6 | 152 | 45 286 XOF |
| 3 | camion_2 | 2 | 3 | 9 858 | 43,2 | 160 | 21 584 XOF |
| 3 | camion_3 | 1 | 2 | 7 329 | 35,8 | 128 | 42 914 XOF |
| 3 | camion_3 | 2 | 3 | 8 576 | 36,0 | 138 | 18 026 XOF |
| 3 | camion_4 | 1 | 2 | 7 247 | 33,6 | 121 | 41 780 XOF |
| 3 | camion_4 | 2 | 3 | 9 945 | 40,5 | 151 | 20 236 XOF |
| 3 | camion_5 | 1 | 2 | 7 904 | 30,9 | 112 | 40 424 XOF |
| 3 | camion_5 | 2 | 3 | 9 993 | 43,3 | 160 | 21 658 XOF |
| 3 | camion_6 | 1 | 2 | 8 019 | 29,1 | 107 | 39 572 XOF |
| 3 | camion_6 | 2 | 2 | 7 561 | 28,9 | 107 | 14 441 XOF |
| 3 | camion_7 | 1 | 3 | 9 764 | 32,7 | 128 | 41 350 XOF |
| 3 | camion_7 | 2 | 2 | 7 904 | 27,2 | 102 | 13 594 XOF |
| 3 | camion_8 | 1 | 3 | 9 783 | 30,6 | 122 | 40 313 XOF |
| 3 | camion_8 | 2 | 3 | 9 311 | 26,8 | 110 | 13 417 XOF |
| 3 | camion_9 | 1 | 3 | 9 852 | 26,5 | 109 | 38 236 XOF |
| 3 | camion_9 | 2 | 4 | 9 728 | 32,2 | 137 | 16 093 XOF |

## Brigade Laabal (aujourd'hui)

- Brigade 1 : 4 dépotoir(s), 45,0 km, 375 min — n° 195 (volume petit, 2 réapparition(s), 3 signalement(s)) ; n° 37 (volume moyen, 1 réapparition(s), 3 signalement(s)) ; n° 161 (volume moyen, 3 réapparition(s), 6 signalement(s)) ; n° 182 (volume petit, 1 réapparition(s), 8 signalement(s))
- Brigade 2 : 4 dépotoir(s), 38,9 km, 357 min — n° 108 (volume petit, 3 réapparition(s), 7 signalement(s)) ; n° 107 (volume moyen, 7 signalement(s)) ; n° 71 (volume moyen, 1 réapparition(s), 8 signalement(s)) ; n° 140 (volume petit, 1 réapparition(s), 7 signalement(s))
- Brigade 3 : 4 dépotoir(s), 31,9 km, 336 min — n° 80 (volume petit, 2 réapparition(s), 4 signalement(s)) ; n° 137 (volume moyen, 3 réapparition(s), 7 signalement(s)) ; n° 73 (volume gros, 2 réapparition(s), 4 signalement(s)) ; n° 90 (volume gros, 1 réapparition(s), 8 signalement(s))
- En attente : 12 dépotoir(s) (capacité Laabal atteinte (3 brigade(s) × 4 dépotoir(s)/jour)).

## Ce qui n'est pas couvert

- Zone Secteur 37 : 38 % de la zone à plus de 300 m d'un point (limite de 60 points par zone atteinte) ; capacité insuffisante : 43 point(s) débordent entre deux passages (197356 kg à stocker pour 180000 kg de capacité)
- Zone Secteur 38 : 37 % de la zone à plus de 300 m d'un point (limite de 60 points par zone atteinte) ; capacité insuffisante : 60 point(s) débordent entre deux passages (228883 kg à stocker pour 180000 kg de capacité)
- Zone Secteur 40 : 26 % de la zone à plus de 300 m d'un point (limite de 60 points par zone atteinte) ; capacité insuffisante : 17 point(s) débordent entre deux passages (168632 kg à stocker pour 180000 kg de capacité) ; dépotoirs à plus de 300 m d'un point : [90]

---

Plan calculé par yilgmde (code MIT). Les valeurs marquées [H] dans la configuration sont des hypothèses de départ ; voir `docs/parametres.md`.
