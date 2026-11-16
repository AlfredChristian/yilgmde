"""Dépendances partagées par les routes.

Une seule connexion SQLite est partagée par toute l'application (voir `main.py`).
FastAPI exécute les routes synchrones dans un pool de threads : on sérialise donc
l'accès à la base avec un verrou, simple et suffisant pour le MVP (D14).
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from typing import Iterator

from fastapi import Request

_VERROU = threading.Lock()


@contextmanager
def acces_db(request: Request) -> Iterator[sqlite3.Connection]:
    """Donne la connexion de l'application, un thread à la fois."""
    with _VERROU:
        yield request.app.state.db
