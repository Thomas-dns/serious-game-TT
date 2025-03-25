# pages/planing.py
# Ce module gère l'interface de planification des trajets de livraison dans l'application Supply Chain
# Il permet de définir le véhicule, les étapes de chargement/déchargement et les routes complètes

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
    """
    Initialise les variables de session nécessaires pour la planification
    Cette fonction garantit que toutes les variables d'état sont correctement configurées
    """
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
    """
    Réinitialise toutes les variables de session liées à la planification
    Entrée: Aucune
    Sortie: Aucune, mais redémarre la page via st.rerun()
    """
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
    """
    Affiche les étapes déjà validées sous forme de tableau
    Entrée: Utilise st.session_state.steps
    Sortie: Affiche un tableau streamlit des étapes validées
    """
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
    """
    Affiche les trajets enregistrés avec leurs étapes
    Entrée: Utilise st.session_state.routes
    Sortie: Affiche des expandeurs streamlit contenant les détails de chaque trajet
    """
    if st.session_state.routes:
        st.subheader("Trajets enregistrés")
        for i, route in enumerate(st.session_state.routes):
            with st.expander(f"Trajet {i+1} - {route.transport} - Depart : {route.departure_time}", expanded=True):
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

def display_warehouse_status():
    """
    Affiche l'état des stocks dans les entrepôts
    Entrée: Utilise st.session_state.Orders_copy
    Sortie: Affiche un tableau stylisé des stocks par entrepôt
    """
    orders = st.session_state.Orders_copy.orders
    data = st.session_state.Orders_copy.get_warehouse_orders()
    
    commandes = sorted(orders.keys())
    entrepots = list(data.keys())
    
    # Création d'un DataFrame avec les commandes en lignes et les entrepôts en colonnes
    df = pd.DataFrame(index=commandes + ['Poids/volume'], columns=entrepots)
    poids_totals = {e: 0.0 for e in entrepots}
    volume_totals = {e: 0.0 for e in entrepots}
    
    # Remplissage du DataFrame avec les proportions de commandes par entrepôt
    for entrepot in data:
        for cmd_id, proportion in data[entrepot]:
            order = orders[cmd_id]
            df.at[cmd_id, entrepot] = proportion
            poids_totals[entrepot] += order.content['poids_kg'] * proportion
            volume_totals[entrepot] += order.content['volume_m3'] * proportion
    
    # Ajout d'une ligne de totaux pour le poids et le volume
    for entrepot in entrepots:
        df.at['Poids/volume', entrepot] = (
            f"{poids_totals[entrepot]:.2f} kg\n"
            f"{volume_totals[entrepot]:.2f} m³"
        )
    
    # Fonction pour appliquer un style à chaque ligne
    def row_style(row):
        styles = []
        for _ in row:
            if row.name == 'Poids/volume':
                styles.append('background-color: #E3F2FD; font-weight: bold;')
            else:
                styles.append('')
        return styles
    
    # Application du style et affichage du dataframe
    styled_df = df.fillna(0).style.apply(row_style, axis=1)
    styled_df = styled_df.set_properties(**{'white-space': 'pre-wrap'})
    
    with st.expander("📦 État des stocks dans les entrepôts", expanded=True):
        st.dataframe(styled_df, use_container_width=True)

def display_vehicle_status():
    """
    Affiche l'état du chargement du véhicule courant
    Entrée: Utilise st.session_state.content_copy, st.session_state.vehicule
    Sortie: Affiche des barres de progression et un tableau du chargement
    """
    orders = st.session_state.Orders_copy.orders
    content_copy = st.session_state.content_copy
    vehicule = st.session_state.vehicule
    
    # Calcul des totaux de poids et volume dans le véhicule
    total_poids = 0.0
    total_volume = 0.0
    
    # Création du DataFrame pour afficher le contenu
    df = pd.DataFrame(index=sorted(orders.keys()) + ['Poids/volume'], columns=['Véhicule'])
    
    # Remplissage du DataFrame avec les proportions de commandes dans le véhicule
    for cmd_id, proportion in content_copy.items():
        if proportion > 0:
            order = orders[cmd_id]
            df.at[cmd_id, 'Véhicule'] = proportion
            total_poids += order.content['poids_kg'] * proportion
            total_volume += order.content['volume_m3'] * proportion
    
    # Ajout de la ligne de totaux
    df.at['Poids/volume', 'Véhicule'] = (
        f"{total_poids:.2f} kg\n"
        f"{total_volume:.2f} m³"
    )
    
    # Fonction pour appliquer un style à chaque ligne
    def row_style(row):
        styles = []
        for _ in row:
            if row.name == 'Poids/volume':
                styles.append('background-color: #E3F2FD; font-weight: bold;')
            else:
                styles.append('')
        return styles
    
    # Application du style et préparation de l'affichage
    styled_df = df.fillna(0).style.apply(row_style, axis=1)
    styled_df = styled_df.set_properties(**{'white-space': 'pre-wrap'})
    
    with st.expander("🚛 État du chargement du véhicule", expanded=True):
        # Barres de progression pour visualiser les pourcentages d'utilisation
        col1, col2 = st.columns(2)
        with col1:
            poids_percent = (total_poids / vehicule.charge_max_emport_kg) * 100
            st.progress(min(poids_percent / 100, 1.0), text=f"Poids: {poids_percent:.1f}%")
        with col2:
            volume_percent = (total_volume / vehicule.volume_max_emport_m3) * 100
            st.progress(min(volume_percent / 100, 1.0), text=f"Volume: {volume_percent:.1f}%")
        
        # Tableau des commandes chargées
        st.dataframe(styled_df, use_container_width=True)

def display_commands():
    """
    Fonction principale qui appelle les affichages d'entrepôts et de véhicule
    Entrée: Aucune
    Sortie: Affiche les onglets avec les deux types d'affichage
    """
    # Section de gestion des stocks avec onglets
    st.subheader("📦 ÉTAT DES STOCKS ET CHARGEMENT")
    tabs = st.tabs(["🏭 Stocks Entrepôts", "🚚 Chargement Véhicule"])
    
    with tabs[0]:
        display_warehouse_status()
    
    with tabs[1]:
        display_vehicle_status()
    
##############################################
# Fonction principale (interface Streamlit)
##############################################

def show_planning_page():
    """
    Fonction principale qui construit l'interface de planification
    Entrée: Utilise de nombreuses variables dans st.session_state
    Sortie: Affiche toute l'interface Streamlit de planification
    """
    # Initialisation des variables nécessaires
    init_session_state()
    st.title("Planning de Livraison Supply Chain")
    
    # Bouton de réinitialisation complète
    if st.button("🔁 Reset Total"):
        reset_session_state()
        st.success("Session réinitialisée!")
    
    # Récupération des listes de véhicules et d'entrepôts
    transports = [v.nom for v in st.session_state.fleet]
    warehouses = st.session_state.warehouse_names

    # Interface pour sélectionner un véhicule et une heure de départ
    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        transport = st.selectbox("Transport", options=transports, index=1, key="transport_select",
                                   placeholder="Sélectionnez un transport disponible")
    with col2:
            departure_time = st.time_input("Heure de départ", key="departure_time", step=600, value=datetime.time(8, 45))
        
    # La suite ne s'affiche que si transport et heure sont définis
    if transport and departure_time:
        # Récupération du véhicule choisi et affichage de ses caractéristiques
        st.session_state.vehicule = next(v for v in st.session_state.fleet if v.nom == transport)
        info = f"Poids max: {st.session_state.vehicule.charge_max_emport_kg} kg | Volume max: {st.session_state.vehicule.volume_max_emport_m3} m³"
        with col3:
            st.markdown(f"<div style='padding-top: 34px;'>{info}</div>", unsafe_allow_html=True)

        st.subheader("Où sont les commandes")
        display_commands()
        
        # Affichage des étapes déjà validées
        with st.container(key="saved_steps"):
            display_steps()
        
        # Interface pour ajouter une nouvelle étape
        with st.container(key="current_steps"):
            st.subheader("Ajouter une étape")
            current_step: Step = st.session_state.current_step
            current_entrepot = st.selectbox("Entrepôt", ["Sélectionnez un entrepôt"] + warehouses,
                                            index=0, key="current_step_entrepot")
            
            # La suite ne s'affiche que si un entrepôt est sélectionné
            if current_entrepot != "Sélectionnez un entrepôt":
                current_step.entrepot = current_entrepot
                st.write("Opérations :")
                updated_operations = []
                
                # Parcours et édition des opérations existantes de l'étape
                for i, op in enumerate(current_step.operations):
                    cols = st.columns([2, 3, 2, 1])
                    current_type = op.type
                    current_produit = op.produit
                    current_quantite = op.quantite
                    
                    # Sélection du type d'opération (Charger ou Décharger)
                    op_type = cols[0].selectbox("Type", ["Charger", "Décharger"],
                                                key=f"type_{i}",
                                                index=["Charger", "Décharger"].index(current_type) if current_type in ["Charger", "Décharger"] else 0)
                    produit = None
                    quantite = None
                    
                    # Gestion spécifique pour le chargement (produits disponibles dans l'entrepôt)
                    if op_type == "Charger":
                        produits_disponibles = st.session_state.Orders_copy.warehouses_content(current_entrepot)
                        produit = cols[1].selectbox("Produit", list(produits_disponibles.keys()),
                                                    key=f"prod_{i}",
                                                    index=list(produits_disponibles.keys()).index(current_produit) if current_produit in produits_disponibles else 0)
                        if produit:
                            # Définir la quantité maximum en fonction du stock disponible
                            max_values = float(produits_disponibles[produit])
                            quantite = cols[2].slider("Quantité", min_value=0.0, max_value=max_values,
                                                       value=current_quantite if current_type=="Charger" else 0.0,
                                                       step=0.05, key=f"qty_{i}")
                    # Gestion spécifique pour le déchargement (produits disponibles dans le véhicule)
                    elif op_type == "Décharger":
                        produits_disponibles = [key for key, value in st.session_state.content_copy.items() if value > 0]
                        produit = cols[1].selectbox("Produit", produits_disponibles,
                                                    key=f"prod_{i}",
                                                    index=produits_disponibles.index(current_produit) if current_produit in produits_disponibles else 0)
                        if produit:
                            # Définir la quantité maximum en fonction de ce qui est dans le véhicule
                            max_values = float(st.session_state.content_copy[produit])
                            quantite = cols[2].slider("Quantité", min_value=0.0, max_value=max_values,
                                                       value=current_quantite if current_type=="Décharger" else 0.0,
                                                       step=0.01, key=f"qty_{i}")
                    
                    # Bouton de suppression d'opération
                    with cols[3]:
                        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                        if st.button("🗑️", key=f"delete_{i}"):
                            current_step.operations.pop(i)
                            st.rerun()
                        else:
                            # Mise à jour de l'opération si les valeurs sont valides
                            if op_type and produit is not None and quantite is not None:
                                updated_operations.append(Operation(op_type, produit, quantite))
                            else:
                                # Sinon on garde l'opération telle quelle
                                updated_operations.append(op)
                
                # Mise à jour de la liste complète des opérations
                current_step.operations = updated_operations
                
                # Bouton pour ajouter une nouvelle opération vide
                if st.button("Ajouter une Opération"):
                    current_step.operations.append(Operation("", "", 0))
                    st.rerun()
        
        # Validation de l'étape en cours
        if st.button("➕ Valider l'étape"):
            vehicule = st.session_state.vehicule
            # Vérification de la validité de l'étape par rapport aux contraintes
            valid, msg, updated_orders, updated_content = st.session_state.current_step.validate(
                vehicule,
                st.session_state.Orders_copy.copy(),
                st.session_state.content_copy.copy()
            )
            if valid:
                # Si valide, on met à jour les états et on passe à une nouvelle étape
                st.session_state.Orders_copy = updated_orders
                st.session_state.content_copy = updated_content
                st.session_state.steps.append(st.session_state.current_step)
                st.session_state.current_step = Step()  # réinitialiser l'étape en cours
                st.rerun()
            else:
                # Sinon on affiche le message d'erreur
                st.error(msg)
        
        st.divider()
        
        # Validation finale du trajet (création d'un Route)
        if st.button("Valider trajet", type="primary"):
            if st.session_state.steps:
                # Vérifier que le véhicule est vide en fin de trajet (bonne pratique logistique)
                if any(quantity > 0 for quantity in st.session_state.content_copy.values()):
                    st.warning("Le véhicule doit être vide en fin de trajet pour valider le trajet.")
                else:
                    # Récupérer le point de départ du véhicule sélectionné
                    storage_point = st.session_state.vehicule.storage_point
                    # Vérifier que le trajet commence et finit au même point de stockage (contrainte logistique)
                    if st.session_state.steps[0].entrepot != storage_point or st.session_state.steps[-1].entrepot != storage_point:
                        st.warning(f"Le trajet doit débuter et se terminer au point de départ du véhicule ({storage_point}).")
                    else:
                        # Création du nouveau trajet avec les étapes validées
                        new_route = Route(transport, departure_time)
                        for step in st.session_state.steps:
                            new_route.add_step(step)
                        st.session_state.routes.append(new_route)
                        # Trier la liste des routes par temps de départ pour faciliter la simulation
                        st.session_state.routes.sort(key=lambda route: route.departure_time)
                        st.session_state.steps = []  # Réinitialisation pour le prochain trajet
                        st.success("Trajet ajouté!")
            else:
                st.warning("Veuillez ajouter au moins une étape au trajet.")

    # Affichage final de tous les trajets planifiés
    display_routes()