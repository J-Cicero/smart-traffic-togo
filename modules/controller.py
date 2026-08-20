# modules/controller.py - Gestion de la machine a etats et securite des feux

import time
from config import TIME_LIMITS, FAILSAFE_CONFIG
from modules.calculator import calculate_green_light_duration


def run_traffic_cycle(lane_name: str, vehicle_counts: dict, camera_active: bool = True) -> int:
    """
    Determine la duree securisee du feu vert pour une voie donnee,
    en integrant la verification des limites et le mode de repli (Fail-Safe).
    """
    # 1. Verification du mode de repli (Securite en cas de panne de la camera ou de l'IA)
    if not camera_active:
        print(f"[ALERTE] Camera ou IA hors service sur la voie {lane_name}. Application du mode Fail-Safe.")
        if FAILSAFE_CONFIG["fallback_action"] == "fixed_timer":
            return FAILSAFE_CONFIG["default_duration"]
        return TIME_LIMITS["T_MIN"]  # Repli minimal par defaut

    try:
        # 2. Calcul normal de la duree via le moteur PCU et les seuils
        green_duration = calculate_green_light_duration(vehicle_counts)
        print(f"[INFO] Voie {lane_name} - Vehicules detectes : {vehicle_counts}")
        print(f"[INFO] Duree du feu vert allouee : {green_duration} secondes")
        return green_duration

    except Exception as e:
        # 3. En cas d'erreur de calcul inattendue, application d'un repli securise
        print(f"[ERREUR] Echec du calcul pour la voie {lane_name} : {e}")
        return TIME_LIMITS["T_MIN"]