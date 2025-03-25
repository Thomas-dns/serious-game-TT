# utils/game_logic.py
# Ce module implémente les classes principales pour la logique du jeu de simulation de chaîne logistique.
# Il gère les opérations de chargement/déchargement, les étapes de livraison, les trajets et la simulation.

import streamlit as st
import pandas as pd
import datetime
import re
from utils.travel import distance_by_zones_exclusive

# Classe représentant une opération individuelle de chargement ou déchargement d'un produit
class Operation:
    """Représente une opération de chargement/déchargement de produit"""
    def __init__(self, op_type, produit, quantite):
        # Entrée: op_type (str): Type d'opération ("Charger" ou "Décharger")
        #         produit (str): Identifiant du produit
        #         quantite (float): Quantité à charger/décharger
        self.type = op_type
        self.produit = produit
        self.quantite = quantite

    def __repr__(self):
        # Sortie: Représentation textuelle de l'opération
        return f"{self.type}({self.produit}: {self.quantite})"


# Classe représentant une étape dans un entrepôt, avec un ensemble d'opérations à effectuer
class Step:
    """Représente une étape dans un entrepôt avec ses opérations"""
    def __init__(self, entrepot=None):
        # Entrée: entrepot (str, optionnel): Nom de l'entrepôt
        self.entrepot = entrepot
        self.operations = []  # Liste des opérations à effectuer
        self.final_load = None  # État du chargement après les opérations

    def add_operation(self, operation: Operation):
        # Ajoute une opération à cette étape
        # Entrée: operation (Operation): L'opération à ajouter
        self.operations.append(operation)

    def validate(self, vehicule, orders, content):
        """Valide les opérations en vérifiant les contraintes de stock et capacité"""
        # Entrée: vehicule (Vehicle): Le véhicule utilisé
        #         orders (Orders): Les commandes disponibles
        #         content (dict): Le contenu actuel du véhicule
        # Sortie: (bool, str, Orders, dict): Validation réussie, message d'erreur, état des commandes, contenu mis à jour
        
        # Appliquer les opérations et vérifier les contraintes
        for op in self.operations:
            product_id = op.produit
            qty = op.quantite
            
            if op.type == "Charger":
                # Vérifier que le stock est suffisant dans l'entrepôt
                stock_dispo = orders.warehouses_content(self.entrepot).get(product_id, 0)
                if stock_dispo < qty:
                    return False, f"Stock {product_id} insuffisant ({stock_dispo} restant)", orders, content
                # Mettre à jour le stock de l'entrepôt et le contenu du véhicule
                orders.update_warehouse_content(self.entrepot, product_id, -qty)
                content[product_id] += qty
            else:  # "Décharger"
                # Vérifier que le produit est disponible dans le véhicule
                if content.get(product_id, 0) < qty:
                    return False, f"{product_id} manquant dans le véhicule", orders, content
                # Mettre à jour le stock de l'entrepôt et le contenu du véhicule
                orders.update_warehouse_content(self.entrepot, product_id, qty)
                content[product_id] -= qty

        # Vérification des capacités du véhicule
        # Calcul du poids et volume total après les opérations
        total_poids = sum(content[pid] * orders.orders[pid].content['poids_kg'] for pid in content)
        total_volume = sum(content[pid] * orders.orders[pid].content['volume_m3'] for pid in content)

        # Vérifier le respect des contraintes de charge maximale
        if total_poids > vehicule.charge_max_emport_kg:
            return False, f"Surcharge : {total_poids:.2f}kg > {vehicule.charge_max_emport_kg}kg", orders, content
        if total_volume > vehicule.volume_max_emport_m3:
            return False, f"Volume dépassé : {total_volume:.2f}m³ > {vehicule.volume_max_emport_m3}m³", orders, content

        # Stocker l'état final du chargement pour référence future
        self.final_load = {
            'content': content.copy(),
            'total_poids': total_poids,
            'total_volume': total_volume
        }
        return True, "", orders, content


# Classe représentant un trajet complet avec plusieurs étapes
class Route:
    """Représente un trajet avec plusieurs étapes"""
    def __init__(self, transport, departure_time):
        # Entrée: transport (str): Nom du véhicule utilisé
        #         departure_time (datetime.time): Heure de départ
        self.transport = transport
        self.steps = []  # Liste des étapes du trajet
        self.impact = None  # Impact environnemental et économique calculé
        self.departure_time = departure_time

    def add_step(self, step: Step):
        # Ajoute une étape au trajet
        # Entrée: step (Step): L'étape à ajouter
        self.steps.append(step)


# Classe principale gérant la simulation de livraison
class Simulation:
    def __init__(self, time_step_seconds=60):
        # Entrée: time_step_seconds (int): Intervalle de temps en secondes pour la simulation
        # Initialisation des paramètres temporels
        self.time_step = datetime.timedelta(seconds=time_step_seconds)
        self.start_time = datetime.datetime(2025, 2, 10, 8, 0, 0)  # Heure de début fixe
        self.end_time = self.start_time + datetime.timedelta(hours=8)  # Simulation sur 8 heures
        self.events = []  # Journal des événements
        # Copie des commandes pour ne pas modifier les originales
        self.simulation_orders = st.session_state.Orders.copy()
        
        # Initialiser l'état de chaque véhicule de la flotte
        self.vehicle_states = {
            v.nom: {
                "available": True,  # Disponibilité initiale
                "current_route": None,  # Route en cours
                "current_step": 0,  # Étape actuelle
                "time_remaining": datetime.timedelta(0),  # Temps restant jusqu'à l'étape suivante
                "current_load": 0,  # Charge actuelle
                "travel_cost": 0,  # Coût de déplacement cumulé
                "travel_emission": 0,  # Émissions cumulées
                "distance": 0,  # Distance parcourue
                "visited_zones": []  # Zones visitées pour vérifier les restrictions
            } for v in st.session_state.fleet
        }
        
        # Organiser les routes par véhicule pour faciliter la simulation
        self.routes_by_vehicle = {v.nom: [] for v in st.session_state.fleet}
        for route in st.session_state.routes:
            self.routes_by_vehicle[route.transport].append(route)
            
        # Trier les routes par heure de départ pour chaque véhicule
        for veh in self.routes_by_vehicle:
            self.routes_by_vehicle[veh].sort(key=lambda r: r.departure_time)

    def compute_segment_time(self, vehicle, start, end, load):
        """Calcule le temps, coût, émission et distance entre deux points"""
        # Entrée: vehicle (Vehicle): Véhicule utilisé
        #         start (str): Point de départ
        #         end (str): Point d'arrivée
        #         load (float): Charge actuelle du véhicule
        # Sortie: (timedelta, float, float, float, list): Temps, coût, émission, distance, zones visitées
        
        # Obtenir distances par zone et zones traversées
        distances, visited_zones = distance_by_zones_exclusive(start, end)
        total_hours = total_cost = total_emission = total_distance = 0.0
        
        # Calculer le temps, coût et émission pour chaque segment de zone
        for zone_name, distance in distances.items():
            # Récupérer les limitations de vitesse de la zone
            zone_obj = next((z for z in st.session_state.zones if z.nom == zone_name), None)
            zone_speed = zone_obj.parameters.get("vitesse_maximale", None) if zone_obj else None
            # Appliquer la limite de vitesse la plus restrictive
            speed = min(vehicle.vitesse_max, zone_speed) if zone_speed else vehicle.vitesse_max
            
            # Convertir en kilomètres et calculer le temps en heures
            dist_km = distance / 1000
            segment_time_hours = dist_km / speed
            
            # Cumuler les valeurs
            total_hours += segment_time_hours
            total_cost += vehicle.travel_cost_km(load) * dist_km
            total_emission += vehicle.travel_emission_km(load) * dist_km
            total_distance += dist_km

        return datetime.timedelta(hours=total_hours), total_cost, total_emission, total_distance, visited_zones

    def is_stock_available(self, warehouse, step):
        """Vérifie la disponibilité du stock pour les opérations"""
        # Entrée: warehouse (str): Entrepôt à vérifier
        #         step (Step): Étape avec les opérations à valider
        # Sortie: bool: True si le stock est disponible, False sinon
        
        for op in step.operations:
            # Vérifier uniquement les opérations de chargement
            if op.type == "Charger" and self.simulation_orders.warehouses_content(warehouse).get(op.produit, 0) < op.quantite:
                return False
        return True

    def log_event(self, time, vehicle, message):
        """Ajoute un événement au journal"""
        # Entrée: time (datetime): Horodatage de l'événement
        #         vehicle (str): Nom du véhicule
        #         message (str): Description de l'événement
        self.events.append({"time": time, "vehicle": vehicle, "event": message})

    def process_step_operations(self, warehouse, vehicle, operations, simulation_clock):
        """Exécute les opérations d'une étape"""
        # Entrée: warehouse (str): Entrepôt actuel
        #         vehicle (str): Nom du véhicule
        #         operations (list): Liste des opérations à exécuter
        #         simulation_clock (datetime): Horodatage actuel
        
        state = self.vehicle_states[vehicle]
        for op in operations:
            if op.type == "Charger":
                # Mettre à jour le stock et journaliser
                self.simulation_orders.update_warehouse_content(warehouse, op.produit, -op.quantite)
                self.log_event(simulation_clock, vehicle, f"Chargement de {op.quantite} de {op.produit} à {warehouse}")
                # Mettre à jour la charge du véhicule
                state["current_load"] += op.quantite * self.simulation_orders.orders[op.produit].content['poids_kg']
            else:  # "Décharger"
                # Mettre à jour le stock et journaliser
                self.simulation_orders.update_warehouse_content(warehouse, op.produit, op.quantite)
                self.log_event(simulation_clock, vehicle, f"Déchargement de {op.quantite} de {op.produit} à {warehouse}")
                # Mettre à jour la charge du véhicule
                state["current_load"] -= op.quantite * self.simulation_orders.orders[op.produit].content['poids_kg']

    def run_simulation_with_time_step(self):
        """Exécute la simulation en avançant par pas de temps"""
        # Sortie: list: Journal des événements
        
        simulation_clock = self.start_time

        # Boucle principale de simulation
        while simulation_clock <= self.end_time:
            # Afficher l'horloge périodiquement pour le suivi
            if simulation_clock.minute % 15 == 0:
                print(f"clock : {simulation_clock}")

            # Traiter chaque véhicule à chaque pas de temps
            for veh_nom, state in self.vehicle_states.items():
                if state["available"]:
                    # Si le véhicule est disponible, vérifier s'il doit démarrer une route
                    if self.routes_by_vehicle[veh_nom]:
                        next_route = self.routes_by_vehicle[veh_nom][0]
                        # Convertir le temps de départ en datetime complet
                        route_departure = datetime.datetime.combine(simulation_clock.date(), next_route.departure_time)
                        
                        if simulation_clock >= route_departure:
                            # C'est l'heure de démarrer la route
                            state["current_route"] = self.routes_by_vehicle[veh_nom].pop(0)
                            state["current_step"] = 0
                            
                            if state["current_route"].steps:
                                # Préparer le déplacement vers la première étape
                                next_step = state["current_route"].steps[0].entrepot
                                vehicle_obj = next(v for v in st.session_state.fleet if v.nom == veh_nom)
                                
                                # Calculer le temps, coût, émission, etc. pour ce segment
                                state["time_remaining"], cost, emission, distance, visited_zones = self.compute_segment_time(
                                    vehicle=vehicle_obj,
                                    start=vehicle_obj.storage_point,
                                    end=next_step,
                                    load=state["current_load"]
                                )
                                
                                # Mettre à jour les statistiques
                                state["travel_cost"] += cost 
                                state["travel_emission"] += emission
                                state["distance"] += distance
                                state["available"] = False
                                state["visited_zones"] = list(set(state["visited_zones"] + visited_zones))
                                
                                self.log_event(simulation_clock, veh_nom, f"Démarrage de la route vers {next_step}")
                else:
                    # Le véhicule est en déplacement
                    # Réduire le temps restant par le pas de temps
                    state["time_remaining"] -= self.time_step
                    
                    # Si le temps de déplacement est terminé
                    if state["time_remaining"] <= datetime.timedelta(0):
                        current_route = state["current_route"]
                        current_step_index = state["current_step"]
                        current_step = current_route.steps[current_step_index]
                        arrived_warehouse = current_step.entrepot

                        self.log_event(simulation_clock, veh_nom, f"Arrivée à {arrived_warehouse}")
                        state["current_step"] += 1

                        # Vérifier si les stocks sont disponibles pour le chargement
                        if any(op.type == "Charger" for op in current_step.operations) and not self.is_stock_available(arrived_warehouse, current_step):
                            # Si le stock est insuffisant, attendre un moment avant de réessayer
                            self.log_event(simulation_clock, veh_nom, f"Attente de chargement à {arrived_warehouse}")
                            state["time_remaining"] = datetime.timedelta(minutes=5)  # Attente arbitraire de 5 minutes
                            continue

                        # Exécuter les opérations de chargement/déchargement
                        self.process_step_operations(arrived_warehouse, veh_nom, current_step.operations, simulation_clock)

                        # Préparer l'étape suivante ou terminer la route
                        if state["current_step"] < len(current_route.steps):
                            # Il reste des étapes - calculer le prochain déplacement
                            next_warehouse = current_route.steps[state["current_step"]].entrepot
                            vehicle_obj = next(v for v in st.session_state.fleet if v.nom == veh_nom)
                            
                            # Calculer la durée, le coût, etc. pour ce nouveau segment
                            state["time_remaining"], cost, emission, distance, visited_zones = self.compute_segment_time(
                                vehicle=vehicle_obj,
                                start=arrived_warehouse,
                                end=next_warehouse,
                                load=state["current_load"]
                            )
                            
                            # Mettre à jour les statistiques cumulées
                            state["travel_cost"] += cost 
                            state["travel_emission"] += emission
                            state["distance"] += distance
                            # Ajouter les nouvelles zones visitées, en évitant les doublons avec set()
                            state["visited_zones"] = list(set(state["visited_zones"] + visited_zones))
                            
                            self.log_event(simulation_clock, veh_nom, f"Départ de {arrived_warehouse} vers {next_warehouse}")
                        else:
                            # Fin de la route - le véhicule devient disponible
                            state["available"] = True
                            state["current_route"] = None
                            self.log_event(simulation_clock, veh_nom, "Fin de route")
                            
            # Avancer le temps de simulation d'un pas
            simulation_clock += self.time_step

        # Trier les événements chronologiquement pour l'affichage
        self.events.sort(key=lambda e: e["time"])
        return self.events
    
    def generate_route_reports(self):
        """Génère des rapports sur les routes planifiées"""
        # Sortie: list: Liste de dictionnaires contenant les informations sur chaque route
        return [
            {
                "Vehicle": route.transport,
                "Departure Time": route.departure_time,
            } for route in st.session_state.routes
        ]

    def check_deliveries(self):
        """Vérifie si les commandes ont été livrées à temps"""
        # Sortie: dict: État de livraison de chaque commande
        delivery_status = {}
        
        # Analyser chaque commande
        for order_id, order in st.session_state.Orders.orders.items():
            end_warehouse = order.end
            required_delivery_time = order.delivery_time
            delivered = False
            quantity_delivered = 0
            actual_delivery_time = None
            
            # Créer une expression régulière pour trouver les événements de déchargement de cette commande
            pattern = re.compile(rf"Déchargement de ([\d.]+) de {order_id} à {end_warehouse}")
            
            # Parcourir tous les événements pour trouver les déchargements
            for event in self.events:
                match = pattern.search(event["event"])
                if match:
                    delivered = True
                    # Cumuler les quantités déchargées (plusieurs livraisons partielles possibles)
                    quantity_delivered += float(match.group(1))
                    actual_delivery_time = event["time"]  # Heure de la dernière livraison
            
            # Logs pour le débogage
            print(f"Commande {order_id}: livrée={delivered}, quantité={quantity_delivered}, heure requise={required_delivery_time}")
            
            # Déterminer le statut de la livraison
            if delivered:
                if actual_delivery_time <= required_delivery_time and quantity_delivered >= 0.99:
                    # Livraison à temps et complète (tolérance de 1%)
                    delivery_status[order_id] = "on_time"
                elif actual_delivery_time >= required_delivery_time and quantity_delivered >= 0.99:
                    # Livraison en retard mais complète
                    delivery_status[order_id] = "late"
                elif actual_delivery_time <= required_delivery_time and quantity_delivered <= 0.99:
                    # Livraison à temps mais partielle
                    delivery_status[order_id] = "on_time_partial"
                elif actual_delivery_time >= required_delivery_time and quantity_delivered <= 0.99:
                    # Livraison en retard et partielle
                    delivery_status[order_id] = "late_partial"
            else:
                # Commande non livrée
                delivery_status[order_id] = "not_delivered"
                
        return delivery_status
    
    def display_impact(self):
        """Affiche les impacts de la simulation"""
        # Cette fonction génère une visualisation des impacts pour chaque véhicule
        
        for vehicle_name, state in self.vehicle_states.items():
            # Récupérer les statistiques cumulées
            c = state["travel_cost"]
            e = state["travel_emission"]
            d = state["distance"]

            # Récupérer l'objet véhicule correspondant
            vehicule = next(v for v in st.session_state.fleet if v.nom == vehicle_name)

            # Ajouter le coût fixe journalier si le véhicule a été utilisé
            if d != 0:
                c += vehicule.cout_fixe_utilisation_journalier

            # Vérifier les infractions aux restrictions de critair
            forbiden_visited_zones = []
            # Niveau critair du véhicule
            critair = vehicule.crit_air

            # Identifier les zones interdites visitées
            for zone in state["visited_zones"]:
                z = next(z for z in st.session_state.zones if z.nom == zone)
                # Si le niveau critair minimum de la zone est plus élevé que celui du véhicule
                if z.parameters.get("critair_min") < critair:
                    forbiden_visited_zones.append(zone)

            # Afficher les impacts dans l'interface Streamlit
            st.subheader(f"Impacte cumulé de {vehicle_name}")
            data = {
                "Description": ["Coût (cout du trajet + cout fixe d'utilisation journalier)", "Émission", "Distance"],
                "Valeur": [f"{c:.1f} €", f"{e:.1f} Kg CO2", f"{d:.1f} Km"]
            }
            df = pd.DataFrame(data)
            st.table(df)

            # Afficher les amendes pour non-respect des zones
            if forbiden_visited_zones:
                st.write(f"Zones visitées interdites : {forbiden_visited_zones}")
                # Calculer l'amende (135€ par zone interdite visitée)
                amende = len(forbiden_visited_zones) * 135
                st.write(f"Amende de {amende}€ pour non respect de la zone crit'air, {len(forbiden_visited_zones)} zones interdite visitées")
            else:
                st.write("Aucune zone interdite visitée")

    def display_simulation(self):
        """Affiche les résultats de la simulation"""
        # Afficher le journal des événements dans Streamlit
        df = pd.DataFrame(self.events)
        # Formater les horodatages pour l'affichage
        df['time'] = df['time'].apply(lambda t: t.strftime("%H:%M:%S"))
        st.dataframe(df)