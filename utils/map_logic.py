import streamlit as st
import leafmap.foliumap as leafmap
import geopandas as gpd
from shapely.geometry import Polygon
import folium
import json
from utils.tools import load_json_data

# utils/domain.py (ou utils/models.py)
class Zone:
    def __init__(self, nom, coordonnees, style, description, parameters):
        self.nom = nom
        self.coordonnees = coordonnees  # liste de coordonnées
        self.style = style              # dictionnaire de style (fillColor, weight, etc.)
        self.parameters = parameters    # dictionnaire de paramètres (vitesse_maximale, critair_min, etc.)
        self.description = description
        
    def __repr__(self):
        return f"Zone({self.nom}, parameters={self.parameters})"

class Warehouse:
    def __init__(self, nom, coordonnees, type_point, description):
        self.nom = nom
        self.coordonnees = coordonnees
        self.type = type_point  # "warehouse", "delivery", "start", etc.
        self.description = description

    def __repr__(self):
        return f"Warehouse({self.nom}, type={self.type})"


def create_map():
    current_round = st.session_state.round

    # Récupérer les points de livraison et zones
    path = f"ressources/maps/map_{current_round}.json"
    data = load_json_data(path)

    ZONES = data['ZONES']
    DELIVERY_POINTS = data['DELIVERY_POINTS']

    # Extraction des descriptions
    descriptions = {"ZONES" : [],
                    "DELIVERY_POINTS" : []}
    
    for zone in ZONES:
        descriptions["ZONES"].append([zone['nom'],zone['description']])
    for delivery_point in DELIVERY_POINTS:
        descriptions["DELIVERY_POINTS"].append([delivery_point['nom'],delivery_point['description']])

    # Créer la carte ON DOIT DECIDER DU CENTER ET DU ZOOM
    m = leafmap.Map(
            center=[48.5, 2.5],
            zoom=9,
            draw_control=False,
            measure_control=False,
            fullscreen_control=False,
            attribution_control=True,
            #tiles=""  # Pour avoir un fond blanc
        )
    
    # Définir une fonction de style qui attribue une couleur en fonction du type de route
    def road_style_function(feature):
        """Retourne un style différent en fonction du type de route."""
        highway_type = feature['properties'].get('highway', 'unknown')
        
        # Dictionnaire des couleurs par type de route
        colors = {
            'motorway': '#E990F9',         # violet
            'trunk': '#F9C890',            # orange
            'primary': '#F55142',          # rouge
            'secondary': '#F3F349',        # jaune
            'tertiary': '#559DF6',         # bleu clair
            'residential': '#6DE373',      # vert
            'service': '#BBBBBB',          # gris
            'footway': '#FFFFA0',          # jaune pâle
            'cycleway': '#9575CD',         # violet clair
            'path': '#00C853',             # vert foncé
            'unknown': '#808080'           # gris pour type inconnu
        }
        
        # Dictionnaire des largeurs par type de route
        weights = {
            'motorway': 5,
            'trunk': 4,
            'primary': 3,
            'secondary': 3,
            'tertiary': 2.5,
            'residential': 2,
            'service': 1.5,
            'footway': 1,
            'cycleway': 1,
            'path': 1,
            'unknown': 1
        }
        
        return {
            'color': colors.get(highway_type, colors['unknown']),
            'weight': weights.get(highway_type, weights['unknown']),
            'opacity': 0.7
        }
    
    with open("ressources/maps/toulouse_road_filtered.geojson", "r") as f:
        geojson_data = json.load(f)

    folium.GeoJson(
        geojson_data,
        name="Routes",
        style_function=road_style_function
        ).add_to(m)

    # Ajouter les zones
    def creer_zone(coordonnes, nom):

        zone = Polygon(coordonnes)

        gdf = gpd.GeoDataFrame(
            {'nom': [nom]},
            geometry=[zone],
            crs="EPSG:4326"
        )
        
        return gdf
    
    legend_dict = {}

    for zone in ZONES:
        gdf = creer_zone(zone['coordonnees'], zone['nom'])
        m.add_gdf(
            gdf,
            style=zone['style'],
            layer_name="Ville"
        )
        legend_dict[zone['nom']] = zone['style']['fillColor']

    m.add_legend(
            title="Legende",
            legend_dict=legend_dict
        )

    # Ajouter les points de livraison 
    for delivery_point in DELIVERY_POINTS:
        if delivery_point['nom'] == "Start":
            folium.Marker(
                delivery_point['coordonnees'],
                popup=delivery_point['nom'],
                icon=folium.Icon(color='green', icon='info-sign')
            ).add_to(m)
        elif delivery_point['type'] == "warehouse":
            folium.Marker(
                delivery_point['coordonnees'],
                popup=delivery_point['nom'],
                icon=folium.Icon(color='lightgreen', icon='info-sign')
            ).add_to(m)
        elif delivery_point['type'] == "delivery":
            folium.Marker(
                delivery_point['coordonnees'],
                popup=delivery_point['nom'],
                icon=folium.Icon(color='ligthred', icon='flag')
            ).add_to(m)

    return m, descriptions