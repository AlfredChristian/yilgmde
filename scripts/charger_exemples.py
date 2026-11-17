"""Remplit la base de développement avec des données fictives.

    python scripts/charger_exemples.py           # petit jeu de data/sample/
    python scripts/charger_exemples.py --ouaga   # jeu réaliste de Ouagadougou (data/ouaga/), pour la démo
    python scripts/charger_exemples.py --ouaga --demo
        # + comptes chauffeur et Laabal, scénarios pluies / panne / sensibilisation (arr. 9),
        #   plan calculé et tournées affectées : prêt pour la démo (backend/demo.py)

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
    if "--demo" in sys.argv:
        import os

        from backend.config import charger_config
        from backend.demo import preparer_demo

        d = preparer_demo(conn, charger_config(os.environ.get("YILGMDE_VILLE", "ouagadougou") or None))
        print(f"Démo prête : {d['points']} points, {d['tournees_affectees']} tournées affectées, "
              f"scénarios {', '.join(d['scenarios'])}")
        admin = os.environ.get("YILGMDE_ADMIN_EMAIL")
        print(f"  admin     : {admin or '(YILGMDE_ADMIN_EMAIL non défini : aucun admin créé)'}")
        for email, mdp, role in d["comptes"]:
            print(f"  {role:<9} : {email} / {mdp}")
    conn.close()


if __name__ == "__main__":
    main()
