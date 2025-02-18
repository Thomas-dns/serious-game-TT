from utils.tools import load_json_data
import copy
import datetime

class Order:
    def __init__(self, id, start, end, content, delivery_time, warehouse):
        self.id = id
        self.start = start
        self.end = end
        self.content = content  # dict with volume_m3, poids_kg, description
        # A terme on peut juste creer des object product (plein d'object = une commande)
        if isinstance(delivery_time, str):
            self.delivery_time = datetime.datetime.strptime(delivery_time, "%Y-%m-%dT%H:%M:%S")
        else:
            self.delivery_time = delivery_time
        

        self.warehouse = warehouse # dict avec les entrepots logistique en keys
                
    # X est une proportion de la commande dans la warehouse : warehouse_name
    def alocate_to_warehouse(self, start_warehouse, end_warehouse, x):
        self.warehouse[end_warehouse] += x
        self.warehouse[start_warehouse] -= x
    
    def copy(self):
        """Méthode pour créer une copie profonde de l'objet Order"""
        return Order(
            self.id,
            self.start,
            self.end,
            copy.deepcopy(self.content),
            self.delivery_time,
            copy.deepcopy(self.warehouse)
        )

class Orders:
    def __init__(self, orders_json_path, warehouses):
        self.warehouses = warehouses
        self.orders = self.read_json_orders(orders_json_path)

    def get_warehouse(self, order):
        warehouse = {}
        for w in self.warehouses:
            if w == order["start"]:
                warehouse[w] = 1
            else:
                warehouse[w] = 0
        return warehouse
    
    def read_json_orders(self, orders_json_path):
        if orders_json_path is not None:
            data = load_json_data(orders_json_path)["ORDERS"]
            dict = {}
            for order in data:
                warehouse = self.get_warehouse(order)
                elt = Order(order["id"],order["start"],order["end"],order["content"],order["delivery_time"],warehouse)
                dict[order["id"]] = elt
        else:
            dict = {}
        return dict
    
    # Fonction qui permet d'obtenir un dictionnaire avec les commandes par entrepot
    def get_warehouse_orders(self):
        result = {}

        for warehouse in self.warehouses:
            result[warehouse] = []
            for name, order in self.orders.items():
                if order.warehouse[warehouse] > 0:
                    result[warehouse].append([order.id, order.warehouse[warehouse]])
        return result
    
    # On renvoit un dict avec les orders et leur proportion dans l'entrepot warehouse
    def warehouses_content(self, warehouse):
        result = {}
        for name, order in self.orders.items():
            if order.warehouse[warehouse] > 0:
                result[order.id] = order.warehouse[warehouse]
        return result

    # Renvoit un dict avec les orders et 0, on s'en sert pour initialiser le véhicule
    def get_orders(self):
        dict = {}
        for name, order in self.orders.items():
            dict[order.id] = 0
        return dict

    def copy(self):
        """Méthode pour créer une copie profonde de l'objet Orders"""
        new_orders = Orders(None, copy.deepcopy(self.warehouses))
        new_orders.orders = {order_id: order.copy() for order_id, order in self.orders.items()}
        return new_orders
    
    def update_warehouse_content(self, warehouse, order_id, quantity_change):
        """
        Met à jour la proportion d'une commande dans un entrepôt.
        :param warehouse: Nom de l'entrepôt
        :param order_id: ID de la commande
        :param quantity_change: Changement de quantité (positif pour charger, négatif pour décharger)
        """
        if order_id in self.orders:
            self.orders[order_id].warehouse[warehouse] += quantity_change
            # S'assurer que la proportion ne devient pas négative
            if self.orders[order_id].warehouse[warehouse] < 0:
                self.orders[order_id].warehouse[warehouse] = 0


    
        
