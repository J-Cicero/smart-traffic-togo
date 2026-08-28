# main.py - Orchestrateur principal du carrefour intelligent (Lome) - Multi-topologies (3 voies / 4 voies)

import os
import time

from config import (
    CAMERA_SOURCES,
    INTERSECTION_TYPE,
    SERVER_CONFIG,
    TIME_LIMITS,
    TOPOLOGY_CONFIGS,
    VISION_CONFIG,
)
from modules.api import GLOBAL_STATE, start_api_server_background
from modules.controller import run_traffic_cycle
from modules.detector import detect_and_count_vehicles, load_yolo_model
from modules.logger import TrafficLogger

try:
    import cv2
except Exception:
    cv2 = None


YELLOW_SECONDS = 3
ALL_RED_SECONDS = 2
MODEL_PATH = "yolov8n.pt"

VEHICLE_CLASSES = [
    "moto",
    "tricycle_passager",
    "tricycle_cargo",
    "voiture",
    "minibus",
    "bus",
    "camion",
    "urgence",
]


def get_current_topology() -> dict:
    """Retourne la configuration de topologie active (3 voies T ou 4 voies Croix)."""
    return TOPOLOGY_CONFIGS.get(INTERSECTION_TYPE, TOPOLOGY_CONFIGS["4_WAY_CROSS"])


def empty_vehicle_counts() -> dict:
    """Construit un dictionnaire de comptage initialise a zero."""
    return {vehicle_class: 0 for vehicle_class in VEHICLE_CLASSES}


def create_empty_observation_buffer(lanes: list[str]) -> dict:
    """Initialise dynamiquement les buffers d'observation selon la liste des voies active."""
    return {lane: empty_vehicle_counts() for lane in lanes}


def aggregate_lane_counts(observed_counts: dict, lane_list: list[str], mode: str = "sum") -> dict:
    """
    Fusionne les comptages d'un groupe de voies.
    - mode='sum': Additionne les comptages (utilise pour evaluer les voies rouges cumulées).
    - mode='max': Prend le MAX par categorie (utilise pour les voies vertes paralleles, car elles s'ecoulent en meme temps).
    """
    aggregated = empty_vehicle_counts()
    if not lane_list:
        return aggregated

    if mode == "max":
        for vehicle_class in VEHICLE_CLASSES:
            max_val = 0
            for lane in lane_list:
                val = observed_counts.get(lane, {}).get(vehicle_class, 0)
                if val > max_val:
                    max_val = val
            aggregated[vehicle_class] = max_val
    else:
        for lane in lane_list:
            counts = observed_counts.get(lane, {})
            for vehicle_class, val in counts.items():
                aggregated[vehicle_class] += val

    return aggregated


def create_vision_context(lanes: list[str]) -> dict:
    """Initialise YOLO et les captures vidéo pour la liste des voies actives."""
    context = {
        "model": None,
        "captures": {},
        "camera_ok": {lane: False for lane in lanes},
    }

    if cv2 is None:
        print("[WARN] OpenCV indisponible. Bascule en observation simulee.")
        return context

    try:
        context["model"] = load_yolo_model(MODEL_PATH)
        print(f"[INFO] Modele YOLO charge avec succes: {MODEL_PATH}")
    except Exception as exc:
        print(f"[WARN] Chargement YOLO impossible ({exc}). Bascule en observation simulee.")
        return context

    for lane in lanes:
        source = CAMERA_SOURCES.get(lane, 0)
        capture = cv2.VideoCapture(source)
        if capture.isOpened():
            context["captures"][lane] = capture
            context["camera_ok"][lane] = True
            print(f"[INFO] Source video active pour {lane} (source={source})")
        else:
            context["captures"][lane] = capture
            print(f"[WARN] Source video indisponible pour {lane} (source={source}). Repli simulation sur cette voie.")

    return context


def release_vision_context(context: dict) -> None:
    for capture in context.get("captures", {}).values():
        try:
            capture.release()
        except Exception:
            pass


def normalize_counts(raw_counts: dict) -> dict:
    normalized = empty_vehicle_counts()
    for vehicle_class in VEHICLE_CLASSES:
        normalized[vehicle_class] = max(0, int(raw_counts.get(vehicle_class, 0)))
    return normalized


def observe_lane_from_camera(lane: str, context: dict) -> dict | None:
    model = context.get("model")
    capture = context.get("captures", {}).get(lane)
    lane_is_available = context.get("camera_ok", {}).get(lane, False)
    if model is None or capture is None or not lane_is_available:
        return None

    ok, frame = capture.read()
    if not ok:
        # Rembobiner le flux si c'est un fichier video
        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, frame = capture.read()
        if not ok:
            context["camera_ok"][lane] = False
            print(f"[WARN] Lecture video echouee sur {lane}. Repli simulation.")
            return None

    try:
        detected = detect_and_count_vehicles(frame, model, lane_name=lane)
    except Exception as exc:
        context["camera_ok"][lane] = False
        print(f"[WARN] Inference YOLO echouee sur {lane} ({exc}). Repli simulation.")
        return None

    return normalize_counts(detected)


def accumulate_simulated_arrivals(observed_counts: dict, lanes_to_observe: list[str]) -> None:
    arrival_defaults = {"moto": 1, "tricycle_passager": 1, "voiture": 1}
    for lane in lanes_to_observe:
        if lane in observed_counts:
            for vehicle_class, amount in arrival_defaults.items():
                observed_counts[lane][vehicle_class] += amount


def merge_snapshot_into_queue(observed_counts: dict, lane: str, snapshot_counts: dict) -> None:
    for vehicle_class in VEHICLE_CLASSES:
        observed_counts[lane][vehicle_class] = max(
            observed_counts[lane][vehicle_class],
            snapshot_counts.get(vehicle_class, 0),
        )


def observe_red_lanes(observed_counts: dict, red_lanes: list[str], context: dict) -> None:
    for lane in red_lanes:
        snapshot = observe_lane_from_camera(lane, context)
        if snapshot is None:
            accumulate_simulated_arrivals(observed_counts, [lane])
        else:
            merge_snapshot_into_queue(observed_counts, lane, snapshot)


def clear_phase_buffer(observed_counts: dict, green_lanes: list[str]) -> None:
    """Remet a zero la file des voies qui viennent de bénéficier de leur feu vert."""
    for lane in green_lanes:
        observed_counts[lane] = empty_vehicle_counts()


def is_phase_camera_active(green_lanes: list[str], context: dict) -> bool:
    """
    Verifie si au moins une camera de la phase est fonctionnelle.
    Si 1 camera sur 2 fonctionne, le systeme reste dynamique sur cette voie active.
    """
    if context.get("model") is None:
        return False
    return any(context.get("camera_ok", {}).get(lane, False) for lane in green_lanes)


def run_phase_green(
    phase_info: dict,
    observed_counts: dict,
    context: dict,
    logger: TrafficLogger,
    phase_previous_loads: dict,
) -> None:
    """Execute la phase verte pour un groupe de voies et observe les voies au rouge."""
    phase_name = phase_info["name"]
    green_lanes = phase_info["green_lanes"]
    red_lanes = phase_info["red_lanes"]

    # Utilisation du mode 'max' car les voies vertes d'un meme axe s'ecoulent en parallele
    active_counts = aggregate_lane_counts(observed_counts, green_lanes, mode="max")
    camera_active = is_phase_camera_active(green_lanes, context)
    prev_load = phase_previous_loads.get(phase_info["phase_id"])

    green_duration, meta = run_traffic_cycle(
        lane_name=phase_name,
        vehicle_counts=active_counts,
        camera_active=camera_active,
        previous_load=prev_load,
    )

    phase_previous_loads[phase_info["phase_id"]] = meta.get("charge_score", 0.0)

    print("\n============================================================")
    print(f"[PHASE VERTE] {phase_name} ({', '.join(green_lanes)})")
    print(f"[VOIES VERTES] {', '.join(green_lanes)} = VERT")
    print(f"[VOIES ROUGES] {', '.join(red_lanes)} = ROUGE")
    print(f"[COMPTAGES VOIES VERTES (MAX PARALLELE)] {active_counts}")
    print(f"[DUREE VERTE] {green_duration}s (Regle: {meta.get('applied_rule')})")

    logger.log_event("GREEN_PHASE_START", {
        "phase": phase_name,
        "green_lanes": green_lanes,
        "duration": green_duration,
        "counts": active_counts,
        "meta": meta,
    })

    # Reinitialiser le buffer de l'axe au vert
    clear_phase_buffer(observed_counts, green_lanes)

    for remaining in range(green_duration, 0, -1):
        observe_red_lanes(observed_counts, red_lanes, context)
        pending_red_counts = aggregate_lane_counts(observed_counts, red_lanes, mode="sum")

        # Verification d'urgence dynamique : Interruption si un vehicule d'urgence arrive sur voie rouge
        if pending_red_counts.get("urgence", 0) > 0:
            print(f"\n[ALERTE URGENCE] Vehicule d'urgence detecte sur voie rouge ! Interruption de la phase verte en cours.")
            logger.log_event("EMERGENCY_INTERRUPTION", {
                "phase": phase_name,
                "remaining_seconds": remaining,
                "red_counts": pending_red_counts,
            })
            break

        GLOBAL_STATE.update_state(
            active_axis=phase_name,
            phase="VERT",
            remaining_seconds=remaining,
            observed_counts=observed_counts,
            lane_camera_ok=context.get("camera_ok", {}),
            last_cycle_metadata=meta,
        )

        print(
            f"[VERT {phase_name}] restant={remaining:02d}s | "
            f"[OBSERVATION VOIES ROUGES] charge en attente: {pending_red_counts}"
        )
        time.sleep(1)


def run_phase_transition(
    phase_info: dict,
    all_lanes: list[str],
    observed_counts: dict,
    context: dict,
    logger: TrafficLogger,
) -> None:
    """Applique la transition Jaune + Tous au Rouge."""
    phase_name = phase_info["name"]
    green_lanes = phase_info["green_lanes"]
    red_lanes = phase_info["red_lanes"]

    print("\n------------------------------------------------------------")
    print(f"[TRANSITION] Fin de {phase_name}: passage au JAUNE ({', '.join(green_lanes)})")
    logger.log_event("YELLOW_PHASE", {"phase": phase_name, "duration": YELLOW_SECONDS})

    for remaining in range(YELLOW_SECONDS, 0, -1):
        observe_red_lanes(observed_counts, red_lanes, context)
        GLOBAL_STATE.update_state(
            active_axis=phase_name,
            phase="JAUNE",
            remaining_seconds=remaining,
            observed_counts=observed_counts,
        )
        print(f"[JAUNE {phase_name}] restant={remaining:02d}s")
        time.sleep(1)

    print("[SECURITE] TOUS AU ROUGE pour degagement du carrefour")
    logger.log_event("ALL_RED_PHASE", {"duration": ALL_RED_SECONDS})

    for remaining in range(ALL_RED_SECONDS, 0, -1):
        observe_red_lanes(observed_counts, all_lanes, context)
        GLOBAL_STATE.update_state(
            active_axis="AUCUN (SECURITE)",
            phase="TOUS_ROUGE",
            remaining_seconds=remaining,
            observed_counts=observed_counts,
        )
        print(f"[TOUS ROUGE] restant={remaining:02d}s")
        time.sleep(1)


def bootstrap_initial_observation(observed_counts: dict) -> None:
    for lane in observed_counts:
        observed_counts[lane].update({"moto": 5, "tricycle_passager": 2, "voiture": 3})


def main() -> None:
    topology = get_current_topology()
    print("=== Demarrage du systeme de regulation intelligente - Smart Traffic Lome ===")
    print(f"Topologie active: {topology['name']} ({len(topology['lanes'])} voies)")
    print("Phases configurees : " + ", ".join(p['name'] for p in topology['phases']))

    logger = TrafficLogger()
    logger.log_event("SYSTEM_BOOT", {"topology": topology["name"], "lanes": topology["lanes"]})

    if SERVER_CONFIG.get("ENABLE_API"):
        start_api_server_background(
            host=SERVER_CONFIG.get("HOST", "0.0.0.0"),
            port=SERVER_CONFIG.get("PORT", 8080),
        )

    observed_counts = create_empty_observation_buffer(topology["lanes"])
    bootstrap_initial_observation(observed_counts)
    vision_context = create_vision_context(topology["lanes"])
    phase_previous_loads = {}

    try:
        while True:
            for phase_info in topology["phases"]:
                run_phase_green(phase_info, observed_counts, vision_context, logger, phase_previous_loads)
                run_phase_transition(phase_info, topology["lanes"], observed_counts, vision_context, logger)

    except KeyboardInterrupt:
        print("\n[INFO] Arret securise du systeme demande par l'operateur.")
        logger.log_event("SYSTEM_SHUTDOWN", {"reason": "KEYBOARD_INTERRUPT"})
    finally:
        release_vision_context(vision_context)


if __name__ == "__main__":
    main()