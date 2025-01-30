import streamlit as st
import leafmap.foliumap as leafmap
import geopandas as gpd
from shapely.geometry import Polygon
import folium
import json
from utils.tools import load_json_data

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
            tiles=""  # Pour avoir un fond blanc
        )

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
