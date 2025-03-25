# Représente un véhicule de transport avec ses caractéristiques techniques et économiques
class Vehicle:
    # Initialise un véhicule avec ses propriétés caractéristiques
    # Paramètres:
    # - nom: nom du véhicule
    # - charge_max_emport_kg: charge maximale en kg
    # - volume_max_emport_m3: volume maximal en m³
    # - autonomie_charge_km: distance maximale parcourable avec une charge
    # - vitesse_max: vitesse maximale en km/h
    # - impact_km_charge_co2, impact_km_vide_co2: impact CO2 par km (chargé/vide)
    # - crit_air: indice de qualité de l'air (classification réglementaire)
    # - cout_utilisation_km_charge, cout_utilisation_km_vide: coût par km (chargé/vide)
    # - cout_fixe_utilisation_journalier: coût fixe journalier
    # - storage_point: point de stockage/dépôt du véhicule
    def __init__(self, nom, charge_max_emport_kg, volume_max_emport_m3, 
                 autonomie_charge_km, vitesse_max, impact_km_charge_co2,
                 impact_km_vide_co2, crit_air, cout_utilisation_km_charge,
                 cout_utilisation_km_vide, cout_fixe_utilisation_journalier,
                 storage_point):
        
        self.nom = nom

        self.charge_max_emport_kg = charge_max_emport_kg
        self.volume_max_emport_m3 = volume_max_emport_m3

        self.autonomie_charge_km = autonomie_charge_km
        self.vitesse_max = vitesse_max

        self.impact_km_charge_co2 = impact_km_charge_co2
        self.impact_km_vide_co2 = impact_km_vide_co2

        self.crit_air = crit_air

        self.cout_utilisation_km_charge = cout_utilisation_km_charge
        self.cout_utilisation_km_vide = cout_utilisation_km_vide
        self.cout_fixe_utilisation_journalier = cout_fixe_utilisation_journalier

        self.storage_point = storage_point
        
        # Dictionnaire pour stocker le contenu transporté par le véhicule
        self.content = {}

    # Calcule le coût par kilomètre en fonction de la charge
    # Paramètres:
    # - load: charge actuelle en kg
    # Retourne:
    # - cout: coût au kilomètre interpolé selon la charge
    def travel_cost_km(self, load):
        # Calcul du coefficient de charge (entre 0 et 1)
        coef = load  /  self.charge_max_emport_kg 
        # Interpolation linéaire entre cout_vide et cout_charge
        # Cette formule permet d'avoir un coût qui varie proportionnellement 
        # en fonction du taux de remplissage du véhicule
        cout =  (self.cout_utilisation_km_charge - self.cout_utilisation_km_vide) * coef + self.cout_utilisation_km_vide
        return cout 
    
    # Calcule l'émission CO2 par kilomètre en fonction de la charge
    # Paramètres:
    # - load: charge actuelle en kg
    # Retourne:
    # - cout: émission CO2 au kilomètre interpolée selon la charge
    def travel_emission_km(self, load):
        # Utilisation du même principe d'interpolation linéaire que pour le coût
        coef = load  /  self.charge_max_emport_kg 
        # Plus le véhicule est chargé, plus il émet de CO2
        cout =  (self.impact_km_charge_co2 - self.impact_km_vide_co2) * coef + self.impact_km_vide_co2

        return cout