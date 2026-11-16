from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Yilgmde API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # serveur de dev du front
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}