"""Génère le jeu de données réaliste de Ouagadougou (livrable 4), dans `data/ouaga/`.

    python scripts/generer_donnees_ouaga.py

Déterministe (graine fixe) : relancer donne exactement les mêmes fichiers.

Ce qui est **réel** (sources dans `data/ouaga/LISEZMOI.md`) :
- **découpage administratif** : 12 arrondissements et 55 secteurs relevés sur la carte de
  l'INSD (monographie RGPH 2019), calés sur le terrain (`scripts/arrondissements_insd.py`, D42) ;
- population de chaque arrondissement : INSD, 5e RGPH 2019, tableau 2.2 ;
- composition des déchets (UN-Habitat) pour la répartition des types signalés ;
- 35 centres de collecte et de tri dans la ville (UN-Habitat), saisis ici comme sites officiels.

Ce qui est **approché ou fictif** (autorisé par les organisateurs) :
- limites **entre secteurs** d'un même arrondissement (Voronoï autour des numéros relevés) ;
- répartition de la population d'un arrondissement entre ses secteurs, au prorata de la
  superficie (la monographie ne donne pas la population par secteur) ;
- position des dépotoirs, des centres de collecte et l'historique des signalements.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shapely.geometry import mapping, shape  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arrondissements_insd import ARRONDISSEMENT_DU_SECTEUR, decoupage  # noqa: E402

from simulation.geometrie import aire_m2, depuis_metres, distance_m  # noqa: E402

GRAINE = 2026
DOSSIER = Path(__file__).resolve().parent.parent / "data" / "ouaga"
CENTRE = (12.368148, -1.5270851)          # centre administratif (OpenStreetMap, node 27565002)
RAYON_PERIPHERIE_M = 7000                 # au-delà : quartiers périphériques, plus de dépôts sauvages [H]
AUJOURD_HUI = datetime(2026, 11, 17, 8, 0, tzinfo=timezone.utc)

# INSD, RGPH 2019, monographie de la commune de Ouagadougou, tableau 2.2.
POPULATION_2019 = {1: 102_528, 2: 83_436, 3: 311_406, 4: 207_647, 5: 129_984, 6: 222_854,
                   7: 282_837, 8: 152_880, 9: 336_483, 10: 263_969, 11: 254_928, 12: 66_314}
DENSITE_2019 = 4385.5                    # hab./km², tableau 2.3

# Composition UN-Habitat (alimentaires 22 %, plastiques 5 %, papiers 6 %, autres 67 %), ramenée
# aux types de l'application : les « autres » sont surtout des ordures ménagères mélangées.
TYPES = [("menager", 0.55), ("organique", 0.20), ("plastiques", 0.10), ("gravats", 0.08),
         ("encombrants", 0.05), ("autre", 0.02)]


def aire_km2(geometrie) -> float:
    return aire_m2(mapping(geometrie)) / 1e6


def repartir(total, poids):
    """Entiers proportionnels à `poids`, de somme exactement `total`."""
    bruts = [total * p / sum(poids) for p in poids]
    entiers = [int(b) for b in bruts]
    for i in sorted(range(len(bruts)), key=lambda i: -(bruts[i] - entiers[i]))[: total - sum(entiers)]:
        entiers[i] += 1
    return entiers


def _arrondir(geo: dict) -> dict:
    def r(c):
        return [r(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 6), round(c[1], 6)]
    return {"type": geo["type"], "coordinates": r(geo["coordinates"])}


def generer_zones():
    """Les 55 secteurs (carte INSD) ; population de l'arrondissement répartie au prorata de la superficie."""
    _, secteurs, _ = decoupage()
    zones = []
    for arr in range(1, 13):
        siens = sorted(s for s, a in ARRONDISSEMENT_DU_SECTEUR.items() if a == arr)
        surfaces = [aire_km2(secteurs[s]) for s in siens]
        for s, surface, pop in zip(siens, surfaces, repartir(POPULATION_2019[arr], surfaces)):
            centre = secteurs[s].representative_point()
            zones.append({
                "type": "Feature",
                "geometry": _arrondir(mapping(secteurs[s])),
                "properties": {"id": s, "nom": f"Secteur {s}", "arrondissement": arr, "population": pop,
                               "densite": round(pop / surface, 1), "superficie_km2": round(surface, 2),
                               "peripherie": distance_m(centre.y, centre.x, *CENTRE) > RAYON_PERIPHERIE_M},
            })
    return zones


def point_dans_piece(rng, zone):
    """Point au hasard dans une zone (tirage dans l'emprise puis test d'appartenance)."""
    from simulation.geometrie import point_dans_geometrie
    min_lo, min_la, max_lo, max_la = shape(zone["geometry"]).bounds
    xs, ys = [min_lo, max_lo], [min_la, max_la]
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
    poids = [z["properties"]["population"] * (2.0 if z["properties"]["peripherie"] else 1.0) for z in zones]
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
        zones, "Les 55 secteurs des 12 arrondissements de Ouagadougou, relevés sur la carte de l'INSD (RGPH 2019) et "
               "calés sur le terrain (D42) ; limites entre secteurs approchées (Voronoï) ; population réelle par "
               "arrondissement (INSD, RGPH 2019), répartie entre secteurs au prorata de la superficie.",
        "ODbL-1.0"))
    arrondissements, _, commune = decoupage()
    ecrire("arrondissements.geojson", collection(
        [{"type": "Feature", "geometry": _arrondir(mapping(g)),
          "properties": {"arrondissement": a, "population": POPULATION_2019[a],
                         "superficie_km2": round(aire_km2(g), 1),
                         "secteurs": sorted(s for s, aa in ARRONDISSEMENT_DU_SECTEUR.items() if aa == a)}}
         for a, g in sorted(arrondissements.items())],
        "Les 12 arrondissements de Ouagadougou relevés sur la carte de l'INSD (RGPH 2019), calés sur le terrain (D42).",
        "ODbL-1.0"))
    ecrire("commune_ouagadougou.geojson", collection(
        [{"type": "Feature", "geometry": _arrondir(mapping(commune)), "properties": {"nom": "Ouagadougou"}}],
        "Contour de la commune d'après la carte de l'INSD (RGPH 2019), calé sur le contour OpenStreetMap (D42).",
        "ODbL-1.0"))
    ecrire("depotoirs.geojson", collection(
        depotoirs, "Dépotoirs FICTIFS mais plausibles ; les 35 sites officiels figurent les centres de collecte et de tri.",
        "ODbL-1.0"))
    ecrire("signalements.geojson", collection(
        signalements, "Signalements citoyens FICTIFS, anonymes (ni appareil, ni photo, ni texte libre).", "ODbL-1.0"))
    pop = sum(z["properties"]["population"] for z in zones)
    print(f"{len(zones)} secteurs ({pop} habitants, {aire_km2(commune):.0f} km²),"
          f" {len(depotoirs)} dépotoirs, "
          f"{len(signalements)} signalements → {DOSSIER}")


if __name__ == "__main__":
    main()
