# utils/game_logic.py

import streamlit as st
import pandas as pd
import datetime
import re
from utils.travel import distance_by_zones_exclusive, distance_network, calculate_segment_distance

class Operation:
    """Représente une opération de chargement/déchargement de produit"""
    def __init__(self, op_type, produit, quantite):
        self.type = op_type
        self.produit = produit
        self.quantite = quantite

    def __repr__(self):
        return f"{self.type}({self.produit}: {self.quantite})"


class Step:
    """Représente une étape dans un entrepôt avec ses opérations"""
    def __init__(self, entrepot=None):
        self.entrepot = entrepot
        self.operations = []  
        self.final_load = None

    def add_operation(self, operation: Operation):
        self.operations.append(operation)

    def validate(self, vehicule, orders, content):
        """Valide les opérations en vérifiant les contraintes de stock et capacité"""
        # Appliquer les opérations et vérifier les contraintes
        for op in self.operations:
            product_id = op.produit
            qty = op.quantite
            
            if op.type == "Charger":
                stock_dispo = orders.warehouses_content(self.entrepot).get(product_id, 0)
                if stock_dispo < qty:
                    return False, f"Stock {product_id} insuffisant ({stock_dispo} restant)", orders, content
                orders.update_warehouse_content(self.entrepot, product_id, -qty)
                content[product_id] += qty
            else:  # "Décharger"
                if content.get(product_id, 0) < qty:
                    return False, f"{product_id} manquant dans le véhicule", orders, content
                orders.update_warehouse_content(self.entrepot, product_id, qty)
                content[product_id] -= qty

        # Vérification des capacités
        total_poids = sum(content[pid] * orders.orders[pid].content['poids_kg'] for pid in content)
        total_volume = sum(content[pid] * orders.orders[pid].content['volume_m3'] for pid in content)

        if total_poids > vehicule.charge_max_emport_kg:
            return False, f"Surcharge : {total_poids:.2f}kg > {vehicule.charge_max_emport_kg}kg", orders, content
        if total_volume > vehicule.volume_max_emport_m3:
            return False, f"Volume dépassé : {total_volume:.2f}m³ > {vehicule.volume_max_emport_m3}m³", orders, content

        self.final_load = {
            'content': content.copy(),
            'total_poids': total_poids,
            'total_volume': total_volume
        }
        return True, "", orders, content


class Route:
    """Représente un trajet avec plusieurs étapes"""
    def __init__(self, transport, departure_time):
        self.transport = transport
        self.steps = []
        self.impact = None
        self.departure_time = departure_time
        self.segment_impacts = []

    def add_step(self, step: Step):
        self.steps.append(step)

    def calculate_impact(self, fleet):
        """Calcule l'impact (coût, émission, distance, temps) du trajet"""
        vehicule = next(v for v in fleet if v.nom == self.transport)
        v_max = vehicule.vitesse_max
        cost = emission = total_d = temps = 0

        for i in range(len(self.steps) - 1):
            step = self.steps[i]
            if not step.final_load:
                continue
                
            warehouse = step.entrepot
            load = step.final_load['total_poids']
            next_warehouse = self.steps[i+1].entrepot
            distances = distance_by_zones_exclusive(warehouse, next_warehouse)
            
            segment_cost = segment_emission = segment_distance = segment_time = 0

            for zone_name, distance in distances.items():
                zone = next((z for z in st.session_state.zones if z.nom == zone_name), None)
                vitesse_limite = zone.parameters.get("vitesse_maximale", None) if zone else None
                vitesse = min(v_max, vitesse_limite) if vitesse_limite else v_max
                
                dist_km = distance / 1000
                segment_cost += vehicule.travel_cost_km(load) * dist_km
                segment_emission += vehicule.travel_emission_km(load) * dist_km
                segment_distance += dist_km
                segment_time += dist_km / vitesse

            self.segment_impacts.append(
                f"{warehouse} -> {next_warehouse} ({segment_distance:.1f} Km): {segment_cost:.1f}€ | {segment_emission:.1f}"
            )

            cost += segment_cost
            emission += segment_emission
            total_d += segment_distance
            temps += segment_time

        self.impact = f"Cout : {cost:.1f} € | Emission : {emission:.1f} | D : {total_d:.1f} Km | temps {temps:.2f}: h"
        return self.impact
        
    def get_segment_impacts(self):
        return self.segment_impacts


class Simulation:
    def __init__(self, time_step_seconds=60):
        self.time_step = datetime.timedelta(seconds=time_step_seconds)
        self.start_time = datetime.datetime(2025, 2, 10, 8, 0, 0)
        self.end_time = self.start_time + datetime.timedelta(hours=8)
        self.events = []
        self.simulation_orders = st.session_state.Orders.copy()
        
        # Initialiser les véhicules
        self.vehicle_states = {
            v.nom: {
                "available": True, 
                "current_route": None,
                "current_step": 0,
                "time_remaining": datetime.timedelta(0),
                "current_load": 0,
                "travel_cost": 0,
                "travel_emission": 0,
                "distance": 0
            } for v in st.session_state.fleet
        }
        
        # Trier les routes par véhicule et heure de départ
        self.routes_by_vehicle = {v.nom: [] for v in st.session_state.fleet}
        for route in st.session_state.routes:
            self.routes_by_vehicle[route.transport].append(route)
            
        for veh in self.routes_by_vehicle:
            self.routes_by_vehicle[veh].sort(key=lambda r: r.departure_time)

    def compute_segment_time(self, vehicle, start, end, load):
        """Calcule le temps, coût, émission et distance entre deux points"""
        distances = distance_by_zones_exclusive(start, end)
        total_hours = total_cost = total_emission = total_distance = 0.0
        
        for zone_name, distance in distances.items():
            zone_obj = next((z for z in st.session_state.zones if z.nom == zone_name), None)
            zone_speed = zone_obj.parameters.get("vitesse_maximale", None) if zone_obj else None
            speed = min(vehicle.vitesse_max, zone_speed) if zone_speed else vehicle.vitesse_max
            
            dist_km = distance / 1000
            segment_time_hours = dist_km / speed
            
            total_hours += segment_time_hours
            total_cost += vehicle.travel_cost_km(load) * dist_km
            total_emission += vehicle.travel_emission_km(load) * dist_km
            total_distance += dist_km

        return datetime.timedelta(hours=total_hours), total_cost, total_emission, total_distance
    
    def compute_segment_time_network(self, vehicle, start, end, load):
        """Calcule le temps, coût, émission et distance entre deux points"""
        valid_roads = vehicle.valid_roads
        segments = distance_network(start, end, valid_roads)

        total_hours = total_cost = total_emission = total_distance = 0.0

        for segment in segments['segments']:
            distance = segment['distance']
            seg_speed = segment['max_speed']
            speed = min(vehicle.vitesse_max, seg_speed)

            segment_time_hours = distance / speed
            
            total_hours += segment_time_hours
            total_cost += vehicle.travel_cost_km(load) * distance
            total_emission += vehicle.travel_emission_km(load) * distance
            total_distance += distance
        
        return datetime.timedelta(hours=total_hours), total_cost, total_emission, total_distance

    def is_stock_available(self, warehouse, step):
        """Vérifie la disponibilité du stock pour les opérations"""
        for op in step.operations:
            if op.type == "Charger" and self.simulation_orders.warehouses_content(warehouse).get(op.produit, 0) < op.quantite:
                return False
        return True

    def log_event(self, time, vehicle, message):
        """Ajoute un événement au journal"""
        self.events.append({"time": time, "vehicle": vehicle, "event": message})

    def process_step_operations(self, warehouse, vehicle, operations, simulation_clock):
        """Exécute les opérations d'une étape"""
        state = self.vehicle_states[vehicle]
        vehicle_obj = next(v for v in st.session_state.fleet if v.nom == vehicle)
        total_loading_time = 0

        for op in operations:
            order = self.simulation_orders.orders[op.produit]
            quantity_kg = op.quantite * order.content['poids_kg']

            if op.type == "Charger":
                self.simulation_orders.update_warehouse_content(warehouse, op.produit, -op.quantite)
                self.log_event(simulation_clock, vehicle, f"Chargement de {op.quantite} de {op.produit} à {warehouse}")
                state["current_load"] += op.quantite * self.simulation_orders.orders[op.produit].content['poids_kg']
                time_spent = vehicle_obj.calculate_loading_time(quantity_kg)
            else:  # "Décharger"
                self.simulation_orders.update_warehouse_content(warehouse, op.produit, op.quantite)
                self.log_event(simulation_clock, vehicle, f"Déchargement de {op.quantite} de {op.produit} à {warehouse}")
                state["current_load"] -= op.quantite * self.simulation_orders.orders[op.produit].content['poids_kg']
                time_spent = vehicle_obj.calculate_unloading_time(quantity_kg)

    def run_simulation_with_time_step(self):
        """Exécute la simulation en avançant par pas de temps"""
        simulation_clock = self.start_time

        while simulation_clock <= self.end_time:
            if simulation_clock.minute % 15 == 0:
                print(f"clock : {simulation_clock}")

            for veh_nom, state in self.vehicle_states.items():
                if state["available"]:
                    # Vérifier si une route doit démarrer
                    if self.routes_by_vehicle[veh_nom]:
                        next_route = self.routes_by_vehicle[veh_nom][0]
                        route_departure = datetime.datetime.combine(simulation_clock.date(), next_route.departure_time)
                        
                        if simulation_clock >= route_departure:
                            # Démarrer la route
                            state["current_route"] = self.routes_by_vehicle[veh_nom].pop(0)
                            state["current_step"] = 0
                            
                            if state["current_route"].steps:
                                next_step = state["current_route"].steps[0].entrepot
                                vehicle_obj = next(v for v in st.session_state.fleet if v.nom == veh_nom)
                                
                                state["time_remaining"], cost, emission, distance = self.compute_segment_time_network(
                                    vehicle=vehicle_obj,
                                    start=vehicle_obj.storage_point,
                                    end=next_step,
                                    load=state["current_load"]
                                )
                                
                                state["travel_cost"] += cost 
                                state["travel_emission"] += emission
                                state["distance"] += distance
                                state["available"] = False
                                
                                self.log_event(simulation_clock, veh_nom, f"Démarrage de la route vers {next_step}")
                else:
                    # Véhicule en cours de route
                    state["time_remaining"] -= self.time_step
                    
                    if state["time_remaining"] <= datetime.timedelta(0):
                        current_route = state["current_route"]
                        current_step_index = state["current_step"]
                        current_step = current_route.steps[current_step_index]
                        arrived_warehouse = current_step.entrepot

                        self.log_event(simulation_clock, veh_nom, f"Arrivée à {arrived_warehouse}")
                        state["current_step"] += 1

                        # Vérifier la disponibilité des stocks
                        if any(op.type == "Charger" for op in current_step.operations) and not self.is_stock_available(arrived_warehouse, current_step):
                            self.log_event(simulation_clock, veh_nom, f"Attente de chargement à {arrived_warehouse}")
                            state["time_remaining"] = datetime.timedelta(minutes=5)
                            continue
                        
                        # Exécuter les opérations
                        self.process_step_operations(arrived_warehouse, veh_nom, current_step.operations, simulation_clock)

                        # Préparer l'étape suivante ou terminer
                        if state["current_step"] < len(current_route.steps):
                            next_warehouse = current_route.steps[state["current_step"]].entrepot
                            vehicle_obj = next(v for v in st.session_state.fleet if v.nom == veh_nom)
                            
                            state["time_remaining"], cost, emission, distance = self.compute_segment_time_network(
                                vehicle=vehicle_obj,
                                start=arrived_warehouse,
                                end=next_warehouse,
                                load=state["current_load"]
                            )
                            
                            state["travel_cost"] += cost 
                            state["travel_emission"] += emission
                            state["distance"] += distance
                            
                            self.log_event(simulation_clock, veh_nom, f"Départ de {arrived_warehouse} vers {next_warehouse}")
                        else:
                            # Fin de la route
                            state["available"] = True
                            state["current_route"] = None
                            self.log_event(simulation_clock, veh_nom, "Fin de route")
                            
            simulation_clock += self.time_step

        # Trier les événements par heure
        self.events.sort(key=lambda e: e["time"])
        return self.events
    
    def generate_route_reports(self):
        """Génère des rapports sur les routes planifiées"""
        return [
            {
                "Vehicle": route.transport,
                "Departure Time": route.departure_time,
                "Segments": route.get_segment_impacts()
            } for route in st.session_state.routes
        ]

    def check_deliveries(self):
        """Vérifie si les commandes ont été livrées à temps"""
        delivery_status = {}
        
        for order_id, order in st.session_state.Orders.orders.items():
            end_warehouse = order.end
            required_delivery_time = order.delivery_time
            delivered = False
            quantity_delivered = 0
            actual_delivery_time = None
            
            # Créer un pattern spécifique pour cette commande et cet entrepôt
            pattern = re.compile(rf"Déchargement de ([\d.]+) de {order_id} à {end_warehouse}")
            
            for event in self.events:
                match = pattern.search(event["event"])
                if match:
                    delivered = True
                    quantity_delivered += float(match.group(1))
                    actual_delivery_time = event["time"]  # Dernière heure de livraison
            
            # Affichage pour debug
            print(f"Commande {order_id}: livrée={delivered}, quantité={quantity_delivered}, heure requise={required_delivery_time}")
            
            if delivered and quantity_delivered >= 0.99:
                if actual_delivery_time <= required_delivery_time:
                    delivery_status[order_id] = "on_time"
                else:
                    delivery_status[order_id] = "late"
            else:
                delivery_status[order_id] = "not_delivered"
                
        return delivery_status
    
    def display_simulation(self):
        """Affiche les résultats de la simulation"""
        df = pd.DataFrame(self.events)
        df['time'] = df['time'].apply(lambda t: t.strftime("%H:%M:%S"))
        st.dataframe(df)