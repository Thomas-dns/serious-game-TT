import json
import networkx as nx
from haversine import haversine

class Network:
    """
    Classe pour manipuler un réseau routier à partir de données GeoJSON
    et effectuer des calculs de plus courts chemins.
    """
    
    def __init__(self, allowed_highway_types):
        """Initialisation de la classe Network"""
        self.graph = None
        self.data = None
        self.highway_types = []
        self.allowed_highway_types = allowed_highway_types

    def load_geojson(self, file_path):
        """
        Charge les données GeoJSON depuis un fichier
        
        Args:
            file_path (str): Chemin vers le fichier GeoJSON
            
        Returns:
            bool: True si le chargement a réussi, False sinon
        """
        try:
            with open(file_path, 'r') as f:
                self.data = json.load(f)

            print(f"Données chargées avec succès. {len(self.data['features'])} features trouvés.")
            return True
        except FileNotFoundError:
            print(f"Erreur: Le fichier {file_path} n'a pas été trouvé.")
            return False
        except json.JSONDecodeError:
            print(f"Erreur: Le fichier {file_path} n'est pas un JSON valide.")
            return False
        except Exception as e:
            print(f"Erreur lors du chargement du fichier: {str(e)}")
            return False
    
    def build_graph(self):
        """
        Construit un graphe NetworkX à partir des données GeoJSON chargées
        
        Returns:
            bool: True si la construction a réussi, False sinon
        """
        if not self.data:
            print("Erreur: Aucune donnée GeoJSON chargée.")
            return False
        
        try:
            self.graph = nx.Graph()
            
            for feature in self.data['features']:
                if 'geometry' not in feature or 'type' not in feature['geometry']:
                    continue
                    
                # Vérifier si ce type de highway est autorisé
                highway_type = feature['properties'].get('highway')
                if self.allowed_highway_types and highway_type not in self.allowed_highway_types:
                    continue
                    
                if feature['geometry']['type'] == 'LineString':
                    self._process_linestring(feature)
                
                elif feature['geometry']['type'] == 'Polygon':
                    self._process_polygon(feature)
            
            print(f"Graphe construit avec {self.graph.number_of_nodes()} nœuds et {self.graph.number_of_edges()} arêtes.")
            return True
        except Exception as e:
            print(f"Erreur lors de la construction du graphe: {str(e)}")
            return False
    
    def _process_linestring(self, feature):
        """
        Traite une géométrie de type LineString et l'ajoute au graphe
        
        Args:
            feature (dict): Feature GeoJSON contenant une LineString
        """
        coordinates = feature['geometry']['coordinates']
        max_speed = feature['properties'].get('maxspeed', '50')
        highway_type = feature['properties'].get('highway')
        
        # Convertir maxspeed en entier si possible
        try:
            max_speed = int(max_speed)
        except ValueError:
            max_speed = 50
        
        # Ajouter chaque segment comme arête dans le graphe
        for i in range(len(coordinates) - 1):
            self._add_edge(coordinates[i], coordinates[i + 1], max_speed, highway_type, feature)
    
    def _process_polygon(self, feature):
        """
        Traite une géométrie de type Polygon et l'ajoute au graphe
        
        Args:
            feature (dict): Feature GeoJSON contenant un Polygon
        """
        max_speed = feature['properties'].get('maxspeed', '50')
        highway_type = feature['properties'].get('highway')
        
        try:
            max_speed = int(max_speed)
        except ValueError:
            max_speed = 50
        
        # Traiter chaque segment du polygone comme une arête
        for ring in feature['geometry']['coordinates']:
            for i in range(len(ring) - 1):
                self._add_edge(ring[i], ring[i + 1], max_speed, highway_type, feature)
    
    def _add_edge(self, point1_coords, point2_coords, max_speed, highway_type, feature):
        """
        Ajoute une arête au graphe avec toutes les propriétés nécessaires
        
        Args:
            point1_coords (list): Coordonnées du premier point [lon, lat]
            point2_coords (list): Coordonnées du second point [lon, lat]
            max_speed (int): Vitesse maximale autorisée
            highway_type (str): Type de route
            feature (dict): Feature GeoJSON complète
        """
        point1 = tuple(point1_coords)
        point2 = tuple(point2_coords)
        
        # Calculer la distance réelle entre les points (en km)
        distance = haversine(
            (point1[1], point1[0]),  # (lat, lon) pour point1
            (point2[1], point2[0])   # (lat, lon) pour point2
        )
        
        # Estimer le temps de trajet en fonction de la vitesse max (en minutes)
        travel_time = distance / max_speed * 60
        
        # Ajouter les nœuds s'ils n'existent pas déjà
        if not self.graph.has_node(point1):
            self.graph.add_node(point1, pos=point1)
        if not self.graph.has_node(point2):
            self.graph.add_node(point2, pos=point2)
        
        # Stocker toutes les propriétés importantes
        properties = {
            'distance': distance,  # en km
            'time': travel_time,   # en minutes
            'max_speed': max_speed,  # en km/h
            'highway_type': highway_type,
            'weight': distance,     # par défaut, le poids est la distance
            'feature_id': feature.get('id', 'Unknown')  # Identifiant de la feature
        }
        
        # Si d'autres propriétés sont disponibles, les ajouter
        for key, value in feature.get('properties', {}).items():
            if key not in properties:
                properties[key] = value
        
        # Ajouter l'arête avec toutes les propriétés
        self.graph.add_edge(point1, point2, **properties)
    
    def find_nearest_node(self, point):
        """
        Trouve le nœud du graphe le plus proche d'un point donné
        
        Args:
            point (list): Coordonnées du point [lon, lat]
            
        Returns:
            tuple: (nœud le plus proche, distance en km)
        """
        if not self.graph:
            print("Erreur: Aucun graphe construit.")
            return None, float('inf')
        
        min_dist = float('inf')
        nearest_node = None
        
        # Convertir le point en tuple pour la comparaison
        query_point = tuple(point)
        
        for node in self.graph.nodes():
            # Calculer la distance entre le point et le nœud
            dist = haversine(
                (node[1], node[0]),      # (lat, lon) pour le nœud
                (query_point[1], query_point[0])  # (lat, lon) pour le point de requête
            )
            
            if dist < min_dist:
                min_dist = dist
                nearest_node = node
        
        return nearest_node, min_dist
    
    def calculate_shortest_path(self, start_point, end_point, weight='weight'):
        """
        Calcule le plus court chemin entre deux points en utilisant NetworkX
        
        Args:
            start_point (list): Coordonnées du point de départ [lon, lat]
            end_point (list): Coordonnées du point d'arrivée [lon, lat]
            weight (str): Critère d'optimisation ('weight', 'distance', 'time')
            
        Returns:
            list: Liste des nœuds formant le chemin ou None si aucun chemin n'est trouvé
        """
        if not self.graph:
            print("Erreur: Aucun graphe construit.")
            return None
        
        # Trouver les nœuds les plus proches des points de départ et d'arrivée
        start_node, start_dist = self.find_nearest_node(start_point)
        end_node, end_dist = self.find_nearest_node(end_point)
        
        if start_node is None or end_node is None:
            print("Erreur: Impossible de trouver les nœuds les plus proches.")
            return None
        
        print(f"Nœud de départ: {start_node} (distance: {start_dist:.4f} km)")
        print(f"Nœud d'arrivée: {end_node} (distance: {end_dist:.4f} km)")
        
        # Utiliser directement la méthode NetworkX pour trouver le plus court chemin
        try:
            path = nx.shortest_path(self.graph, source=start_node, target=end_node, weight=weight)
            return path
        except nx.NetworkXNoPath:
            print("Erreur: Aucun chemin trouvé entre les points spécifiés.")
            return None
        except Exception as e:
            print(f"Erreur lors du calcul du chemin: {str(e)}")
            return None
        
    def calculate_detailed_path(self, start_point, end_point, weight='weight'):
        """
        Calcule le plus court chemin entre deux points et renvoie les détails de chaque segment
        
        Args:
            start_point (list): Coordonnées du point de départ [lon, lat]
            end_point (list): Coordonnées du point d'arrivée [lon, lat]
            weight (str): Critère d'optimisation ('weight', 'distance', 'time')
            
        Returns:
            dict: Dictionnaire contenant le chemin et les détails des segments
                - 'nodes': Liste des nœuds formant le chemin
                - 'segments': Liste des dictionnaires contenant les détails de chaque segment
                - 'total_distance': Distance totale du chemin en km
                - 'total_time': Temps total de parcours en minutes
            ou None si aucun chemin n'a été trouvé
        """
        if not self.graph:
            print("Erreur: Aucun graphe construit.")
            return None
            
        # Trouver les nœuds les plus proches des points de départ et d'arrivée
        start_node, start_dist = self.find_nearest_node(start_point)
        end_node, end_dist = self.find_nearest_node(end_point)
        
        if start_node is None or end_node is None:
            print("Erreur: Impossible de trouver les nœuds les plus proches.")
            return None
            
        print(f"Nœud de départ: {start_node} (distance: {start_dist:.4f} km)")
        print(f"Nœud d'arrivée: {end_node} (distance: {end_dist:.4f} km)")
        
        try:
            # Utiliser les méthodes NetworkX directement
            path = nx.shortest_path(self.graph, source=start_node, target=end_node, weight=weight)
            
            # Si le chemin est vide, retourner None
            if not path:
                print("Aucun chemin trouvé.")
                return None
                
            # Calculer la longueur du chemin avec la méthode NetworkX
            path_length = nx.path_weight(self.graph, path, weight='distance')
            
            # Initialiser les variables pour les totaux
            total_distance = 0
            total_time = 0
            
            # Préparer la liste pour stocker les détails des segments
            segments = []
            
            # Parcourir chaque segment du chemin
            for i in range(len(path) - 1):
                # Récupérer les données de l'arête entre deux nœuds consécutifs
                edge_data = self.graph.get_edge_data(path[i], path[i + 1])
                
                # Créer un dictionnaire avec les données du segment
                segment_info = {
                    'start_node': path[i],
                    'end_node': path[i + 1],
                    'distance': edge_data['distance'],
                    'max_speed': edge_data['max_speed'],
                    'highway_type': edge_data.get('highway_type', 'unknown')
                }
                
                # Ajouter les informations du segment à la liste
                segments.append(segment_info)
                
                # Mettre à jour les totaux
                total_distance += edge_data['distance']
                total_time += edge_data['time']
            
            # Préparer le résultat
            result = {
                'nodes': path,
                'segments': segments,
                'total_distance': total_distance,
                'total_time': total_time,
                'num_segments': len(segments)
            }
            
            return result
            
        except nx.NetworkXNoPath:
            print("Erreur: Aucun chemin trouvé entre les points spécifiés.")
            return None
        except Exception as e:
            print(f"Erreur lors du calcul du chemin: {str(e)}")
            return None


import matplotlib.pyplot as plt
import contextily as ctx

import pyproj

def plot_route(self, path_details, output_file='route.jpg'):
    """
    Génère une image JPG du trajet sur la carte
    
    Args:
        path_details (dict): Résultat de calculate_detailed_path
        output_file (str): Nom du fichier de sortie
    """
    if not self.graph:
        print("Erreur: Aucun graphe construit.")
        return

    # Créer un transformateur de coordonnées
    transformer = pyproj.Transformer.from_crs(
        'EPSG:4326',  # WGS84 (lon/lat)
        'EPSG:3857',  # Web Mercator
        always_xy=True
    )

    fig, ax = plt.subplots(figsize=(12, 12))
    
    # Tracer toutes les routes du réseau
    for u, v in self.graph.edges():
        # Conversion des coordonnées en Web Mercator
        x1, y1 = transformer.transform(u[0], u[1])
        x2, y2 = transformer.transform(v[0], v[1])
        ax.plot([x1, x2], [y1, y2], color='grey', linewidth=0.3, alpha=0.5, zorder=1)

    # Tracer le trajet trouvé
    if path_details:
        path = path_details['nodes']
        for i in range(len(path) - 1):
            lon1, lat1 = path[i]
            lon2, lat2 = path[i+1]
            x1, y1 = transformer.transform(lon1, lat1)
            x2, y2 = transformer.transform(lon2, lat2)
            ax.plot([x1, x2], [y1, y2], color='red', linewidth=2, zorder=2)

        # Points de départ et d'arrivée
        start = path[0]
        end = path[-1]
        xs, ys = transformer.transform(start[0], start[1])
        xe, ye = transformer.transform(end[0], end[1])
        ax.scatter([xs], [ys], color='lime', s=100, label='Départ', zorder=3)
        ax.scatter([xe], [ye], color='blue', s=100, label='Arrivée', zorder=3)

    # Ajout de la carte OpenStreetMap
    ctx.add_basemap(ax, crs='EPSG:3857', source=ctx.providers.OpenStreetMap.Mapnik)
    
    ax.set_axis_off()
    plt.legend()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    # Ajouter la méthode à la classe Network
Network.plot_route = plot_route

# Exemple d'utilisation
if __name__ == "__main__":
    network = Network(allowed_highway_types=['motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'residential', 'service'])
    network.load_geojson('ressources/maps/toulouse_road_filtered.geojson')
    network.build_graph()

    start_point = [1.4437, 43.6043]  # Capitole
    end_point = [1.4603, 43.6122]    # Oncopole
    
    path = network.calculate_detailed_path(start_point, end_point)
    
    if path:
        network.plot_route(path, 'mon_trajet.jpg')
        print("Carte générée avec succès dans mon_trajet.jpg")