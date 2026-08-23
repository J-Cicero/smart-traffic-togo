# modules/calculator.py - Moteur de calcul PCU, urgence et lissage temporel

from config import EMERGENCY_CLASSES, EMERGENCY_GREEN_TIME, PCU_WEIGHTS, SMOOTHING_ALPHA, TIME_LIMITS


def check_emergency_priority(vehicle_counts: dict) -> tuple[bool, int]:
    """
    Verifie si des vehicules d'urgence sont presents dans la voie/axe.
    Retourne (True, EMERGENCY_GREEN_TIME) si detecte, sinon (False, 0).
    """
    for em_cls in EMERGENCY_CLASSES:
        if vehicle_counts.get(em_cls, 0) > 0:
            return True, EMERGENCY_GREEN_TIME
    return False, 0


def compute_traffic_load(vehicle_counts: dict) -> float:
    """
    Calcule le score de charge total (S) d'une voie en appliquant
    les coefficients PCU a chaque categorie de vehicule detectee.
    """
    total_load = 0.0

    for vehicle_class, count in vehicle_counts.items():
        if vehicle_class in PCU_WEIGHTS:
            total_load += count * PCU_WEIGHTS[vehicle_class]

    return round(total_load, 2)


def compute_smoothed_load(current_counts: dict, previous_load: float | None = None, alpha: float = SMOOTHING_ALPHA) -> float:
    """
    Applique un lissage par moyenne mobile exponentielle (EMA) sur la charge calculée
    pour eviter les fluctuations brutales dues au bruit d'infereance.
    """
    raw_load = compute_traffic_load(current_counts)
    if previous_load is None:
        return raw_load

    smoothed = alpha * raw_load + (1 - alpha) * previous_load
    return round(smoothed, 2)


def calculate_green_light_duration(
    vehicle_counts: dict,
    previous_load: float | None = None,
    use_smoothing: bool = False,
) -> tuple[int, dict]:
    """
    Transforme le comptage de vehicules en une duree de feu vert (en secondes).
    Gere l'urgence prioritaire, le lissage et l'encadrement strict (T_MIN <= T <= T_MAX).
    Retourne un tuple (duree_secondes, metadata_dict).
    """
    # 1. Verification priorite vehicule d'urgence
    has_emergency, emergency_duration = check_emergency_priority(vehicle_counts)
    if has_emergency:
        return emergency_duration, {
            "is_emergency": True,
            "charge_score": compute_traffic_load(vehicle_counts),
            "applied_rule": "EMERGENCY_PREEMPTION",
        }

    # 2. Calcul du score de charge (avec ou sans lissage)
    if use_smoothing and previous_load is not None:
        charge_score = compute_smoothed_load(vehicle_counts, previous_load)
    else:
        charge_score = compute_traffic_load(vehicle_counts)

    # 3. Formule dynamique : T = T_base + (Charge * K_factor)
    t_base = TIME_LIMITS["T_BASE"]
    k_factor = TIME_LIMITS["K_FACTOR"]
    calculated_time = t_base + (charge_score * k_factor)

    # 4. Gardes-fous stricts de securite
    t_min = TIME_LIMITS["T_MIN"]
    t_max = TIME_LIMITS["T_MAX"]

    final_duration = max(t_min, min(int(calculated_time), t_max))

    return final_duration, {
        "is_emergency": False,
        "charge_score": charge_score,
        "calculated_time": round(calculated_time, 2),
        "applied_rule": "STANDARD_PCU_DYNAMIC",
    }