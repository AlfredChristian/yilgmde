# Front Yilgmdé (React + Vite, PWA)

## Lancer avec les données d'exemple (sans API)

```
npm install
npm run dev            # VITE_USE_MOCK=true (voir .env.example)
```

Comptes de test du mode mock : `admin@test`, `chauffeur@test`, `laabal@test`, mot de passe `test`.

## Lancer branché sur la vraie API

1. Dans un premier terminal, à la racine du dépôt, avec une base vide :

   ```
   set YILGMDE_ADMIN_EMAIL=admin@ouaga.bf          (PowerShell : $env:YILGMDE_ADMIN_EMAIL="admin@ouaga.bf")
   set YILGMDE_ADMIN_PASSWORD=admin12345
   python scripts/charger_exemples.py --ouaga
   uvicorn backend.main:app --reload
   ```

2. Dans `frontend/`, créer `.env.local` (ignoré par git) :

   ```
   VITE_API_URL=/api
   VITE_USE_MOCK=false
   ```

   puis `npm run dev`. Vite redirige `/api` vers `http://localhost:8000`.

3. Se connecter avec le compte admin. Les comptes chauffeur et Laabal se créent avec
   `POST /admin/utilisateurs`, puis l'admin affecte une tournée avec
   `POST /admin/tournees/{id}/affecter` (voir `docs/api-contract.md`, ou `http://localhost:8000/docs`).

## Où l'API est appelée

Tout passe par `src/api/client.js` : les pages ne savent pas si les données viennent du mock
ou de l'API. Le formulaire du plan (`pages/Plan.jsx`) travaille sur des champs simples
(périmètre, camions en panne, saison, budget) que `versApi` traduit en paramètres de scénario.
