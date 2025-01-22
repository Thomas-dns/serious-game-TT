import streamlit as st
from utils.tools import load_json_data
import pandas as pd

def transport_view():
    st.title("🚗 Vehicules List")
    
    vehicules_data = load_json_data("ressources/vehicules.json")["Vehicules"]

    df = pd.DataFrame(vehicules_data)

    st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    transport_view()