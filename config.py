# config.py - Parametres globaux pour le systeme de gestion du trafic a Lome

# Coefficients PCU (Passenger Car Unit) valides pour le trafic local
PCU_WEIGHTS = {
    "moto": 0.30,
    "tricycle_passager": 0.55,
    "tricycle_cargo": 0.65,
    "voiture": 1.00,  # Regroupe voitures et taxis
    "minibus": 2.00,
    "bus": 2.75,
    "camion": 3.50,
}

# Seuils de securite temporelle (en secondes) pour les feux tricolores
TIME_LIMITS = {
    "T_MIN": 15,  # Temps minimal syndical
    "T_MAX": 75,  # Plafond maximal pour eviter l'asphyxie
    "T_BASE": 10,  # Constante de depart
    "K_FACTOR": 2.5,  # Facteur de conversion de la charge en secondes
}

# Mode de repli de securite en cas de panne camera/IA
FAILSAFE_CONFIG = {
    "fallback_action": "fixed_timer",
    "default_duration": 30,
}