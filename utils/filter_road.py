import json

def filter_geojson(input_file, output_file):
    # Lire le fichier GeoJSON
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filtrer les features avec maxspeed
    filtered_features = []
    
    for feature in data['features']:
        if 'maxspeed' in feature['properties']:
            # Créer un nouveau feature simplifié
            new_feature = {
                'type': 'Feature',
                'geometry': feature['geometry'],
                'properties': {
                    'highway': feature['properties'].get('highway', ''),
                    'maxspeed': feature['properties']['maxspeed']
                }
            }
            
            # Ajouter l'ID si souhaité
            if 'id' in feature:
                new_feature['id'] = feature['id']
            
            filtered_features.append(new_feature)
    
    # Créer le nouveau GeoJSON
    output_data = {
        'type': 'FeatureCollection',
        'features': filtered_features
    }
    
    # Écrire dans le fichier de sortie
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    return len(filtered_features)

# Exemple d'utilisation
if __name__ == "__main__":
    input_file = "utils/export_toulouse.geojson"
    output_file = "ressources/maps/toulouse_road_filtered.geojson"
    
    count = filter_geojson(input_file, output_file)
    print(f"{count} routes avec maxspeed ont été sauvegardées dans {output_file}")