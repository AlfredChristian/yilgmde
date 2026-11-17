# Plan de gestion des déchets — arrondissement 9

Scénario **Base — arrondissement 9** · plan n° 1 calculé le 2026-11-17 23:07 UTC en 6605 ms · saison sèche · 4 zone(s), 336 483 habitants.

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
| Distance d'un passage | 2 591,2 km |
| Coût d'un passage | 2 213 499 XOF |
| Coût mensuel estimé | 19 183 658 XOF (budget 25 074 000 XOF) |
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
| 1 | camion_1 | 1 | 1 | 3 746 | 43,4 | 140 | 46 697 XOF |
| 1 | camion_1 | 2 | 3 | 9 858 | 43,5 | 161 | 21 776 XOF |
| 1 | camion_10 | 1 | 5 | 8 659 | 26,5 | 129 | 38 234 XOF |
| 1 | camion_10 | 2 | 5 | 8 824 | 25,8 | 128 | 12 910 XOF |
| 1 | camion_11 | 1 | 3 | 9 766 | 23,6 | 101 | 36 804 XOF |
| 1 | camion_11 | 2 | 3 | 8 756 | 23,1 | 99 | 11 527 XOF |
| 1 | camion_12 | 1 | 5 | 9 649 | 23,0 | 119 | 36 522 XOF |
| 1 | camion_12 | 2 | 4 | 9 981 | 27,4 | 122 | 13 718 XOF |
| 1 | camion_13 | 1 | 4 | 9 766 | 20,8 | 102 | 35 420 XOF |
| 1 | camion_13 | 2 | 4 | 9 986 | 22,3 | 107 | 11 134 XOF |
| 1 | camion_2 | 1 | 3 | 9 956 | 44,7 | 164 | 47 367 XOF |
| 1 | camion_2 | 2 | 2 | 7 689 | 39,0 | 137 | 19 500 XOF |
| 1 | camion_3 | 1 | 3 | 9 957 | 37,9 | 144 | 43 953 XOF |
| 1 | camion_3 | 2 | 2 | 7 295 | 36,5 | 130 | 18 252 XOF |
| 1 | camion_4 | 1 | 3 | 9 945 | 39,9 | 150 | 44 954 XOF |
| 1 | camion_4 | 2 | 3 | 9 759 | 35,8 | 137 | 17 873 XOF |
| 1 | camion_5 | 1 | 3 | 9 956 | 33,8 | 132 | 41 908 XOF |
| 1 | camion_5 | 2 | 3 | 9 863 | 38,5 | 145 | 19 238 XOF |
| 1 | camion_6 | 1 | 2 | 7 904 | 30,4 | 111 | 40 198 XOF |
| 1 | camion_6 | 2 | 3 | 9 863 | 36,1 | 138 | 18 042 XOF |
| 1 | camion_7 | 1 | 2 | 7 790 | 28,7 | 106 | 39 357 XOF |
| 1 | camion_7 | 2 | 3 | 9 977 | 34,4 | 133 | 17 208 XOF |
| 1 | camion_8 | 1 | 2 | 8 248 | 28,0 | 104 | 38 998 XOF |
| 1 | camion_8 | 2 | 2 | 7 904 | 27,3 | 102 | 13 642 XOF |
| 1 | camion_9 | 1 | 3 | 8 573 | 29,8 | 119 | 39 880 XOF |
| 1 | camion_9 | 2 | 3 | 9 994 | 30,0 | 120 | 14 981 XOF |
| 2 | camion_1 | 1 | 2 | 7 689 | 42,9 | 149 | 46 430 XOF |
| 2 | camion_1 | 2 | 3 | 9 956 | 43,7 | 161 | 21 842 XOF |
| 2 | camion_10 | 1 | 3 | 9 559 | 24,9 | 105 | 37 460 XOF |
| 2 | camion_10 | 2 | 3 | 9 766 | 25,1 | 105 | 12 538 XOF |
| 2 | camion_11 | 1 | 4 | 8 891 | 24,8 | 114 | 37 386 XOF |
| 2 | camion_11 | 2 | 4 | 9 646 | 25,4 | 116 | 12 679 XOF |
| 2 | camion_12 | 1 | 4 | 9 236 | 22,4 | 107 | 36 212 XOF |
| 2 | camion_12 | 2 | 3 | 8 503 | 20,6 | 92 | 10 280 XOF |
| 2 | camion_13 | 1 | 3 | 9 298 | 18,8 | 86 | 34 420 XOF |
| 2 | camion_13 | 2 | 4 | 9 850 | 19,4 | 98 | 9 724 XOF |
| 2 | camion_2 | 1 | 3 | 9 858 | 39,3 | 148 | 44 652 XOF |
| 2 | camion_2 | 2 | 2 | 7 689 | 38,3 | 135 | 19 139 XOF |
| 2 | camion_3 | 1 | 3 | 9 661 | 40,1 | 150 | 45 070 XOF |
| 2 | camion_3 | 2 | 3 | 9 562 | 36,1 | 138 | 18 036 XOF |
| 2 | camion_4 | 1 | 3 | 9 945 | 39,6 | 149 | 44 822 XOF |
| 2 | camion_4 | 2 | 2 | 8 134 | 33,5 | 121 | 16 766 XOF |
| 2 | camion_5 | 1 | 2 | 8 134 | 31,6 | 115 | 40 777 XOF |
| 2 | camion_5 | 2 | 2 | 7 904 | 35,7 | 127 | 17 838 XOF |
| 2 | camion_6 | 1 | 2 | 7 904 | 30,8 | 112 | 40 384 XOF |
| 2 | camion_6 | 2 | 2 | 7 561 | 29,8 | 109 | 14 890 XOF |
| 2 | camion_7 | 1 | 3 | 8 335 | 40,1 | 150 | 45 062 XOF |
| 2 | camion_7 | 2 | 3 | 9 764 | 33,0 | 129 | 16 478 XOF |
| 2 | camion_8 | 1 | 3 | 8 251 | 28,5 | 116 | 39 247 XOF |
| 2 | camion_8 | 2 | 4 | 8 618 | 31,4 | 134 | 15 714 XOF |
| 2 | camion_9 | 1 | 2 | 8 935 | 25,1 | 95 | 37 574 XOF |
| 2 | camion_9 | 2 | 3 | 9 261 | 27,1 | 111 | 13 573 XOF |
| 3 | camion_1 | 1 | 3 | 9 956 | 46,0 | 168 | 48 018 XOF |
| 3 | camion_1 | 2 | 3 | 9 858 | 41,1 | 153 | 20 536 XOF |
| 3 | camion_10 | 1 | 5 | 9 071 | 27,1 | 131 | 38 566 XOF |
| 3 | camion_10 | 2 | 5 | 9 154 | 25,1 | 125 | 12 559 XOF |
| 3 | camion_11 | 1 | 5 | 9 896 | 24,2 | 123 | 37 123 XOF |
| 3 | camion_11 | 2 | 3 | 8 924 | 22,3 | 97 | 11 131 XOF |
| 3 | camion_12 | 1 | 5 | 9 731 | 21,7 | 115 | 35 850 XOF |
| 3 | camion_12 | 2 | 4 | 9 977 | 22,8 | 108 | 11 412 XOF |
| 3 | camion_13 | 1 | 6 | 9 978 | 33,2 | 160 | 41 620 XOF |
| 3 | camion_13 | 2 | 4 | 9 898 | 21,9 | 106 | 10 934 XOF |
| 3 | camion_2 | 1 | 3 | 9 957 | 45,4 | 166 | 47 688 XOF |
| 3 | camion_2 | 2 | 3 | 9 858 | 39,2 | 148 | 19 592 XOF |
| 3 | camion_3 | 1 | 3 | 9 714 | 37,2 | 142 | 43 604 XOF |
| 3 | camion_3 | 2 | 2 | 7 446 | 33,7 | 121 | 16 868 XOF |
| 3 | camion_4 | 1 | 3 | 9 908 | 42,3 | 157 | 46 162 XOF |
| 3 | camion_4 | 2 | 3 | 9 977 | 38,8 | 146 | 19 419 XOF |
| 3 | camion_5 | 1 | 2 | 8 592 | 32,0 | 116 | 40 998 XOF |
| 3 | camion_5 | 2 | 2 | 8 248 | 31,5 | 114 | 15 744 XOF |
| 3 | camion_6 | 1 | 2 | 8 134 | 30,1 | 110 | 40 062 XOF |
| 3 | camion_6 | 2 | 2 | 8 248 | 29,2 | 108 | 14 621 XOF |
| 3 | camion_7 | 1 | 2 | 7 675 | 28,1 | 104 | 39 046 XOF |
| 3 | camion_7 | 2 | 3 | 9 914 | 39,1 | 147 | 19 568 XOF |
| 3 | camion_8 | 1 | 3 | 8 949 | 31,6 | 125 | 40 774 XOF |
| 3 | camion_8 | 2 | 3 | 8 935 | 31,3 | 124 | 15 654 XOF |
| 3 | camion_9 | 1 | 3 | 9 146 | 29,0 | 117 | 39 514 XOF |
| 3 | camion_9 | 2 | 4 | 9 893 | 34,7 | 144 | 17 350 XOF |

## Brigade Laabal (aujourd'hui)

- Brigade 1 : 4 dépotoir(s), 40,7 km, 362 min — n° 182 (volume petit, 1 réapparition(s), 8 signalement(s)) ; n° 161 (volume moyen, 3 réapparition(s), 6 signalement(s)) ; n° 71 (volume moyen, 1 réapparition(s), 8 signalement(s)) ; n° 140 (volume petit, 1 réapparition(s), 7 signalement(s))
- Brigade 2 : 4 dépotoir(s), 40,4 km, 361 min — n° 108 (volume petit, 3 réapparition(s), 7 signalement(s)) ; n° 107 (volume moyen, 7 signalement(s)) ; n° 195 (volume petit, 2 réapparition(s), 3 signalement(s)) ; n° 37 (volume moyen, 1 réapparition(s), 3 signalement(s))
- Brigade 3 : 4 dépotoir(s), 33,2 km, 340 min — n° 80 (volume petit, 2 réapparition(s), 4 signalement(s)) ; n° 137 (volume moyen, 3 réapparition(s), 7 signalement(s)) ; n° 73 (volume gros, 2 réapparition(s), 4 signalement(s)) ; n° 90 (volume gros, 1 réapparition(s), 8 signalement(s))
- En attente : 12 dépotoir(s) (capacité Laabal atteinte (3 brigade(s) × 4 dépotoir(s)/jour)).

## Ce qui n'est pas couvert

- Zone Secteur 37 : 38 % de la zone à plus de 300 m d'un point (limite de 60 points par zone atteinte) ; capacité insuffisante : 43 point(s) débordent entre deux passages (197356 kg à stocker pour 180000 kg de capacité)
- Zone Secteur 38 : 37 % de la zone à plus de 300 m d'un point (limite de 60 points par zone atteinte) ; capacité insuffisante : 60 point(s) débordent entre deux passages (228883 kg à stocker pour 180000 kg de capacité)
- Zone Secteur 40 : 26 % de la zone à plus de 300 m d'un point (limite de 60 points par zone atteinte) ; capacité insuffisante : 17 point(s) débordent entre deux passages (168632 kg à stocker pour 180000 kg de capacité) ; dépotoirs à plus de 300 m d'un point : [90]

---

Plan calculé par yilgmde (code MIT). Les valeurs marquées [H] dans la configuration sont des hypothèses de départ ; voir `docs/parametres.md`.
