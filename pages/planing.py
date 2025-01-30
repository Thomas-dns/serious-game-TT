import streamlit as st
from dataclasses import dataclass
from typing import Dict, List
import pandas as pd
from utils.travel import distance_by_zones_exclusive
from ressources.vehicules import Vehicle

def init_session_state():
    if 'Orders_copy' not in st.session_state: # On travail sur une copie des Orders
        st.session_state.Orders_copy = st.session_state.Orders.copy()
    if 'content_copy' not in st.session_state:
        st.session_state.content_copy = st.session_state.Orders_copy.get_orders()
    if 'steps' not in st.session_state:
        st.session_state.steps = []
    if 'routes' not in st.session_state:
        st.session_state.routes = []
    if 'current_step' not in st.session_state:
        st.session_state.current_step = initialize_current_step(0)

def initialize_current_step(step_index):
    current_step = {
                "entrepot": None,
                "operations": [],
                "final_load": None
            }
    return current_step

def validate_step():
    # Vérifications initiales des opérations
    if not st.session_state.current_step['operations']:
        st.error("Aucune opération n'a été ajoutée.")
        return False
    
    for op in st.session_state.current_step['operations']:
        if not op['type'] or not op['produit'] or op['quantite'] <= 0:
            st.error("Opérations incomplètes détectées.")
            return False

    # Création de copies temporaires pour la simulation
    temp_orders = st.session_state.Orders_copy.copy()
    temp_content = st.session_state.content_copy.copy()
    vehicule = st.session_state.vehicule
    total_poids = 0 
    total_volume = 0

    # Simulation de toutes les opérations
    for op in st.session_state.current_step['operations']:
        product_id = op['produit']
        qty = op['quantite'] #proportion de la commande totale
        warehouse = st.session_state.current_step['entrepot']
        produit = temp_orders.orders[product_id]

        # Vérification stock selon le type d'opération
        if op['type'] == 'Charger':
            stock_dispo = temp_orders.warehouses_content(warehouse).get(product_id, 0)
            if stock_dispo < qty:
                st.error(f"Stock {product_id} insuffisant ({stock_dispo} restant)")
                return False
            
            # Mise à jour temporaire
            temp_orders.update_warehouse_content(warehouse, product_id, -qty)
            temp_content[product_id] += qty

        elif op['type'] == 'Décharger':
            if temp_content.get(product_id, 0) < qty:
                st.error(f"{product_id} manquant dans le véhicule")
                return False
            
            temp_orders.update_warehouse_content(warehouse, product_id, qty)
            temp_content[product_id] -= qty

        # Calcul des totaux
        total_poids += temp_content[product_id] * produit.content['poids_kg']
        total_volume += temp_content[product_id] * produit.content['volume_m3']

    # Vérification capacité véhicule
    if total_poids > vehicule.charge_max_emport_kg:
        st.error(f"Surcharge : {total_poids:.2f}kg > {vehicule.charge_max_emport_kg}kg")
        return False
    
    if total_volume > vehicule.volume_max_emport_m3:
        st.error(f"Volume dépassé : {total_volume:.2f}m³ > {vehicule.volume_max_emport_m3}m³")
        return False

    # Si tout est OK, appliquer les VRAIES modifications
    st.session_state.Orders_copy = temp_orders
    st.session_state.content_copy = temp_content

    # On ajoute la charge dans le camion a la fin de l'étape
    current_step_with_load = st.session_state.current_step.copy()
    current_step_with_load['final_load'] = {
        'content': temp_content.copy(),
        'total_poids': total_poids,
        'total_volume': total_volume
    }
    
    # Validation finale
    st.session_state.steps.append(current_step_with_load)
    st.session_state.current_step = initialize_current_step(len(st.session_state.steps))
    return True

def display_steps():
    if st.session_state.steps:
        st.write("Étapes déja validées:")
        
        # Préparer les données pour le tableau
        table_data = []
        
        for step in st.session_state.steps:
            # Initialiser les listes pour les opérations de chargement et déchargement
            chargements = []
            dechargements = []
            
            # Trier les opérations par type
            for operation in step['operations']:
                if operation['type'] == 'Charger':
                    chargements.append(f"{operation['produit']}: {operation['quantite']}")
                elif operation['type'] == 'Décharger':
                    dechargements.append(f"{operation['produit']}: {operation['quantite']}")
            
            # Ajouter une ligne au tableau
            table_data.append({
                "Entrepôt": step['entrepot'],
                "Charger": "\n".join(chargements) if chargements else "-",
                "Décharger": "\n".join(dechargements) if dechargements else "-"
            })
        
        # Créer et afficher le DataFrame
        df = pd.DataFrame(table_data)
        st.table(df)

def display_routes():
    if st.session_state.routes:
        st.subheader("Trajets enregistrés")
        
        calculate_score()

        for i, route in enumerate(st.session_state.routes):
            # Créer un expander pour chaque trajet
            with st.expander(f"Trajet {i+1} - {route['transport']}", expanded=True):
                # Préparer les données pour le tableau de ce trajet
                table_data = []

                st.write(route['impacte'])
                
                for step in route['etapes']:
                    # Initialiser les listes pour les opérations de chargement et déchargement
                    chargements = []
                    dechargements = []
                    
                    # Trier les opérations par type
                    for operation in step['operations']:
                        if operation['type'] == 'Charger':
                            chargements.append(f"{operation['produit']}: {operation['quantite']}")
                        elif operation['type'] == 'Décharger':
                            dechargements.append(f"{operation['produit']}: {operation['quantite']}")
                    
                    # Ajouter une ligne au tableau
                    table_data.append({
                        "Entrepôt": step['entrepot'],
                        "Charger": "\n".join(chargements) if chargements else "-",
                        "Décharger": "\n".join(dechargements) if dechargements else "-"
                    })
                
                # Créer et afficher le DataFrame pour ce trajet
                df = pd.DataFrame(table_data)
                
                st.table(df)
                
def display_commands():
    orders = st.session_state.Orders_copy.orders  # Accès direct au dictionnaire des Order
    data = st.session_state.Orders_copy.get_warehouse_orders()
    data_bis = st.session_state.content_copy

    # Création des listes pour le DataFrame
    commandes = sorted(orders.keys())  # Liste des IDs de commandes triés
    entrepots = list(data.keys()) + ['Véhicule']

    # Création du DataFrame
    df = pd.DataFrame(index=commandes + ['Poids/volume'], columns=entrepots)

    # Dictionnaires pour les totaux
    poids_totals = {e: 0.0 for e in entrepots}
    volume_totals = {e: 0.0 for e in entrepots}

    # Remplissage des données pour chaque entrepôt
    for entrepot in data:
        for cmd_id, proportion in data[entrepot]:
            order = orders[cmd_id]  # Récupération de l'objet Order
            
            # Remplissage de la proportion
            df.at[cmd_id, entrepot] = proportion
            
            # Calcul des totaux
            poids_totals[entrepot] += order.content['poids_kg'] * proportion
            volume_totals[entrepot] += order.content['volume_m3'] * proportion

    # Remplissage pour le véhicule
    for cmd_id, proportion in data_bis.items():
        if proportion > 0:
            order = orders[cmd_id]
            df.at[cmd_id, 'Véhicule'] = proportion
            poids_totals['Véhicule'] += order.content['poids_kg'] * proportion
            volume_totals['Véhicule'] += order.content['volume_m3'] * proportion

    # Ajout de la ligne des totaux
    for entrepot in entrepots:
        df.at['Poids/volume', entrepot] = (
            f"{poids_totals[entrepot]:.2f} kg\n"
            f"{volume_totals[entrepot]:.2f} m³"
        )

    # Style du tableau
    def row_style(row):
        styles = []
        for cell in row:
            if row.name == 'Poids/volume':
                styles.append('background-color: #FFB6C1; font-weight: bold;')
            else:
                styles.append('')
        return styles

    styled_df = df.fillna(0).style.apply(row_style, axis=1)
    styled_df = styled_df.set_properties(**{'white-space': 'pre-wrap'})

    st.write("Tableau de répartition des commandes :")
    st.dataframe(styled_df)

def calculate_score():
    """
    Renvois le score pour les différents trajet : Consomation + Emission / Ajouter les malus critair voire comment on prend en compte
    celui ci
    """
    for travel in st.session_state.routes:
        vehicule = [v for v in st.session_state.fleet if v.nom == travel["transport"]][0]

        cost, emission, total_d = 0, 0, 0

        for i, step in enumerate(travel["etapes"]):
            warehouse = step["entrepot"]
            load = step["final_load"]['total_poids'] # Poid dans le camion en Kg
            
            # Si ce n'est pas le dernier entrepôt, on peut calculer la distance jusqu'au prochain
            if i < len(travel["etapes"]) - 1:
                next_warehouse = travel["etapes"][i + 1]["entrepot"]
                # On doit récuperer les coord des entrepots.
                distances = distance_by_zones_exclusive(warehouse, next_warehouse)

                for zone, distance in distances.items():
                    cost += vehicule.travel_cost_km(load) * distance / 1000
                    emission += vehicule.travel_emission_km(load) * distance / 1000
                    total_d += distance
            
        travel["impacte"] = f"Cout : {cost:.1f} € | Emission : {emission:.1f} | D : {total_d:.1f} m"


def reset_session_state():
    keys_to_reset = ['Orders_copy', 'steps', 'routes', 'gestionnaire_stock', 'current_step','content_copy']
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    init_session_state()
    st.rerun()

def main():
    init_session_state()

    st.title("Planning de Livraison Supply Chain")
    
    if st.button("🔁 Reset Total"):
        reset_session_state()
        st.success("Session réinitialisée!")
    
    transports = [v.nom for v in st.session_state.fleet]
    warehouses = st.session_state.warehouses
    
    col1, col2 = st.columns(2)

    with col1:
        transport = st.selectbox("Transport", options=transports, index=1, key="transport_select", placeholder="Sélectionnez un transport disponible")
        
    if transport:
        st.session_state.vehicule = [v for v in st.session_state.fleet if v.nom == transport][0]
        
        #st.write(st.session_state.content_copy)

        info = f"Poids max: {st.session_state.vehicule.charge_max_emport_kg} kg | Volume max: {st.session_state.vehicule.volume_max_emport_m3} m³"
    
        with col2:
            st.markdown(f"<div style='padding-top: 34px;'>{info}</div>", unsafe_allow_html=True)

        st.subheader("Où sont les commandes")
        display_commands()
        # Afficher les étapes déjà validées
        with st.container(key="saved_steps"):
            display_steps()
        
        # Ajouter une étape
        with st.container(key="current_steps"):
            st.subheader("Ajouter une étape")
            
            current_step = st.session_state.current_step

            current_step_entrepot = st.selectbox(
                "Entrepôt",
                ["Sélectionnez un entrepôt"] + warehouses,
                index=0,
                key="current_step_entrepot",
            )

            if current_step_entrepot != "Sélectionnez un entrepôt":
                st.session_state.current_step["entrepot"] = current_step_entrepot
                
                st.write("Opérations:")

                # On crée une liste temporaire pour stocker les opérations mises à jour
                updated_operations = []
                
                for i, op in enumerate(current_step.get("operations", [])):
                    cols = st.columns([2, 3, 2, 1])
                    
                    # On récupère les valeurs actuelles pour pré-remplir les champs
                    current_type = op.get("type", "")
                    current_produit = op.get("produit", "")
                    current_quantite = op.get("quantite", 0)
                    
                    # Type d'opération
                    op_type = cols[0].selectbox(
                        "Type",
                        ["Charger", "Décharger"],
                        key=f"type_{i}",
                        index=["Charger", "Décharger"].index(current_type) if current_type else None,
                        placeholder="Sélectionnez une opération"
                    )
                    
                    produit = None
                    quantite = None
                    
                    if op_type == "Charger":
                        produits_disponibles = st.session_state.Orders_copy.warehouses_content(current_step_entrepot)
                        produit = cols[1].selectbox(
                            "Produit", 
                            produits_disponibles, 
                            key=f"prod_{i}",
                            index=list(produits_disponibles.keys()).index(current_produit) if current_produit in produits_disponibles else None
                        )
                        if produit:
                            max_values = float(produits_disponibles[produit])
                            quantite = cols[2].slider(
                                "Quantité", 
                                min_value=0.0, 
                                max_value=max_values, 
                                value=current_quantite if current_type == "Charger" else 0.0,
                                step=0.05, 
                                key=f"qty_{i}"
                            )
                        
                    elif op_type == "Décharger":
                        produits = st.session_state.content_copy
                        produits_disponibles = [key for key, value in produits.items() if value > 0]
                        produit = cols[1].selectbox(
                            "Produit", 
                            produits_disponibles, 
                            key=f"prod_{i}",
                            index=produits_disponibles.index(current_produit) if current_produit in produits_disponibles else None
                        )
                        if produit:
                            max_values = float(produits[produit])
                            quantite = cols[2].slider(
                                "Quantité", 
                                min_value=0.0, 
                                max_value=max_values, 
                                value=current_quantite if current_type == "Décharger" else 0.0,
                                step=0.01, 
                                key=f"qty_{i}"
                            )

                    # Bouton de suppression        
                    if cols[3].button("🗑️", key=f"delete_{i}"):
                        st.session_state.current_step["operations"].pop(i)
                        st.rerun()
                    else:
                        # On met à jour l'opération si elle a des valeurs, sinon on garde l'existante
                        if op_type and produit is not None and quantite is not None:
                            updated_operations.append({
                                "type": op_type,
                                "produit": produit,
                                "quantite": quantite
                            })
                        else:
                            # On préserve l'opération incomplète
                            updated_operations.append(op)
                
                # À la fin de la boucle, on met à jour les opérations avec notre liste mise à jour
                st.session_state.current_step["operations"] = updated_operations

                add_op = st.button("Ajouter une Opération")
                if add_op:
                    current_step["operations"].append({
                        "type": "",
                        "produit": "",
                        "quantite": 0
                    })
                    st.rerun()

        if st.button("➕ Valider l'étape"):
            if validate_step():
                display_commands()  # Mettre à jour l'affichage des commandes
                st.rerun()

        if st.button("Valider trajet"):
            if st.session_state.steps:
                st.session_state.routes.append({
                    "transport": transport,
                    "etapes": st.session_state.steps.copy()
                })
                st.session_state.steps = []
                st.success("Trajet ajouté!")
                initialize_current_step(len(st.session_state.steps))
            else:
                st.warning("Veuillez ajouter au moins une étape au trajet.")

    display_routes()
    #st.write(st.session_state.routes)
    #st.write(st.session_state.steps)

if __name__ == "__main__":
    main()