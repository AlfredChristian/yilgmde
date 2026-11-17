"""Score de confiance des contributeurs (A2, A3, D33).

Le score (0 à 1, 0,5 au départ) est lu par la vérification automatique (A2) :
sous `verification.seuil_confiance_appareil`, le signalement est pénalisé. Il
évolue avec les **décisions humaines** de la modération seulement (un rejet
automatique peut être un faux positif) :

- validation : `s ← s + gain_validation × (1 − s)` (se rapproche de 1) ;
- rejet      : `s ← s − perte_rejet × s`          (se rapproche de 0).

La perte est plus forte que le gain [H] : quelques faux signalements font vite
baisser un appareil, il faut plusieurs signalements justes pour remonter. Le score
reste dans [0, 1] par construction. Il n'est jamais montré au public.
"""

from __future__ import annotations

import sqlite3


def nouveau_score(score: float, decision: str, config: dict) -> float:
    c = config.get("verification", {})
    if decision == "valide":
        score = score + float(c.get("gain_confiance_validation", 0.1)) * (1 - score)
    elif decision == "rejete":
        score = score - float(c.get("perte_confiance_rejet", 0.25)) * score
    else:
        raise ValueError(f"décision inconnue : {decision!r}")
    return round(min(1.0, max(0.0, score)), 4)


def ajuster_confiance(conn: sqlite3.Connection, contributeur_id: int | None, decision: str, config: dict) -> float | None:
    """Met à jour le score du contributeur (dans la transaction de l'appelant). None si pas de contributeur."""
    if contributeur_id is None:
        return None
    ligne = conn.execute("SELECT score_confiance FROM contributeur WHERE id = ?", (contributeur_id,)).fetchone()
    if ligne is None:
        return None
    score = nouveau_score(ligne["score_confiance"], decision, config)
    conn.execute("UPDATE contributeur SET score_confiance = ? WHERE id = ?", (score, contributeur_id))
    return score


def ajuster_confiance_signalement(conn: sqlite3.Connection, signalement_id: int, decision: str, config: dict) -> float | None:
    """Comme `ajuster_confiance`, à partir du signalement jugé."""
    ligne = conn.execute("SELECT contributeur_id FROM signalement WHERE id = ?", (signalement_id,)).fetchone()
    return ajuster_confiance(conn, ligne["contributeur_id"] if ligne else None, decision, config)
