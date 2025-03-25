from utils.tools import load_json_data
import copy
import datetime

# Classe représentant une commande individuelle dans le système logistique
# Gère les informations de base d'une commande et son allocation dans différents entrepôts
class Order:
    def __init__(self, id, start, end, content, delivery_time, warehouse):
        """
        Initialise une nouvelle commande avec ses attributs de base
        
        Entrée:
            id: Identifiant unique de la commande
            start: Point de départ de la commande
            end: Point de livraison de la commande
            content: Dictionnaire contenant volume_m3, poids_kg, et description
            delivery_time: Heure de livraison prévue (string ou datetime)
            warehouse: Dictionnaire avec les entrepôts comme clés et leurs proportions comme valeurs
        """
        self.id = id
        self.start = start
        self.end = end
        self.content = content  # dict with volume_m3, poids_kg, description
        # A terme on peut juste creer des object product (plein d'object = une commande)
        
        # Conversion de la chaîne delivery_time en objet datetime si nécessaire
        if isinstance(delivery_time, str):
            self.delivery_time = datetime.datetime.strptime(delivery_time, "%Y-%m-%dT%H:%M:%S")
        else:
            self.delivery_time = delivery_time
        
        self.warehouse = warehouse # dict avec les entrepots logistique en keys
                
    def alocate_to_warehouse(self, start_warehouse, end_warehouse, x):
        """
        Transfère une proportion x d'une commande d'un entrepôt à un autre
        
        Entrée:
            start_warehouse: Entrepôt source
            end_warehouse: Entrepôt de destination
            x: Proportion à transférer
        """
        self.warehouse[end_warehouse] += x
        self.warehouse[start_warehouse] -= x
    
    def copy(self):
        """
        Crée une copie profonde de l'objet Order
        
        Sortie:
            Une nouvelle instance d'Order avec les mêmes valeurs
        """
        return Order(
            self.id,
            self.start,
            self.end,
            copy.deepcopy(self.content),
            self.delivery_time,
            copy.deepcopy(self.warehouse)
        )

# Classe gérant l'ensemble des commandes du système
# Permet de charger, suivre et manipuler les commandes dans différents entrepôts
class Orders:
    def __init__(self, orders_json_path, warehouses):
        """
        Initialise la collection de commandes à partir d'un fichier JSON
        
        Entrée:
            orders_json_path: Chemin vers le fichier JSON contenant les commandes
            warehouses: Liste des entrepôts disponibles
        """
        self.warehouses = warehouses
        self.orders = self.read_json_orders(orders_json_path)

    def get_warehouse(self, order):
        """
        Crée un dictionnaire d'allocation initiale des commandes aux entrepôts
        
        Entrée:
            order: Données brutes d'une commande
            
        Sortie:
            Un dictionnaire avec les entrepôts comme clés et la proportion (1 ou 0) comme valeurs
        """
        warehouse = {}
        # Attribue 1 à l'entrepôt de départ et 0 aux autres
        for w in self.warehouses:
            if w == order["start"]:
                warehouse[w] = 1
            else:
                warehouse[w] = 0
        return warehouse
    
    def read_json_orders(self, orders_json_path):
        """
        Lit et transforme les données JSON des commandes en objets Order
        
        Entrée:
            orders_json_path: Chemin vers le fichier JSON ou None
            
        Sortie:
            Un dictionnaire avec les ID des commandes comme clés et les objets Order comme valeurs
        """
        if orders_json_path is not None:
            data = load_json_data(orders_json_path)["ORDERS"]
            dict = {}
            # Convertit chaque commande JSON en objet Order
            for order in data:
                warehouse = self.get_warehouse(order)
                elt = Order(order["id"],order["start"],order["end"],order["content"],order["delivery_time"],warehouse)
                dict[order["id"]] = elt
        else:
            dict = {}
        return dict
    
    def get_warehouse_orders(self):
        """
        Retourne un dictionnaire des commandes regroupées par entrepôt
        
        Sortie:
            Un dictionnaire avec les entrepôts comme clés et une liste de [ID, proportion] comme valeurs
        """
        result = {}

        for warehouse in self.warehouses:
            result[warehouse] = []
            for name, order in self.orders.items():
                # N'inclut que les commandes qui ont une proportion positive dans cet entrepôt
                if order.warehouse[warehouse] > 0:
                    result[warehouse].append([order.id, order.warehouse[warehouse]])
        return result
    
    def warehouses_content(self, warehouse):
        """
        Obtient toutes les commandes avec leur proportion stockée dans un entrepôt spécifique
        
        Entrée:
            warehouse: Nom de l'entrepôt
            
        Sortie:
            Un dictionnaire avec les ID des commandes comme clés et leurs proportions comme valeurs
        """
        result = {}
        for name, order in self.orders.items():
            if order.warehouse[warehouse] > 0:
                result[order.id] = order.warehouse[warehouse]
        return result

    def get_orders(self):
        """
        Crée un dictionnaire d'initialisation pour le véhicule
        
        Sortie:
            Un dictionnaire avec les ID des commandes comme clés et 0 comme valeurs
        """
        dict = {}
        for name, order in self.orders.items():
            dict[order.id] = 0
        return dict

    def copy(self):
        """
        Crée une copie profonde de l'objet Orders
        
        Sortie:
            Un nouvel objet Orders avec les mêmes valeurs
        """
        new_orders = Orders(None, copy.deepcopy(self.warehouses))
        new_orders.orders = {order_id: order.copy() for order_id, order in self.orders.items()}
        return new_orders
    
    def update_warehouse_content(self, warehouse, order_id, quantity_change):
        """
        Met à jour la proportion d'une commande dans un entrepôt
        
        Entrée:
            warehouse: Nom de l'entrepôt
            order_id: ID de la commande
            quantity_change: Changement de quantité (positif pour charger, négatif pour décharger)
        """
        if order_id in self.orders:
            self.orders[order_id].warehouse[warehouse] += quantity_change
            # S'assurer que la proportion ne devient pas négative
            # Cela prévient les erreurs de calcul ou de logique
            if self.orders[order_id].warehouse[warehouse] < 0:
                self.orders[order_id].warehouse[warehouse] = 0