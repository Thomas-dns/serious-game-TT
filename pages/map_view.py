import streamlit as st
from utils.map_logic import create_map

def map_view():
    st.title("Map View")
    
    m, descriptions = create_map()
    # Afficher la carte
    m.to_streamlit(height=500)
    
    # Section des Zones
    st.markdown("<h1 style='text-align: center;'>Déscription des Points de livraison et des Zones</h1>", unsafe_allow_html=True)
    st.header("📍 Zones")

    for zone in st.session_state.zones:
        with st.expander(f"Zone : {zone.nom}"):
            st.write(zone.description)
    
    # Section des Points de livraison
    st.header("🚚 Points de livraison")
    for point in st.session_state.warehouses_info:
        with st.expander(f"Entrepôt : {point.nom}"):
            st.write(point.description)

if __name__ == "__main__":
    map_view()