import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta

def init_session_state():
    """Initialise les variables de session si elles n'existent pas."""
    if 'round' not in st.session_state:
        st.session_state.round = 1
    if 'commandes' not in st.session_state:
        st.session_state.commandes = {}

# Liste des clients avec leurs informations
clients_data = [
    {"ClientID": 10001, "Nom": "Entreprise ABC", "Adresse": "123 Rue des Affaires"},
    {"ClientID": 10002, "Nom": "Entreprise XYZ", "Adresse": "456 Avenue du Commerce"},
    {"ClientID": 10003, "Nom": "Particulier Dupont", "Adresse": "78 Boulevard Privé"},
]

# Nouveau catalogue des produits avec caractéristiques détaillées
catalogue = {
    "Bonbons": {"Prix": 10, "Conditionnement": "Carton de 10 boites", "Volume": 0.036, "Poids": 6, "Unités": 10},
    "Perceuses": {"Prix": 120, "Conditionnement": "Cartons de 6 perceuses", "Volume": 0.096, "Poids": 8, "Unités": 6},
    "Petites vis": {"Prix": 30, "Conditionnement": "Carton de 10 000 vis", "Volume": 0.096, "Poids": 12, "Unités": 10000},
    "Grandes vis": {"Prix": 35, "Conditionnement": "Carton de 8 000 vis", "Volume": 0.096, "Poids": 12, "Unités": 8000},
    "Paire de ski": {"Prix": 200, "Conditionnement": "Paire unique par carton", "Volume": 0.12, "Poids": 10, "Unités": 1},
    "Veste de sport": {"Prix": 50, "Conditionnement": "Carton de 50 vestes", "Volume": 0.288, "Poids": 6, "Unités": 50},
    "Pantalon de sport": {"Prix": 40, "Conditionnement": "Carton de 50 pantalons", "Volume": 0.288, "Poids": 4, "Unités": 50},
    "Paire de basket": {"Prix": 80, "Conditionnement": "Carton de 20 paires", "Volume": 0.288, "Poids": 9, "Unités": 20},
    "Pack d'eau": {"Prix": 15, "Conditionnement": "Demi palette de 48 packs", "Volume": 0.96, "Poids": 432, "Unités": 48},
    "Pack de bière": {"Prix": 25, "Conditionnement": "Demi palette de 55 packs", "Volume": 0.96, "Poids": 550, "Unités": 55},
    "Gateaux secs": {"Prix": 30, "Conditionnement": "Demi palette de 120 boites", "Volume": 0.96, "Poids": 80, "Unités": 120},
    "Pack de soda": {"Prix": 18, "Conditionnement": "Demi palette de 48 packs", "Volume": 0.96, "Poids": 432, "Unités": 48},
}

def generer_commandes():
    """Génère des commandes aléatoires pour un round donné, avec regroupement des achats."""
    commandes = []
    
    for _ in range(random.randint(5, 10)):  
        produit = random.choice(list(catalogue.keys()))
        quantite = random.randint(1, 5)
        client = random.choice(clients_data)  
        date_achat = (datetime.now() - timedelta(days=random.randint(0, 4))).strftime("%Y-%m-%d")  

        commandes.append({
            "ClientID": client["ClientID"],
            "Nom": client["Nom"],
            "Adresse": client["Adresse"],
            "Date": date_achat,
            "Produit": produit,
            "Quantité": quantite,
            "PrixUnitaire": catalogue[produit]["Prix"],
            "Total": quantite * catalogue[produit]["Prix"],
            "VolumeTotal": quantite * catalogue[produit]["Volume"],
            "PoidsTotal": quantite * catalogue[produit]["Poids"]
        })

    # Regrouper les commandes par ClientID, Date et Produit
    df = pd.DataFrame(commandes)
    df_grouped = df.groupby(["ClientID", "Date", "Nom", "Adresse", "Produit"], as_index=False).agg({
        "Quantité": "sum",
        "PrixUnitaire": "first",
        "Total": "sum",
        "VolumeTotal": "sum",
        "PoidsTotal": "sum"
    })

    return df_grouped.to_dict(orient="records")

def orders_view():
    """Affichage des commandes, catalogue des articles et liste des clients."""
    init_session_state()  

    st.title("Orders View - Gestion des Bons de Commande")

    # Afficher la liste des clients
    st.subheader("Liste des Clients")
    df_clients = pd.DataFrame(clients_data)
    st.dataframe(df_clients)

    # Afficher le tableau du catalogue des articles
    st.subheader("Catalogue des Articles en Vente")
    df_catalogue = pd.DataFrame.from_dict(catalogue, orient="index")
    st.dataframe(df_catalogue)

    # Générer de nouvelles commandes si le round actuel n'existe pas encore
    if st.session_state.round not in st.session_state.commandes:
        st.session_state.commandes[st.session_state.round] = generer_commandes()

    # Récupérer les commandes du round actuel
    df_commandes = pd.DataFrame(st.session_state.commandes[st.session_state.round])

    # Sélecteur pour filtrer les commandes par client et par date
    st.subheader("Filtrer les commandes")
    col1, col2 = st.columns(2)

    with col1:
        client_selectionne = st.selectbox(
            "Sélectionner un client :", 
            ["Tous"] + [client["Nom"] for client in clients_data]
        )

    with col2:
        dates_disponibles = sorted(df_commandes["Date"].unique(), reverse=True)
        date_selectionnee = st.selectbox("Sélectionner une date :", ["Toutes"] + dates_disponibles)

    # Appliquer les filtres
    if client_selectionne != "Tous":
        df_commandes = df_commandes[df_commandes["Nom"] == client_selectionne]
    
    if date_selectionnee != "Toutes":
        df_commandes = df_commandes[df_commandes["Date"] == date_selectionnee]

    st.subheader(f"Commandes - Round {st.session_state.round}")
    st.dataframe(df_commandes)

    # Afficher la somme du volume total et du poids total
    total_volume = df_commandes["VolumeTotal"].sum()
    total_poids = df_commandes["PoidsTotal"].sum()

    st.markdown(f"### **Volume total des commandes affichées :** {total_volume:.2f} m³")
    st.markdown(f"### **Poids total des commandes affichées :** {total_poids:.2f} kg")

if __name__ == "__main__":
    orders_view()
