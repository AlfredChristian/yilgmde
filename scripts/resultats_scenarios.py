"""Livrable 5 : chiffres, tableaux, courbes et plan de gestion pour le rapport.

    python scripts/resultats_scenarios.py              # arrondissement 9, 30 jours, graine 42
    python scripts/resultats_scenarios.py --arrondissement 4 --jours 60

Calcule, sur le jeu de Ouagadougou (`data/ouaga/`) et la config de Ouaga, le plan et la
simulation de chaque scénario, et écrit dans `docs/rapport/` :
- `resultats.md` : scénarios, indicateurs du plan, résumé des simulations (à copier dans le rapport) ;
- `resultats.csv` et `simulation_par_jour.csv` : les mêmes chiffres, pour un tableur ;
- `courbes_*.png` : évolution jour par jour (part captée, déchets sauvages et coût cumulés) ;
- `carte_plan.png` : secteurs, points de regroupement et tournées du scénario de base ;
- `plan_de_gestion.md` : la synthèse lisible du plan de base (même texte que l'API).

Déterministe : même graine, mêmes chiffres. Rien n'est lu en base : tout part des fichiers.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from backend.config import appliquer_surcharges, charger_config  # noqa: E402
from backend.synthese import synthese_markdown  # noqa: E402
from simulation.agents import simuler  # noqa: E402
from simulation.plan import calculer_plan  # noqa: E402

DOSSIER_DONNEES = RACINE / "data" / "ouaga"
DOSSIER_SORTIE = RACINE / "docs" / "rapport"

# Palette catégorielle validée (ordre fixe, jamais recyclé) ; texte et grille en encres neutres.
COULEURS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
ENCRE, ENCRE_2, GRILLE, FOND = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def scenarios(config: dict) -> list[tuple[str, str, dict]]:
    """(nom court, description, surcharges). La panne retire les 60 premiers camions sur 70."""
    n = len(config["camions"])
    panne = [{"id": c["id"], "disponible": False} for c in config["camions"][: max(0, n - 10)]]
    budget = config["mairie"]["budget_mensuel_xof"]
    return [
        ("Base", "Paramètres de Ouagadougou, saison sèche", {}),
        ("Pluies", "Saison des pluies : +10 % de déchets, camions 30 % plus lents, moins d'apport volontaire",
         {"scenario": {"saison": "pluies"}}),
        ("Panne", f"{len(panne)} camions sur {n} indisponibles (il en reste {n - len(panne)})", {"camions": panne}),
        ("Sensibilisation", "Apport volontaire aux points porté de 60 % à 80 %",
         {"simulation": {"prob_apport_volontaire": 0.8}}),
        ("Abonnements", "Abonnement aux pré-collecteurs porté de 30 % à 50 % des ménages",
         {"population": {"taux_abonnement_precollecteurs": 0.5}}),
        ("Budget ÷ 2", f"Budget mensuel de la commune réduit de moitié ({budget // 2:,} XOF)".replace(",", " "),
         {"mairie": {"budget_mensuel_xof": budget // 2}}),
    ]


def lire_donnees() -> dict:
    zones = json.loads((DOSSIER_DONNEES / "zones.geojson").read_text(encoding="utf-8"))["features"]
    depotoirs = json.loads((DOSSIER_DONNEES / "depotoirs.geojson").read_text(encoding="utf-8"))["features"]
    return {
        "zones": [{**{k: f["properties"][k] for k in ("id", "nom", "population", "densite", "arrondissement")},
                   "geometrie": f["geometry"]} for f in zones],
        "depotoirs": [dict(f["properties"], latitude=f["geometry"]["coordinates"][1],
                           longitude=f["geometry"]["coordinates"][0]) for f in depotoirs],
    }


def calculer(arrondissement: int, jours: int, graine: int) -> tuple[dict, list[dict]]:
    base = charger_config("ouagadougou")
    donnees = lire_donnees()
    resultats = []
    for nom, description, surcharges in scenarios(base):
        config = appliquer_surcharges(base, {**surcharges, "perimetre": {"arrondissements": [arrondissement]}})
        debut = time.perf_counter()
        plan = calculer_plan(donnees, config)
        duree_ms = int((time.perf_counter() - debut) * 1000)
        sim = simuler(donnees, config, jours, graine, plan=plan)
        resultats.append({"nom": nom, "description": description, "surcharges": surcharges, "config": config,
                          "plan": plan, "duree_ms": duree_ms, "simulation": sim})
    return donnees, resultats


# --- Sorties texte ------------------------------------------------------------------------

def nb(v, d=0) -> str:
    return f"{v:,.{d}f}".replace(",", " ").replace(".", ",")


def ecrire_tableaux(resultats, arrondissement, jours, graine) -> None:
    lignes_plan, lignes_sim = [], []
    for r in resultats:
        i, s = r["plan"]["indicateurs"], r["simulation"]["resume"]
        lignes_plan.append(f"| {r['nom']} | {nb(i['capacite_collecte_pct'], 1)} % | {nb(i['part_captee_estimee_pct'], 1)} % "
                           f"| {i['nb_points_regroupement']} | {len(i['camions_utilises'])} | {nb(i['distance_totale_km'])} "
                           f"| {nb(i['cout_mensuel_estime_xof'] / 1e6, 1)} | {nb(i['budget_mensuel_xof'] / 1e6, 1)} "
                           f"| {nb(r['duree_ms'] / 1000, 1)} s |")
        lignes_sim.append(f"| {r['nom']} | {nb(s['part_captee_moyenne_pct'], 1)} % | {nb(s['dechets_sauvages_kg'] / 1000)} t "
                          f"| {s['depotoirs_actifs_debut']} → {s['depotoirs_actifs_fin']} | {s['depotoirs_eradiques']} "
                          f"| {s['passages_collecte']} / {s['passages_suspendus_budget']} | {nb(s['cout_total_xof'] / 1e6, 1)} "
                          f"| {nb(s['amendes_total_xof'] / 1000)} k |")
    pop = resultats[0]["plan"]["indicateurs"]["perimetre"]["population"]
    secteurs = resultats[0]["plan"]["indicateurs"]["perimetre"]["zones"]
    texte = [
        f"# Résultats des scénarios — arrondissement {arrondissement} de Ouagadougou", "",
        f"Généré par `scripts/resultats_scenarios.py` le {datetime.now(timezone.utc):%Y-%m-%d} : jeu `data/ouaga/`, "
        f"config de Ouagadougou, simulation de {jours} jours, graine {graine}. Arrondissement {arrondissement} : "
        f"{nb(pop)} habitants (RGPH 2019), secteurs {secteurs[0]} à {secteurs[-1]}. Relancer donne les mêmes chiffres.", "",
        "## Scénarios", "", "| Scénario | Ce qui change |", "|---|---|",
        *[f"| {r['nom']} | {r['description']} |" for r in resultats], "",
        "## Plan de gestion (un passage de collecte)", "",
        "- **Capacité de collecte** : part du stock des points que les camions peuvent vider.",
        "- **Part captée estimée** : part des déchets produits qui arrive aux points (pré-collecte + apport volontaire).", "",
        "| Scénario | Capacité de collecte | Part captée estimée | Points | Camions utilisés | Distance (km) "
        "| Coût mensuel (M XOF) | Budget de l'arr. (M XOF) | Calcul |",
        "|---|---|---|---|---|---|---|---|---|", *lignes_plan, "",
        f"## Simulation sur {jours} jours", "",
        "| Scénario | Part captée moyenne | Déchets sauvages | Dépotoirs actifs (début → fin) | Éradications (cumul) "
        "| Passages faits / annulés | Coût (M XOF) | Amendes (XOF) |",
        "|---|---|---|---|---|---|---|---|", *lignes_sim, "",
        "Les dépotoirs suivent le même chemin dans tous les scénarios : dès qu'une zone produit "
        f"des déchets sauvages au-delà de `seuil_nouveau_depotoir_kg`, un nouveau dépotoir y apparaît chaque jour "
        "(c'est le cas des 4 secteurs dans tous les scénarios), et les brigades Laabal, dont la capacité "
        "dépasse ces apparitions, ne dépendent pas des camions. L'effet des "
        "scénarios se lit donc sur les tonnes de déchets sauvages, pas sur le nombre de dépotoirs.", "",
        "Courbes : `courbes_part_captee.png`, `courbes_dechets_sauvages.png`, `courbes_cout.png`. "
        "Plan de base détaillé : `plan_de_gestion.md`, carte : `carte_plan.png`.", "",
        "Les hypothèses `[H]` sont listées dans `docs/parametres.md` ; les sources dans `data/ouaga/LISEZMOI.md`.", "",
    ]
    (DOSSIER_SORTIE / "resultats.md").write_text("\n".join(texte), encoding="utf-8")

    with open(DOSSIER_SORTIE / "resultats.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["scenario", "capacite_collecte_pct", "part_captee_estimee_pct", "points", "camions_utilises",
                    "distance_km", "cout_mensuel_xof", "budget_mensuel_xof", "part_captee_moyenne_pct",
                    "dechets_sauvages_kg", "depotoirs_actifs_debut", "depotoirs_actifs_fin", "depotoirs_eradiques",
                    "passages_collecte", "passages_suspendus_budget", "cout_simulation_xof", "amendes_xof"])
        for r in resultats:
            i, s = r["plan"]["indicateurs"], r["simulation"]["resume"]
            w.writerow([r["nom"], i["capacite_collecte_pct"], i["part_captee_estimee_pct"], i["nb_points_regroupement"],
                        len(i["camions_utilises"]), i["distance_totale_km"], i["cout_mensuel_estime_xof"],
                        i["budget_mensuel_xof"], s["part_captee_moyenne_pct"], s["dechets_sauvages_kg"],
                        s["depotoirs_actifs_debut"], s["depotoirs_actifs_fin"], s["depotoirs_eradiques"],
                        s["passages_collecte"], s["passages_suspendus_budget"], s["cout_total_xof"],
                        s["amendes_total_xof"]])
    with open(DOSSIER_SORTIE / "simulation_par_jour.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        champs = ["jour", "part_captee_pct", "depotoirs_actifs", "dechets_sauvages_kg", "cout_xof", "passage",
                  "collecte_suspendue", "depotoirs_eradiques", "reapparitions", "amendes_xof", "budget_restant_xof"]
        w.writerow(["scenario", *champs])
        for r in resultats:
            for j in r["simulation"]["indicateurs"]:
                w.writerow([r["nom"], *[j[c] for c in champs]])


def ecrire_plan(donnees, resultats, arrondissement) -> None:
    base = resultats[0]
    plan = dict(base["plan"], id=1, calcule_le=datetime.now(timezone.utc).isoformat(), duree_calcul_ms=base["duree_ms"])
    texte = synthese_markdown(plan, {"nom": f"Base — arrondissement {arrondissement}",
                                     "parametres": {"perimetre": {"arrondissements": [arrondissement]}}},
                              donnees["zones"], base["config"])
    (DOSSIER_SORTIE / "plan_de_gestion.md").write_text(texte, encoding="utf-8")


# --- Graphiques ----------------------------------------------------------------------------

def _axes(ax, titre, unite):
    ax.set_title(titre, loc="left", fontsize=12, color=ENCRE, pad=10)
    ax.set_ylabel(unite, color=ENCRE_2, fontsize=9)
    ax.set_xlabel("jour", color=ENCRE_2, fontsize=9)
    ax.grid(axis="y", color=GRILLE, linewidth=0.8)
    ax.set_facecolor(FOND)
    for cote in ("top", "right"):
        ax.spines[cote].set_visible(False)
    for cote in ("left", "bottom"):
        ax.spines[cote].set_color(GRILLE)
    ax.tick_params(colors=ENCRE_2, labelsize=8)


def courbes(resultats, cle, titre, unite, fichier, cumul=False, echelle=1.0) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150, facecolor=FOND)
    _axes(ax, titre, unite)
    fins = []
    for r, couleur in zip(resultats, COULEURS):
        jours = [j["jour"] for j in r["simulation"]["indicateurs"]]
        valeurs, total = [], 0.0
        for j in r["simulation"]["indicateurs"]:
            total = total + j[cle] if cumul else j[cle]
            valeurs.append(total / echelle)
        ax.plot(jours, valeurs, color=couleur, linewidth=2, label=r["nom"], solid_capstyle="round")
        fins.append((valeurs[-1], r["nom"], jours[-1]))
    # Étiquettes directes en bout de courbe, écartées pour ne pas se chevaucher (texte en encre neutre).
    bas, haut = ax.get_ylim()
    ecart = (haut - bas) * 0.045
    positions = []
    for v, nom, x in sorted(fins):
        y = max(v, positions[-1] + ecart) if positions else v
        positions.append(y)
        ax.annotate(nom, (x, v), xytext=(x + 0.6, y), fontsize=8, color=ENCRE_2, va="center",
                    arrowprops={"arrowstyle": "-", "color": GRILLE, "lw": 0.8})
    ax.set_xlim(1, resultats[0]["simulation"]["indicateurs"][-1]["jour"] + 6)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.16), ncol=6, frameon=False, fontsize=8, labelcolor=ENCRE_2)
    fig.tight_layout()
    fig.savefig(DOSSIER_SORTIE / fichier, facecolor=FOND)
    plt.close(fig)


def carte(donnees, resultats, arrondissement) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plan = resultats[0]["plan"]
    zones = [z for z in donnees["zones"] if z["arrondissement"] == arrondissement]
    fig, ax = plt.subplots(figsize=(7.5, 7.5), dpi=150, facecolor=FOND)
    ax.set_facecolor(FOND)

    def anneaux(g):
        return g["coordinates"] if g["type"] == "Polygon" else [r for p in g["coordinates"] for r in p]
    for z in zones:
        for anneau in anneaux(z["geometrie"]):
            xs, ys = zip(*anneau)
            ax.fill(xs, ys, color="#eeede9", zorder=0)
            ax.plot(xs, ys, color="#b9b7b0", linewidth=0.8, zorder=1)
        cx = sum(x for x, _ in z["geometrie"]["coordinates"][0]) / len(z["geometrie"]["coordinates"][0])
        cy = sum(y for _, y in z["geometrie"]["coordinates"][0]) / len(z["geometrie"]["coordinates"][0])
        ax.text(cx, cy, f"secteur {z['id']}", fontsize=8, color=ENCRE_2, ha="center", zorder=5)
    # Une tournée par jour du passage (couleurs 1 à 3), un trait fin par rotation.
    for t in plan["tournees"]:
        if t["type"] != "collecte" or not t["arrets"]:
            continue
        xs = [a["longitude"] for a in t["arrets"]]
        ys = [a["latitude"] for a in t["arrets"]]
        ax.plot(xs, ys, color=COULEURS[(t.get("jour", 1) - 1) % 3], linewidth=0.9, alpha=0.75, zorder=2)
    ax.scatter([p["longitude"] for p in plan["points_regroupement"]], [p["latitude"] for p in plan["points_regroupement"]],
               s=9, color=ENCRE, zorder=3, label="point de regroupement")
    illegaux = [d for d in donnees["depotoirs"] if d.get("arrondissement") == arrondissement
                and d["legalite"] == "illegal" and d["statut"] == "actif"]
    ax.scatter([d["longitude"] for d in illegaux], [d["latitude"] for d in illegaux], s=28, marker="x",
               color="#6250d6", linewidths=1.6, zorder=4, label="dépotoir illégal actif")
    for jour in sorted({t.get("jour", 1) for t in plan["tournees"] if t["type"] == "collecte"}):
        ax.plot([], [], color=COULEURS[(jour - 1) % 3], linewidth=2, label=f"tournées du jour {jour}")
    ax.set_title(f"Plan de base — arrondissement {arrondissement} : {len(plan['points_regroupement'])} points, "
                 f"{sum(1 for t in plan['tournees'] if t['type'] == 'collecte')} rotations",
                 loc="left", fontsize=11, color=ENCRE)
    ax.set_aspect(1 / 0.976)          # cos(12,4°) : distances est-ouest à la bonne échelle
    ax.axis("off")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.01), ncol=2, frameon=False, fontsize=8, labelcolor=ENCRE_2)
    fig.tight_layout()
    fig.savefig(DOSSIER_SORTIE / "carte_plan.png", facecolor=FOND)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arrondissement", type=int, default=9)
    parser.add_argument("--jours", type=int, default=30)
    parser.add_argument("--graine", type=int, default=42)
    args = parser.parse_args()

    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    donnees, resultats = calculer(args.arrondissement, args.jours, args.graine)
    ecrire_tableaux(resultats, args.arrondissement, args.jours, args.graine)
    ecrire_plan(donnees, resultats, args.arrondissement)
    courbes(resultats, "part_captee_pct", "Part des déchets captée, jour par jour", "% de la production",
            "courbes_part_captee.png")
    courbes(resultats, "dechets_sauvages_kg", "Déchets sauvages cumulés (hors des points et des camions)", "tonnes",
            "courbes_dechets_sauvages.png", cumul=True, echelle=1000)
    courbes(resultats, "cout_xof", "Coût cumulé de la collecte", "millions de XOF", "courbes_cout.png",
            cumul=True, echelle=1e6)
    carte(donnees, resultats, args.arrondissement)
    print(f"{len(resultats)} scénarios → {DOSSIER_SORTIE}")


if __name__ == "__main__":
    main()
