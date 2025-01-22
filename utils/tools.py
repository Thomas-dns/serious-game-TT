import json
import streamlit as st

def load_json_data(path):
    try:
        with open(path, 'r') as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        st.error("Fichier de configuration non trouvé")
        return None
    except json.JSONDecodeError:
        st.error("Erreur dans le format du fichier JSON")
        return None
