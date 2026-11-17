import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import db
from backend.config import charger_config
from backend.limitation import creer_limiteurs
from backend.plans import creer_scenario_base_si_absent
from backend.routes import (admin_donnees, admin_export, admin_signalements, admin_utilisateurs, auth, depotoirs,
                            donnees_ouvertes, scenarios, signalements, terrain, zones)
from backend.utilisateurs import creer_admin_si_absent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # La config est lue une fois au démarrage ; chaque scénario la surcharge ensuite
    # de façon partielle (voir backend/config.py), sans jamais la modifier.
    # G2 : la commune se choisit sans toucher au code (config/<ville>.yaml).
    app.state.config = charger_config(os.environ.get("YILGMDE_VILLE", "ouagadougou") or None)
    app.state.db = db.connecter()
    db.initialiser(app.state.db)
    # Premier admin : variables d'environnement, jamais de compte dans le dépôt (D11).
    creer_admin_si_absent(app.state.db)
    # Scénario « base » (sans surcharge), actif : donne le plan courant dès le départ.
    creer_scenario_base_si_absent(app.state.db)
    # Compteurs d'échecs de connexion (D32), en mémoire : remis à zéro au démarrage.
    app.state.limiteurs_login = creer_limiteurs(app.state.config)
    yield
    app.state.db.close()


app = FastAPI(title="Yilgmde API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # serveur de dev du front
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(signalements.router)
app.include_router(depotoirs.router)
app.include_router(zones.router)
app.include_router(auth.router)
app.include_router(admin_utilisateurs.router)
app.include_router(admin_signalements.router)
app.include_router(admin_donnees.router)
app.include_router(scenarios.router)
app.include_router(terrain.router)
app.include_router(admin_export.router)
app.include_router(donnees_ouvertes.router)


@app.get("/health")
def health():
    return {"status": "ok"}
