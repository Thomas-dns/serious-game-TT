# utils/travel.py

import pyproj
from shapely.geometry import Polygon, LineString
from shapely.ops import transform, unary_union
from functools import partial
import streamlit as st
from utils.tools import load_json_data

# Calcule la distance parcourue dans chaque zone géographique lors d'un trajet entre deux points
# Entrée: 
#   - start: nom du point de départ (correspond à un nom d'entrepôt ou point de livraison)
#   - end: nom du point d'arrivée
# Sortie:
#   - results: dictionnaire {nom_zone: distance_parcourue_en_mètres}
#   - visited_zones: liste des noms des zones traversées
def distance_by_zones_exclusive(start, end):
    # On construit la ligne (trajet) en shapely avec des coordonnées (lon, lat)
    # Shapely attend (x, y) = (lon, lat). Il faut faire attention à l'ordre des coordonnées.
    current_round = st.session_state.round
    path = f"ressources/maps/map_{current_round}.json"
    data = load_json_data(path)

    delivery_points = data["DELIVERY_POINTS"]

    # Récupération des coordonnées des points de départ et d'arrivée à partir de leurs noms
    start_point = next((p for p in delivery_points if p["nom"] == start), None)
    coord_start = start_point["coordonnees"] 

    end_point = next((p for p in delivery_points if p["nom"] == end), None)
    coord_end = end_point["coordonnees"] 

    # Inversion de l'ordre des coordonnées pour respecter le format (lon, lat) attendu par Shapely
    start_lon, start_lat = coord_start[1], coord_start[0]
    end_lon, end_lat     = coord_end[1],   coord_end[0]

    # Création d'une ligne droite entre le point de départ et d'arrivée
    line = LineString([(start_lon, start_lat), (end_lon, end_lat)])
    
    # Configuration de la projection pour convertir les coordonnées géographiques en mètres
    # Passage du système WGS84 (GPS mondial) au Lambert93 (système français en mètres)
    projection = partial(
        pyproj.transform,
        pyproj.CRS("EPSG:4326"),   # source WGS84
        pyproj.CRS("EPSG:2154")    # destination Lambert93
    )

    # Application de la projection à notre ligne pour avoir des distances en mètres
    projected_line = transform(projection, line)

    # Extraction des zones géographiques à partir des données
    raw_zones = data.get("ZONES", [])
    
    # Préparation des zones avec leurs géométries projetées
    zones_processed = []
    for z in raw_zones:
        nom_zone = z["nom"]
        coords   = z["coordonnees"]
        style    = z.get("style", {})
        z_index  = style.get("zIndex")  # Index d'empilement visuel des zones

        # Création du polygone représentant la zone et projection en Lambert93
        polygon = Polygon(coords)
        projected_polygon = transform(projection, polygon)

        zones_processed.append(
            {
                "name": nom_zone,
                "zIndex": z_index,
                "geom": projected_polygon
            }
        )
    
    # Tri des zones par zIndex décroissant pour traiter d'abord les zones de priorité supérieure
    # Cela permet de gérer correctement le chevauchement des zones
    zones_sorted = sorted(zones_processed, key=lambda x: x["zIndex"], reverse=True)

    # Calcul des distances exclusives par zone (sans compter deux fois les portions qui se chevauchent)
    processed_union = None  # Contiendra l'union des zones déjà traitées
    results = {}           # Stockage des résultats
    visited_zones = []     # Liste des zones effectivement traversées

    for zinfo in zones_sorted:
        zname = zinfo["name"]
        zgeom = zinfo["geom"]

        # Pour les zones qui se chevauchent, on ne compte que la partie qui n'est pas 
        # déjà couverte par une zone de priorité supérieure
        if processed_union is None:
            zone_exclusive = zgeom  # Première zone traitée ou aucun chevauchement
        else:
            zone_exclusive = zgeom.difference(processed_union)  # On retire les parties déjà comptées

        # Calcul de l'intersection entre la ligne de trajet et la zone (partie exclusive)
        intersect_line_zone = projected_line.intersection(zone_exclusive)
        dist_m = intersect_line_zone.length  # Longueur en mètres

        # Enregistrement de la distance pour cette zone
        results[zname] = dist_m
        
        # Si la distance est positive, la zone est considérée comme visitée
        if dist_m > 0:
            visited_zones.append(zname)

        # Mise à jour de l'union des zones traitées pour les prochains calculs
        # On utilise la géométrie complète de la zone, pas seulement sa partie exclusive
        if processed_union is None:
            processed_union = zgeom
        else:
            processed_union = processed_union.union(zgeom)
            
    return results, visited_zones