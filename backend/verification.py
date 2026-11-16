"""Vérification automatique des signalements (A2).

Fonction pure : `verdict = verifier(signalement, config, contexte)`. Aucun accès
à la base ici (D09) ; `contexte_depuis_db` rassemble ce qu'il faut lire en base.
Tous les seuils viennent de `config/` (D10), rien n'est en dur.

Règles :
  - rejet automatique (statut `rejete_auto`, motif lisible) : appareil bloqué,
    limite par heure dépassée, position incohérente, hors zone d'étude,
    photo manquante si `verification.photo_requise` ;
  - sinon `en_attente_revue`, avec des alertes pour l'admin (doublon probable,
    dépotoir déjà connu à proximité) et un score entre 0 et 1.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from backend.schemas import StatutSignalement, Verdict

RAYON_TERRE_M = 6_371_008.8

# Valeurs de repli si une clé manque dans la config [H] (la config reste prioritaire).
_PENALITE_DOUBLON_DEFAUT = 0.3
_PENALITE_DEPOTOIR_DEFAUT = 0.1
_PENALITE_CONTRIBUTEUR_DEFAUT = 0.2
_SEUIL_CONTRIBUTEUR_DEFAUT = 0.3


@dataclass(frozen=True)
class Voisin:
    """Un objet déjà connu près duquel un signalement peut tomber."""

    id: int
    latitude: float
    longitude: float
    type: str  # "signalement" ou "depotoir"


@dataclass(frozen=True)
class Contexte:
    """Ce que la vérification a besoin de savoir de la base, sous forme de données."""

    voisins: tuple[Voisin, ...] = ()
    nb_signalements_derniere_heure: int = 0
    appareil_bloque: bool = False
    score_confiance_appareil: float = 0.5
    avec_photo: bool = False


@dataclass
class _Etat:
    alertes: list[str] = field(default_factory=list)
    penalite: float = 0.0


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance en mètres entre deux points WGS84 (haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * RAYON_TERRE_M * math.asin(math.sqrt(a))


def _dans_bbox(lat: float, lon: float, bbox: dict) -> bool:
    return bbox["min_lat"] <= lat <= bbox["max_lat"] and bbox["min_lon"] <= lon <= bbox["max_lon"]


def _rejet(motif: str, alertes: list[str]) -> Verdict:
    return Verdict(
        statut=StatutSignalement.rejete_auto,
        motif=motif,
        score_auto=0.0,
        alertes=alertes,
    )


def verifier(latitude: float, longitude: float, config: dict, contexte: Contexte) -> Verdict:
    """Décide du sort d'un signalement. Ne modifie ni `config` ni `contexte`."""
    regles = config.get("verification", {})
    bbox = config.get("zone_etude", {}).get("bbox")

    # 1. Appareil bloqué ou trop actif : abus par appareil.
    if contexte.appareil_bloque:
        return _rejet("appareil bloqué", ["appareil_bloque"])
    limite = regles.get("max_signalements_par_appareil_heure")
    if limite is not None and contexte.nb_signalements_derniere_heure >= limite:
        return _rejet(
            f"trop de signalements depuis cet appareil (maximum {limite} par heure)",
            ["limite_appareil"],
        )

    # 2. Position incohérente : non finie, (0, 0), ou latitude/longitude inversées.
    if not (math.isfinite(latitude) and math.isfinite(longitude)):
        return _rejet("position incohérente (coordonnées invalides)", ["position_incoherente"])
    if latitude == 0 and longitude == 0:
        return _rejet("position incohérente (coordonnées 0, 0)", ["position_incoherente"])
    if bbox is not None and not _dans_bbox(latitude, longitude, bbox) and _dans_bbox(longitude, latitude, bbox):
        return _rejet(
            "position incohérente (latitude et longitude semblent inversées)",
            ["position_incoherente"],
        )

    # 3. Hors zone d'étude.
    if bbox is not None and not _dans_bbox(latitude, longitude, bbox):
        return _rejet("hors zone d'étude", ["hors_zone"])

    # 4. Photo obligatoire selon la config.
    if regles.get("photo_requise", False) and not contexte.avec_photo:
        return _rejet("photo requise manquante", ["photo_manquante"])

    # 5. Alertes (pas de rejet : c'est l'admin qui tranche).
    etat = _Etat()
    rayon = regles.get("rayon_doublon_m")
    if rayon is not None:
        proches = sorted(
            (
                (distance_m(latitude, longitude, v.latitude, v.longitude), v)
                for v in contexte.voisins
            ),
            key=lambda dv: (dv[0], dv[1].id),
        )
        proches = [(d, v) for d, v in proches if d <= rayon]
        signalements_proches = [v for _, v in proches if v.type == "signalement"]
        depotoirs_proches = [v for _, v in proches if v.type == "depotoir"]
        for v in signalements_proches:
            etat.alertes.append(f"doublon_probable:{v.id}")
        if signalements_proches:
            etat.penalite += regles.get("penalite_doublon", _PENALITE_DOUBLON_DEFAUT)
        for v in depotoirs_proches:
            etat.alertes.append(f"depotoir_proche:{v.id}")
        if depotoirs_proches:
            etat.penalite += regles.get("penalite_depotoir_proche", _PENALITE_DEPOTOIR_DEFAUT)

    seuil = regles.get("seuil_confiance_appareil", _SEUIL_CONTRIBUTEUR_DEFAUT)
    if contexte.score_confiance_appareil < seuil:
        etat.alertes.append("appareil_peu_fiable")
        etat.penalite += regles.get("penalite_appareil_peu_fiable", _PENALITE_CONTRIBUTEUR_DEFAUT)

    score = round(max(0.0, min(1.0, 1.0 - etat.penalite)), 2)
    return Verdict(
        statut=StatutSignalement.en_attente_revue,
        motif=None,
        score_auto=score,
        alertes=etat.alertes,
    )


def contexte_depuis_db(
    conn: sqlite3.Connection,
    jeton_appareil: str | None,
    latitude: float,
    longitude: float,
    config: dict,
    avec_photo: bool = False,
    maintenant: datetime | None = None,
) -> Contexte:
    """Lit en base le contexte d'un signalement : voisins, activité et fiabilité de l'appareil.

    Les distances restent calculées en Python (D14). On limite les voisins à une
    petite fenêtre autour du point pour ne pas charger toute la table.
    """
    maintenant = maintenant or datetime.now(timezone.utc)
    rayon = config.get("verification", {}).get("rayon_doublon_m", 0) or 0
    marge_deg = rayon / 111_000 * 1.5 + 1e-6  # fenêtre englobante large, la distance exacte est recalculée

    voisins: list[Voisin] = []
    for ligne in conn.execute(
        "SELECT id, latitude, longitude FROM signalement"
        " WHERE statut IN ('soumis', 'en_attente_revue', 'verifie')"
        " AND latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?",
        (latitude - marge_deg, latitude + marge_deg, longitude - marge_deg, longitude + marge_deg),
    ):
        voisins.append(Voisin(ligne["id"], ligne["latitude"], ligne["longitude"], "signalement"))
    for ligne in conn.execute(
        "SELECT id, latitude, longitude FROM depotoir WHERE statut != 'classe'"
        " AND latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?",
        (latitude - marge_deg, latitude + marge_deg, longitude - marge_deg, longitude + marge_deg),
    ):
        voisins.append(Voisin(ligne["id"], ligne["latitude"], ligne["longitude"], "depotoir"))

    nb_heure, bloque, confiance = 0, False, 0.5
    if jeton_appareil:
        c = conn.execute(
            "SELECT id, score_confiance, bloque FROM contributeur WHERE jeton_appareil = ?",
            (jeton_appareil,),
        ).fetchone()
        if c is not None:
            bloque, confiance = bool(c["bloque"]), c["score_confiance"]
            depuis = (maintenant - timedelta(hours=1)).isoformat()
            nb_heure = conn.execute(
                "SELECT COUNT(*) FROM signalement WHERE contributeur_id = ? AND cree_le >= ?",
                (c["id"], depuis),
            ).fetchone()[0]

    return Contexte(
        voisins=tuple(voisins),
        nb_signalements_derniere_heure=nb_heure,
        appareil_bloque=bloque,
        score_confiance_appareil=confiance,
        avec_photo=avec_photo,
    )
