# utils/game_logic.py

import streamlit as st
import pandas as pd
from utils.travel import distance_by_zones_exclusive


##############################################
# definition of the classes Operation, Step and Route used for planning the delivery
##############################################

class Operation:
    """
    Représente une opération sur une commande.
    - type : "Charger" ou "Décharger"
    - produit : identifiant de la commande (ex: "BC001")
    - quantite : quantité à charger/décharger
    """
    def __init__(self, op_type, produit, quantite):
        self.type = op_type
        self.produit = produit
        self.quantite = quantite

    def __repr__(self):
        return f"{self.type}({self.produit}: {self.quantite})"


class Step:
    """
    Représente une étape de livraison.
    - entrepot : nom de l'entrepôt associé à l'étape
    - operations : liste d'objets Operation effectuées à cet entrepôt
    - final_load : dictionnaire (mis à jour lors de la validation) qui contient le contenu final, le poids total et le volume total dans le véhicule
    """
    def __init__(self, entrepot=None):
        self.entrepot = entrepot
        self.operations = []  # liste d'objets Operation
        self.final_load = None

    def add_operation(self, operation: Operation):
        self.operations.append(operation)

    def is_valid(self):
        """Vérifie qu'une étape comporte au moins une opération complète."""
        return True, ""

    def validate(self, vehicule, orders, content):
        """
        Simule et valide l'étape en appliquant toutes les opérations, puis en calculant
        la charge finale (poids et volume). On retourne False avec un message d'erreur
        si une contrainte (stock, surcharge, volume) n'est pas respectée.
        
        :param vehicule: objet Vehicle sélectionné
        :param orders: copie des commandes (st.session_state.Orders_copy)
        :param content: copie du contenu présent dans le véhicule (st.session_state.content_copy)
        :return: (bool, message, orders_updated, content_updated)
        """
        # Vérification de la complétude de l'étape
        valid, msg = self.is_valid()
        if not valid:
            return False, msg, orders, content

        # Appliquer toutes les opérations pour mettre à jour le contenu
        for op in self.operations:
            product_id = op.produit
            qty = op.quantite
            produit = orders.orders[product_id]
            if op.type == "Charger":
                stock_dispo = orders.warehouses_content(self.entrepot).get(product_id, 0)
                if stock_dispo < qty:
                    return False, f"Stock {product_id} insuffisant ({stock_dispo} restant)", orders, content
                orders.update_warehouse_content(self.entrepot, product_id, -qty)
                content[product_id] += qty
            elif op.type == "Décharger":
                if content.get(product_id, 0) < qty:
                    return False, f"{product_id} manquant dans le véhicule", orders, content
                orders.update_warehouse_content(self.entrepot, product_id, qty)
                content[product_id] -= qty

        # Calculer le poids et le volume totaux une fois toutes les opérations appliquées
        total_poids = sum(content[pid] * orders.orders[pid].content['poids_kg'] for pid in content)
        total_volume = sum(content[pid] * orders.orders[pid].content['volume_m3'] for pid in content)

        # Vérifier les capacités du véhicule
        if total_poids > vehicule.charge_max_emport_kg:
            return False, f"Surcharge : {total_poids:.2f}kg > {vehicule.charge_max_emport_kg}kg", orders, content
        if total_volume > vehicule.volume_max_emport_m3:
            return False, f"Volume dépassé : {total_volume:.2f}m³ > {vehicule.volume_max_emport_m3}m³", orders, content

        # Enregistrer la charge finale dans l'étape
        self.final_load = {
            'content': content.copy(),
            'total_poids': total_poids,
            'total_volume': total_volume
        }
        return True, "", orders, content


class Route:
    """
    Représente un trajet constitué d'une série d'étapes.
    - transport : nom du véhicule utilisé
    - steps : liste d'objets Step validés
    - impact : chaîne résumant le coût et l'émission calculés sur l'ensemble du trajet
    """
    def __init__(self, transport, departure_time):
        self.transport = transport
        self.steps = []  # liste d'objets Step
        self.impact = None
        self.departure_time = departure_time

    def add_step(self, step: Step):
        self.steps.append(step)

    def calculate_impact(self, fleet):
        """
        Calcule l'impact (coût, émission et distance) du trajet en parcourant les étapes.
        - fleet : liste des véhicules pour retrouver l'objet Vehicle associé
        """
        vehicule = next(v for v in fleet if v.nom == self.transport)
        v_max = vehicule.vitesse_max
        cost = 0
        emission = 0
        total_d = 0
        temps = 0

        for i, step in enumerate(self.steps):
            if i < len(self.steps) - 1 and step.final_load:
                warehouse = step.entrepot
                load = step.final_load['total_poids']
                next_warehouse = self.steps[i+1].entrepot
                distances = distance_by_zones_exclusive(warehouse, next_warehouse)
                for zone_name, distance in distances.items():
                    zone = next((z for z in st.session_state.zones if z.nom == zone_name), None)
    
                    if zone is not None:
                        vitesse_limite = zone.parameters.get("vitesse_maximale", None)
                    else:
                        vitesse_limite = None

                    vitesse = min(v_max, vitesse_limite) if vitesse_limite is not None else v_max

                    cost += vehicule.travel_cost_km(load) * distance / 1000
                    emission += vehicule.travel_emission_km(load) * distance / 1000
                    total_d += distance / 1000
                    temps += distance / 1000 / vitesse
        self.impact = f"Cout : {cost:.1f} € | Emission : {emission:.1f} | D : {total_d:.1f} Km | temps {temps:.2f}: h"
        return self.impact


##############################################
# Logic for game simulation
##############################################

from utils.tools import load_json_data
from utils.map_logic import Zone, Warehouse
from ressources.vehicules import Vehicle
from ressources.orders.orders import Orders

class Simulation:
    def __init__(self):
        if 'round' not in st.session_state:
            st.session_state.round = 1

    def init_session_state_round(round):
        st.session_state.fleet = []
        st.session_state.orders = []
        
        # Charger les données de configuration, carte et commandes
        data = load_json_data(f"ressources/config/config_{round}.json")
        map_data = load_json_data(f"ressources/maps/map_{round}.json")

        # Stocker la carte complète
        st.session_state.map_data = map_data
        
        # Créer des objets Zone à partir de la clé "ZONES"
        zones_raw = map_data.get("ZONES", [])
        st.session_state.zones = [
            Zone(
                nom=z["nom"],
                coordonnees=z["coordonnees"],
                style=z.get("style", {}),
                description=z.get("description", ""),
                parameters=z.get("parameters", {})
            )
            for z in zones_raw
        ]
        
        # Créer des objets Warehouse à partir des points de livraison de type "warehouse"
        delivery_points = map_data.get("DELIVERY_POINTS", [])
        st.session_state.warehouses_info = [
            Warehouse(
                nom=p["nom"],
                coordonnees=p["coordonnees"],
                type_point=p["type"],
                description=p.get("description", "")
            )
            for p in delivery_points if p.get("type") == "warehouse"
        ]
        
        # Conserver la liste des noms d'entrepôts pour la gestion des commandes
        st.session_state.warehouse_names = [w.nom for w in st.session_state.warehouses_info]
        
        # Initialiser la flotte
        for vehicule in data["fleet"]:
            st.session_state.fleet.append(Vehicle(**vehicule))
        
        # Instancier Orders en lui passant la liste des noms d'entrepôts
        st.session_state.Orders = Orders(f"ressources/orders/order_{round}.json", st.session_state.warehouse_names)

