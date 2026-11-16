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
| GET | `/points-regroupement` | Points du plan courant, GeoJSON |
| POST | `/signalements` | Créer un signalement (anonyme) |
| GET | `/signalements/suivi/{code_suivi}` | Statut d'un signalement |

**POST `/signalements`** — `multipart/form-data` : `latitude`, `longitude`, `type_dechet`, `volume_estime`, `description` (optionnel), `photo` (fichier, optionnel).
Réponse `201` :
```json
{ "id": 12, "code_suivi": "K7M-4QD", "statut": "en_attente_revue", "motif": null }
```
Si rejeté automatiquement : `"statut": "rejete_auto"` et `"motif": "hors zone d'étude"`.

**GET `/signalements/suivi/{code}`** → `{"code_suivi": "K7M-4QD", "statut": "verifie", "motif": null, "depotoir_id": 3}`

## Authentification

- `POST /auth/login` : `{"email": "...", "mot_de_passe": "..."}` → `{"access_token": "...", "token_type": "bearer", "role": "admin"}`
- `GET /auth/moi` → `{"id": 1, "nom": "...", "role": "admin"}`

## Administrateur

**Modération**
- `GET /admin/signalements?statut=en_attente_revue` →
```json
[{ "id": 12, "latitude": 12.3714, "longitude": -1.5197, "type_dechet": "menager",
   "volume_estime": "moyen", "photo_url": "/uploads/12.jpg", "statut": "en_attente_revue",
   "score_auto": 0.82, "alertes": ["doublon_probable:3"], "cree_le": "2026-11-17T09:30:00Z" }]
```
- `POST /admin/signalements/{id}/valider` : `{"fusionner_avec": null}` (ou l'id d'un dépotoir existant) → `{"signalement": {...}, "depotoir": {...}}`
- `POST /admin/signalements/{id}/rejeter` : `{"motif": "photo sans rapport"}`
- `POST /admin/signalements/import` (P2) : GeoJSON `FeatureCollection` de `Point`, propriétés `type_dechet`, `volume_estime`, `description`.

**Comptes et suivi**
- `POST /admin/utilisateurs` : `{"nom": "...", "email": "...", "mot_de_passe": "...", "role": "chauffeur"}`
- `GET /admin/utilisateurs`
- `GET /admin/journal?limit=50`
- `GET /admin/export/depotoirs.geojson` : dépotoirs vérifiés, prêt pour OSM
- `POST /admin/tournees/{id}/affecter` (P2) : `{"utilisateur_id": 4}`

**Scénarios et plan**
- `GET /scenarios` · `POST /scenarios` : `{"nom": "2 camions en moins", "base_sur": 1, "parametres": {}}`
- `GET /scenarios/{id}`
- `PUT /scenarios/{id}/parametres` : modification **partielle**, fusionnée sur la config ; renvoie le **plan recalculé**.
  Exemples : `{"saison": "pluies"}` · `{"camions": [{"id": "camion_2", "disponible": false}]}` · `{"zones_ajoutees": ["<GeoJSON de la zone>"]}`
- `POST /scenarios/{id}/calculer` → Plan
- `GET /scenarios/{id}/plan` → dernier Plan
- `POST /scenarios/{id}/simuler` : `{"jours": 30, "graine": 42}` → `{"indicateurs": [{"jour": 1, "pct_collecte": 61.2, "depotoirs_actifs": 14, "cout_xof": 140000, "distance_km": 12.4}]}`
- `GET /scenarios/comparer?ids=1,2` (P2)

**Plan (réponse type)**
```json
{
  "id": 7, "scenario_id": 1, "calcule_le": "2026-11-17T10:00:00Z", "duree_calcul_ms": 840,
  "points_regroupement": [
    { "id": 1, "latitude": 12.37, "longitude": -1.52, "capacite_kg": 3000, "zone_id": 2,
      "explication": "Centre de gravité de 5 dépotoirs, à moins de 300 m des ménages desservis" }
  ],
  "tournees": [
    { "id": 1, "type": "collecte", "camion_id": "camion_1", "distance_km": 14.2, "duree_min": 95, "cout_xof": 21000,
      "arrets": [{ "ordre": 1, "cible_type": "point_regroupement", "cible_id": 1,
                   "latitude": 12.37, "longitude": -1.52, "statut": "a_faire" }] }
  ],
  "indicateurs": { "dechets_collectes_pct": 82.5, "depotoirs_actifs": 14, "cout_total_xof": 4200000, "distance_totale_km": 310.4 },
  "non_couverts": [{ "depotoir_id": 5, "raison": "capacité insuffisante (camion_2 indisponible)" }]
}
```

## Chauffeur

- `GET /chauffeur/tournee` → Tournée du jour avec ses arrêts.
- `POST /chauffeur/arrets/{arret_id}/effectue`
- `POST /chauffeur/incidents` : `{"type": "panne", "description": "..."}` (`panne` ou `route_impraticable`). Une `panne` marque le camion indisponible et déclenche le recalcul du scénario actif.

## Brigade Laabal

- `GET /laabal/depotoirs-a-traiter` → liste triée par `priorite` (avec `raison`).
- `GET /laabal/tournee` → tournée d'intervention du jour.
- `POST /laabal/depotoirs/{id}/intervention` : `{"statut": "en_cours"}` ou `{"statut": "eradique"}` (photo optionnelle, multipart).
- `POST /laabal/depotoirs/{id}/surveillance` : met le dépotoir `sous_surveillance`.
- `POST /laabal/constats` (P2) : `{"depotoir_id": 3, "description": "...", "montant_xof": 10000}` (preuves en multipart).
