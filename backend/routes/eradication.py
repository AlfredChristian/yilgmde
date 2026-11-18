"""Suivi de l'éradication des dépotoirs (D60), pour l'administrateur.

Pour chaque dépotoir illégal (hors sites classés), la chaîne complète, datée :
signalé (premier signalement reçu), validé (premier signalement vérifié par la mairie),
intervention de la brigade Laabal (`en_cours`), éradiqué, mis sous surveillance.
Les positions sont celles données dans les signalements eux-mêmes ; le dépotoir est
placé à leur position. Le front rejoue ces étapes dans le temps, comme le suivi de la flotte.

Les signalements reçus après l'intervention sont des réapparitions : ils ne comptent pas pour
« signalé » et « validé ». Les dates manquantes (dépotoirs importés avec un statut mais sans
historique) sont prises sur `premiere_detection` ou `derniere_maj` et signalées par `dates_estimees`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import median

from fastapi import APIRouter, Depends, Request

from backend.deps import acces_db
from backend.schemas import Role
from backend.securite import exiger_role

router = APIRouter(tags=["eradication"])
admin = exiger_role(Role.admin)

ETAPES = ("signale", "valide", "intervention", "eradique", "surveillance")
SUIVIS = ("actif", "intervention_planifiee", "eradique", "sous_surveillance")


def _jours(debut: str | None, fin: str | None) -> float | None:
    if not debut or not fin:
        return None
    return round((datetime.fromisoformat(fin) - datetime.fromisoformat(debut)).total_seconds() / 86400, 1)


@router.get("/admin/suivi-depotoirs")
def suivi_depotoirs(request: Request, _=Depends(admin)):
    with acces_db(request) as conn:
        zones = {l["id"]: l["nom"] for l in conn.execute("SELECT id, nom FROM zone")}
        noms = {l["id"]: l["nom"] for l in conn.execute("SELECT id, nom FROM utilisateur")}
        depotoirs = conn.execute(
            "SELECT * FROM depotoir WHERE legalite = 'illegal' AND statut IN (%s) ORDER BY id" % ",".join("?" * len(SUIVIS)),
            SUIVIS,
        ).fetchall()
        signalements: dict[int, list] = {}
        for l in conn.execute(
            "SELECT id, depotoir_id, latitude, longitude, cree_le, valide_le, statut FROM signalement "
            "WHERE depotoir_id IS NOT NULL AND statut = 'verifie' ORDER BY cree_le"
        ):
            signalements.setdefault(l["depotoir_id"], []).append(l)
        interventions: dict[int, list] = {}
        for l in conn.execute("SELECT depotoir_id, laabal_id, statut, date, photo FROM intervention ORDER BY date"):
            interventions.setdefault(l["depotoir_id"], []).append(l)
        surveillances = {
            l["objet_id"]: l["quand"]
            for l in conn.execute(
                "SELECT objet_id, MAX(date) AS quand FROM journal_audit WHERE action = 'surveillance' "
                "AND objet_type = 'depotoir' GROUP BY objet_id"
            )
        }

    maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sortie = []
    for d in depotoirs:
        maj = min(d["derniere_maj"], maintenant)     # le jeu importé a quelques dates futures
        sigs = signalements.get(d["id"], [])
        ints = interventions.get(d["id"], [])
        en_cours = next((i for i in ints if i["statut"] == "en_cours"), None)
        fini = next((i for i in reversed(ints) if i["statut"] == "eradique"), None)
        intervention = en_cours["date"] if en_cours else (fini["date"] if fini else None)
        # Les signalements reçus après l'intervention sont des réapparitions : seule la
        # chaîne d'avant compte pour « signalé » et « validé ».
        avant = [s for s in sigs if not intervention or s["cree_le"] <= intervention]
        estimees = False
        signale = min([d["premiere_detection"]] + [s["cree_le"] for s in avant[:1]])
        valide = next((s["valide_le"] or s["cree_le"] for s in avant), None)
        if valide and intervention and valide > intervention:
            valide = None
        if not valide and (intervention or sigs):
            # Dépotoir importé déjà vérifié (ou validé hors application) : validé dès sa détection.
            valide, estimees = signale, True
        etapes = {
            "signale": signale, "valide": valide, "intervention": intervention,
            "eradique": fini["date"] if fini else None,
            "surveillance": surveillances.get(d["id"]),
        }
        # Statut importé sans historique : dates prises sur la dernière mise à jour.
        if d["statut"] in ("eradique", "sous_surveillance") and not etapes["eradique"]:
            etapes["eradique"], estimees = maj, True
        if d["statut"] in ("intervention_planifiee", "eradique", "sous_surveillance") and not etapes["intervention"]:
            etapes["intervention"], estimees = etapes["eradique"] or maj, True
        if d["statut"] == "sous_surveillance" and not etapes["surveillance"]:
            etapes["surveillance"], estimees = max(maj, etapes["eradique"]), True
        derniere = fini or en_cours
        brigade = noms.get(derniere["laabal_id"]) if derniere else None
        sortie.append({
            "id": d["id"], "latitude": d["latitude"], "longitude": d["longitude"],
            "zone_id": d["zone_id"], "zone_nom": zones.get(d["zone_id"]),
            "volume_estime": d["volume_estime"], "statut": d["statut"],
            "nb_signalements": d["nb_signalements"], "nb_reapparitions": d["nb_reapparitions"],
            "etapes": etapes, "dates_estimees": estimees, "brigade": brigade,
            "photo_intervention": bool(fini and fini["photo"]),
            "delai_eradication_jours": _jours(etapes["signale"], etapes["eradique"]),
            "signalements": [
                {"id": s["id"], "latitude": s["latitude"], "longitude": s["longitude"], "cree_le": s["cree_le"]}
                for s in sigs
            ],
        })

    delais = [d["delai_eradication_jours"] for d in sortie if d["delai_eradication_jours"] is not None]
    dates = sorted(v for d in sortie for v in d["etapes"].values() if v)
    par_statut = {s: sum(1 for d in sortie if d["statut"] == s) for s in SUIVIS}
    return {
        "debut": dates[0] if dates else None,
        "fin": dates[-1] if dates else None,
        "resume": {
            "depotoirs": len(sortie),
            "a_traiter": par_statut["actif"],
            "en_intervention": par_statut["intervention_planifiee"],
            "eradiques": par_statut["eradique"] + par_statut["sous_surveillance"],
            "sous_surveillance": par_statut["sous_surveillance"],
            "delai_median_jours": round(median(delais), 1) if delais else None,
        },
        "depotoirs": sortie,
    }
