# Jeu de données réaliste de Ouagadougou

Données de démonstration pour yilgmde (livrable 4). Le **découpage administratif est réel** : il a été relevé sur la carte de l'INSD. Les dépotoirs et signalements sont **fictifs mais réalistes**, comme l'ont autorisé les organisateurs du hackathon : la mairie ne disposait pas encore des données réelles.

Généré par `scripts/generer_donnees_ouaga.py` (graine fixe : relancer redonne exactement les mêmes fichiers ; un test le vérifie). Chargement dans la base de démonstration :

```bash
python scripts/charger_exemples.py --ouaga
```

## Fichiers

| Fichier | Contenu |
|---|---|
| `arrondissements.geojson` | Les **12 arrondissements**, relevés sur la carte de l'INSD : population, superficie, secteurs |
| `zones.geojson` | Les **55 secteurs** (numéros officiels), zones de calcul du plan : `arrondissement`, `population`, `densite`, `superficie_km2`, `peripherie` |
| `commune_ouagadougou.geojson` | Contour de la commune d'après la carte de l'INSD, calé sur le terrain |
| `commune_osm.geojson` | Contour de la commune dans OpenStreetMap (relation 5675756), qui a servi au calage |
| `depotoirs.geojson` | 215 sites : 35 centres de collecte et de tri (`officiel`) et 180 dépotoirs `illegal` |
| `signalements.geojson` | ≈ 940 signalements citoyens **anonymes** (vérifiés, 60 en attente, 45 rejetés) |

## Comment le découpage a été obtenu (D42)

Les limites des arrondissements ne sont publiées dans aucune base ouverte : OpenStreetMap ne les contient pas, et HDX comme geoBoundaries s'arrêtent au niveau des communes. Elles ont donc été **relevées sur la carte** « Le nouveau découpage administratif de la Commune de Ouagadougou » de l'INSD (12 arrondissements, 55 secteurs ; loi 066-2009/AN modifiée par la loi 026-2012/AN), par `scripts/arrondissements_insd.py` :

1. relevé à la main, en pixels, du contour, des limites d'arrondissement et des 55 numéros de secteur ;
2. **échelle** : barre d'échelle de la carte (5 km = 88 px, soit 56,8 m/px). Un ajustement libre sur le contour OpenStreetMap trouve 56,6 m/px, à 0,5 % près ;
3. **position** : la translation qui recouvre au mieux le contour OpenStreetMap. Les deux contours se recouvrent à 83 % : ils diffèrent surtout au nord-est. Celui de l'INSD mesure 509 km², proche des 518 km² officiels ; celui d'OSM 529 km² ;
4. **arrondissements** : polygones reconstruits à partir des limites relevées ;
5. **secteurs** : limites approchées par Voronoï autour des numéros, à l'intérieur de leur arrondissement.

**Contrôle** : la superficie de chaque arrondissement est comparée à celle qu'on déduit de l'INSD (population / densité, tableaux 2.2 et A 15). 9 arrondissements sur 12 sont à ±7 % ; les écarts restants (arr. 8 : −20 %, 10 : +26 %, 11 : +19 %) se retrouvent sur la carte elle-même. Précision des limites d'arrondissement : quelques centaines de mètres.

| Arr. | Relevé (km²) | INSD (km²) | Secteurs |
|---|---|---|---|
| 1 | 18,3 | 18,4 | 1 à 6 |
| 2 | 12,5 | 12,9 | 7 à 11 |
| 3 | 38,5 | 41,1 | 12 à 16 |
| 4 | 82,0 | 82,0 | 17 à 20 |
| 5 | 20,3 | 21,5 | 21 à 24 |
| 6 | 26,4 | 28,4 | 25 à 29 |
| 7 | 50,1 | 51,3 | 30 à 33 |
| 8 | 53,2 | 66,8 | 34 à 36 |
| 9 | 85,5 | 89,4 | 37 à 40 |
| 10 | 33,0 | 26,2 | 41 à 45 |
| 11 | 48,2 | 40,6 | 46 à 51 |
| 12 | 40,6 | 40,3 | 52 à 55 |

## Ce qui est réel

| Donnée | Valeur | Source |
|---|---|---|
| Arrondissements et secteurs | 12 arrondissements, 55 secteurs | INSD, carte du découpage administratif (monographie RGPH 2019), relevée et calée (voir ci-dessus) |
| Population par arrondissement | de 66 314 (arr. 12) à 336 483 (arr. 9), total 2 415 266 | INSD, 5e RGPH 2019, *Monographie de la commune de Ouagadougou*, tableau 2.2 |
| Densité par arrondissement | de 1 644,9 (arr. 12) à 10 061,3 hab./km² (arr. 10) | idem, tableau A 15 (sert au contrôle des superficies) |
| Contour de la commune (calage) | relation 5675756 | OpenStreetMap (© contributeurs OpenStreetMap, ODbL), extrait publié par `missinglink/osm-boundaries` |
| Production de déchets | 0,60 kg par habitant et par jour | DGEP, cité par *Sidwaya* ; la mairie donne 0,57 kg (0,21 t/hab/an) |
| Fréquence de collecte | 2 fois par semaine en quartier résidentiel, 3 au centre | UN-Habitat, profil de gestion des déchets de Ouagadougou |
| Centres de collecte et de tri | 35 dans la ville | UN-Habitat, idem |
| Composition des déchets | alimentaires 22 %, plastiques 5 %, papiers 6 %, autres 67 % | UN-Habitat, idem (sert à répartir les types signalés) |

## Ce qui est approché ou fictif

- Les **limites entre secteurs** d'un même arrondissement (Voronoï) : seuls le numéro et la position de chaque secteur sont relevés.
- La **population par secteur** : celle de l'arrondissement, répartie au prorata de la superficie (la monographie ne la donne pas par secteur).
- La position des centres de collecte, des dépotoirs et des signalements ; leurs statuts, volumes et dates.
- Dans `config/ouagadougou.yaml`, les valeurs marquées `[H]` : flotte de 70 bennes de 10 t, coûts, pré-collecteurs, brigades Laabal, budget mensuel de 180 M XOF, position approximative du centre de traitement de Polesgo.

Si la mairie fournit un jour les limites officielles en fichier, il suffit de remplacer `arrondissements.geojson` et `zones.geojson` en gardant les mêmes propriétés.

## Licence

Les fichiers de ce dossier sont sous **Open Database License (ODbL) 1.0** : https://opendatacommons.org/licenses/odbl/1-0/. Le découpage est un relevé de la carte publiée par l'INSD, dont la source est citée. Le code de yilgmde est sous licence MIT.

## Vie privée

Les signalements ne contiennent ni identifiant d'appareil, ni photo, ni note vocale, ni texte libre. L'application publie aussi en continu les signalements **vérifiés** sous ODbL (`GET /donnees/signalements.geojson`), avec des positions arrondies à environ 11 m et la date au jour près.
