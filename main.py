import streamlit as st
import pandas as pd

def init_session_state():
    # Variables simples
    if 'round' not in st.session_state:
        st.session_state.round = 1

def main():
    st.set_page_config(page_title="Serious Game - Supply Chain", layout="wide")
    
    # Initialiser toutes les variables de session
    init_session_state()
    
    st.title("Serious Game - Supply Chain")

    # Simple bouton de reset
    if st.button("Reset Round"):
        st.session_state.round = 1
        st.rerun()

    # Afficher le round actuel
    st.write(f"Round actuel : {st.session_state.round}")


if __name__ == "__main__":
    main()