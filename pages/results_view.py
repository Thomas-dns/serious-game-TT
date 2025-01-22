# pages/results_view.py

import streamlit as st
from utils.tools import load_json_data
from utils.travel import distance_by_zones_exclusive

def results_view():
    st.title("🌍 Résultats distances par zones (exclusives)")

    current_round = st.session_state.round
    path = f"maps/map_{current_round}.json"
    data = load_json_data(path)

    # Récupérer la liste des points de livraison
    delivery_points = data["DELIVERY_POINTS"]
    # Trouver "Start"
    start_point = next((p for p in delivery_points if p["nom"] == "Start"), None)
    if not start_point:
        st.warning("Pas de point nommé 'Start' dans DELIVERY_POINTS.")
        return

    start_coord = start_point["coordonnees"]  # ex. [48.2, 2.3] => [lat, lon]

    # Affichage
    st.subheader(f"Trajet depuis {start_point['nom']}")

    # Calcul pour chaque entrepôt
    for point in delivery_points:
        if point["nom"] == "Start":
            continue
        end_coord = point["coordonnees"]
        dist_dict = distance_by_zones_exclusive(data, start_coord, end_coord)
        
        st.write(dist_dict)
        st.write(f"**Start → {point['nom']}**")
        total_dist_covered = 0.0
        for zone_name, dist_m in dist_dict.items():
            st.write(f" - Zone '{zone_name}': {dist_m:.2f} m")

if __name__ == "__main__":
    results_view()
