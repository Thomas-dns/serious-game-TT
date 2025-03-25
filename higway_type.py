import json

# Charger le fichier GeoJSON
with open('ressources/maps/toulouse_road_filtered.geojson', 'r') as f:
    data = json.load(f)

# Extraire tous les types de highway uniques
highway_types = set()
for feature in data['features']:
    if 'properties' in feature and 'highway' in feature['properties']:
        highway_types.add(feature['properties']['highway'])

# Convertir en liste et trier
highway_types_list = sorted(list(highway_types))
print(highway_types_list)