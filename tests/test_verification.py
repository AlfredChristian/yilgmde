import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend import db
from backend.config import charger_config
from backend.schemas import StatutSignalement
from backend.verification import Contexte, Voisin, contexte_depuis_db, distance_m, verifier

RACINE = Path(__file__).resolve().parent.parent
LAT, LON = 12.3714, -1.5197


@pytest.fixture
def config():
    return charger_config("ouagadougou")


def test_distance_connue():
    # 0,001° de latitude ≈ 111 m
    assert distance_m(12.0, -1.5, 12.001, -1.5) == pytest.approx(111.2, abs=1)
    assert distance_m(LAT, LON, LAT, LON) == 0


def test_signalement_normal_en_attente_de_revue(config):
    v = verifier(LAT, LON, config, Contexte())
    assert v.statut == StatutSignalement.en_attente_revue
    assert v.motif is None
    assert v.score_auto == 1.0
    assert v.alertes == []


def test_hors_zone_rejete_avec_motif(config):
    v = verifier(5.36, -4.0083, config, Contexte())
    assert v.statut == StatutSignalement.rejete_auto
    assert v.motif == "hors zone d'étude"
    assert v.alertes == ["hors_zone"]


def test_position_zero_zero(config):
    v = verifier(0.0, 0.0, config, Contexte())
    assert v.statut == StatutSignalement.rejete_auto
    assert "position incohérente" in v.motif


def test_latitude_longitude_inversees(config):
    v = verifier(-1.5197, 12.3714, config, Contexte())
    assert v.statut == StatutSignalement.rejete_auto
    assert "inversées" in v.motif


def test_coordonnees_non_finies(config):
    v = verifier(float("nan"), LON, config, Contexte())
    assert v.statut == StatutSignalement.rejete_auto
    assert v.alertes == ["position_incoherente"]


def test_doublon_proche_alerte_sans_rejet(config):
    ctx = Contexte(voisins=(Voisin(1, 12.37142, -1.51972, "signalement"),))
    v = verifier(LAT, LON, config, ctx)
    assert v.statut == StatutSignalement.en_attente_revue
    assert v.alertes == ["doublon_probable:1"]
    assert v.score_auto == pytest.approx(0.7)


def test_voisin_hors_rayon_ignore(config):
    # ≈ 111 m au nord, rayon par défaut 30 m
    ctx = Contexte(voisins=(Voisin(1, LAT + 0.001, LON, "signalement"),))
    assert verifier(LAT, LON, config, ctx).alertes == []


def test_rayon_doublon_vient_de_la_config(config):
    config = charger_config("ouagadougou", {"verification": {"rayon_doublon_m": 200}})
    ctx = Contexte(voisins=(Voisin(1, LAT + 0.001, LON, "signalement"),))
    assert verifier(LAT, LON, config, ctx).alertes == ["doublon_probable:1"]


def test_depotoir_connu_proche(config):
    ctx = Contexte(voisins=(Voisin(4, LAT, LON, "depotoir"),))
    v = verifier(LAT, LON, config, ctx)
    assert v.alertes == ["depotoir_proche:4"]
    assert v.score_auto == pytest.approx(0.9)


def test_limite_par_appareil(config):
    limite = config["verification"]["max_signalements_par_appareil_heure"]
    v = verifier(LAT, LON, config, Contexte(nb_signalements_derniere_heure=limite))
    assert v.statut == StatutSignalement.rejete_auto
    assert str(limite) in v.motif
    # juste en dessous de la limite : accepté
    assert verifier(LAT, LON, config, Contexte(nb_signalements_derniere_heure=limite - 1)).statut == (
        StatutSignalement.en_attente_revue
    )


def test_appareil_bloque(config):
    v = verifier(LAT, LON, config, Contexte(appareil_bloque=True))
    assert v.statut == StatutSignalement.rejete_auto
    assert v.motif == "appareil bloqué"


def test_photo_requise_selon_config(config):
    config = charger_config("ouagadougou", {"verification": {"photo_requise": True}})
    assert verifier(LAT, LON, config, Contexte()).alertes == ["photo_manquante"]
    assert verifier(LAT, LON, config, Contexte(avec_photo=True)).statut == StatutSignalement.en_attente_revue


def test_appareil_peu_fiable_baisse_le_score(config):
    v = verifier(LAT, LON, config, Contexte(score_confiance_appareil=0.1))
    assert "appareil_peu_fiable" in v.alertes
    assert v.score_auto == pytest.approx(0.8)


def test_score_reste_entre_0_et_1(config):
    voisins = tuple(Voisin(i, LAT, LON, "signalement") for i in range(1, 6))
    v = verifier(LAT, LON, config, Contexte(voisins=voisins, score_confiance_appareil=0.0))
    assert 0 <= v.score_auto <= 1


def test_fonction_pure_ne_modifie_pas_la_config(config):
    import copy

    avant = copy.deepcopy(config)
    verifier(LAT, LON, config, Contexte(voisins=(Voisin(1, LAT, LON, "signalement"),)))
    assert config == avant


def test_jeu_d_exemple_conforme_aux_attentes(config):
    """Rejoue data/sample/signalements_exemple.geojson dans l'ordre, comme des envois successifs."""
    collection = json.loads((RACINE / "data/sample/signalements_exemple.geojson").read_text(encoding="utf-8"))
    acceptes: list[Voisin] = []
    for f in collection["features"]:
        lon, lat = f["geometry"]["coordinates"]
        p = f["properties"]
        v = verifier(lat, lon, config, Contexte(voisins=tuple(acceptes)))
        attendu = p["attendu"]
        if attendu.startswith("rejete_auto"):
            assert v.statut == StatutSignalement.rejete_auto, p
            assert attendu.split(": ")[1] in v.alertes
        elif attendu.startswith("alerte "):
            assert v.statut == StatutSignalement.en_attente_revue, p
            assert attendu.removeprefix("alerte ") in v.alertes
        else:
            assert v.statut.value == attendu, p
            assert v.alertes == [], p
        if v.statut == StatutSignalement.en_attente_revue:
            acceptes.append(Voisin(p["id"], lat, lon, "signalement"))


# ---------- contexte_depuis_db ----------

def _base():
    conn = db.connecter(":memory:")
    db.initialiser(conn)
    return conn


def _signalement(conn, code, lat, lon, statut, contributeur_id=None, cree_le=None):
    cree_le = cree_le or datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO signalement (contributeur_id, latitude, longitude, type_dechet, volume_estime,"
        " code_suivi, statut, cree_le) VALUES (?, ?, ?, 'menager', 'petit', ?, ?, ?)",
        (contributeur_id, lat, lon, code, statut, cree_le),
    )
    conn.commit()


def test_contexte_db_voisins_et_statuts(config):
    conn = _base()
    _signalement(conn, "A", LAT, LON, "en_attente_revue")
    _signalement(conn, "B", LAT, LON, "rejete")        # un rejet ne compte pas comme doublon
    _signalement(conn, "C", LAT + 0.5, LON, "verifie")  # trop loin
    ctx = contexte_depuis_db(conn, None, LAT, LON, config)
    assert [(v.id, v.type) for v in ctx.voisins] == [(1, "signalement")]
    assert verifier(LAT, LON, config, ctx).alertes == ["doublon_probable:1"]


def test_contexte_db_depotoir_et_classe_ignore(config):
    conn = _base()
    maintenant = datetime.now(timezone.utc).isoformat()
    for statut in ("actif", "classe"):
        conn.execute(
            "INSERT INTO depotoir (latitude, longitude, volume_estime, statut, premiere_detection, derniere_maj)"
            " VALUES (?, ?, 'moyen', ?, ?, ?)",
            (LAT, LON, statut, maintenant, maintenant),
        )
    conn.commit()
    ctx = contexte_depuis_db(conn, None, LAT, LON, config)
    assert [(v.id, v.type) for v in ctx.voisins] == [(1, "depotoir")]


def test_contexte_db_compte_la_derniere_heure(config):
    conn = _base()
    conn.execute("INSERT INTO contributeur (jeton_appareil) VALUES ('tok')")
    maintenant = datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc)
    for i, delta in enumerate([timedelta(minutes=5), timedelta(minutes=50), timedelta(minutes=90)]):
        _signalement(conn, f"S{i}", LAT + i, LON, "verifie", 1, (maintenant - delta).isoformat())
    ctx = contexte_depuis_db(conn, "tok", LAT, LON, config, maintenant=maintenant)
    assert ctx.nb_signalements_derniere_heure == 2   # celui d'il y a 90 min est exclu


def test_contexte_db_appareil_bloque_et_inconnu(config):
    conn = _base()
    conn.execute("INSERT INTO contributeur (jeton_appareil, bloque, score_confiance) VALUES ('mauvais', 1, 0.1)")
    conn.commit()
    ctx = contexte_depuis_db(conn, "mauvais", LAT, LON, config)
    assert ctx.appareil_bloque and ctx.score_confiance_appareil == 0.1
    inconnu = contexte_depuis_db(conn, "nouveau", LAT, LON, config)
    assert not inconnu.appareil_bloque and inconnu.nb_signalements_derniere_heure == 0
