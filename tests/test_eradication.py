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
