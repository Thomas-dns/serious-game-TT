# pages/planing.py

##############################################
# Imports
##############################################

# Import des librairies
import streamlit as st
import pandas as pd
import datetime
# Import des classes
from utils.travel import distance_by_zones_exclusive
from ressources.vehicules import Vehicle
from utils.game_logic import Operation, Step, Route

##############################################
# Fonctions de gestion de la session
##############################################

def init_session_state():
    # Initialisation de copies pour travailler sur les commandes et leur contenu
    if 'Orders_copy' not in st.session_state:
        st.session_state.Orders_copy = st.session_state.Orders.copy()
    if 'content_copy' not in st.session_state:
        st.session_state.content_copy = st.session_state.Orders_copy.get_orders()
    if 'steps' not in st.session_state:
        st.session_state.steps = []  # liste des étapes validées (objets Step)
    if 'routes' not in st.session_state:
        st.session_state.routes = []  # liste des trajets (objets Route)
    if 'current_step' not in st.session_state:
        st.session_state.current_step = Step()


def reset_session_state():
    keys_to_reset = ['Orders_copy', 'steps', 'routes', 'gestionnaire_stock', 'current_step','content_copy']
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    init_session_state()
    st.rerun()

##############################################
# Fonctions d'affichage
##############################################

def display_steps():
    if st.session_state.steps:
        st.write("Étapes déjà validées :")
        table_data = []
        for step in st.session_state.steps:
            chargements = []
            dechargements = []
            for op in step.operations:
                if op.type == "Charger":
                    chargements.append(f"{op.produit}: {op.quantite}")
                elif op.type == "Décharger":
                    dechargements.append(f"{op.produit}: {op.quantite}")
            table_data.append({
                "Entrepôt": step.entrepot,
                "Charger": "\n".join(chargements) if chargements else "-",
                "Décharger": "\n".join(dechargements) if dechargements else "-"
            })
        df = pd.DataFrame(table_data)
        st.table(df)

def display_routes():
    if st.session_state.routes:
        st.subheader("Trajets enregistrés")
        for i, route in enumerate(st.session_state.routes):
            route.calculate_impact(st.session_state.fleet)
            with st.expander(f"Trajet {i+1} - {route.transport} - Depart : {route.departure_time}", expanded=True):
                st.write(route.impact)
                table_data = []
                for step in route.steps:
                    chargements = []
                    dechargements = []
                    for op in step.operations:
                        if op.type == "Charger":
                            chargements.append(f"{op.produit}: {op.quantite}")
                        elif op.type == "Décharger":
                            dechargements.append(f"{op.produit}: {op.quantite}")
                    table_data.append({
                        "Entrepôt": step.entrepot,
                        "Charger": "\n".join(chargements) if chargements else "-",
                        "Décharger": "\n".join(dechargements) if dechargements else "-"
                    })
                df = pd.DataFrame(table_data)
                st.table(df)

def display_commands():
    orders = st.session_state.Orders_copy.orders  # dictionnaire des Order
    data = st.session_state.Orders_copy.get_warehouse_orders()
    content_copy = st.session_state.content_copy

    commandes = sorted(orders.keys())
    entrepots = list(data.keys()) + ['Véhicule']

    df = pd.DataFrame(index=commandes + ['Poids/volume'], columns=entrepots)
    poids_totals = {e: 0.0 for e in entrepots}
    volume_totals = {e: 0.0 for e in entrepots}

    for entrepot in data:
        for cmd_id, proportion in data[entrepot]:
            order = orders[cmd_id]
            df.at[cmd_id, entrepot] = proportion
            poids_totals[entrepot] += order.content['poids_kg'] * proportion
            volume_totals[entrepot] += order.content['volume_m3'] * proportion

    for cmd_id, proportion in content_copy.items():
        if proportion > 0:
            order = orders[cmd_id]
            df.at[cmd_id, 'Véhicule'] = proportion
            poids_totals['Véhicule'] += order.content['poids_kg'] * proportion
            volume_totals['Véhicule'] += order.content['volume_m3'] * proportion

    for entrepot in entrepots:
        df.at['Poids/volume', entrepot] = (
            f"{poids_totals[entrepot]:.2f} kg\n"
            f"{volume_totals[entrepot]:.2f} m³"
        )

    def row_style(row):
        styles = []
        for _ in row:
            if row.name == 'Poids/volume':
                styles.append('background-color: #FFB6C1; font-weight: bold;')
            else:
                styles.append('')
        return styles

    styled_df = df.fillna(0).style.apply(row_style, axis=1)
    styled_df = styled_df.set_properties(**{'white-space': 'pre-wrap'})
    st.write("Tableau de répartition des commandes :")
    st.dataframe(styled_df)

##############################################
# Fonction principale (interface Streamlit)
##############################################

def main():
    st.set_page_config(page_title="Planning de Livraison Supply Chain", layout="wide")
    init_session_state()
    st.title("Planning de Livraison Supply Chain")
    
    if st.button("🔁 Reset Total"):
        reset_session_state()
        st.success("Session réinitialisée!")
    
    transports = [v.nom for v in st.session_state.fleet]
    warehouses = st.session_state.warehouse_names

    
    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        transport = st.selectbox("Transport", options=transports, index=1, key="transport_select",
                                   placeholder="Sélectionnez un transport disponible")
    with col2:
            departure_time = st.time_input("Heure de départ", key="departure_time", step=600, value=datetime.time(8, 45))
        
    if transport and departure_time:
        st.session_state.vehicule = next(v for v in st.session_state.fleet if v.nom == transport)
        info = f"Poids max: {st.session_state.vehicule.charge_max_emport_kg} kg | Volume max: {st.session_state.vehicule.volume_max_emport_m3} m³"
        with col3:
            st.markdown(f"<div style='padding-top: 34px;'>{info}</div>", unsafe_allow_html=True)

        st.subheader("Où sont les commandes")
        display_commands()
        
        # Affichage des étapes validées
        with st.container(key="saved_steps"):
            display_steps()
        
        # Ajout d'une nouvelle étape
        with st.container(key="current_steps"):
            st.subheader("Ajouter une étape")
            current_step: Step = st.session_state.current_step
            current_entrepot = st.selectbox("Entrepôt", ["Sélectionnez un entrepôt"] + warehouses,
                                            index=0, key="current_step_entrepot")
            if current_entrepot != "Sélectionnez un entrepôt":
                current_step.entrepot = current_entrepot
                st.write("Opérations :")
                updated_operations = []
                # Parcours des opérations existantes de l'étape
                for i, op in enumerate(current_step.operations):
                    cols = st.columns([2, 3, 2, 1])
                    current_type = op.type
                    current_produit = op.produit
                    current_quantite = op.quantite
                    op_type = cols[0].selectbox("Type", ["Charger", "Décharger"],
                                                key=f"type_{i}",
                                                index=["Charger", "Décharger"].index(current_type) if current_type in ["Charger", "Décharger"] else 0)
                    produit = None
                    quantite = None
                    if op_type == "Charger":
                        produits_disponibles = st.session_state.Orders_copy.warehouses_content(current_entrepot)
                        produit = cols[1].selectbox("Produit", list(produits_disponibles.keys()),
                                                    key=f"prod_{i}",
                                                    index=list(produits_disponibles.keys()).index(current_produit) if current_produit in produits_disponibles else 0)
                        if produit:
                            max_values = float(produits_disponibles[produit])
                            quantite = cols[2].slider("Quantité", min_value=0.0, max_value=max_values,
                                                       value=current_quantite if current_type=="Charger" else 0.0,
                                                       step=0.05, key=f"qty_{i}")
                    elif op_type == "Décharger":
                        produits_disponibles = [key for key, value in st.session_state.content_copy.items() if value > 0]
                        produit = cols[1].selectbox("Produit", produits_disponibles,
                                                    key=f"prod_{i}",
                                                    index=produits_disponibles.index(current_produit) if current_produit in produits_disponibles else 0)
                        if produit:
                            max_values = float(st.session_state.content_copy[produit])
                            quantite = cols[2].slider("Quantité", min_value=0.0, max_value=max_values,
                                                       value=current_quantite if current_type=="Décharger" else 0.0,
                                                       step=0.01, key=f"qty_{i}")
                    with cols[3]:
                        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                        if st.button("🗑️", key=f"delete_{i}"):
                            current_step.operations.pop(i)
                            st.rerun()
                        else:
                            if op_type and produit is not None and quantite is not None:
                                updated_operations.append(Operation(op_type, produit, quantite))
                            else:
                                updated_operations.append(op)
                current_step.operations = updated_operations
                if st.button("Ajouter une Opération"):
                    current_step.operations.append(Operation("", "", 0))
                    st.rerun()
        
        # Validation de l'étape en cours
        if st.button("➕ Valider l'étape"):
            vehicule = st.session_state.vehicule
            valid, msg, updated_orders, updated_content = st.session_state.current_step.validate(
                vehicule,
                st.session_state.Orders_copy.copy(),
                st.session_state.content_copy.copy()
            )
            if valid:
                st.session_state.Orders_copy = updated_orders
                st.session_state.content_copy = updated_content
                st.session_state.steps.append(st.session_state.current_step)
                st.session_state.current_step = Step()  # réinitialiser l'étape en cours
                st.rerun()
            else:
                st.error(msg)
        
        # Validation finale du trajet (création d'un Route)
        if st.button("Valider trajet"):
            if st.session_state.steps:
                # Vérifier que le véhicule est vide en fin de trajet
                if any(quantity > 0 for quantity in st.session_state.content_copy.values()):
                    st.warning("Le véhicule doit être vide en fin de trajet pour valider le trajet.")
                else:
                    # Récupérer le point de départ (storage_point) du véhicule sélectionné
                    storage_point = st.session_state.vehicule.storage_point
                    # Vérifier que la première étape et la dernière étape correspondent bien au storage_point
                    if st.session_state.steps[0].entrepot != storage_point or st.session_state.steps[-1].entrepot != storage_point:
                        st.warning(f"Le trajet doit débuter et se terminer au point de départ du véhicule ({storage_point}).")
                    else:
                        new_route = Route(transport, departure_time)
                        for step in st.session_state.steps:
                            new_route.add_step(step)
                        st.session_state.routes.append(new_route)
                        # Trier la liste des routes par temps de départ croissant
                        st.session_state.routes.sort(key=lambda route: route.departure_time)
                        st.session_state.steps = []
                        st.success("Trajet ajouté!")
            else:
                st.warning("Veuillez ajouter au moins une étape au trajet.")

    display_routes()

    st.write(st.session_state.routes)


if __name__ == "__main__":
    main()
