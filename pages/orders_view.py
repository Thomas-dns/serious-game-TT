import streamlit as st
from utils.tools import load_json_data
import pandas as pd

def orders_view():
    st.title("📦 Order list")
    
    current_round = st.session_state.round

    order_data = load_json_data(f"ressources/orders/order_{current_round}.json")["ORDERS"]

    df = pd.DataFrame(order_data)

    st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    orders_view()