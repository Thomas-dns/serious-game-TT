import streamlit as st
import pandas as pd

from ressources.vehicules import Vehicle
from ressources.orders.orders import Order, Orders

from utils.tools import load_json_data
def init_session_state():
    # On initialise le round a 1
    if 'round' not in st.session_state:
        st.session_state.round = 1

def init_session_state_round(round):
    
    st.session_state.fleet = []
    st.session_state.orders = []
    st.session_state.Orders = Order
    # On initialise les vehicules
    data = load_json_data(f"ressources/config/config_{round}.json")
    map = load_json_data(f"ressources/maps/map_{round}.json")
    orders = load_json_data(f"ressources/orders/order_{round}.json")

    st.session_state.warehouses = []
    for point in map["DELIVERY_POINTS"]:
        st.session_state.warehouses.append(point["nom"])

    for vehicule in data["fleet"]:
        st.session_state.fleet.append(Vehicle(**vehicule))
    
    st.session_state.Orders = Orders(f"ressources/orders/order_{round}.json", st.session_state.warehouses)


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


if __name__ == "__main__":
    main()