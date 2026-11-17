# Jeu de données réaliste de Ouagadougou

Données de démonstration pour yilgmde (livrable 4), **fictives mais réalistes**, comme l'ont autorisé les organisateurs du hackathon : la mairie ne disposait pas encore des données réelles.

Généré par `scripts/generer_donnees_ouaga.py` (graine fixe : relancer redonne exactement les mêmes fichiers ; un test le vérifie). Chargement dans la base de démonstration :

```bash
python scripts/charger_exemples.py --ouaga
```

## Fichiers

| Fichier | Contenu |
|---|---|
| `commune_ouagadougou.geojson` | **Contour réel** de la commune et son centre administratif, d'OpenStreetMap (relation 5675756) |
| `zones.geojson` | 52 secteurs des 12 arrondissements, découpés dans ce contour : `arrondissement`, `population`, `densite`, `superficie_km2` |
| `depotoirs.geojson` | 215 sites : 35 centres de collecte et de tri (`officiel`) et 180 dépotoirs `illegal` avec leur statut, leur volume, leur nombre de signalements et de réapparitions |
| `signalements.geojson` | ≈ 890 signalements citoyens **anonymes** (vérifiés, 60 en attente, 45 rejetés) |

## Ce qui est réel

| Donnée | Valeur | Source |
|---|---|---|
| Population par arrondissement | de 66 314 (arr. 12) à 336 483 (arr. 9), total 2 415 266 | INSD, 5e RGPH 2019, *Monographie de la commune de Ouagadougou*, tableau 2.2 |
| Contour de la commune et centre administratif | ≈ 529 km² (le RGPH en déduit 551 à partir de la densité de 4 385,5 hab./km²) | OpenStreetMap, relation 5675756 (© contributeurs OpenStreetMap, ODbL), extrait publié par `missinglink/osm-boundaries` |
| Production de déchets | 0,60 kg par habitant et par jour | DGEP, cité par *Sidwaya* (« Surpopulation à Ouagadougou : une entrave à la gestion des déchets ménagers ») ; la mairie donne 0,57 kg (0,21 t/hab/an) |
| Fréquence de collecte | 2 fois par semaine en quartier résidentiel, 3 au centre | UN-Habitat, profil de gestion des déchets de Ouagadougou |
| Centres de collecte et de tri | 35 dans la ville | UN-Habitat, idem |
| Composition des déchets | alimentaires 22 %, plastiques 5 %, papiers 6 %, autres 67 % | UN-Habitat, idem (sert à répartir les types signalés) |

## Ce qui est fictif

- **Les limites des arrondissements**, à l'intérieur du vrai contour : un disque central (arrondissements 1 et 2) et une couronne découpée en secteurs dont l'angle est proportionnel à la population. Ces limites internes sont **schématiques** : ce ne sont **pas** les limites administratives. Elles ne sont pas publiées en données ouvertes (OpenStreetMap ne les contient pas ; HDX et geoBoundaries s'arrêtent aux communes). Si la mairie fournit les vraies limites, il suffit de les mettre dans `zones.geojson` avec les mêmes propriétés.
- La répartition de la population entre les secteurs d'un arrondissement (le centre est un peu plus dense que la périphérie).
- La position des centres de collecte, des dépotoirs et des signalements ; les statuts, volumes et dates.
- Dans `config/ouagadougou.yaml`, les valeurs marquées `[H]` : flotte de 70 bennes de 10 t, coûts, pré-collecteurs, brigades Laabal, budget mensuel de 180 M XOF, position approximative du centre de traitement de Polesgo.

## Licence

Les fichiers de ce dossier sont sous **Open Database License (ODbL) 1.0** : https://opendatacommons.org/licenses/odbl/1-0/. Le code de yilgmde est sous licence MIT.

## Vie privée

Les signalements ne contiennent ni identifiant d'appareil, ni photo, ni note vocale, ni texte libre. L'application publie aussi en continu les signalements **vérifiés** sous ODbL (`GET /donnees/signalements.geojson`), avec des positions arrondies à environ 11 m et la date au jour près.
