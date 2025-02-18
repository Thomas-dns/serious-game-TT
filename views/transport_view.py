import streamlit as st
from utils.tools import load_json_data
import pandas as pd

def transport_view():
    st.title("🚗 Vehicules du round")

    vehicules_data = load_json_data(f"ressources/config/config_{st.session_state.round}.json")["fleet"]

    for index, vehicule in enumerate(vehicules_data):
        with st.expander(f"Name: {vehicule['nom']}"):
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