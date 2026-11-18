"""D60 : suivi de l'éradication des dépotoirs, du signalement à la surveillance."""

from backend.main import app
from backend.schemas import Role
from tests.test_terrain import PNG, client, compte  # noqa: F401  (fixture réutilisée)


def suivi(client):
    _, h = compte(client, Role.admin)
    r = client.get("/admin/suivi-depotoirs", headers=h)
    assert r.status_code == 200
    return r.json()


def test_reserve_a_l_administrateur(client):
    _, hl = compte(client, Role.laabal)
    assert client.get("/admin/suivi-depotoirs").status_code == 401
    assert client.get("/admin/suivi-depotoirs", headers=hl).status_code == 403


def test_chaine_complete_signalement_intervention_eradication_surveillance(client):
    base = next(d for d in suivi(client)["depotoirs"] if d["statut"] == "actif")
    # Un citoyen signale ce dépotoir, à quelques mètres, et la mairie valide le signalement.
    app.state.db.execute(
        "INSERT INTO signalement (latitude, longitude, type_dechet, volume_estime, code_suivi, statut, depotoir_id,"
        " valide_le, cree_le) VALUES (?, ?, 'menager', 'moyen', 'ESSAI-D60', 'verifie', ?, ?, ?)",
        (base["latitude"] + 0.0002, base["longitude"] - 0.0001, base["id"], "2026-11-01T10:00:00+00:00", "2026-11-01T08:00:00+00:00"),
    )
    app.state.db.commit()
    s = suivi(client)
    actif = next(d for d in s["depotoirs"] if d["id"] == base["id"])
    assert actif["etapes"]["valide"] == "2026-11-01T10:00:00+00:00"
    assert actif["etapes"]["signale"] and actif["etapes"]["intervention"] is None and actif["etapes"]["eradique"] is None
    assert all(d["statut"] != "classe" for d in s["depotoirs"])

    _, hl = compte(client, Role.laabal, "Brigade Laabal 2")
    url = f"/laabal/depotoirs/{actif['id']}/intervention"
    assert client.post(url, data={"statut": "en_cours"}, headers=hl).status_code == 200
    assert client.post(url, data={"statut": "eradique"}, files={"photo": ("p.png", PNG, "image/png")}, headers=hl).status_code == 200
    assert client.post(f"/laabal/depotoirs/{actif['id']}/surveillance", headers=hl).status_code == 200

    d = next(x for x in suivi(client)["depotoirs"] if x["id"] == actif["id"])
    e = d["etapes"]
    assert d["statut"] == "sous_surveillance" and d["brigade"] == "Brigade Laabal 2" and d["photo_intervention"]
    assert e["signale"] <= e["intervention"] <= e["eradique"] <= e["surveillance"]
    assert not d["dates_estimees"] and d["delai_eradication_jours"] >= 0
    # La position est celle des signalements : le dépotoir est là où les citoyens l'ont signalé.
    assert d["signalements"]
    for sig in d["signalements"]:
        assert abs(sig["latitude"] - d["latitude"]) < 0.01 and abs(sig["longitude"] - d["longitude"]) < 0.01


def test_statut_importe_sans_historique_a_des_dates_estimees(client):
    app.state.db.execute("DELETE FROM intervention")
    s = suivi(client)
    for d in s["depotoirs"]:
        if d["statut"] in ("eradique", "sous_surveillance"):
            assert d["etapes"]["eradique"] and d["dates_estimees"]
    r = s["resume"]
    assert r["depotoirs"] == len(s["depotoirs"])
    assert r["a_traiter"] + r["en_intervention"] + r["eradiques"] == r["depotoirs"]
    assert s["debut"] <= s["fin"]


def test_itineraire_de_la_brigade_aller_et_retour(client):
    """D61 : trajet de la base au dépotoir et retour, pour l'animation de la carte de la brigade."""
    _, hc = compte(client, Role.chauffeur)
    _, hl = compte(client, Role.laabal)
    d = client.get("/laabal/depotoirs-a-traiter", headers=hl).json()[0]
    url = f"/laabal/depotoirs/{d['id']}/itineraire"
    assert client.get(url, headers=hc).status_code == 403
    assert client.get("/laabal/depotoirs/999999/itineraire", headers=hl).status_code == 404
    r = client.get(url, headers=hl).json()
    base = (r["base"]["latitude"], r["base"]["longitude"])
    proche = lambda p, q: abs(p[0] - q[0]) < 1e-4 and abs(p[1] - q[1]) < 1e-4
    assert proche(r["aller"][0], base) and proche(r["aller"][-1], (d["latitude"], d["longitude"]))
    assert proche(r["retour"][0], (d["latitude"], d["longitude"])) and proche(r["retour"][-1], base)
    assert r["distance_aller_m"] > 0 and r["distance_retour_m"] > 0
    if r["sur_les_voies"]:
        assert len(r["aller"]) > 2           # le trajet suit les rues, pas une ligne droite
