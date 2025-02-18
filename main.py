import streamlit as st
import pandas as pd

from ressources.vehicules import Vehicle
from ressources.orders.orders import Order, Orders
from utils.tools import load_json_data
from utils.map_logic import Zone, Warehouse

from views.map_view import show_map_page
from views.orders_view import show_orders_page
from views.planning import show_planning_page
from views.transport_view import transport_view
from views.simulation_view import show_simulation_page

def init_session_state():
    # Initialisation de la page courante
    if 'page' not in st.session_state:
        st.session_state.page = 'main'
    # On initialise le round a 1
    if 'round' not in st.session_state:
        st.session_state.round = 1

def init_session_state_round(round):
    st.session_state.fleet = []
    st.session_state.orders = []
    
    # Charger les données de configuration, carte et commandes
    data = load_json_data(f"ressources/config/config_{round}.json")
    map_data = load_json_data(f"ressources/maps/map_{round}.json")
    orders = load_json_data(f"ressources/orders/order_{round}.json")
    
    # Stocker la carte complète
    st.session_state.map_data = map_data
    # Créer des objets Zone à partir de la clé "ZONES"
    zones_raw = map_data.get("ZONES", [])
    st.session_state.zones = [
        Zone(
            nom=z["nom"],
            coordonnees=z["coordonnees"],
            style=z.get("style", {}),
            description=z.get("description", ""),
            parameters=z.get("parameters", {})
        )
        for z in zones_raw
    ]
    
    # Créer des objets Warehouse à partir des points de livraison de type "warehouse"
    delivery_points = map_data.get("DELIVERY_POINTS", [])
    st.session_state.warehouses_info = [
        Warehouse(
            nom=p["nom"],
            coordonnees=p["coordonnees"],
            type_point=p["type"],
            description=p.get("description", "")
        )
        for p in delivery_points if (p.get("type") == "warehouse" or p.get("type") == "delivery")
    ]
    
    # Conserver la liste des noms d'entrepôts pour la gestion des commandes
    st.session_state.warehouse_names = [w.nom for w in st.session_state.warehouses_info]
    
    # Initialiser la flotte
    for vehicule in data["fleet"]:
        st.session_state.fleet.append(Vehicle(**vehicule))
    
    # Instancier Orders en lui passant la liste des noms d'entrepôts
    st.session_state.Orders = Orders(f"ressources/orders/order_{round}.json", st.session_state.warehouse_names)

def show_main_page():
    st.title("Serious Game - Supply Chain")
    st.write(f"Round actuel : {st.session_state.round}")
    
    transport_view()

    show_orders_page()
    # Simple bouton de reset
    if st.button("Reset Round"):
        st.session_state.round = 1
        st.rerun()

    if st.button("Augmenter le round"):
        st.session_state.round += 1
        st.rerun()

def show_navigation():
    col1, col2, col3, col4= st.columns(4)
    
    with col1:
        if st.button("🏠 Main", use_container_width=True, 
                    type="primary" if st.session_state.page == 'main' else "secondary"):
            st.session_state.page = 'main'
            st.rerun()
            
    with col2:
        if st.button("🗺️ Map", use_container_width=True,
                    type="primary" if st.session_state.page == 'map' else "secondary"):
            st.session_state.page = 'map'
            st.rerun()
            
    with col3:
        if st.button("📅 Planning", use_container_width=True,
                    type="primary" if st.session_state.page == 'planning' else "secondary"):
            st.session_state.page = 'planning'
            st.rerun()
            
    with col4:
        if st.button("🔄 Simulation", use_container_width=True,
                    type="primary" if st.session_state.page == 'simulation' else "secondary"):
            st.session_state.page = 'simulation'
            st.rerun()

def main():
    # Configuration de la page
    st.set_page_config(
        page_title="Supply Chain Game",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Cacher la sidebar
    hide_streamlit_style = """
        <style>
        #MainMenu {visibility: hidden;}
        section[data-testid="stSidebar"] {display: none;}
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    # Initialiser toutes les variables de session
    init_session_state()
    init_session_state_round(st.session_state.round)
    
    # Afficher la navigation
    show_navigation()
    
    # Gérer l'affichage des pages
    if st.session_state.page == 'main':
        show_main_page()
    elif st.session_state.page == 'map':
        show_map_page()
    elif st.session_state.page == 'orders':
        show_orders_page()
    elif st.session_state.page == 'planning':
        show_planning_page()
    elif st.session_state.page == 'simulation':
        show_simulation_page()

if __name__ == "__main__":
    main()