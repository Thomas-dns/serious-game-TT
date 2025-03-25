import json
import streamlit as st

# Fonction qui charge et lit des données JSON à partir d'un fichier
# Entrée: path - chemin du fichier JSON à charger
# Sortie: données JSON chargées ou None en cas d'erreur
def load_json_data(path):
    try:
        # Ouvre le fichier spécifié en mode lecture
        with open(path, 'r') as f:
            # Parse le contenu JSON et le stocke dans data
            data = json.load(f)
            return data
    except FileNotFoundError:
        # Gestion d'erreur: affiche un message si le fichier n'existe pas
        st.error("Fichier de configuration non trouvé")
        return None
    except json.JSONDecodeError:
        # Gestion d'erreur: affiche un message si le format JSON est invalide
        st.error("Erreur dans le format du fichier JSON")
        return None