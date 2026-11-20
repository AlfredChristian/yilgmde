import os

# Pas de préchauffage des données en arrière-plan pendant les tests (D68) : chaque client de
# test démarre l'API, et ce chargement ne sert qu'au premier calcul d'un vrai serveur.
os.environ.setdefault("YILGMDE_PRECHAUFFER", "0")
