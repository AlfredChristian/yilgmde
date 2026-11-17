"""Schémas Pydantic. Valeurs d'énumération alignées sur `docs/api-contract.md`
et `docs/modele-donnees.md`."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    """Réponse 201 de POST /signalements (200 si `id_client` déjà reçu : renvoi)."""

    id: int
    code_suivi: str
    statut: StatutSignalement
    motif: str | None = None
    photo_masquee: dict | None = None     # {"visages": 1, "plaques": 0, "methode": "opencv-haar"}
    deja_recu: bool = False               # True : renvoi d'un signalement déjà enregistré


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
    motif: str | None = None
    depotoir_id: int | None = None
    cree_le: datetime


class Verdict(BaseModel):
    """Résultat de la vérification automatique d'un signalement (A2)."""

    statut: StatutSignalement          # rejete_auto ou en_attente_revue
    motif: str | None = None           # toujours renseigné en cas de rejet
    score_auto: float = Field(ge=0, le=1)
    alertes: list[str] = []


# ---------- Modération (A3) ----------

class ValiderEntree(BaseModel):
    """Corps de POST /admin/signalements/{id}/valider."""

    fusionner_avec: int | None = None   # id d'un dépotoir existant, sinon on en crée un


class RejeterEntree(BaseModel):
    """Corps de POST /admin/signalements/{id}/rejeter : le motif est obligatoire."""

    motif: str = Field(min_length=1, max_length=300)

    @field_validator("motif")
    @classmethod
    def _motif_non_vide(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("le motif ne peut pas être vide")
        return v


class DepotoirSortie(Position):
    id: int
    statut: StatutDepotoir
    legalite: Legalite
    volume_estime: VolumeEstime
    zone_id: int | None = None
    nb_signalements: int
    nb_reapparitions: int
    premiere_detection: datetime
    derniere_maj: datetime


class ResultatValidation(BaseModel):
    signalement: SignalementAdmin
    depotoir: DepotoirSortie


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


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UtilisateurAdmin(UtilisateurSortie):
    """Ligne de GET /admin/utilisateurs (et réponse de la création)."""

    email: str
    actif: bool


class UtilisateurCreation(BaseModel):
    nom: str = Field(min_length=1)
    email: str
    mot_de_passe: str = Field(min_length=8)
    role: Role

    @field_validator("email")
    @classmethod
    def _email_valide(cls, v: str) -> str:
        if not _EMAIL.match(v.strip()):
            raise ValueError("email invalide")
        return v

    @field_validator("mot_de_passe")
    @classmethod
    def _limite_bcrypt(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:  # bcrypt ignore ou refuse au-delà de 72 octets
            raise ValueError("mot de passe trop long (72 octets maximum)")
        return v


# --- Scénarios (C4, D1–D4) -----------------------------------------------------------

class ScenarioCreation(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    base_sur: int | None = None          # copie les paramètres de ce scénario
    parametres: dict = Field(default_factory=dict)
    activer: bool = False                # devient le scénario du « plan courant »


class ScenarioSortie(BaseModel):
    id: int
    nom: str
    parametres: dict
    actif: bool
    cree_par: int | None
    cree_le: str


class SimulationEntree(BaseModel):
    jours: int = Field(default=30, ge=1, le=365)
    graine: int | None = None          # par défaut : scenario.graine_aleatoire de la config
