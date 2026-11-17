"""Remplit la base de développement avec des données fictives.

    python scripts/charger_exemples.py           # petit jeu de data/sample/
    python scripts/charger_exemples.py --ouaga   # jeu réaliste de Ouagadougou (data/ouaga/), pour la démo

La base est celle de `YILGMDE_DB` (par défaut `data/processed/yilgmde.sqlite3`).
Idempotent : sans effet sur une table déjà remplie.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import db  # noqa: E402
from backend.exemples import DOSSIER_OUAGA, charger_exemples  # noqa: E402


def main() -> None:
    conn = db.connecter()
    db.initialiser(conn)
    n = charger_exemples(conn, DOSSIER_OUAGA if "--ouaga" in sys.argv else None)
    print(f"Zones ajoutées : {n['zones']} — dépotoirs : {n['depotoirs']} — signalements : {n['signalements']}")
    conn.close()


if __name__ == "__main__":
    main()
