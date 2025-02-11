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
        self.segment_impacts = []

    def add_step(self, step: Step):
        self.steps.append(step)

    # On peut soit calculer par segment soit par trajet ( les segment on a une duplication pour le premier ...)
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
                segment_cost = 0
                segment_emission = 0
                segment_distance = 0
                segment_time = 0

                for zone_name, distance in distances.items():
                    zone = next((z for z in st.session_state.zones if z.nom == zone_name), None)
                    if zone is not None:
                        vitesse_limite = zone.parameters.get("vitesse_maximale", None)
                    else:
                        vitesse_limite = None

                    vitesse = min(v_max, vitesse_limite) if vitesse_limite is not None else v_max

                    segment_cost += vehicule.travel_cost_km(load) * distance / 1000
                    segment_emission += vehicule.travel_emission_km(load) * distance / 1000
                    segment_distance += distance / 1000
                    segment_time += distance / 1000 / vitesse

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
    

##############################################
# Logic for game simulation
##############################################
import datetime
import re


class Simulation:
    def __init__(self, time_step_seconds=60):
        self.time_step = datetime.timedelta(seconds=time_step_seconds)
        self.start_time = datetime.datetime.combine(datetime.date.today(), datetime.time(8, 0, 0))
        # Par exemple, une simulation sur 8 heures
        self.end_time = self.start_time + datetime.timedelta(hours=8)
        self.events = []  # liste des événements de simulation

        self.simulation_orders = st.session_state.Orders.copy()

        # Initialiser l'état de chaque véhicule
        self.vehicle_states = {}
        for v in st.session_state.fleet:
            self.vehicle_states[v.nom] = {
                "available": True,
                "current_route": None,    # route en cours
                "current_step": 0,        # indice de l'étape dans la route
                "time_remaining": datetime.timedelta(0),
                "current_load": 0,
                "travel_cost": 0,
                "travel_emission": 0,
                "distance": 0
            }
        
        # Regrouper les routes par véhicule (si plusieurs routes sont planifiées pour le même véhicule)
        self.routes_by_vehicle = {}
        for v in st.session_state.fleet:
            self.routes_by_vehicle[v.nom] = []
        for route in st.session_state.routes:
            self.routes_by_vehicle[route.transport].append(route)
        # Trier par heure de départ pour chaque véhicule
        for veh in self.routes_by_vehicle:
            self.routes_by_vehicle[veh].sort(key=lambda r: r.departure_time)

    def compute_segment_time(self, vehicle, start, end, load):
        """
        Calcule le temps de parcours entre deux points (start et end, qui sont les noms des entrepôts)
        en fonction des distances par zone et des limitations de vitesse.
        """
        from utils.travel import distance_by_zones_exclusive
        # Récupérer le dictionnaire {zone: distance_en_mètres}
        distances = distance_by_zones_exclusive(start, end)
        total_hours = 0.0
        total_cost = 0.0
        total_emission = 0.0
        total_distance = 0.0
        for zone_name, distance in distances.items():
            # Récupérer la zone dans st.session_state
            zone_obj = next((z for z in st.session_state.zones if z.nom == zone_name), None)
            if zone_obj is not None:
                zone_speed = zone_obj.parameters.get("vitesse_maximale", None)
            else:
                zone_speed = None
            # La vitesse effective est le minimum entre la vitesse du véhicule et la vitesse limite de la zone (si définie)
            if zone_speed is not None:
                speed = min(vehicle.vitesse_max, zone_speed)
            else:
                speed = vehicle.vitesse_max
            # Convertir la distance en kilomètres et calculer le temps (en heures)
            segment_time_hours = (distance / 1000) / speed
            total_hours += segment_time_hours
            # On calcul les couts
            total_cost += vehicle.travel_cost_km(load) * distance / 1000
            total_emission += vehicle.travel_emission_km(load) * distance / 1000
            total_distance += distance / 1000

        return datetime.timedelta(hours=total_hours), total_cost, total_emission, total_distance

    def is_stock_available(self, warehouse, step):
        """
        Vérifie si le stock requis pour les opérations de chargement dans l'étape est disponible
        dans l'état simulation_orders (état original des commandes).
        """
        for op in step.operations:
            if op.type == "Charger":
                available = self.simulation_orders.warehouses_content(warehouse).get(op.produit, 0)
                if available < op.quantite:
                    return False
        return True

    def run_simulation_with_time_step(self):
        simulation_clock = self.start_time

        while simulation_clock <= self.end_time:
            # Affichage périodique de l'horloge de simulation
            if simulation_clock.minute % 15 == 0:
                print(f"clock : {simulation_clock}")

            for veh_nom, state in self.vehicle_states.items():
                if state["available"]:
                    # Vérifier si une route doit démarrer
                    if self.routes_by_vehicle[veh_nom]:
                        next_route = self.routes_by_vehicle[veh_nom][0]
                        # Convertir l'heure de départ en datetime
                        route_departure = datetime.datetime.combine(simulation_clock.date(), next_route.departure_time)
                        if simulation_clock >= route_departure:
                            # Démarrer la route
                            state["current_route"] = self.routes_by_vehicle[veh_nom].pop(0)
                            state["current_step"] = 0
                            if state["current_route"].steps:
                                next_step = state["current_route"].steps[0].entrepot
                                vehicle_obj = next(v for v in st.session_state.fleet if v.nom == veh_nom)
                                start_warehouse = vehicle_obj.storage_point
                                state["time_remaining"],cost ,emission ,distance = self.compute_segment_time(
                                    vehicle=vehicle_obj,
                                    start=start_warehouse,
                                    end=next_step,
                                    load=state["current_load"]
                                )
                                state["travel_cost"] += cost 
                                state["travel_emission"] += emission
                                state["distance"] += distance

                                state["available"] = False
                                self.events.append({
                                    "time": simulation_clock,
                                    "vehicle": veh_nom,
                                    "event": f"Démarrage de la route vers {next_step}"
                                })
                else:
                    # Le véhicule est en cours d'exécution d'une route, décrémenter le temps restant
                    state["time_remaining"] -= self.time_step
                    if state["time_remaining"] <= datetime.timedelta(0):
                        current_route = state["current_route"]
                        current_step_index = state["current_step"]
                        current_step = current_route.steps[current_step_index]
                        arrived_warehouse = current_step.entrepot

                        # Enregistrer l'arrivée à l'entrepôt
                        self.events.append({
                            "time": simulation_clock,
                            "vehicle": veh_nom,
                            "event": f"Arrivée à {arrived_warehouse}"
                        })
                        state["current_step"] += 1

                        # Pour les opérations de chargement, vérifier la disponibilité dans simulation_orders
                        if any(op.type == "Charger" for op in current_step.operations):
                            if not self.is_stock_available(arrived_warehouse, current_step):
                                # Le stock n'est pas suffisant : le véhicule attend
                                self.events.append({
                                    "time": simulation_clock,
                                    "vehicle": veh_nom,
                                    "event": f"Attente de chargement à {arrived_warehouse}"
                                })
                                # On prolonge le temps d'attente avant de revérifier (par exemple, 5 minutes)
                                state["time_remaining"] = datetime.timedelta(minutes=5)
                                continue

                        # SIMULER L'EXÉCUTION DES OPÉRATIONS SUR L'ÉTAT DES COMMANDES ORIGINALES
                        for op in current_step.operations:
                            if op.type == "Charger":
                                self.simulation_orders.update_warehouse_content(arrived_warehouse, op.produit, -op.quantite)
                                self.events.append({
                                    "time": simulation_clock,
                                    "vehicle": veh_nom,
                                    "event": f"Chargement de {op.quantite} de {op.produit} à {arrived_warehouse}"
                                })
                                state["current_load"] += op.quantite * self.simulation_orders.orders[op.produit].content['poids_kg']

                            elif op.type == "Décharger":
                                self.simulation_orders.update_warehouse_content(arrived_warehouse, op.produit, op.quantite)
                                self.events.append({
                                    "time": simulation_clock,
                                    "vehicle": veh_nom,
                                    "event": f"Déchargement de {op.quantite} de {op.produit} à {arrived_warehouse}"
                                })
                                state["current_load"] -= op.quantite * self.simulation_orders.orders[op.produit].content['poids_kg']


                        # S'il reste d'autres étapes, calculer le temps pour le prochain segment
                        if state["current_step"] < len(current_route.steps):
                            start_warehouse = arrived_warehouse
                            next_warehouse = current_route.steps[state["current_step"]].entrepot
                            vehicle_obj = next(v for v in st.session_state.fleet if v.nom == veh_nom)
                            state["time_remaining"], cost, emission, distance  = self.compute_segment_time(
                                vehicle=vehicle_obj,
                                start=start_warehouse,
                                end=next_warehouse,
                                load=state["current_load"]
                            )

                            state["travel_cost"] += cost 
                            state["travel_emission"] += emission
                            state["distance"] += distance

                            self.events.append({
                                "time": simulation_clock,
                                "vehicle": veh_nom,
                                "event": f"Départ de {start_warehouse} vers {next_warehouse}"
                            })
                        else:
                            # Fin de la route : le véhicule redevient disponible
                            state["available"] = True
                            state["current_route"] = None
                            self.events.append({
                                "time": simulation_clock,
                                "vehicle": veh_nom,
                                "event": "Fin de route"
                            })
            # Incrémenter l'horloge de simulation
            simulation_clock += self.time_step

        # Trier et retourner les événements une fois la simulation terminée
        self.events.sort(key=lambda e: e["time"])
        return self.events
    
    def generate_route_reports(self):
        reports = []
        for route in st.session_state.routes:
            report = {
                "Vehicle": route.transport,
                "Departure Time": route.departure_time,
                "Segments": route.get_segment_impacts()
            }
            reports.append(report)
        return reports

    # Fonction pour verifier si les commandes arrivent a destination (on regarde si elles sont arrivé au point de livraison)
    def check_deliveries(self):
        delivery_status = {}
        for order_id, order in st.session_state.Orders.orders.items():
            end_warehouse = order.end
            required_delivery_time = order.delivery_time
            # delivered = any(
            #     event["event"].startswith(f"Déchargement de {order_id}") and event["event"].endswith(f"à {end_warehouse}")
            #     for event in self.events
            # )
            delivered = False
            quantity_delivered = 0
            pattern = re.compile(rf"Déchargement de ([\d.]+) de {order_id} à {end_warehouse}")

            for event in self.events:
                match = pattern.search(event["event"])
                
                if match:
                    delivered = True
                    quantity_delivered += float(match.group(1))
                    actual_delivery_time = event["time"] # On garde l'heure de la derniere livraison au point de livraison

            if delivered and quantity_delivered >= 0.99:
                if actual_delivery_time <= required_delivery_time:
                    delivery_status[order_id] = "on_time"
                else: 
                    delivery_status[order_id] = "late"
            else:
                delivery_status[order_id] = "not_delivered"

        return delivery_status


    def display_simulation(self):
        # Affichage des événements (par exemple via un DataFrame)
        import pandas as pd
        df = pd.DataFrame(self.events)
        df['time'] = df['time'].apply(lambda t: t.strftime("%H:%M:%S"))
        st.dataframe(df)
    
