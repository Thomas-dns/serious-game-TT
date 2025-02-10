# pages/simulation_view.py

import streamlit as st
from utils.game_logic import Simulation
import pandas as pd

def simulation_view():
    st.title("🔄 Simulation des livraisons")

    if st.button("Lancer la simulation avec pas de temps"):
        sim = Simulation()
        events = sim.run_simulation_with_time_step()
        st.session_state.simulation_events = events
        st.success("Simulation terminée avec pas de temps !")
        sim.display_simulation()

        # Afficher les rapports par trajet
        st.subheader("Rapport d'impacte par véhicule")
        
        for v in st.session_state.fleet:
            c = sim.vehicle_states[v.nom]["travel_cost"]
            e = sim.vehicle_states[v.nom]["travel_emission"]
            d = sim.vehicle_states[v.nom]["distance"]
            st.subheader(f"Impacte cumulé de {v.nom}")
            st.write(f"\t Cout : {c:.1f} | Emission : {e:.1f} | Distance : {d:.1f}")

        st.subheader("Rapport d'état de livraison")

        delivery_status = sim.check_deliveries()
        # Création du DataFrame
        data = {
            "Commande": list(delivery_status.keys()),
            "État": list(delivery_status.values())
        }
        df = pd.DataFrame(data)

        # Fonction pour appliquer les couleurs
        def color_status(status):
            if status == "on_time":
                return "background-color: green; color: white;"
            elif status == "late":
                return "background-color: orange; color: white;"
            else:
                return "background-color: red; color: white;"

        # Interface Streamlit
        st.title("État des Livraisons")

        # Appliquer le style aux cellules
        styled_df = df.style.applymap(lambda v: color_status(v) if v in ["on_time", "late", "not_delivered"] else "")

        # Afficher le tableau
        st.dataframe(styled_df)
        

    else:
        st.write("Cliquez sur le bouton pour lancer la simulation.")


if __name__ == "__main__":
    simulation_view()
