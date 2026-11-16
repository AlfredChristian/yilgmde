"""Schémas Pydantic. Valeurs d'énumération alignées sur `docs/api-contract.md`
et `docs/modele-donnees.md`."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TypeDechet(str, Enum):
    menager = "menager"
    gravats = "gravats"
    encombrants = "encombrants"
    plastiques = "plastiques"
    organique = "organique"
    autre = "autre"


class VolumeEstime(str, Enum):
    petit = "petit"
    moyen = "moyen"
    gros = "gros"


class StatutSignalement(str, Enum):
    soumis = "soumis"
    rejete_auto = "rejete_auto"
    en_attente_revue = "en_attente_revue"
    verifie = "verifie"
    rejete = "rejete"


class StatutDepotoir(str, Enum):
    actif = "actif"
    intervention_planifiee = "intervention_planifiee"
    eradique = "eradique"
    sous_surveillance = "sous_surveillance"
    classe = "classe"


class Legalite(str, Enum):
    illegal = "illegal"
    officiel = "officiel"


class Role(str, Enum):
    admin = "admin"
    chauffeur = "chauffeur"
    laabal = "laabal"


# ---------- Signalements ----------

class Position(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class SignalementEntree(Position):
    """Corps de POST /signalements (champs du formulaire multipart, sans la photo)."""

    type_dechet: TypeDechet
    volume_estime: VolumeEstime
    description: str | None = Field(default=None, max_length=500)


class SignalementCree(BaseModel):
    """Réponse 201 de POST /signalements."""

    id: int
    code_suivi: str
    statut: StatutSignalement
    motif: str | None = None


class SuiviSignalement(BaseModel):
    code_suivi: str
    statut: StatutSignalement
    motif: str | None = None
    depotoir_id: int | None = None


class SignalementAdmin(Position):
    """Ligne de GET /admin/signalements."""

    id: int
    type_dechet: TypeDechet
    volume_estime: VolumeEstime
    photo_url: str | None = None
    statut: StatutSignalement
    score_auto: float | None = None
    alertes: list[str] = []
    cree_le: datetime


class Verdict(BaseModel):
    """Résultat de la vérification automatique d'un signalement (A2)."""

    statut: StatutSignalement          # rejete_auto ou en_attente_revue
    motif: str | None = None           # toujours renseigné en cas de rejet
    score_auto: float = Field(ge=0, le=1)
    alertes: list[str] = []


# ---------- Authentification ----------

class LoginEntree(BaseModel):
    email: str
    mot_de_passe: str


class TokenSortie(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


class UtilisateurSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    role: Role


class UtilisateurCreation(BaseModel):
    nom: str = Field(min_length=1)
    email: str
    mot_de_passe: str = Field(min_length=8)
    role: Role
