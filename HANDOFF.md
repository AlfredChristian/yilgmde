# HANDOFF

> À remplir **uniquement** quand on change de conversation avec l'IA ou qu'on passe la main. Une section par personne. Écraser l'ancien contenu.

## Christian (front)

- **Objectif en cours** : afficher la carte des dépotoirs (Leaflet) dans le front React, alimentée par les données d'exemple.
- **Fichiers modifiés** : `frontend/` créé avec Vite + React ; `leaflet` et `react-leaflet` installés (`package.json`). Branche `front/init-react`.
- **Bugs ouverts** : aucun.
- **Prochaine étape précise** :
  1. créer `frontend/.env.example` (`VITE_API_URL`, `VITE_USE_MOCK=true`) ;
  2. copier les fichiers de `data/sample/` dans `frontend/public/mock/` ;
  3. créer `frontend/src/api/client.js` avec `getDepotoirs()` ;
  4. créer un composant `Carte.jsx` (MapContainer centré sur 12.3714, -1.5197, importer le CSS de Leaflet) ;
  5. y afficher les dépotoirs d'exemple, puis l'utiliser dans `App.jsx`.

## Faissal (back / moteur)

- **Objectif en cours** : zones et demande (C1) terminés (branche `back/zones-demande`). `main` contient déjà A1, l'authentification et A3 (PR #7, #8, #9). Ensuite : points de regroupement (C2).
- **Fichiers modifiés** : `simulation/geometrie.py` (point dans un polygone), `simulation/demande.py` (`estimer_demande`, fonction pure), `backend/zones.py` (lecture, import GeoJSON tout ou rien, `zone_id_pour_point`), `backend/routes/zones.py` (`GET /zones`), `backend/routes/admin_signalements.py` (le dépotoir créé à la validation reçoit son `zone_id`), `backend/exemples.py` et `scripts/charger_exemples.py`, `data/sample/zones_exemple.geojson` (fictif), `docs/api-contract.md`, `tests/test_geometrie.py`, `tests/test_demande.py`, `tests/test_zones.py` (28 nouveaux tests), `TODO.md`, `DECISIONS.md` (D23).
- **Bugs ouverts** : aucun. Il n'existe **aucune vraie donnée de zone** : polygones et populations réels sont à fournir (Cramer : recensement ou mairie) au format de `zones_exemple.geojson`, via `importer_zones_geojson`. Pas encore de route admin d'import de zones (utile pour D4, nouveau quartier). Pas de limitation des tentatives de connexion. `contributeur.score_confiance` n'est jamais mis à jour. La suite complète n'a pas été relancée sur cette branche après l'ajout de zones (seuls les 28 nouveaux tests l'ont été).
- **Pour lancer avec des données** : `python scripts/charger_exemples.py`, puis `uvicorn backend.main:app --reload` ; `GET /depotoirs` et `GET /zones` ne sont plus vides. Le front peut quitter le mode mock (`VITE_USE_MOCK=false`).
- **Prochaine étape précise** :
  1. installer scikit-learn et OR-Tools dans l'environnement, puis C2 : `simulation/regroupement.py`, fonction pure `placer_points(depotoirs_actifs, zones, config)` avec `points_regroupement.capacite_kg` et `distance_max_a_pied_m`, chaque point avec son `explication` ;
  2. C3 : tournées OR-Tools avec repli plus proche voisin et temps limite ; `camions_disponibles(config)` pour ne jamais utiliser un camion en panne ;
  3. C4 : `calculer_plan(donnees, config)` qui assemble C1, C2, C3 ; routes `/scenarios` et `/points-regroupement`.

## Cramer (docs / données / présentation)

- **Objectif en cours** :
- **Fichiers modifiés** :
- **Bugs ouverts** :
- **Prochaine étape précise** :
