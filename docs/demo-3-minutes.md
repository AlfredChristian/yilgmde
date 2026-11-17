# Démonstration jury — 3 minutes

## Préparation (avant de parler)

1. Base de démonstration neuve chargée : `python scripts/charger_exemples.py --ouaga --demo` (comptes chauffeur et Laabal, scénarios base / pluies / panne / sensibilisation sur l'arrondissement 9, tournées affectées ; identifiants affichés par le script).
2. API ouverte sur `http://localhost:8000` et front sur Vite.
3. Administrateur connecté ; ouvrir `/admin/plan` dans un onglet et `/signaler` dans un autre.
4. Les variantes « pluies », « panne » et « sensibilisation » existent déjà : à 2:20, choisir la variante comme scénario de travail et comparer avec « base ». Pour en créer une en direct, la nommer : elle devient le scénario de travail et la référence reste intacte.

## Script chronométré

| Temps | Action à l'écran | Message à dire |
|---|---|---|
| 0:00–0:20 | Accueil puis carte | « Yilgmde aide Ouagadougou à passer du signalement citoyen à une décision de collecte mesurable. » |
| 0:20–0:45 | `/signaler` : position, type, volume, note vocale ; envoyer | « Un citoyen peut signaler sans compte, même hors connexion. L'appareil reçoit un identifiant anonyme et le signalement reste traçable par code. » |
| 0:45–1:05 | `/admin` : file de modération ; valider | « La mairie garde la décision humaine : les doublons et incohérences sont expliqués, mais ne remplacent pas la modération. Les photos sont floutées côté serveur avant stockage. » |
| 1:05–1:35 | `/admin/plan` : choisir arrondissement 9 | « À partir des dépotoirs vérifiés et de la population, le moteur propose des points, des tournées et distingue capacité des camions et part de déchets réellement captée. » |
| 1:35–1:55 | Modifier « saison des pluies » ou pannes | « Le jury peut changer un paramètre en direct. Le plan se recalcule ; on voit immédiatement l'effet sur les tournées, le coût et le budget. » |
| 1:55–2:20 | Lancer simulation 30 jours, graine 42 | « La simulation rend visible l'évolution quotidienne : part captée, déchets sauvages, dépotoirs actifs et coût. Même graine, mêmes résultats : la comparaison est juste. » |
| 2:20–2:40 | Comparer base et variante | « Ici, nous comparons deux décisions à hasard identique. La meilleure valeur est mise en évidence, avec l'écart à la référence. » |
| 2:40–3:00 | Données ouvertes / conclusion | « Le code est MIT, les données de démonstration ODbL et le moteur est réutilisable par une autre commune. La prochaine étape est de remplacer les hypothèses par les données officielles. » |

## Règles de présentation

- Ne jamais promettre une donnée réelle lorsque le jeu est fictif ou une valeur `[H]`.
- Si le calcul dépasse quelques secondes, sélectionner d'abord un arrondissement plutôt que la commune entière.
- Garder l'écran de comparaison ouvert pour répondre aux questions sur les pluies, les pannes, le budget ou la sensibilisation.