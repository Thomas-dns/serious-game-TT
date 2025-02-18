import streamlit as st
from utils.tools import load_json_data
import pandas as pd

def show_orders_page():
    st.title("📦 Orders du round")

    current_round = st.session_state.round

    order_data = load_json_data(f"ressources/orders/order_{current_round}.json")["ORDERS"]

    for index, order in enumerate(order_data):
        with st.expander(f"ID: {order['id']}"):
            st.write(f"**Start:** {order['start']}")
            st.write(f"**End:** {order['end']}")
            st.write(f"**Delivery Time:** {order['delivery_time']}")
            st.write("**Content:**")
            st.write(f"- **Volume:** {order['content']['volume_m3']} m³")
            st.write(f"- **Weight:** {order['content']['poids_kg']} kg")
            st.write(f"- **Description:** {order['content']['description']}")

