import streamlit as st
from utils.tools import load_json_data
import pandas as pd

# Fonction qui affiche les informations des véhicules disponibles pour le round actuel
# Entrée: Aucune (utilise st.session_state.round)
# Sortie: Affichage Streamlit des véhicules et leurs caractéristiques
def transport_view():
    # Titre de la section avec emoji
    st.title("🚗 Vehicules du round")

    # Chargement des données de véhicules à partir du fichier de configuration correspondant au round actuel
    # Le chemin est construit dynamiquement avec le numéro du round stocké dans la session Streamlit
    vehicules_data = load_json_data(f"ressources/config/config_{st.session_state.round}.json")["fleet"]

    # Itération sur chaque véhicule pour afficher ses caractéristiques
    for index, vehicule in enumerate(vehicules_data):
        # Création d'un élément dépliable (expander) pour chaque véhicule
        # Le nom du véhicule est utilisé comme titre de l'expander
        with st.expander(f"Name: {vehicule['nom']}"):
            # Affichage des caractéristiques du véhicule avec mise en forme en gras pour les labels
            st.write(f"**Max Load Weight:** {vehicule['charge_max_emport_kg']} kg")
            st.write(f"**Max Load Volume:** {vehicule['volume_max_emport_m3']} m³")
            st.write(f"**Range:** {vehicule['autonomie_charge_km']} km")
            st.write(f"**Max Speed:** {vehicule['vitesse_max']} km/h")
            st.write(f"**CO2 Impact (Loaded):** {vehicule['impact_km_charge_co2']} kg CO2/km")
            st.write(f"**CO2 Impact (Empty):** {vehicule['impact_km_vide_co2']} kg CO2/km")
            st.write(f"**Air Quality Score:** {vehicule['crit_air']}")
            st.write(f"**Cost per km (Loaded):** €{vehicule['cout_utilisation_km_charge']}")
            st.write(f"**Cost per km (Empty):** €{vehicule['cout_utilisation_km_vide']}")
            st.write(f"**Daily Fixed Cost:** €{vehicule['cout_fixe_utilisation_journalier']}")
            st.write(f"**Storage Point:** {vehicule['storage_point']}")
            # Note: L'utilisation d'expanders est un bon choix UI pour montrer plusieurs
            # véhicules sans prendre trop d'espace vertical sur la page