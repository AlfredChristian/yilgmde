# Chiffres du rapport (livrable 5)

Tout ce dossier est produit par :

```
python scripts/resultats_scenarios.py                       # arrondissement 9, 30 jours, graine 42
python scripts/resultats_scenarios.py --arrondissement 4    # un autre arrondissement
```

| Fichier | Contenu |
|---|---|
| `resultats.md` | scénarios, indicateurs du plan, résumé des simulations (à copier dans le rapport) |
| `resultats.csv`, `simulation_par_jour.csv` | les mêmes chiffres pour un tableur |
| `courbes_part_captee.png` | part des déchets captée, jour par jour |
| `courbes_dechets_sauvages.png` | déchets sauvages cumulés |
| `courbes_cout.png` | coût cumulé de la collecte |
| `carte_plan.png` | secteurs, points de regroupement, tournées par jour du passage, dépotoirs illégaux |
| `plan_de_gestion.md` | plan de gestion lisible du scénario de base (même texte que `GET /scenarios/{id}/plan/synthese`) |

Les chiffres sont déterministes (seuls la date et le temps de calcul changent d'une exécution à l'autre).
Données : `data/ouaga/` (fictives mais réalistes, ODbL). Hypothèses : `docs/parametres.md`. Décision : D43.
