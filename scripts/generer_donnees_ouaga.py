"""Génère le jeu de données réaliste de Ouagadougou (livrable 4), dans `data/ouaga/`.

    python scripts/generer_donnees_ouaga.py

Déterministe (graine fixe) : relancer donne exactement les mêmes fichiers.

Ce qui est **réel** (sources dans `data/ouaga/LISEZMOI.md`) :
- population de chaque arrondissement : INSD, 5e RGPH 2019, monographie de la commune
  de Ouagadougou, tableau 2.2 ;
- superficie de la commune déduite de la densité 2019 (4 385,5 hab./km², tableau 2.3) ;
- composition des déchets (UN-Habitat) pour la répartition des types signalés ;
- 35 centres de collecte et de tri dans la ville (UN-Habitat), saisis ici comme sites officiels.

Ce qui est **fictif mais plausible** (autorisé par les organisateurs) :
- contours **schématiques** des arrondissements et secteurs : un disque central (arr. 1
  et 2) et une couronne partagée en secteurs angulaires proportionnels à la population ;
  ce ne sont PAS les limites administratives ;
- position des dépotoirs, des centres de collecte et l'historique des signalements.
"""

from __future__ import annotations

import json
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from simulation.geometrie import depuis_metres  # noqa: E402

GRAINE = 2026
CENTRE = (12.3714, -1.5197)              # centre-ville (place des Nations)
DOSSIER = Path(__file__).resolve().parent.parent / "data" / "ouaga"
AUJOURD_HUI = datetime(2026, 11, 17, 8, 0, tzinfo=timezone.utc)

# INSD, RGPH 2019, monographie de la commune de Ouagadougou, tableau 2.2.
POPULATION_2019 = {1: 102_528, 2: 83_436, 3: 311_406, 4: 207_647, 5: 129_984, 6: 222_854,
                   7: 282_837, 8: 152_880, 9: 336_483, 10: 263_969, 11: 254_928, 12: 66_314}
DENSITE_2019 = 4385.5                    # hab./km², tableau 2.3
SUPERFICIE_KM2 = sum(POPULATION_2019.values()) / DENSITE_2019   # ≈ 551 km²
RAYON_COMMUNE_M = math.sqrt(SUPERFICIE_KM2 * 1e6 / math.pi)       # ≈ 13,2 km
RAYON_CENTRE_M = 3200                    # disque central des arrondissements 1 et 2 (schématique)
POIDS_BANDE = {"interieure": 1.4, "exterieure": 0.8}   # le centre est plus dense que la périphérie

# Composition UN-Habitat (alimentaires 22 %, plastiques 5 %, papiers 6 %, autres 67 %), ramenée
# aux types de l'application : les « autres » sont surtout des ordures ménagères mélangées.
TYPES = [("menager", 0.55), ("organique", 0.20), ("plastiques", 0.10), ("gravats", 0.08),
         ("encombrants", 0.05), ("autre", 0.02)]


def arc(r_int, r_ext, a0, a1, pas_deg=2.0):
    """Polygone (lon, lat) d'un secteur d'anneau entre les angles a0 et a1 (degrés, 0 = est)."""
    n = max(2, int(abs(a1 - a0) / pas_deg) + 1)
    angles = [a0 + (a1 - a0) * i / (n - 1) for i in range(n)]
    pts = []
    for a in angles:
        x, y = r_ext * math.cos(math.radians(a)), r_ext * math.sin(math.radians(a))
        la, lo = depuis_metres(x, y, *CENTRE)
        pts.append([round(lo, 6), round(la, 6)])
    if r_int > 0:
        for a in reversed(angles):
            x, y = r_int * math.cos(math.radians(a)), r_int * math.sin(math.radians(a))
            la, lo = depuis_metres(x, y, *CENTRE)
            pts.append([round(lo, 6), round(la, 6)])
    else:
        lo_c, la_c = CENTRE[1], CENTRE[0]
        pts.append([lo_c, la_c])
    pts.append(pts[0])
    return pts


def aire_secteur(r_int, r_ext, a0, a1):
    return math.pi * (r_ext ** 2 - r_int ** 2) * abs(a1 - a0) / 360


def repartir(total, poids):
    """Entiers proportionnels à `poids`, de somme exactement `total`."""
    bruts = [total * p / sum(poids) for p in poids]
    entiers = [int(b) for b in bruts]
    for i in sorted(range(len(bruts)), key=lambda i: -(bruts[i] - entiers[i]))[: total - sum(entiers)]:
        entiers[i] += 1
    return entiers


def generer_zones():
    """Arr. 1 et 2 : moitiés ouest et est du disque central ; arr. 3 à 12 : couronne."""
    pieces = []   # (arrondissement, r_int, r_ext, a0, a1, bande)
    for arr, (a0, a1) in ((1, (90, 270)), (2, (-90, 90))):
        milieu = (a0 + a1) / 2
        pieces += [(arr, 0, RAYON_CENTRE_M, a0, milieu, "interieure"),
                   (arr, 0, RAYON_CENTRE_M, milieu, a1, "interieure")]
    couronne = list(range(3, 13))
    total = sum(POPULATION_2019[a] for a in couronne)
    angle, rayon_milieu = 90.0, (RAYON_CENTRE_M + RAYON_COMMUNE_M) / 2 - 1500
    for arr in couronne:                                  # dans le sens horaire depuis le nord
        largeur = 360 * POPULATION_2019[arr] / total
        n = max(1, round(POPULATION_2019[arr] / 96_000))
        for k in range(n):
            a0 = angle - largeur * k / n
            a1 = angle - largeur * (k + 1) / n
            pieces += [(arr, RAYON_CENTRE_M, rayon_milieu, a1, a0, "interieure"),
                       (arr, rayon_milieu, RAYON_COMMUNE_M, a1, a0, "exterieure")]
        angle -= largeur

    zones, numero = [], 1
    for arr in range(1, 13):
        siennes = [p for p in pieces if p[0] == arr]
        poids = [aire_secteur(*p[1:5]) * POIDS_BANDE[p[5]] for p in siennes]
        for (a, r_int, r_ext, a0, a1, bande), pop in zip(siennes, repartir(POPULATION_2019[arr], poids)):
            aire_km2 = aire_secteur(r_int, r_ext, a0, a1) / 1e6
            zones.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [arc(r_int, r_ext, a0, a1)]},
                "properties": {"id": numero, "nom": f"Arr. {arr} — secteur {numero}", "arrondissement": arr,
                               "population": pop, "densite": round(pop / aire_km2, 1),
                               "bande": bande, "superficie_km2": round(aire_km2, 2)},
            })
            numero += 1
    return zones


def point_dans_piece(rng, zone):
    """Point au hasard dans une zone (tirage dans l'emprise puis test d'appartenance)."""
    from simulation.geometrie import point_dans_geometrie
    xs = [c[0] for c in zone["geometry"]["coordinates"][0]]
    ys = [c[1] for c in zone["geometry"]["coordinates"][0]]
    while True:
        lo, la = rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys))
        if point_dans_geometrie(la, lo, zone["geometry"]):
            return round(la, 6), round(lo, 6)


def tirer(rng, table):
    r, cumul = rng.random(), 0.0
    for valeur, p in table:
        cumul += p
        if r <= cumul:
            return valeur
    return table[-1][0]


def generer_depotoirs(rng, zones):
    """35 centres de collecte (officiels) + 180 dépotoirs illégaux, plus nombreux en périphérie."""
    poids = [z["properties"]["population"] * (2.0 if z["properties"]["bande"] == "exterieure" else 1.0) for z in zones]
    depotoirs = []

    def ajouter(zone, legalite, statut, volume, nb_sig, reap, premiere):
        la, lo = point_dans_piece(rng, zone)
        depotoirs.append({
            "type": "Feature", "geometry": {"type": "Point", "coordinates": [lo, la]},
            "properties": {"id": len(depotoirs) + 1, "zone_id": zone["properties"]["id"],
                           "arrondissement": zone["properties"]["arrondissement"], "legalite": legalite,
                           "statut": statut, "volume_estime": volume, "nb_signalements": nb_sig,
                           "nb_reapparitions": reap, "premiere_detection": premiere.isoformat(),
                           "derniere_maj": (premiere + timedelta(days=rng.randint(0, 20))).isoformat()},
        })

    # Centres de collecte et de tri : au moins deux par arrondissement de la couronne, un au centre.
    par_arr = {}
    for z in zones:
        par_arr.setdefault(z["properties"]["arrondissement"], []).append(z)
    centres = [rng.choice(par_arr[a]) for a in (1, 2)] + \
        [rng.choice(par_arr[a]) for a in range(3, 13) for _ in range(3 if POPULATION_2019[a] > 250_000 else 2)]
    centres = (centres + rng.choices(zones, weights=poids, k=35))[:35]
    for z in centres:
        ajouter(z, "officiel", "actif", "gros", 0, 0, AUJOURD_HUI - timedelta(days=rng.randint(400, 2000)))

    statuts = [("actif", 0.70), ("intervention_planifiee", 0.05), ("eradique", 0.10),
               ("sous_surveillance", 0.10), ("classe", 0.05)]
    volumes = [("petit", 0.50), ("moyen", 0.35), ("gros", 0.15)]
    for z in rng.choices(zones, weights=poids, k=180):
        statut = tirer(rng, statuts)
        reap = rng.choice([0, 0, 0, 1, 1, 2, 3]) if statut in ("actif", "sous_surveillance") else 0
        ajouter(z, "illegal", statut, tirer(rng, volumes), rng.randint(1, 8), reap,
                AUJOURD_HUI - timedelta(days=rng.randint(5, 120)))
    return depotoirs


def generer_signalements(rng, zones, depotoirs):
    """Historique anonyme : signalements vérifiés liés aux dépotoirs, en attente et rejetés."""
    signalements = []

    def ajouter(la, lo, zone_id, arr, statut, depotoir_id, quand, motif=None):
        signalements.append({
            "type": "Feature", "geometry": {"type": "Point", "coordinates": [lo, la]},
            "properties": {"id": len(signalements) + 1, "type_dechet": tirer(rng, TYPES),
                           "volume_estime": tirer(rng, [("petit", 0.45), ("moyen", 0.40), ("gros", 0.15)]),
                           "statut": statut, "motif": motif, "depotoir_id": depotoir_id, "zone_id": zone_id,
                           "arrondissement": arr, "cree_le": quand.isoformat()},
        })

    illegaux = [d for d in depotoirs if d["properties"]["legalite"] == "illegal"]
    for d in illegaux:                                     # chaque signalement compté par le dépotoir
        p = d["properties"]
        debut = datetime.fromisoformat(p["premiere_detection"])
        for _ in range(p["nb_signalements"]):
            lo, la = d["geometry"]["coordinates"]
            dx, dy = rng.uniform(-18, 18), rng.uniform(-18, 18)   # à moins de 25 m du dépotoir
            la2, lo2 = depuis_metres(dx, dy, la, lo)
            quand = debut + timedelta(hours=rng.randint(0, max(1, int((AUJOURD_HUI - debut).total_seconds() // 3600))))
            ajouter(round(la2, 6), round(lo2, 6), p["zone_id"], p["arrondissement"], "verifie", p["id"], quand)

    poids = [z["properties"]["population"] for z in zones]
    for z in rng.choices(zones, weights=poids, k=60):      # récents, pas encore modérés
        la, lo = point_dans_piece(rng, z)
        ajouter(la, lo, z["properties"]["id"], z["properties"]["arrondissement"], "en_attente_revue", None,
                AUJOURD_HUI - timedelta(hours=rng.randint(1, 72)))
    motifs = ["photo sans rapport", "doublon", "déjà traité", "dépôt autorisé (centre de collecte)"]
    for z in rng.choices(zones, weights=poids, k=45):      # rejetés par la modération
        la, lo = point_dans_piece(rng, z)
        ajouter(la, lo, z["properties"]["id"], z["properties"]["arrondissement"], "rejete", None,
                AUJOURD_HUI - timedelta(days=rng.randint(1, 90)), rng.choice(motifs))
    signalements.sort(key=lambda f: f["properties"]["cree_le"])
    for i, f in enumerate(signalements, start=1):
        f["properties"]["id"] = i
    return signalements


def collection(features, description, licence):
    return {"type": "FeatureCollection",
            "metadata": {"description": description, "licence": licence, "genere_par": "scripts/generer_donnees_ouaga.py",
                         "graine": GRAINE, "date_reference": AUJOURD_HUI.isoformat(), "fictif": True},
            "features": features}


def main():
    rng = random.Random(GRAINE)
    zones = generer_zones()
    depotoirs = generer_depotoirs(rng, zones)
    signalements = generer_signalements(rng, zones, depotoirs)
    DOSSIER.mkdir(parents=True, exist_ok=True)
    ecrire = lambda nom, contenu: (DOSSIER / nom).write_text(
        json.dumps(contenu, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    ecrire("zones.geojson", collection(
        zones, "Secteurs SCHÉMATIQUES des 12 arrondissements de Ouagadougou ; population réelle par "
               "arrondissement (INSD, RGPH 2019), répartie entre secteurs. Ce ne sont pas les limites administratives.",
        "ODbL-1.0"))
    ecrire("depotoirs.geojson", collection(
        depotoirs, "Dépotoirs FICTIFS mais plausibles ; les 35 sites officiels figurent les centres de collecte et de tri.",
        "ODbL-1.0"))
    ecrire("signalements.geojson", collection(
        signalements, "Signalements citoyens FICTIFS, anonymes (ni appareil, ni photo, ni texte libre).", "ODbL-1.0"))
    pop = sum(z["properties"]["population"] for z in zones)
    print(f"{len(zones)} secteurs ({pop} habitants, {SUPERFICIE_KM2:.0f} km²), {len(depotoirs)} dépotoirs, "
          f"{len(signalements)} signalements → {DOSSIER}")


if __name__ == "__main__":
    main()
