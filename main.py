import streamlit as st
import pandas as pd

from ressources.vehicules import Vehicle
from ressources.orders.orders import Order, Orders

from utils.tools import load_json_data
def init_session_state():
    # On initialise le round a 1
    if 'round' not in st.session_state:
        st.session_state.round = 1

from utils.map_logic import Zone, Warehouse

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


def main():
    st.set_page_config(page_title="Serious Game - Supply Chain", layout="wide")
    
    # Initialiser toutes les variables de session
    init_session_state()
    init_session_state_round(st.session_state.round)
    st.title("Serious Game - Supply Chain")

    st.write(f"Round actuel : {st.session_state.round}")
    
    a, b = [], []
    for vehicule in st.session_state.fleet:
            a.append(vehicule.nom)
    st.write(f"vehicules : {a}")
    
    st.write(f"orders : {st.session_state.Orders.orders}")
    st.write(f"{st.session_state.Orders.get_warehouse_orders()}")
    # Simple bouton de reset
    if st.button("Reset Round"):
        st.session_state.round = 1
        st.rerun()

    # Afficher le round actuel
    st.write(f"Round actuel : {st.session_state.round}")

    st.write(st.session_state.warehouses_info)
    st.write(st.session_state.zones)


if __name__ == "__main__":
    main()