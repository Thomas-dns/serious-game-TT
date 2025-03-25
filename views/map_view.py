import streamlit as st
from utils.map_logic import create_map

# Fonction qui affiche la page de carte dans l'application Streamlit
# Entrée: Aucune - utilise la session_state de Streamlit pour accéder aux données
# Sortie: Affiche la carte et les informations des zones et points de livraison
def show_map_page():
    # Définit le titre de la page
    st.title("Map View")
    
    # Crée une carte interactive avec les points de livraison et zones
    # La fonction create_map() renvoie la carte et les descriptions associées
    m, descriptions = create_map()
    
    # Affiche la carte avec une hauteur fixe de 500 pixels
    m.to_streamlit(height=500)
    
    # Crée un titre centré pour la section de description
    st.markdown("<h1 style='text-align: center;'>Déscription des Points de livraison et des Zones</h1>", unsafe_allow_html=True)
    
    # Section pour afficher les informations des zones
    st.header("📍 Zones")

    # Parcourt toutes les zones stockées dans la session_state
    # Pour chaque zone, crée un élément expansible qui affiche sa description
    for zone in st.session_state.zones:
        with st.expander(f"Zone : {zone.nom}"):
            # Affiche la description de la zone quand l'élément est étendu
            st.write(zone.description)
    
    # Section pour afficher les informations des points de livraison
    st.header("🚚 Points de livraison")
    
    # Parcourt tous les entrepôts/points de livraison stockés dans la session_state
    # Pour chaque point, crée un élément expansible qui affiche sa description
    for point in st.session_state.warehouses_info:
        with st.expander(f"Entrepôt : {point.nom}"):
            # Affiche la description du point de livraison quand l'élément est étendu
            st.write(point.description)