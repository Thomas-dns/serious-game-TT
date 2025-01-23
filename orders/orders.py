class Order:
    def __init__(self, id, start, end, content, delivery_time, warehouse):
        self.id = id
        self.start = start
        self.end = end
        self.content = content  # dict with volume_m3, poids_kg, description
        self.delivery_time = delivery_time

        self.warehouse = warehouse # dict avec les entrepots logistique en keys

        self.warehouse["Start"] = 1 # Tous est dans start au debut
        
    # X est une proportion de la commande dans la warehouse : warehouse_name
    def alocate_to_warehouse(self, start_warehouse, end_warehouse, x):
        self.warehouse[end_warehouse] += x
        self.warehouse[start_warehouse] -= x
    
        
