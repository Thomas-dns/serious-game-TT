import streamlit as st
from utils.create_map import create_map

def map_view():
    st.title("Map View")
    
    m, descriptions = create_map()
    # Afficher la carte
    m.to_streamlit(height=500)
    
    # Section des Zones
    st.markdown("<h1 style='text-align: center;'>Déscription des Points de livraison et des Zones</h1>", unsafe_allow_html=True)
    st.header("📍 Zones")
    for zone_name, zone_desc in descriptions["ZONES"]:
        with st.expander(f"Zone : {zone_name}"):
            st.write(zone_desc)
    
    # Section des Points de livraison
    st.header("🚚 Points de livraison")
    for point_name, point_desc in descriptions["DELIVERY_POINTS"]:
        with st.expander(f"Point : {point_name}"):
            st.write(point_desc)

if __name__ == "__main__":
    map_view()