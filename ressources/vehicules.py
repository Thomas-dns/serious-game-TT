class Vehicle:
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

        self.is_used = False
        self.storage_point = storage_point
        
        self.content = {}

    # Renvois le cout par kilomètre
    def travel_cost_km(self, load):
        # Calcul du coefficient de charge (entre 0 et 1)
        coef = load  /  self.charge_max_emport_kg 
        # Interpolation linéaire entre cout_vide et cout_charge
        cout =  (self.cout_utilisation_km_charge - self.cout_utilisation_km_vide) * coef + self.cout_utilisation_km_vide
        return cout 
    
    # Renvois le score d'impacte par kilomètre
    def travel_emission_km(self, load):
        coef = load  /  self.charge_max_emport_kg 
        cout =  (self.impact_km_charge_co2 - self.impact_km_vide_co2) * coef + self.impact_km_vide_co2

        return cout
    
    
