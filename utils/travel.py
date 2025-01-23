# utils/travel.py

import pyproj
from shapely.geometry import Polygon, LineString
from shapely.ops import transform, unary_union
from functools import partial

# Renvois la distance parcourue dans chaque zone par la ligne entre coord_start et coord_end
def distance_by_zones_exclusive(map_data, coord_start, coord_end):
    # On construit la line (trajet) en shapely (lon, lat)
    # Shapely attend (x, y) = (lon, lat). il faut faire attention.
    start_lon, start_lat = coord_start[1], coord_start[0]
    end_lon, end_lat     = coord_end[1],   coord_end[0]

    line = LineString([(start_lon, start_lat), (end_lon, end_lat)])
    
    # On définti la projection pour passer en mètres
    projection = partial(
        pyproj.transform,
        pyproj.CRS("EPSG:4326"),   # source WGS84
        pyproj.CRS("EPSG:2154")    # destination Lambert93
    )

    projected_line = transform(projection, line)

    # On extraire les ZONES et prépare une liste (zone_name, zIndex, geom) pour un traitement plus simple
    raw_zones = map_data.get("ZONES", [])
    
    zones_processed = []
    for z in raw_zones:
        nom_zone = z["nom"]
        coords   = z["coordonnees"]
        style    = z.get("style", {})
        z_index  = style.get("zIndex")  # 0 par défaut si absent

        # Construire le Polygon pour chaque zone (supposant coords = [ [lon, lat], [lon, lat], ... ])
        polygon = Polygon(coords)
        projected_polygon = transform(projection, polygon) # On projete en Lambert93

        zones_processed.append(
            {
                "name": nom_zone,
                "zIndex": z_index,
                "geom": projected_polygon
            }
        )
    
    # On trie les zones par zIndex descendant pour que les zones les plus "haute" passe en première
    zones_sorted = sorted(zones_processed, key=lambda x: x["zIndex"], reverse=True)

    # On boucle et calcule la distance "exclusivement" dans chaque zone
    # On maintient un union des zones déjà traitées, pour "masquer" ces portions aux zones de zIndex inférieur.
    processed_union = None
    results = {}

    for zinfo in zones_sorted:
        zname = zinfo["name"]
        zgeom = zinfo["geom"]

        # Extraire la portion qui n'est PAS déjà couverte par d'autres zones (zIndex plus grand)
        # On enlève les zones déjà traitées (processed_union) a la zone actuelle
        if processed_union is None:
            zone_exclusive = zgeom  # aucune zone plus haute n'a été traitée
        else:
            zone_exclusive = zgeom.difference(processed_union)

        # Calcul de l'intersection entre la ligne et la zone actuelle => distance
        intersect_line_zone = projected_line.intersection(zone_exclusive)
        dist_m = intersect_line_zone.length

        results[zname] = dist_m # On stocke la distance pour cette zone

        # Mettre à jour la "union" de tout ce qui a été traité
        # On unionne la géométrie initiale (zgeom), pas la portion exclusive,
        # pour ne plus compter aucun bout de cette zone dans les zIndex inférieurs.
        if processed_union is None:
            processed_union = zgeom # si processed_union n'existe pas encore
        else:
            processed_union = processed_union.union(zgeom)

    return results
