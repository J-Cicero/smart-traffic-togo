# modules/controller.py - Gestion de la machine a etats, securite et priorites

from config import FAILSAFE_CONFIG, TIME_LIMITS
from modules.calculator import calculate_green_light_duration


def run_traffic_cycle(
    lane_name: str,
    vehicle_counts: dict,
    camera_active: bool = True,
    previous_load: float | None = None,
) -> tuple[int, dict]:
    """
    Determine la duree securisee du feu vert pour une voie/axe donnee.
    Integre le mode Fail-Safe, la priorite d'urgence et l'encadrement strict.
    Retourne (duree_secondes, info_dict).
    """
    # 1. Mode Fail-Safe (secours en cas de panne camera ou IA)
    if not camera_active:
        action = FAILSAFE_CONFIG.get("fallback_action", "fixed_timer")
        duration = FAILSAFE_CONFIG.get("default_duration", 30) if action == "fixed_timer" else TIME_LIMITS["T_MIN"]
        print(f"[ALERTE FAILSAFE] Defaut camera/IA sur {lane_name}. Application duree secours: {duration}s.")
        return duration, {
            "is_failsafe": True,
            "is_emergency": False,
            "applied_rule": "FAILSAFE_FALLBACK",
            "charge_score": 0.0,
        }

    try:
        # 2. Calcul dynamique via le moteur PCU / urgence
        duration, meta = calculate_green_light_duration(vehicle_counts, previous_load=previous_load, use_smoothing=True)
        meta["is_failsafe"] = False

        if meta.get("is_emergency"):
            print(f"[URGENCE PREEMPTION] Vehicule d'urgence detecte sur {lane_name}! Feu vert prioritaire: {duration}s")
        else:
            print(f"[INFO CONTROL] {lane_name} - Charge PCU: {meta['charge_score']} | Duree allouee: {duration}s")

        return duration, meta

    except Exception as e:
        # 3. Repli de secours universel en cas d'erreur logicielle imprevue
        print(f"[ERREUR CRITIQUE] Echec du controleur sur {lane_name} ({e}). Reprise securisee minimal {TIME_LIMITS['T_MIN']}s.")
        return TIME_LIMITS["T_MIN"], {
            "is_failsafe": True,
            "is_emergency": False,
            "applied_rule": "CRITICAL_EXCEPTIONAL_FALLBACK",
            "charge_score": 0.0,
            "error": str(e),
        }