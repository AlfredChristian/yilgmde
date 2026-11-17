# Contrat d'API (BROUILLON — à valider par Christian et Faissal)

Toute modification d'API passe par une PR qui met à jour ce fichier. La documentation interactive générée par FastAPI est sur `/docs`.

## Conventions

- Base : `http://localhost:8000`. Format : JSON, noms de champs en `snake_case` français.
- Positions : `latitude`, `longitude` (WGS84). Dates : ISO 8601 UTC.
- **Citoyen anonyme** : en-tête `X-Device-Token: <UUID généré par l'appareil>`.
- **Comptes** (admin, chauffeur, laabal) : `Authorization: Bearer <token>` obtenu par `/auth/login`.
- Erreurs : `{"detail": "message lisible"}` avec le code HTTP adapté (400, 401, 403, 404, 422).
- Recalcul : synchrone si rapide (visé < 5 s) ; les routes qui modifient un scénario renvoient le plan recalculé.

## Énumérations

- `type_dechet` : `menager`, `gravats`, `encombrants`, `plastiques`, `organique`, `autre`
- `volume_estime` : `petit`, `moyen`, `gros`
- Statuts : voir `docs/modele-donnees.md`.

## Droits par rôle

| Zone | Anonyme | admin | chauffeur | laabal |
|---|---|---|---|---|
| `/health`, `/depotoirs`, `/points-regroupement`, `/signalements` (POST), suivi | oui | oui | oui | oui |
| `/auth/*` | login | oui | oui | oui |
| `/admin/*`, `/scenarios/*` | non | oui | non | non |
| `/chauffeur/*` | non | non | oui | non |
| `/laabal/*` | non | non | non | oui |

## Public

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/health` | → `{"status": "ok"}` |
| GET | `/depotoirs?statut=&zone_id=` | Dépotoirs **vérifiés** en GeoJSON (`FeatureCollection`, propriétés : `id`, `statut`, `legalite`, `volume_estime`, `nb_signalements`, `zone_id`, `derniere_maj`) |
| GET | `/zones` | Zones (quartiers ou secteurs) en GeoJSON, avec la demande de déchets estimée (C1) |
| GET | `/points-regroupement` | Points du plan courant (scénario actif), GeoJSON |
| POST | `/signalements` | Créer un signalement (anonyme) |
| GET | `/signalements/suivi/{code_suivi}` | Statut d'un signalement |

**GET `/zones`** → `FeatureCollection` de `Polygon` (ou `MultiPolygon`), propriétés : `id`, `nom`, `population` (peut être `null`), `densite`, `demande_kg_jour`. La demande vaut `population × production_dechets_kg_hab_jour × coef_production(saison)` selon la config courante ; elle vaut `0` si la population est inconnue. Vide tant qu'aucune zone n'est chargée.

À la validation d'un signalement, le nouveau dépotoir est rattaché à la zone qui le contient (`zone_id`), ou `null` si aucune zone ne le contient.

**GET `/points-regroupement`** → `FeatureCollection` de `Point` + `plan_id` et `scenario_id` du plan courant. Propriétés : `id`, `capacite_kg`, `zone_id` (`null` hors zone ; peut être une zone ajoutée par le scénario), `explication`, `charge_kg_jour` (`null` si inconnue), `stock_entre_passages_kg`, `sature`, `depotoirs_desservis` (ids). Le plan est recalculé d'abord si les dépotoirs, les zones ou les paramètres ont changé. Vide s'il n'y a pas de scénario actif.

**POST `/signalements`** — `multipart/form-data` : `latitude`, `longitude`, `type_dechet`, `volume_estime`, `description` (optionnel), `photo` (fichier, optionnel), `note_vocale` (fichier audio webm ou mp4, optionnel, 60 s max). En-tête `X-Device-Token` : jeton anonyme de l'appareil (limite par appareil, filtre anti-abus).Réponse `201` :
```json
{ "id": 12, "code_suivi": "K7M-4QD", "statut": "en_attente_revue", "motif": null }
```
Si rejeté automatiquement : `"statut": "rejete_auto"` et `"motif": "hors zone d'étude"`.

**GET `/signalements/suivi/{code}`** → `{"code_suivi": "K7M-4QD", "statut": "verifie", "motif": null, "depotoir_id": 3}`

## Authentification

- `POST /auth/login` : `{"email": "...", "mot_de_passe": "..."}` → `{"access_token": "...", "token_type": "bearer", "role": "admin"}`
  - Après `securite.max_echecs_par_email` échecs pour un même e-mail, ou `max_echecs_par_ip` depuis une même adresse IP, en `fenetre_echecs_min` minutes : `429` `{"detail": "trop de tentatives, réessayez dans 15 min"}` avec l'en-tête `Retry-After` (secondes), **même avec le bon mot de passe**, pendant `blocage_min` minutes. Même comportement que le compte existe ou non. Une connexion réussie remet à zéro le compteur de l'e-mail. Le blocage est tracé dans le journal (D32).
- `GET /auth/moi` → `{"id": 1, "nom": "...", "role": "admin"}`
- Identifiants faux, email inconnu ou compte désactivé : même réponse `401 {"detail": "identifiants invalides"}`.
- Jeton absent, invalide ou expiré : `401`. Rôle insuffisant : `403`. Le rôle et l'état du compte sont relus en base à chaque requête.
- Durée du jeton : `securite.duree_token_min` (config). Le premier admin est créé au démarrage depuis `YILGMDE_ADMIN_EMAIL` et `YILGMDE_ADMIN_PASSWORD` (jamais dans le dépôt).

## Administrateur

**Modération**
- `GET /admin/signalements?statut=en_attente_revue` : file de modération, **les plus anciens d'abord** ; sans `statut`, tous les signalements. `422` si le statut est inconnu.
```json
[{ "id": 12, "latitude": 12.3714, "longitude": -1.5197, "type_dechet": "menager",
   "volume_estime": "moyen", "photo_url": "/admin/signalements/12/photo", "statut": "en_attente_revue",
   "score_auto": 0.82, "alertes": ["doublon_probable:3"], "motif": null, "depotoir_id": null,
   "cree_le": "2026-11-17T09:30:00+00:00" }]
```
- `GET /admin/signalements/{id}/photo` : la photo (`image/jpeg`, `image/png` ou `image/webp`), **admin seulement** ; `404` s'il n'y en a pas. Aucune photo n'est servie publiquement.
- `POST /admin/signalements/{id}/valider` : `{"fusionner_avec": null}` (ou l'id d'un dépotoir existant ; le corps peut être omis) → `{"signalement": {...}, "depotoir": {...}}`.
  - `fusionner_avec` nul : crée un dépotoir `actif`, `illegal`, `nb_signalements` 1.
  - sinon : fusion (`nb_signalements` + 1, jamais de doublon). Si le dépotoir est `eradique`, `sous_surveillance` ou `classe`, c'est une **réapparition** : il repasse `actif` et `nb_reapparitions` + 1. Dans les autres statuts, son statut ne change pas.
  - `404` si le signalement ou le dépotoir est inconnu ; `409` si le signalement n'est plus `en_attente_revue`.
- `POST /admin/signalements/{id}/rejeter` : `{"motif": "photo sans rapport"}` (motif obligatoire, 1 à 300 caractères) → le signalement, statut `rejete`. `404`, `409` comme ci-dessus ; `422` si le motif est vide.
- Valider ou rejeter fait évoluer le `score_confiance` (privé) de l'appareil qui a signalé : validation `s + gain × (1 − s)`, rejet `s − perte × s` (D33). Un appareil sous `verification.seuil_confiance_appareil` voit ses signalements suivants marqués « peu fiable » par la vérification automatique.
- Chaque validation et chaque rejet est écrit dans `journal_audit` ; un échec n'écrit rien.
- `POST /admin/signalements/import` (A4) : corps JSON = GeoJSON `FeatureCollection` de `Point`, propriétés `type_dechet`, `volume_estime`, `description` (facultative). Propriété facultative `jeton_appareil` : les règles de cet appareil (limite par heure, score de confiance) s'appliquent ; sans elle, pas de limite par appareil. Chaque entrée passe par **la même vérification automatique** que les citoyens (rejet d'office ou `en_attente_revue` avec alertes) ; les doublons à l'intérieur du lot sont repérés ; des coordonnées hors bornes donnent un `rejete_auto` « position incohérente ». Les entrées sans géométrie Point ou aux propriétés invalides sont listées dans `erreurs` sans bloquer les autres. Le jeu `data/sample/signalements_pieges.geojson` s'importe tel quel et donne les résultats de sa colonne `attendu`. Au plus `import.max_par_lot` entrées (`413` sinon) ; `422` si ce n'est pas une FeatureCollection. Une ligne au journal par lot.
```json
{ "importes": 4, "par_statut": {"en_attente_revue": 3, "rejete_auto": 1},
  "erreurs": [{"index": 4, "raison": "géométrie Point attendue"}, {"index": 5, "raison": "propriétés invalides : type_dechet"}],
  "signalements": [{"index": 0, "id": 12, "code_suivi": "K7M-4QD", "statut": "en_attente_revue", "motif": null, "alertes": []}] }
```

**Comptes et suivi**
- `POST /admin/utilisateurs` : `{"nom": "...", "email": "...", "mot_de_passe": "...", "role": "chauffeur"}` → `201` `{"id": 4, "nom": "...", "email": "...", "role": "chauffeur", "actif": true}`. `409` si l'email existe, `422` si mot de passe < 8 caractères ou > 72 octets, email invalide ou rôle inconnu.
- `GET /admin/utilisateurs` → liste de `{id, nom, email, role, actif}` (jamais de mot de passe)

**Dépotoirs (B5, B6)**
- `POST /admin/depotoirs` : `{"latitude": 12.37, "longitude": -1.52, "volume_estime": "moyen", "legalite": "officiel"}` (`volume_estime` et `legalite` facultatifs, `officiel` par défaut) → `201` le dépotoir, statut `actif`, zone calculée. Sert à saisir les **sites officiels** (jamais proposés à la brigade Laabal ni exportés comme dépôt sauvage).
- `PATCH /admin/depotoirs/{id}` : `{"legalite": "officiel"}` et/ou `{"statut": "classe"}` → le dépotoir. `classe` seulement depuis `sous_surveillance` (`409` sinon) ; tout autre statut → `422` (ils suivent les interventions Laabal). `404` si inconnu. Chaque changement est journalisé.

**Constats**
- `GET /admin/constats` → `{"nombre": 2, "montant_total_xof": 12500, "constats": [<constat>]}`.
- `GET /admin/journal?limit=50`
- `GET /admin/export/depotoirs.geojson?statut=actif&statut=eradique` (admin) : dépotoirs vérifiés en GeoJSON téléchargeable (`application/geo+json`, `depotoirs_yilgmde.geojson`), prêt à ouvrir dans JOSM. Par défaut : statuts `actif` et `intervention_planifiee` (présents sur le terrain), au moins `export_osm.min_signalements` signalements. Les propriétés ne sont **que des étiquettes OSM**, sans aucune donnée personnelle ; l'id interne est dans le `id` de la Feature. Export tracé dans le journal (D30).
```json
{ "type": "FeatureCollection",
  "metadata": { "genere_le": "...", "commune": "Ouagadougou", "statuts": ["actif", "intervention_planifiee"],
                "min_signalements": 1, "nombre": 1, "licence": null, "avertissement": "..." },
  "features": [{ "type": "Feature", "id": "yilgmde/depotoir/1",
                 "geometry": { "type": "Point", "coordinates": [-1.5201, 12.3701] },
                 "properties": { "amenity": "waste_dump_site", "waste": "plastic",
                                 "description": "Déchets plastiques, gravats",
                                 "check_date": "2026-11-15", "source": "survey;YilGmdé" } }] }
```
  Illégal → `amenity=waste_dump_site` ; officiel → `landuse=landfill`. `waste` seulement pour `menager` (`trash`), `plastiques` (`plastic`), `organique` (`organic`) ; tous les types vont dans `description`, le plus fréquent d'abord (signalements `verifie` seulement).
- `POST /admin/tournees/{id}/affecter` : `{"utilisateur_id": 4}` → la tournée avec `affectee_a`. Collecte → compte `chauffeur`, intervention → compte `laabal` (`422` sinon) ; `404` si la tournée n'est pas dans le plan courant ou si le compte est inconnu ou désactivé. Tracé dans le journal.

**Scénarios et plan**

Un scénario = des surcharges **partielles** de la config (`config/*.yaml`). Au démarrage, un scénario `base` (sans surcharge) est créé et **actif** s'il n'en existe aucun ; le scénario actif donne le « plan courant ». Chaque création, modification et activation est écrite dans `journal_audit`.

- `GET /scenarios` → `[{"id": 1, "nom": "base", "parametres": {}, "actif": true, "cree_par": null, "cree_le": "..."}]`
- `POST /scenarios` : `{"nom": "2 camions en moins", "base_sur": 1, "parametres": {}, "activer": false}` → `201` scénario. `base_sur` (optionnel) copie les paramètres d'un scénario puis applique `parametres`. `404` si `base_sur` est inconnu, `422` si les paramètres sont invalides.
- `GET /scenarios/{id}` → scénario ; `404` s'il est inconnu.
- `PUT /scenarios/{id}/parametres` : modification **partielle**, fusionnée sur les paramètres du scénario ; renvoie le **plan recalculé**. `422` (et rien n'est enregistré) si la config devient invalide.
  - `{"saison": "pluies"}` (raccourci de `{"scenario": {"saison": "pluies"}}`) : production × `coef_production`, vitesse × `coef_vitesse_camion` (D3).
  - `{"camions": [{"id": "camion_2", "disponible": false}]}` : fusion par `id` ; un camion indisponible n'est jamais utilisé (D2).
  - `{"zones_ajoutees": [<Feature ou géométrie GeoJSON, ou sa chaîne JSON>]}` : nouveau quartier (D4), propriétés `nom`, `population` (sans population : seuls ses dépotoirs reçoivent un point). Les zones **s'ajoutent** à celles déjà ajoutées. Les dépotoirs sans zone qu'elles contiennent leur sont rattachés.
  - tout autre paramètre de la config : `{"collecte": {"frequence_passages_par_semaine": 3}}`, `{"points_regroupement": {"distance_max_a_pied_m": 200}}`, `{"laabal": {"nombre_brigades": 2}}`, `{"mairie": {"budget_mensuel_xof": 4000000}}`…
- `POST /scenarios/{id}/activer` → scénario, devenu le seul actif.
- `POST /scenarios/{id}/calculer` → Plan, calcul forcé.
- `GET /scenarios/{id}/plan` → dernier Plan, **recalculé d'abord si les entrées ont changé** (dépotoirs, zones, paramètres) ; sinon le même plan est renvoyé.
- `POST /scenarios/{id}/simuler` : `{"jours": 30, "graine": 42}` (corps optionnel ; `jours` de 1 à 365, défaut 30 ; `graine` par défaut celle de la config). Simule sur le plan à jour du scénario ; **même graine = mêmes résultats**. `422` si `jours` hors bornes, `404` si scénario inconnu. Les colonnes `pct_collecte`, `depotoirs_actifs`, `cout_xof`, `distance_km` sont enregistrées dans `indicateur_simulation` (la simulation précédente du même plan est remplacée).
```json
{ "scenario_id": 1, "plan_id": 7, "graine": 42,
  "indicateurs": [{ "jour": 1, "pct_collecte": 78.2, "depotoirs_actifs": 2, "cout_xof": 0, "distance_km": 0.0,
                    "production_kg": 10000, "dechets_sauvages_kg": 2185, "stock_points_kg": 7816, "collecte_kg": 0,
                    "passage": false, "collecte_suspendue": false, "depotoirs_eradiques": 2,
                    "depotoirs_sous_surveillance": 0, "reapparitions": 0, "constats": 0, "amendes_xof": 0,
                    "budget_restant_xof": 166667 }],
  "resume": { "jours": 30, "pct_collecte_moyen": 77.7, "depotoirs_actifs_debut": 2, "depotoirs_actifs_fin": 5,
              "nouveaux_depotoirs": 41, "depotoirs_eradiques": 54, "reapparitions": 16, "dechets_sauvages_kg": 66921,
              "passages_collecte": 8, "passages_suspendus_budget": 0, "cout_total_xof": 804048,
              "distance_totale_km": 1110.2, "amendes_total_xof": 150000, "constats": 15, "budget_restant_xof": 4345952 } }
```
  - `pct_collecte` : part de la production du jour arrivée aux points (pré-collecte + apport volontaire − débordement). `cout_xof`, `distance_km` : non nuls les seuls jours de passage. `budget_restant_xof` : `null` si pas de budget dans la config.
- `GET /scenarios/comparer?ids=1,2&jours=30&graine=42` (D6) : 2 à 4 scénarios distincts (`422` sinon, `404` si l'un est inconnu), plan à jour et simulation de chacun avec la **même graine** (par défaut celle de la config).
```json
{ "jours": 30, "graine": 42,
  "scenarios": [{ "id": 1, "nom": "base", "parametres": {}, "plan_id": 7 }, { "id": 2, "nom": "2 camions en moins", "parametres": {...}, "plan_id": 8 }],
  "indicateurs": [{ "source": "simulation", "indicateur": "dechets_sauvages_kg", "valeurs": [66921, 93300],
                    "ecart_a_la_reference": [0, 26379], "sens": "moins", "meilleur": [1] }],
  "details": [{ "scenario_id": 1, "plan": { <indicateurs du plan> }, "simulation": { <résumé de /simuler> } }] }
```
  Le premier scénario est la référence des écarts. `sens` : `plus` ou `moins` est meilleur, `null` si ça dépend ; `meilleur` liste le ou les scénarios gagnants, `null` si égalité ou sans sens. Indicateurs comparés : plan (`dechets_collectes_pct`, `nb_points_regroupement`, `distance_totale_km`, `cout_total_xof`, `cout_mensuel_estime_xof`) et simulation (`pct_collecte_moyen`, `depotoirs_actifs_fin`, `dechets_sauvages_kg`, `cout_total_xof`, `passages_suspendus_budget`).

**Plan (réponse)**
```json
{
  "id": 7, "scenario_id": 1, "calcule_le": "2026-11-17T10:00:00+00:00", "duree_calcul_ms": 840,
  "points_regroupement": [
    { "id": 1, "latitude": 12.37, "longitude": -1.52, "capacite_kg": 3000, "zone_id": 2,
      "charge_kg_jour": 174, "stock_entre_passages_kg": 607, "sature": false, "depotoirs_desservis": [1],
      "explication": "Zone exemple A : 6000 kg/jour, 33 point(s) (capacité : 7, marche ≤ 300 m : 26, ...) ; couverture 96 %. ..." }
  ],
  "tournees": [
    { "id": 1, "type": "collecte", "camion_id": "camion_1", "rotation": 1, "affectee_a": null,
      "distance_km": 14.2, "duree_min": 95, "cout_xof": 21000, "charge_kg": 5930,
      "arrets": [{ "id": 31, "ordre": 1, "cible_type": "point_regroupement", "cible_id": 1,
                   "latitude": 12.37, "longitude": -1.52, "charge_kg": 607, "statut": "a_faire" }] },
    { "id": 2, "type": "intervention", "camion_id": null, "brigade": 1, "distance_km": 6.8, "duree_min": 150, "cout_xof": 0,
      "arrets": [{ "id": 40, "ordre": 1, "cible_type": "depotoir", "cible_id": 3, "latitude": 12.37, "longitude": -1.52,
                   "priorite": 7.5, "raison": "volume moyen, 2 réapparition(s), 1 signalement(s)", "statut": "a_faire" }] }
  ],
  "indicateurs": {
    "demande_totale_kg_jour": 10000, "zones_population_inconnue": [], "nb_points_regroupement": 66,
    "stock_a_collecter_kg": 35000, "dechets_collectes_pct": 100.0, "depotoirs_actifs": 2,
    "depotoirs_planifies_laabal": 2, "depotoirs_en_attente_laabal": 0,
    "camions_utilises": ["camion_1", "camion_2", "camion_3"], "camions_indisponibles": [],
    "distance_totale_km": 145.1, "cout_total_xof": 100000, "cout_mensuel_estime_xof": 866667,
    "budget_mensuel_xof": 5000000, "budget_depasse": false, "saison": "seche", "methode_tournees": "ortools"
  },
  "non_couverts": [
    { "zone_id": 3, "raison": "population inconnue et aucun dépotoir actif : besoin non estimable" },
    { "point_regroupement_id": 12, "raison": "capacité ou temps de collecte insuffisants (camion_2 indisponible)" },
    { "depotoir_id": 5, "raison": "capacité ou temps de collecte insuffisants (camion_2 indisponible)" }
  ],
  "laabal_en_attente": [{ "depotoir_id": 4, "priorite": 2.5, "raison": "volume moyen, 1 signalement(s)",
                          "motif": "capacité Laabal atteinte (1 brigade(s) × 2 dépotoir(s)/jour)" }],
  "zones_ajoutees": []
}
```
- Une tournée de collecte = une **rotation** (dépôt → points → dépôt) d'un camion ; `cout_xof` inclut le coût journalier du camion sur sa 1re rotation. `cout_total_xof` = coût d'un passage de collecte ; `cout_mensuel_estime_xof` = ce coût × passages par mois.
- `dechets_collectes_pct` = part du stock des points effectivement chargée dans les tournées.
- `cible_id` d'un arrêt de collecte = `id` du point de regroupement de ce plan ; d'un arrêt d'intervention = `id` du dépotoir.

## Chauffeur

Tout porte sur le **plan courant** (scénario actif, recalculé si les entrées ont changé). Un recalcul du même jour **garde** les affectations (même camion et rotation, même brigade) et les arrêts déjà `effectue` (même point ou même dépotoir).

- `GET /chauffeur/tournee` → `{"plan_id": 7, "tournees": [<tournées de collecte affectées à ce chauffeur, avec arrêts>]}` (liste vide si rien n'est affecté).
- `POST /chauffeur/arrets/{arret_id}/effectue` → l'arrêt, `statut: "effectue"`. `403` si l'arrêt n'est pas dans une de ses tournées, `404` s'il n'est pas dans le plan courant.
- `POST /chauffeur/incidents` : `{"type": "panne", "description": "...", "camion_id": null}` (`panne` ou `route_impraticable`).
  - `panne` : le camion (par défaut celui de sa tournée ; `422` s'il n'en a pas et n'en donne pas, `404` si inconnu) devient `disponible: false` dans les paramètres du scénario actif → `{"type": "panne", "camion_id": "camion_2", "enregistre": true, "plan": <plan recalculé>}`.
  - `route_impraticable` : tracé dans le journal → `{"type": "route_impraticable", "enregistre": true, "plan": null}`.

## Brigade Laabal

- `GET /laabal/depotoirs-a-traiter` → dépotoirs `illegal` en statut `actif` ou `intervention_planifiee`, triés par `priorite` décroissante : `[{"id", "latitude", "longitude", "zone_id", "statut", "volume_estime", "nb_signalements", "nb_reapparitions", "priorite", "raison"}]`.
- `GET /laabal/tournee` → `{"plan_id", "tournees": [<tournées d'intervention affectées à ce compte>], "en_attente": [...]}`.
- `POST /laabal/arrets/{arret_id}/effectue` : comme pour le chauffeur.
- `POST /laabal/depotoirs/{id}/intervention` : `multipart/form-data`, `statut` = `en_cours` (dépotoir → `intervention_planifiee`) ou `eradique` (dépotoir → `eradique`), `photo` optionnelle (JPEG/PNG/WebP, jamais publique) → `{"intervention_id", "depotoir_id", "statut_depotoir", "photo": true}`. `409` si site officiel ou dépotoir ni `actif` ni `intervention_planifiee` ; `404`, `413`, `422` (photo).
- `POST /laabal/depotoirs/{id}/surveillance` : `eradique` → `sous_surveillance` ; `409` sinon.
- Chaque intervention et mise sous surveillance est tracée dans le journal. Un signalement validé ensuite près du dépotoir le fait réapparaître (A3).
- `POST /laabal/constats` (H4) : `multipart/form-data`, `depotoir_id`, `description` (facultative, 500 caractères), `montant_xof` (≥ 0, par défaut `laabal.montant_amende_xof`), `preuves` (0 à 5 photos JPEG/PNG/WebP, jamais publiques) → `201` `{"id", "depotoir_id", "laabal_id", "date", "description", "preuves": 2, "montant_xof", "statut": "enregistre"}`. `409` sur un site officiel ; `404`, `413`, `422`. Journalisé.
- `GET /laabal/constats` → ses propres constats, du plus récent au plus ancien.
