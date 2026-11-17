"""Accès SQLite (D14). Schéma fidèle à `docs/modele-donnees.md`.

Les opérations spatiales (distances, appartenance à une zone) sont faites en
Python, pas en SQL. Les champs de type liste ou dictionnaire sont stockés en JSON.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

CHEMIN_DB_DEFAUT = Path(os.environ.get("YILGMDE_DB", "data/processed/yilgmde.sqlite3"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS utilisateur (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    mot_de_passe_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'chauffeur', 'laabal')),
    actif INTEGER NOT NULL DEFAULT 1,
    cree_le TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contributeur (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jeton_appareil TEXT NOT NULL UNIQUE,
    nb_signalements INTEGER NOT NULL DEFAULT 0,
    score_confiance REAL NOT NULL DEFAULT 0.5,
    bloque INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS zone (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    geometrie TEXT NOT NULL,          -- polygone GeoJSON
    population INTEGER,
    densite REAL
);

CREATE TABLE IF NOT EXISTS depotoir (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    zone_id INTEGER REFERENCES zone(id),
    volume_estime TEXT NOT NULL CHECK (volume_estime IN ('petit', 'moyen', 'gros')),
    statut TEXT NOT NULL DEFAULT 'actif' CHECK (statut IN
        ('actif', 'intervention_planifiee', 'eradique', 'sous_surveillance', 'classe')),
    legalite TEXT NOT NULL DEFAULT 'illegal' CHECK (legalite IN ('illegal', 'officiel')),
    nb_signalements INTEGER NOT NULL DEFAULT 0,
    nb_reapparitions INTEGER NOT NULL DEFAULT 0,
    premiere_detection TEXT NOT NULL,
    derniere_maj TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signalement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contributeur_id INTEGER REFERENCES contributeur(id),
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    photo TEXT,
    description TEXT,
    type_dechet TEXT NOT NULL,
    volume_estime TEXT NOT NULL,
    code_suivi TEXT NOT NULL UNIQUE,
    statut TEXT NOT NULL CHECK (statut IN
        ('soumis', 'rejete_auto', 'en_attente_revue', 'verifie', 'rejete')),
    motif TEXT,
    score_auto REAL,
    alertes TEXT NOT NULL DEFAULT '[]',   -- JSON : liste de chaînes
    depotoir_id INTEGER REFERENCES depotoir(id),
    valide_par INTEGER REFERENCES utilisateur(id),
    valide_le TEXT,
    cree_le TEXT NOT NULL,                -- réception par le serveur
    capture_le TEXT,                      -- prise de vue sur le téléphone (envoi différé, hors connexion)
    id_client TEXT,                       -- identifiant choisi par l'application : un renvoi n'est pas un doublon
    note_vocale TEXT,                     -- fichier audio (jamais public)
    masquage TEXT                         -- JSON : visages et plaques floutés sur la photo
);
CREATE INDEX IF NOT EXISTS idx_signalement_statut ON signalement(statut);
CREATE INDEX IF NOT EXISTS idx_signalement_contributeur ON signalement(contributeur_id, cree_le);

CREATE TABLE IF NOT EXISTS scenario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    parametres TEXT NOT NULL DEFAULT '{}',   -- JSON, fusionné sur config/
    cree_par INTEGER REFERENCES utilisateur(id),
    cree_le TEXT NOT NULL,
    actif INTEGER NOT NULL DEFAULT 0         -- scénario dont le plan est le « plan courant »
);

CREATE TABLE IF NOT EXISTS plan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id INTEGER NOT NULL REFERENCES scenario(id),
    calcule_le TEXT NOT NULL,
    duree_calcul_ms INTEGER,
    indicateurs TEXT NOT NULL DEFAULT '{}',
    non_couverts TEXT NOT NULL DEFAULT '[]',
    signature TEXT,                          -- empreinte des entrées (données + paramètres)
    details TEXT NOT NULL DEFAULT '{}'       -- JSON : reste de la sortie du moteur
);

CREATE TABLE IF NOT EXISTS point_regroupement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL REFERENCES plan(id),
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    capacite_kg REAL NOT NULL,
    zone_id INTEGER,                         -- peut être une zone ajoutée par le scénario (D4)
    explication TEXT,
    details TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS tournee (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL REFERENCES plan(id),
    type TEXT NOT NULL CHECK (type IN ('collecte', 'intervention')),
    camion_id TEXT,
    affectee_a INTEGER REFERENCES utilisateur(id),
    distance_km REAL,
    duree_min REAL,
    cout_xof REAL,
    details TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS arret_tournee (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournee_id INTEGER NOT NULL REFERENCES tournee(id),
    ordre INTEGER NOT NULL,
    cible_type TEXT NOT NULL CHECK (cible_type IN ('point_regroupement', 'depotoir')),
    cible_id INTEGER NOT NULL,
    statut TEXT NOT NULL DEFAULT 'a_faire' CHECK (statut IN ('a_faire', 'effectue')),
    details TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS indicateur_simulation (
    plan_id INTEGER NOT NULL REFERENCES plan(id),
    jour INTEGER NOT NULL,
    pct_collecte REAL,
    depotoirs_actifs INTEGER,
    cout_xof REAL,
    distance_km REAL,
    PRIMARY KEY (plan_id, jour)
);

CREATE TABLE IF NOT EXISTS intervention (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    depotoir_id INTEGER NOT NULL REFERENCES depotoir(id),
    laabal_id INTEGER NOT NULL REFERENCES utilisateur(id),
    statut TEXT NOT NULL CHECK (statut IN ('en_cours', 'eradique')),
    photo TEXT,
    date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS constat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    depotoir_id INTEGER NOT NULL REFERENCES depotoir(id),
    laabal_id INTEGER NOT NULL REFERENCES utilisateur(id),
    date TEXT NOT NULL,
    description TEXT,
    preuves TEXT NOT NULL DEFAULT '[]',
    montant_xof REAL,
    statut TEXT NOT NULL DEFAULT 'enregistre'
);

CREATE TABLE IF NOT EXISTS journal_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    utilisateur_id INTEGER REFERENCES utilisateur(id),
    action TEXT NOT NULL,
    objet_type TEXT NOT NULL,
    objet_id INTEGER,
    date TEXT NOT NULL
);
"""


def connecter(chemin: str | Path | None = None) -> sqlite3.Connection:
    """Ouvre une connexion avec clés étrangères et accès par nom de colonne."""
    chemin = str(chemin if chemin is not None else CHEMIN_DB_DEFAUT)
    if chemin != ":memory:":
        Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(chemin, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Colonnes ajoutées après la première version du schéma : `CREATE TABLE IF NOT
# EXISTS` ne les crée pas dans une base existante, on les ajoute à la main.
COLONNES_AJOUTEES = [
    ("scenario", "actif", "INTEGER NOT NULL DEFAULT 0"),
    ("plan", "signature", "TEXT"),
    ("plan", "details", "TEXT NOT NULL DEFAULT '{}'"),
    ("point_regroupement", "details", "TEXT NOT NULL DEFAULT '{}'"),
    ("tournee", "details", "TEXT NOT NULL DEFAULT '{}'"),
    ("arret_tournee", "details", "TEXT NOT NULL DEFAULT '{}'"),
    ("signalement", "capture_le", "TEXT"),
    ("signalement", "id_client", "TEXT"),
    ("signalement", "note_vocale", "TEXT"),
    ("signalement", "masquage", "TEXT"),
]

# Index sur des colonnes ajoutées : créés après la migration.
INDEX_APRES_MIGRATION = [
    # Un même appareil ne crée qu'un signalement par identifiant client (renvois hors connexion).
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_signalement_id_client"
    " ON signalement(contributeur_id, id_client) WHERE id_client IS NOT NULL",
]


def initialiser(conn: sqlite3.Connection) -> None:
    """Crée les tables si elles n'existent pas (idempotent), complète les anciennes bases."""
    conn.executescript(SCHEMA)
    # La première version liait point_regroupement.zone_id à la table zone : une zone
    # ajoutée par un scénario (D4) n'y est pas. Table jamais remplie avant C4 : on la recrée.
    vers_zone = [l for l in conn.execute("PRAGMA foreign_key_list(point_regroupement)") if l[2] == "zone"]
    if vers_zone and not conn.execute(
        "SELECT 1 FROM point_regroupement LIMIT 1"
    ).fetchone():
        conn.execute("DROP TABLE point_regroupement")
        conn.executescript(SCHEMA)
    for table, colonne, definition in COLONNES_AJOUTEES:
        existantes = {l[1] for l in conn.execute(f"PRAGMA table_info({table})")}
        if colonne not in existantes:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {colonne} {definition}")
    for index in INDEX_APRES_MIGRATION:
        conn.execute(index)
    conn.commit()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Valide si tout se passe bien, annule sinon."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def en_json(valeur) -> str:
    return json.dumps(valeur, ensure_ascii=False)


def depuis_json(texte: str | None, defaut=None):
    if texte is None or texte == "":
        return defaut
    return json.loads(texte)
