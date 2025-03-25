# pages/simulation_view.py

import streamlit as st
from utils.game_logic import Simulation
import pandas as pd

# Fonction principale pour afficher et gérer la page de simulation
# Entrée: Aucune
# Sortie: Interface utilisateur Streamlit pour la simulation des livraisons
def show_simulation_page():
    # Affiche le titre de la page
    st.title("🔄 Simulation des livraisons")
    # Crée un bouton pour lancer la simulation

    if 'routes' not in st.session_state:
        st.session_state.routes = []

    if st.button("Lancer la simulation avec pas de temps") and st.session_state.routes != []:
        # Initialise un nouvel objet Simulation
        sim = Simulation()
        # Exécute la simulation qui avance par pas de temps et récupère les événements générés
        events = sim.run_simulation_with_time_step()
        # Stocke les événements dans l'état de session pour une utilisation ultérieure
        st.session_state.simulation_events = events
        # Affiche un message de succès
        st.success("Simulation terminée avec pas de temps !")
        # Affiche les résultats de la simulation (tableau des événements)
        sim.display_simulation()

        # Affiche l'en-tête pour le rapport d'impact
        st.subheader("Rapport d'impacte par véhicule")
        
        # Affiche les impacts pour chaque véhicule (coûts, émissions, distances)
        sim.display_impact()

        # Affiche l'en-tête pour le rapport d'état des livraisons
        st.subheader("Rapport d'état de livraison")

        # Récupère l'état des livraisons (à l'heure, en retard, non livrées)
        delivery_status = sim.check_deliveries()
        # Prépare les données pour le DataFrame
        data = {
            "Commande": list(delivery_status.keys()),
            "État": list(delivery_status.values())
        }
        # Crée un DataFrame pandas avec les données préparées
        df = pd.DataFrame(data)

        # Fonction pour définir la coloration conditionnelle des cellules
        # Entrée: status - statut de livraison
        # Sortie: chaîne de style CSS pour la coloration de la cellule
        def color_status(status):
            # Colore en vert les livraisons à l'heure
            if status == "on_time":
                return "background-color: green; color: white;"
            # Colore en orange les livraisons en retard
            elif status == "late":
                return "background-color: orange; color: white;"
            # Colore en vert clair les livraisons partielles à l'heure
            elif status == "on_time_partial":
                return "background-color: lightgreen; color: black;"
            # Colore en or les livraisons partielles en retard
            elif status == "late_partial":
                return "background-color: gold; color: black;"
            # Colore en rouge les commandes non livrées
            elif status == "not_delivered":
                return "background-color: red; color: white;"
            # Colore en gris les autres cas (non définis)
            else:
                return "background-color: gray; color: white;"

        # Affiche un titre pour la section
        st.title("État des Livraisons")

        # Applique la coloration conditionnelle au DataFrame
        # Note: La fonction est appliquée uniquement aux valeurs spécifiques pour éviter les erreurs
        styled_df = df.style.applymap(lambda v: color_status(v) if v in ["on_time", "late", "not_delivered"] else "")

        # Affiche le tableau avec les couleurs appliquées
        st.dataframe(styled_df)

    elif st.session_state.routes == []:
        st.warning('Pas encore de planning crée')

    # Affiche un message d'instruction si la simulation n'a pas encore été lancée
    else:
        st.write("Cliquez sur le bouton pour lancer la simulation.")