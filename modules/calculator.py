# modules/calculator.py - Moteur de calcul de charge PCU et de duree de feu vert

from config import PCU_WEIGHTS, TIME_LIMITS


def compute_traffic_load(vehicle_counts: dict) -> float:
    """
    Calcule le score de charge total (S) d'une voie en appliquant
    les coefficients PCU a chaque categorie de vehicule detectee.

    Exemple d'entree : {"moto": 12, "voiture": 4, "camion": 1}
    """
    total_load = 0.0

    for vehicle_class, count in vehicle_counts.items():
        if vehicle_class in PCU_WEIGHTS:
            total_load += count * PCU_WEIGHTS[vehicle_class]

    return round(total_load, 2)


def calculate_green_light_duration(vehicle_counts: dict) -> int:
    """
    Transforme le score de charge S en une duree de feu vert (en secondes),
    encadree obligatoirement par les seuils T_MIN et T_MAX pour des raisons de securite.
    """
    # 1. Calcul du score de charge
    charge_score = compute_traffic_load(vehicle_counts)

    # 2. Application de la formule dynamique : T = T_base + (Charge * K_factor)
    t_base = TIME_LIMITS["T_BASE"]
    k_factor = TIME_LIMITS["K_FACTOR"]
    calculated_time = t_base + (charge_score * k_factor)

    # 3. Application des gardes-fous stricts de securite (T_min <= T <= T_max)
    t_min = TIME_LIMITS["T_MIN"]
    t_max = TIME_LIMITS["T_MAX"]

    final_duration = max(t_min, min(int(calculated_time), t_max))

    return final_duration