# Modèle de données

Base SQLite pour le MVP (voir `DECISIONS.md`). Positions en WGS84 (`latitude`, `longitude`). Dates en ISO 8601 UTC.

## Utilisateurs et acteurs

- **Utilisateur** : id, nom, email, mot_de_passe_hash, role (`admin` | `chauffeur` | `laabal`), actif, cree_le. Sert uniquement aux comptes.
- **Contributeur** : id, jeton_appareil (UUID généré côté client), nb_signalements, score_confiance, bloque. Limite les abus sans compte citoyen.

## Signalement et dépotoir

- **Signalement** : id, contributeur_id, latitude, longitude, photo (chemin), description, type_dechet, volume_estime, code_suivi, statut, motif, score_auto (0 à 1), alertes (liste), depotoir_id (nullable), valide_par, valide_le, cree_le.
- **Depotoir** : id, latitude, longitude, zone_id, volume_estime, statut, legalite, nb_signalements, nb_reapparitions, premiere_detection, derniere_maj.
- **Zone** : id, nom (quartier ou secteur), geometrie (polygone GeoJSON), population, densite.

## Plan et simulation

- **Scenario** : id, nom, parametres (JSON, fusionné sur `config/`), cree_par, cree_le.
- **Camion** : id, scenario_id, capacite_kg, cout_km_xof, cout_jour_xof, disponible.
- **Plan** : id, scenario_id, calcule_le, duree_calcul_ms, indicateurs (JSON), non_couverts (JSON).
- **PointRegroupement** : id, plan_id, latitude, longitude, capacite_kg, zone_id, explication.
- **Tournee** : id, plan_id, type (`collecte` | `intervention`), camion_id (nullable), affectee_a (utilisateur_id, nullable), distance_km, duree_min, cout_xof.
- **ArretTournee** : id, tournee_id, ordre, cible_type (`point_regroupement` | `depotoir`), cible_id, statut (`a_faire` | `effectue`).
- **IndicateurSimulation** : plan_id, jour, pct_collecte, depotoirs_actifs, cout_xof, distance_km.

## Brigade Laabal

- **Intervention** : id, depotoir_id, laabal_id, statut (`en_cours` | `eradique`), photo, date.
- **Constat** : id, depotoir_id, laabal_id, date, description, preuves (chemins), montant_xof, statut. Données personnelles réduites au strict nécessaire ; accès réservé à Laabal et admin.

## Traçabilité

- **JournalAudit** : id, utilisateur_id, action, objet_type, objet_id, date.

## Statuts

- **Signalement.statut** : `soumis` → `rejete_auto` (motif automatique) ou `en_attente_revue` → `verifie` ou `rejete` (motif humain).
- **Depotoir.statut** : `actif` → `intervention_planifiee` → `eradique` → `sous_surveillance` → `classe`. Un nouveau signalement vérifié près d'un dépotoir éradiqué ou sous surveillance le ramène à `actif` et incrémente `nb_reapparitions`.
- **Depotoir.legalite** : `illegal` (à éradiquer) | `officiel`.

## Alertes automatiques (Signalement.alertes)

`doublon_probable:<depotoir_id>`, `hors_zone`, `position_incoherente`, `appareil_suspect`, `volume_aberrant`.

## Règles de cohérence

1. Un signalement n'apparaît **publiquement** que s'il est `verifie`.
2. Un dépotoir regroupe un ou plusieurs signalements vérifiés : on fusionne, on ne duplique pas.
3. Le plan se calcule à partir des seuls dépotoirs `actif` (et des points officiels) et des paramètres du scénario courant.
4. Un camion `disponible = false` n'est jamais utilisé dans une tournée.
5. Chaque validation, rejet, modification de paramètre ou intervention est écrite dans `JournalAudit`.
