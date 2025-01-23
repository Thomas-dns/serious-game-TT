import streamlit as st
import pandas as pd
from utils.tools import load_json_data

def planning_view():
    st.title("Planning de livraison")

    # --- 1) Charger les données ---
    current_round = st.session_state.round
    orders_data = load_json_data(f"orders/order_{current_round}.json")
    vehicles_data = load_json_data("ressources/vehicules.json")
    map_data = load_json_data(f"maps/map_{current_round}.json")

    if not orders_data or not vehicles_data or not map_data:
        st.warning("Impossible de charger toutes les données nécessaires.")
        return

    orders_list = orders_data["ORDERS"]
    vehicles_list = vehicles_data["Vehicules"]
    delivery_points = map_data["DELIVERY_POINTS"]

    # Pour simplifier, on extrait les noms de tous les entrepôts (hors Start)
    warehouse_names = [
        dp["nom"] for dp in delivery_points
        if dp["type"] == "warehouse" and dp["nom"] != "Start"
    ]

    # Initialiser un conteneur de planning dans la session si pas déjà fait
    if "delivery_plan" not in st.session_state:
        st.session_state["delivery_plan"] = {}  # { order_id : { vehicle, route } }

    # --- 2) Formulaire de configuration d'un plan ---
    st.subheader("Configurer un plan de livraison")

    # Sélection de la commande
    order_ids = [order["id"] for order in orders_list]
    selected_order_id = st.selectbox("Sélectionnez une commande", order_ids)

    # Récupération des détails de la commande choisie
    selected_order = next((o for o in orders_list if o["id"] == selected_order_id), None)
    if selected_order:
        st.write("**Détails de la commande :**")
        st.json(selected_order)

    # Sélection du véhicule
    vehicle_names = [v["nom"] for v in vehicles_list]
    selected_vehicle_name = st.selectbox("Sélectionnez un véhicule", vehicle_names)

    # Proposition d'entrepôts intermédiaires (multi-sélection)
    # La commande a un champ "end" qui indique l'entrepôt de destination
    # Si vous avez d'autres points de type "delivery", ajustez selon vos besoins
    # Exclure le point de départ 'Start' et la destination finale
    end_point = selected_order["end"]
    possible_intermediates = [w for w in warehouse_names if w != end_point]
    selected_stops = st.multiselect("Sélectionnez les entrepôts intermédiaires (facultatifs)", possible_intermediates)

    # Le trajet final : Start -> [stops...] -> end
    route = ["Start"] + selected_stops + [end_point]

    # --- 3) Bouton de validation => sauvegarde dans session_state ---
    if st.button("Planifier cette livraison"):
        st.session_state["delivery_plan"][selected_order_id] = {
            "vehicle": selected_vehicle_name,
            "route": route
        }
        st.success(f"Plan enregistré pour la commande {selected_order_id} !")

    # --- 4) Afficher le plan global pour toutes les commandes ---

    st.subheader("Planning de livraison courant")
    if st.session_state["delivery_plan"]:
        for order_id, plan_info in st.session_state["delivery_plan"].items():
            st.markdown(f"### Commande : {order_id}")
            st.write(f"- Véhicule : **{plan_info['vehicle']}**")
            st.write(f"- Trajet : {' → '.join(plan_info['route'])}")
    else:
        st.info("Aucun plan enregistré pour le moment.")

if __name__ == "__main__":
    planning_view()
