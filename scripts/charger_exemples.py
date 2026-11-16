"""Remplit la base de développement avec les données fictives de `data/sample/`.

    python scripts/charger_exemples.py

La base est celle de `YILGMDE_DB` (par défaut `data/processed/yilgmde.sqlite3`).
Idempotent : sans effet sur une table déjà remplie.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import db  # noqa: E402
from backend.exemples import charger_exemples  # noqa: E402


def main() -> None:
    conn = db.connecter()
    db.initialiser(conn)
    n = charger_exemples(conn)
    print(f"Zones ajoutées : {n['zones']} — dépotoirs ajoutés : {n['depotoirs']}")
    conn.close()


if __name__ == "__main__":
    main()
