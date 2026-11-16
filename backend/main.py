from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import db
from backend.config import charger_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    # La config est lue une fois au démarrage ; chaque scénario la surcharge ensuite
    # de façon partielle (voir backend/config.py), sans jamais la modifier.
    app.state.config = charger_config("ouagadougou")
    app.state.db = db.connecter()
    db.initialiser(app.state.db)
    yield
    app.state.db.close()


app = FastAPI(title="Yilgmde API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # serveur de dev du front
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}
