"""Limitation des tentatives de connexion (F1, sécurité transverse).

Compteur d'**échecs** par clé (e-mail normalisé, et adresse IP) sur une fenêtre
glissante. Au-delà du seuil, la clé est bloquée pendant `blocage_min` : la
connexion répond `429` avec `Retry-After`, **avant** de vérifier le mot de passe
(pas de bcrypt gaspillé, pas de test possible pendant le blocage). Une connexion
réussie remet à zéro le compteur de l'e-mail (pas celui de l'IP).

Même traitement que le compte existe ou non : pas d'énumération de comptes.

État **en mémoire** (D32) : suffisant pour un seul processus uvicorn (MVP) ; il
repart à zéro au redémarrage. Avec plusieurs processus, il faudra une table
SQLite ou un cache partagé.
"""

from __future__ import annotations

import threading
import time
from collections import deque


class LimiteurTentatives:
    def __init__(self, max_echecs: int, fenetre_s: float, blocage_s: float, horloge=time.monotonic):
        self.max_echecs = max(1, int(max_echecs))
        self.fenetre_s = float(fenetre_s)
        self.blocage_s = float(blocage_s)
        self.horloge = horloge
        self._echecs: dict[str, deque] = {}
        self._bloque_jusqu_a: dict[str, float] = {}
        self._verrou = threading.Lock()

    def attente_s(self, cle: str) -> float:
        """Secondes de blocage restantes (0 si la clé n'est pas bloquée)."""
        with self._verrou:
            fin = self._bloque_jusqu_a.get(cle)
            if fin is None:
                return 0.0
            reste = fin - self.horloge()
            if reste <= 0:
                del self._bloque_jusqu_a[cle]
                return 0.0
            return reste

    def echec(self, cle: str) -> bool:
        """Enregistre un échec ; renvoie True si la clé vient d'être bloquée."""
        with self._verrou:
            maintenant = self.horloge()
            file = self._echecs.setdefault(cle, deque())
            file.append(maintenant)
            while file and file[0] <= maintenant - self.fenetre_s:
                file.popleft()
            if len(file) >= self.max_echecs:
                self._bloque_jusqu_a[cle] = maintenant + self.blocage_s
                file.clear()
                return True
            return False

    def succes(self, cle: str) -> None:
        with self._verrou:
            self._echecs.pop(cle, None)

    def nettoyer(self) -> None:
        """Oublie les clés inactives (appelé de temps en temps pour borner la mémoire)."""
        with self._verrou:
            maintenant = self.horloge()
            for cle in [c for c, f in self._echecs.items() if not f or f[-1] <= maintenant - self.fenetre_s]:
                del self._echecs[cle]
            for cle in [c for c, fin in self._bloque_jusqu_a.items() if fin <= maintenant]:
                del self._bloque_jusqu_a[cle]


def creer_limiteurs(config: dict) -> dict[str, LimiteurTentatives]:
    s = config.get("securite", {})
    fenetre = float(s.get("fenetre_echecs_min", 15)) * 60
    blocage = float(s.get("blocage_min", 15)) * 60
    return {
        "email": LimiteurTentatives(s.get("max_echecs_par_email", 5), fenetre, blocage),
        "ip": LimiteurTentatives(s.get("max_echecs_par_ip", 20), fenetre, blocage),
    }
