import streamlit as st
from utils.tools import load_json_data
import pandas as pd

# Cette fonction affiche l'interface utilisateur pour visualiser les commandes du round actuel
# Entrée: Aucune (utilise st.session_state pour accéder au round courant)
# Sortie: Interface Streamlit affichant les commandes détaillées
def show_orders_page():
    # Définit le titre de la page avec une icône
    st.title("📦 Orders du round")

    # Récupère le numéro du round actuel depuis l'état de la session Streamlit
    current_round = st.session_state.round

    # Charge les données des commandes pour le round actuel depuis le fichier JSON correspondant
    # La clé "ORDERS" est utilisée pour accéder au tableau des commandes dans le JSON
    order_data = load_json_data(f"ressources/orders/order_{current_round}.json")["ORDERS"]

    # Parcourt chaque commande et crée un élément d'interface expandable pour chacune
    for index, order in enumerate(order_data):
        # Crée un élément dépliable pour chaque commande, identifié par son ID
        with st.expander(f"ID: {order['id']}"):
            # Affiche les informations de base de la commande avec mise en forme (gras)
            st.write(f"**Start:** {order['start']}")  # Point de départ
            st.write(f"**End:** {order['end']}")      # Point d'arrivée
            st.write(f"**Delivery Time:** {order['delivery_time']}")  # Heure de livraison prévue
            
            # Affiche les détails du contenu de la commande
            st.write("**Content:**")
            # Affiche le volume en mètres cubes
            st.write(f"- **Volume:** {order['content']['volume_m3']} m³")
            # Affiche le poids en kilogrammes
            st.write(f"- **Weight:** {order['content']['poids_kg']} kg")
            # Affiche la description textuelle du contenu
            st.write(f"- **Description:** {order['content']['description']}")