import streamlit as st
import leafmap.foliumap as leafmap
import geopandas as gpd
from shapely.geometry import Polygon
import folium
import json
from utils.tools import load_json_data

# Classe représentant une zone géographique avec ses caractéristiques et contraintes
class Zone:
    def __init__(self, nom, coordonnees, style, description, parameters):
        self.nom = nom
        self.coordonnees = coordonnees  # liste de coordonnées
        self.style = style              # dictionnaire de style (fillColor, weight, etc.)
        self.parameters = parameters    # dictionnaire de paramètres (vitesse_maximale, critair_min, etc.)
        self.description = description
        
    def __repr__(self):
        return f"Zone({self.nom}, parameters={self.parameters})"

# Classe représentant un point de livraison ou un entrepôt sur la carte
class Warehouse:
    def __init__(self, nom, coordonnees, type_point, description):
        self.nom = nom
        self.coordonnees = coordonnees
        self.type = type_point  # "warehouse", "delivery", "start", etc.
        self.description = description

    def __repr__(self):
        return f"Warehouse({self.nom}, type={self.type})"


# Fonction qui crée et configure la carte interactive avec toutes les zones et points de livraison
# Entrée: Aucune (utilise le round actuel depuis st.session_state)
# Sortie: Tuple (carte configurée, dictionnaire des descriptions)
def create_map():
    # Récupération du round actuel depuis la session Streamlit
    current_round = st.session_state.round

    # Récupérer les points de livraison et zones depuis le fichier JSON correspondant au round
    path = f"ressources/maps/map_{current_round}.json"
    data = load_json_data(path)

    ZONES = data['ZONES']
    DELIVERY_POINTS = data['DELIVERY_POINTS']

    # Extraction des descriptions pour affichage ultérieur
    descriptions = {"ZONES" : [],
                    "DELIVERY_POINTS" : []}
    
    for zone in ZONES:
        descriptions["ZONES"].append([zone['nom'],zone['description']])
    for delivery_point in DELIVERY_POINTS:
        descriptions["DELIVERY_POINTS"].append([delivery_point['nom'],delivery_point['description']])

    # Création de la carte avec des paramètres par défaut centrés sur la France
    # Note: center et zoom semblent être des valeurs temporaires qui mériteraient d'être ajustées
    m = leafmap.Map(
            center=[48.5, 2.5],
            zoom=9,
            draw_control=False,
            measure_control=False,
            fullscreen_control=False,
            attribution_control=True,
            #tiles=""  # Pour avoir un fond blanc
        )

    # Fonction interne pour créer une zone géographique à partir de coordonnées
    # Entrée: coordonnées et nom de la zone
    # Sortie: GeoDataFrame (format utilisé par leafmap)
    def creer_zone(coordonnes, nom):
        # Création d'un polygone Shapely à partir des coordonnées
        zone = Polygon(coordonnes)

        # Création d'un GeoDataFrame avec le polygone
        gdf = gpd.GeoDataFrame(
            {'nom': [nom]},
            geometry=[zone],
            crs="EPSG:4326"  # Système de coordonnées WGS84 standard
        )
        
        return gdf
    
    # Dictionnaire pour stocker les couleurs de la légende
    legend_dict = {}

    # Ajout de chaque zone à la carte
    for zone in ZONES:
        # Conversion des coordonnées en GeoDataFrame
        gdf = creer_zone(zone['coordonnees'], zone['nom'])
        # Ajout à la carte avec le style défini dans le JSON
        m.add_gdf(
            gdf,
            style=zone['style'],
            layer_name="Ville"  # Toutes les zones sont dans la couche "Ville"
        )
        # Ajout de la couleur à la légende
        legend_dict[zone['nom']] = zone['style']['fillColor']

    # Ajout de la légende à la carte
    m.add_legend(
            title="Legende",
            legend_dict=legend_dict
        )

    # Ajout des points de livraison avec des marqueurs différenciés par type
    for delivery_point in DELIVERY_POINTS:
        if delivery_point['nom'] == "Start":
            # Point de départ en vert
            folium.Marker(
                delivery_point['coordonnees'],
                popup=delivery_point['nom'],
                icon=folium.Icon(color='green', icon='info-sign')
            ).add_to(m)
        elif delivery_point['type'] == "warehouse":
            # Entrepôts en vert clair
            folium.Marker(
                delivery_point['coordonnees'],
                popup=delivery_point['nom'],
                icon=folium.Icon(color='lightgreen', icon='info-sign')
            ).add_to(m)
        elif delivery_point['type'] == "delivery":
            # Points de livraison en rouge clair
            folium.Marker(
                delivery_point['coordonnees'],
                popup=delivery_point['nom'],
                icon=folium.Icon(color='ligthred', icon='flag')
            ).add_to(m)

    # Retourne la carte configurée et les descriptions pour utilisation ultérieure
    return m, descriptions