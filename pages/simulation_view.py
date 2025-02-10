# pages/simulation_view.py

import streamlit as st
from utils.game_logic import Simulation

def simulation_view():
    st.title("🔄 Simulation des livraisons")

    if st.button("Lancer la simulation avec pas de temps"):
        sim = Simulation()
        events = sim.run_simulation_with_time_step()
        st.session_state.simulation_events = events
        st.success("Simulation terminée avec pas de temps !")
        sim.display_simulation()

        # Afficher les rapports par trajet
        st.subheader("Rapports par Trajet avec les route en sortie du planning")
        for route in st.session_state.routes:
            st.write(route.transport)
            st.write(route.calculate_impact(st.session_state.fleet))
            st.write("\n")
        
        for v in st.session_state.fleet:
            c = sim.vehicle_states[v.nom]["travel_cost"]
            e = sim.vehicle_states[v.nom]["travel_emission"]
            st.subheader(f"Impacte cumulé de {v.nom}")
            st.write(f"\t Cout : {c} | Emission : {e}")

    else:
        st.write("Cliquez sur le bouton pour lancer la simulation.")


if __name__ == "__main__":
    simulation_view()
