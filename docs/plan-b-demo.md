# Plan B de démonstration hors-ligne

## Dossier à préparer avant la présentation

- Une copie locale du dépôt et de l'environnement Python `.venv`.
- `frontend/node_modules/` installé et `npm run build` validé.
- Une base SQLite de démonstration déjà remplie dans `data/processed/yilgmde.sqlite3`.
- Les fichiers générés sous `docs/rapport/` : résultats, courbes, carte et plan de gestion.
- Une vidéo courte de l'enchaînement complet et 5 captures : signalement, modération, plan, simulation, comparaison.
- Les identifiants de démonstration stockés hors dépôt (variables d'environnement ou gestionnaire de mots de passe).

## Démarrage local sans Internet

```powershell
Set-Location C:\Users\HP\HACK_MIN\yilgmde
$env:YILGMDE_ADMIN_EMAIL = "admin@ouaga.bf"
$env:YILGMDE_ADMIN_PASSWORD = "mot-de-passe-de-demo"
$env:YILGMDE_JWT_SECRET = "secret-de-demo-long-et-aleatoire"
python scripts/charger_exemples.py --ouaga --demo
uvicorn backend.main:app
```

Dans un second terminal :

```powershell
Set-Location C:\Users\HP\HACK_MIN\yilgmde\frontend
npm run dev
```

## Réponse aux incidents

| Incident | Réponse immédiate |
|---|---|
| Pas de réseau | Utiliser l'application locale ; les tuiles déjà visitées restent dans le cache PWA. Sinon montrer la carte et les captures préparées. |
| API indisponible | Montrer la vidéo ou passer le front en mode mock (`VITE_USE_MOCK=true`). Puis expliquer que le moteur et les résultats du rapport sont générés localement. |
| Calcul communal trop long | Sélectionner l'arrondissement 9 ; le rapport utilise ce périmètre et une graine 42. |
| Compte admin absent | Reprendre les trois variables `YILGMDE_ADMIN_*` / `YILGMDE_JWT_SECRET`, redémarrer l'API, puis se connecter. |
| Navigateur ou carte bloqués | Ouvrir les images de `docs/rapport/` et suivre le script de démo sans interaction. |

## Vérification 15 minutes avant le jury

1. Lancer l'API et vérifier `http://localhost:8000/health`.
2. Ouvrir le front, se connecter, charger `/admin/plan`.
3. Lancer une simulation sur 30 jours, graine 42.
4. Vérifier une comparaison base / variante.
5. Ouvrir les captures et la vidéo, même si la démo en direct fonctionne.