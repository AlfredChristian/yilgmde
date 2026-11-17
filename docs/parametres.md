# Paramètres du moteur et du simulateur (livrable 2)

Tous les paramètres sont dans deux fichiers YAML, **aucun n'est écrit dans le code** :

- `config/default.yaml` : valeurs génériques, valables pour n'importe quelle commune ;
- `config/ouagadougou.yaml` : ce qui est propre à Ouagadougou, fusionné par-dessus ;
- un **scénario** modifie ensuite quelques valeurs sans toucher aux fichiers (`PUT /scenarios/{id}/parametres`, ex. `{"saison": "pluies"}`).

Colonnes :
- **Défaut** : valeur de `default.yaml` ;
- **Ouaga** : valeur de `ouagadougou.yaml` quand elle la remplace (vide sinon) ;
- **Statut** : `source` (valeur tirée d'une source, citée) ; `[H]` (hypothèse de départ, à ajuster avec la mairie ou des observations) ; `technique` (réglage de calcul, sans effet sur le sens des résultats) ; `informatif` (décrit la commune, pas lu par le moteur).

Les sources sont détaillées dans `data/ouaga/LISEZMOI.md`. Un test (`tests/test_parametres_doc.py`) vérifie que chaque paramètre des deux fichiers figure dans ce document.

## Commune (`ouagadougou.yaml`)

| Paramètre | Rôle | Unité | Ouaga | Statut |
|---|---|---|---|---|
| `ville` | Nom de la commune (titres, exports) | — | Ouagadougou | informatif |
| `pays` | Code du pays | ISO 3166 | BF | informatif |
| `devise` | Devise des coûts | ISO 4217 | XOF | informatif |
| `crs_geographique` | Système de coordonnées des données | EPSG | 4326 | informatif |
| `crs_metrique` | Système métrique de référence (le moteur calcule en projection locale) | EPSG | 32630 | informatif |
| `zone_etude.bbox` | Rectangle hors duquel un signalement est rejeté (« hors zone ») | degrés | lat 12,24–12,50 ; lon −1,66–−1,39 | source : emprise de la commune (carte INSD calée) |
| `population_totale` | Population de la commune | habitants | 2 415 266 | source : RGPH 2019 |
| `secteur_equipe` | Secteur attribué à l'équipe par la mairie | — | aucun | informatif |
| `sources_donnees` | Liste des sources utilisées | — | — | informatif |

## Scénario

| Paramètre | Rôle | Unité | Défaut | Ouaga | Statut |
|---|---|---|---|---|---|
| `scenario.nom` | Nom du jeu de paramètres de base | — | base | | informatif |
| `scenario.saison` | `seche` ou `pluies` : choisit les coefficients de `saisons` | — | seche | | levier de scénario |
| `scenario.horizon_jours` | Durée par défaut d'une simulation et d'une comparaison | jours | 30 | | [H] |
| `scenario.graine_aleatoire` | Graine par défaut : même graine = même simulation | — | 42 | | technique |

## Population et déchets

| Paramètre | Rôle | Unité | Défaut | Ouaga | Statut |
|---|---|---|---|---|---|
| `population.production_dechets_kg_hab_jour` | Déchets produits par habitant (demande, C1) | kg/hab/jour | 0,5 | 0,60 | source : DGEP (cité par *Sidwaya*) ; mairie 0,57 |
| `population.taux_abonnement_precollecteurs` | Part des ménages abonnés à un pré-collecteur | 0–1 | 0,3 | 0,3 | [H] |
| `population.habitants_par_menage` | Taille moyenne d'un ménage | habitants | 6 | | informatif (pas encore utilisé) |
| `saisons.seche.coef_production` | Multiplie la production en saison sèche | × | 1,0 | | référence |
| `saisons.seche.coef_vitesse_camion` | Multiplie la vitesse des camions | × | 1,0 | | référence |
| `saisons.seche.coef_depots_sauvages` | Divise l'apport volontaire aux points | × | 1,0 | | référence |
| `saisons.pluies.coef_production` | Production en saison des pluies | × | 1,1 | | [H] |
| `saisons.pluies.coef_vitesse_camion` | Vitesse des camions sur routes dégradées | × | 0,7 | | [H] |
| `saisons.pluies.coef_depots_sauvages` | Moins d'apport volontaire (boue, distances) | × | 1,2 | | [H] |

## Vérification des signalements (A2) et modération (A3)

| Paramètre | Rôle | Unité | Défaut | Statut |
|---|---|---|---|---|
| `verification.rayon_doublon_m` | Deux signalements plus proches = doublon probable | m | 30 | [H] |
| `verification.max_signalements_par_appareil_heure` | Au-delà, rejet d'office (comptés à l'heure de prise de vue) | signalements/h | 5 | [H] |
| `verification.photo_requise` | Rejeter les signalements sans photo | oui/non | non | choix |
| `verification.photo_taille_max_mo` | Photo plus grosse : refusée (413) | Mo | 5 | technique |
| `verification.penalite_doublon` | Retiré du score si un signalement proche existe | 0–1 | 0,3 | [H] |
| `verification.penalite_depotoir_proche` | Retiré du score si un dépotoir connu est proche | 0–1 | 0,1 | [H] |
| `verification.seuil_confiance_appareil` | Sous ce score, l'appareil est « peu fiable » | 0–1 | 0,3 | [H] |
| `verification.penalite_appareil_peu_fiable` | Retiré du score pour un appareil peu fiable | 0–1 | 0,2 | [H] |
| `verification.gain_confiance_validation` | Validation : score ← score + gain × (1 − score) | 0–1 | 0,1 | [H] |
| `verification.perte_confiance_rejet` | Rejet : score ← score − perte × score | 0–1 | 0,25 | [H] |

## Signalement hors connexion et masquage (livrable 1)

| Paramètre | Rôle | Unité | Défaut | Statut |
|---|---|---|---|---|
| `hors_ligne.tolerance_horloge_min` | `capture_le` accepté jusqu'à ce délai dans le futur | min | 5 | technique |
| `hors_ligne.anciennete_max_jours` | Plus vieux : accepté avec l'alerte `capture_ancienne` | jours | 30 | [H] |
| `hors_ligne.max_envois_par_heure` | Plafond d'envois reçus par appareil (429 au-delà) | envois/h | 30 | [H] |
| `hors_ligne.note_vocale_taille_max_mo` | Taille maximale d'une note vocale | Mo | 2 | technique |
| `masquage.cote_max_px` | Photo réduite au-delà de ce côté | px | 1600 | technique |
| `masquage.cote_detection_px` | Détection sur une copie réduite à ce côté | px | 800 | technique |
| `masquage.facteur_echelle` | Pas de la recherche multi-échelle d'OpenCV | × | 1,1 | technique |
| `masquage.voisins_min_visage` | Plus haut : moins de fausses détections, plus de visages manqués | — | 5 | [H] |
| `masquage.voisins_min_plaque` | Idem pour les plaques | — | 4 | [H] |
| `masquage.taille_min_px` | Plus petit visage ou plaque cherché | px | 20 | technique |
| `masquage.marge` | Zone floutée élargie de chaque côté | fraction | 0,25 | choix (prudence) |
| `masquage.qualite_jpeg` | Qualité du JPEG enregistré | 0–100 | 85 | technique |

## Points de regroupement (C2)

| Paramètre | Rôle | Unité | Défaut | Statut |
|---|---|---|---|---|
| `points_regroupement.capacite_kg` | Capacité d'un point (bac, aire de dépôt) | kg | 3000 | [H] |
| `points_regroupement.distance_max_a_pied_m` | Distance qu'un ménage accepte de parcourir | m | 300 | [H] |
| `points_regroupement.couverture_cible` | Part de la zone à distance de marche d'un point | 0–1 | 0,95 | choix |
| `points_regroupement.max_points_par_zone` | Borne le calcul ; au-delà, la zone est signalée mal couverte | points | 60 | technique |
| `points_regroupement.poids_depotoir` | Attraction d'un dépotoir actif sur le placement | × | 5 | [H] |
| `points_regroupement.pas_echantillonnage_m` | Résolution de la grille des ménages | m | 100 | technique |
| `points_regroupement.max_echantillons_par_zone` | Borne le temps de calcul | points | 2000 | technique |

## Collecte et tournées (C3)

| Paramètre | Rôle | Unité | Défaut | Ouaga | Statut |
|---|---|---|---|---|---|
| `camions[]` | Flotte : `id`, `capacite_kg`, `cout_km_xof`, `cout_jour_xof`, `disponible` | — | 3 camions de 6 t | 70 bennes de 10 t, 500 XOF/km, 25 000 XOF/jour | [H] |
| `collecte.depot` | Point de départ et de vidage des camions | lat/lon | — | 12,43 ; −1,47 (CTVD de Polesgo) | [H] position approximative |
| `collecte.frequence_passages_par_semaine` | Passages de collecte par semaine | /semaine | 2 | 2 | source : UN-Habitat (2 en résidentiel, 3 au centre) |
| `collecte.jours_ouvres_par_semaine` | Un passage s'étale sur jours ouvrés / fréquence jours (D39) | jours | absent (1 jour) | 6 | [H] |
| `collecte.vitesse_moyenne_kmh` | Vitesse moyenne en ville | km/h | 20 | | [H] |
| `collecte.coef_detour` | Distance routière ≈ vol d'oiseau × coef | × | 1,3 | | [H] |
| `collecte.temps_arret_min` | Chargement d'un point | min | 10 | | [H] |
| `collecte.duree_max_tournee_min` | Journée de travail d'un camion | min | 480 | | [H] |
| `collecte.rotations_max_par_jour` | Allers-retours au dépôt par camion et par jour | rotations | 2 | | [H] |
| `collecte.temps_calcul_max_s` | Sécurité seulement : le calcul doit finir avant | s | 30 | | technique |
| `collecte.max_arrets_recherche_locale` | Au-delà, solution de départ OR-Tools seule (D38) | arrêts | 150 | | technique |

## Pré-collecte, Laabal, mairie

| Paramètre | Rôle | Unité | Défaut | Ouaga | Statut |
|---|---|---|---|---|---|
| `precollecteurs.nombre` | Nombre de pré-collecteurs | — | 20 | 1000 | [H] |
| `precollecteurs.capacite_kg_jour` | Ce qu'un pré-collecteur ramasse par jour | kg/jour | 150 | 300 | [H] |
| `precollecteurs.abonnement_mensuel_xof` | Prix de l'abonnement d'un ménage | XOF/mois | 1000 | 1000 | informatif (pas encore utilisé) |
| `laabal.nombre_brigades` | Brigades d'éradication | — | 1 | 3 | [H] |
| `laabal.capacite_eradication_par_jour` | Dépotoirs traités par brigade et par jour | dépotoirs | 2 | 4 | [H] |
| `laabal.temps_intervention_min` | Durée d'une éradication sur place | min | 60 | | [H] |
| `laabal.frequence_surveillance_jours` | Fréquence de surveillance d'un site éradiqué | jours | 7 | | informatif (pas encore utilisé) |
| `laabal.taux_controle` | Probabilité de constater une tentative de dépôt sur un site surveillé | 0–1 | 0,3 | | [H] |
| `laabal.montant_amende_xof` | Amende par constat | XOF | 10 000 | | [H] |
| `laabal.effet_dissuasion` | Réduction des dépôts près d'un site surveillé | 0–1 | 0,3 | | [H] |
| `laabal.priorite.poids_volume` | Priorité selon le volume (petit, moyen, gros) | points | 1, 2, 3 | | [H] |
| `laabal.priorite.poids_reapparition` | Priorité par réapparition | points | 2 | | [H] |
| `laabal.priorite.poids_signalement` | Priorité par signalement | points | 0,5 | | [H] |
| `mairie.budget_mensuel_xof` | Budget de collecte ; un arrondissement en reçoit sa part au prorata de sa population (D39) | XOF/mois | 5 000 000 | 180 000 000 | [H] |

## Simulation (E1–E4)

| Paramètre | Rôle | Unité | Défaut | Ouaga | Statut |
|---|---|---|---|---|---|
| `simulation.prob_apport_volontaire` | Un ménage non abonné à distance de marche apporte ses déchets au point. **Levier principal de la part captée** (D41) | 0–1 | 0,6 |  | [H] |
| `simulation.seuil_nouveau_depotoir_kg` | Échelle de déchets sauvages du jour : plus elle est basse, plus le risque d'un nouveau dépotoir augmente vite. Ouaga : recalibré sur 12 à 20 t/jour de déchets sauvages par secteur (D50) | kg | 1500 | 40 000 | [H] |
| `simulation.prob_nouveau_depotoir_max` | Plafond journalier de probabilité d'apparition d'un nouveau dépotoir ; évite qu'un seuil dépassé crée un dépôt à coup sûr | 0–1 | 0,45 |  | [H] |
| `simulation.prob_reapparition` | Réapparition d'un site surveillé, par jour (× (1 − dissuasion)) | 0–1 | 0,05 |  | [H] |
| `simulation.prob_tentative_depot_surveille` | Tentative de dépôt sur un site surveillé, par jour | 0–1 | 0,1 |  | [H] |
| `simulation.jours_par_mois` | Répartition du budget mensuel | jours | 30 |  | technique |
| `simulation.max_echantillons_couverture` | Borne le calcul de la couverture à pied | points | 400 |  | technique |
## Périmètre d'un plan (livrable 3)

| Paramètre | Rôle | Unité | Défaut | Statut |
|---|---|---|---|---|
| `perimetre.arrondissements` | Limiter plan, tournées et simulation à ces arrondissements | numéros | [] (toute la commune) | levier de scénario |
| `perimetre.zones` | Idem pour des zones (secteurs) choisies | ids | [] | levier de scénario |

## Données ouvertes, export, import

| Paramètre | Rôle | Unité | Défaut | Statut |
|---|---|---|---|---|
| `donnees_ouvertes.licence` | Licence du jeu de signalements publié | — | ODbL-1.0 | choix (D40) |
| `donnees_ouvertes.attribution` | Mention d'attribution | — | yilgmde et contributeurs | choix |
| `donnees_ouvertes.decimales_position` | Arrondi des positions publiées (4 ≈ 11 m) | décimales | 4 | choix (vie privée) |
| `export_osm.min_signalements` | Signalements vérifiés minimum pour exporter un dépotoir | — | 1 | [H] |
| `export_osm.source` | Étiquette `source` OSM | — | survey;YilGmdé | choix |
| `export_osm.licence` | Licence déclarée dans l'export OSM | — | ODbL-1.0 | choix |
| `import.max_par_lot` | Taille maximale d'un import de signalements | signalements | 1000 | technique |

## Sécurité

| Paramètre | Rôle | Unité | Défaut | Statut |
|---|---|---|---|---|
| `securite.duree_token_min` | Durée de validité d'une connexion | min | 480 | [H] |
| `securite.max_echecs_par_email` | Échecs avant blocage temporaire de l'e-mail | — | 5 | [H] |
| `securite.max_echecs_par_ip` | Échecs avant blocage temporaire de l'adresse IP | — | 20 | [H] |
| `securite.fenetre_echecs_min` | Fenêtre glissante de comptage des échecs | min | 15 | [H] |
| `securite.blocage_min` | Durée du blocage | min | 15 | [H] |

## Les leviers qui comptent le plus

D'après les scénarios simulés sur l'arrondissement 9 (voir le rapport) :

1. `simulation.prob_apport_volontaire` et `population.taux_abonnement_precollecteurs` : ils décident de la **part captée** des déchets (sensibilisation, abonnements) ;
2. `camions[].disponible`, `capacite_kg` et `collecte.jours_ouvres_par_semaine` : ils décident de la **capacité de collecte** ;
3. `scenario.saison` : la saison des pluies réduit l'apport volontaire et ralentit les camions ;
4. `mairie.budget_mensuel_xof` : en dessous du coût mensuel du plan, des passages sont annulés.

Ce sont aussi des hypothèses `[H]` : ce sont les premières à mesurer sur le terrain.
