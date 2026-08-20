# main.py - Orchestrateur principal du carrefour intelligent (Lome)

import os
import time

from config import TIME_LIMITS
from modules.controller import run_traffic_cycle
from modules.detector import detect_and_count_vehicles, load_yolo_model

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
]

AXIS_LANES = {
    "Axe Nord-Sud": ("Voie Nord", "Voie Sud"),
    "Axe Est-Ouest": ("Voie Est", "Voie Ouest"),
}

# Sources video par voie (index webcam locale ou URL/chemin de flux).
CAMERA_SOURCES = {
    "Voie Nord": 0,
    "Voie Sud": 1,
    "Voie Est": 2,
    "Voie Ouest": 3,
}

# Repli simulation: arrivees par seconde si la vision est indisponible sur une voie.
ARRIVAL_PER_SECOND = {
    "Voie Nord": {"moto": 1, "tricycle_passager": 1, "voiture": 1},
    "Voie Sud": {"moto": 2, "tricycle_passager": 1, "voiture": 1, "camion": 1},
    "Voie Est": {"moto": 1, "voiture": 1},
    "Voie Ouest": {"moto": 1, "tricycle_cargo": 1, "voiture": 1},
}


def empty_vehicle_counts() -> dict:
    """Construit un dictionnaire de comptage initialise a zero."""
    return {vehicle_class: 0 for vehicle_class in VEHICLE_CLASSES}


def create_empty_observation_buffer() -> dict:
    """Initialise le buffer d'observation par voie (utilise pendant les phases rouges)."""
    return {
        "Voie Nord": empty_vehicle_counts(),
        "Voie Sud": empty_vehicle_counts(),
        "Voie Est": empty_vehicle_counts(),
        "Voie Ouest": empty_vehicle_counts(),
    }


def aggregate_axis_counts(first_lane_counts: dict, second_lane_counts: dict) -> dict:
    """Fusionne les comptages de deux voies d'un meme axe (Nord-Sud ou Est-Ouest)."""
    axis_counts: dict = {}
    all_classes = set(first_lane_counts) | set(second_lane_counts)
    for vehicle_class in all_classes:
        axis_counts[vehicle_class] = first_lane_counts.get(vehicle_class, 0) + second_lane_counts.get(vehicle_class, 0)
    return axis_counts


def create_vision_context() -> dict:
    """Initialise YOLO et les captures camera avec mode repli automatique."""
    context = {
        "model": None,
        "captures": {},
        "camera_ok": {lane: False for lane in CAMERA_SOURCES},
    }

    if cv2 is None:
        print("[WARN] OpenCV indisponible. Bascule en observation simulee.")
        return context

    if not os.path.exists(MODEL_PATH):
        print(
            f"[WARN] Modele YOLO introuvable ({MODEL_PATH}). "
            "Placez un fichier local puis relancez pour activer la vision."
        )
        return context

    try:
        context["model"] = load_yolo_model(MODEL_PATH)
        print(f"[INFO] Modele YOLO charge: {MODEL_PATH}")
    except Exception as exc:
        print(f"[WARN] Chargement YOLO impossible ({exc}). Bascule en observation simulee.")
        return context

    for lane, source in CAMERA_SOURCES.items():
        capture = cv2.VideoCapture(source)
        if capture.isOpened():
            context["captures"][lane] = capture
            context["camera_ok"][lane] = True
            print(f"[INFO] Camera active pour {lane} (source={source})")
        else:
            context["captures"][lane] = capture
            print(f"[WARN] Camera indisponible pour {lane} (source={source}). Repli simulation sur cette voie.")

    return context


def release_vision_context(context: dict) -> None:
    """Libere proprement les ressources camera en fin d'execution."""
    for capture in context.get("captures", {}).values():
        try:
            capture.release()
        except Exception:
            pass


def normalize_counts(raw_counts: dict) -> dict:
    """Garantit la presence des classes attendues avec valeurs entieres non negatives."""
    normalized = empty_vehicle_counts()
    for vehicle_class in VEHICLE_CLASSES:
        normalized[vehicle_class] = max(0, int(raw_counts.get(vehicle_class, 0)))
    return normalized


def observe_lane_from_camera(lane: str, context: dict) -> dict | None:
    """Retourne un snapshot de comptage pour une voie via camera+YOLO, sinon None."""
    model = context.get("model")
    capture = context.get("captures", {}).get(lane)
    lane_is_available = context.get("camera_ok", {}).get(lane, False)
    if model is None or capture is None or not lane_is_available:
        return None

    ok, frame = capture.read()
    if not ok:
        context["camera_ok"][lane] = False
        print(f"[WARN] Lecture camera echouee sur {lane}. Passage en mode repli simulation pour cette voie.")
        return None

    try:
        detected = detect_and_count_vehicles(frame, model)
    except Exception as exc:
        context["camera_ok"][lane] = False
        print(f"[WARN] Inference YOLO echouee sur {lane} ({exc}). Repli simulation pour cette voie.")
        return None

    return normalize_counts(detected)


def accumulate_simulated_arrivals(observed_counts: dict, lanes_to_observe: tuple[str, ...]) -> None:
    """Ajoute des arrivees simulees par seconde (repli si camera indisponible)."""
    for lane in lanes_to_observe:
        arrivals = ARRIVAL_PER_SECOND.get(lane, {})
        for vehicle_class, amount in arrivals.items():
            observed_counts[lane][vehicle_class] += amount


def merge_snapshot_into_queue(observed_counts: dict, lane: str, snapshot_counts: dict) -> None:
    """Met a jour la file observee: on garde le max pour eviter le double comptage brut frame-a-frame."""
    for vehicle_class in VEHICLE_CLASSES:
        observed_counts[lane][vehicle_class] = max(
            observed_counts[lane][vehicle_class],
            snapshot_counts.get(vehicle_class, 0),
        )


def observe_red_lanes(observed_counts: dict, lanes_to_observe: tuple[str, ...], context: dict) -> None:
    """Observe les voies au rouge via YOLO; si indisponible, bascule sur la simulation pour la voie concernee."""
    for lane in lanes_to_observe:
        snapshot = observe_lane_from_camera(lane, context)
        if snapshot is None:
            accumulate_simulated_arrivals(observed_counts, (lane,))
        else:
            merge_snapshot_into_queue(observed_counts, lane, snapshot)


def clear_axis_buffer(observed_counts: dict, axis_lanes: tuple[str, str]) -> None:
    """Remet a zero les compteurs de l'axe qui vient d'obtenir son feu vert."""
    lane_a, lane_b = axis_lanes
    observed_counts[lane_a] = empty_vehicle_counts()
    observed_counts[lane_b] = empty_vehicle_counts()


def is_axis_camera_active(axis_name: str, context: dict) -> bool:
    """Retourne True si les deux voies de l'axe sont actuellement observables par camera+YOLO."""
    lane_a, lane_b = AXIS_LANES[axis_name]
    return context.get("model") is not None and context.get("camera_ok", {}).get(lane_a, False) and context.get("camera_ok", {}).get(lane_b, False)


def run_green_phase(active_axis_name: str, opposite_axis_name: str, observed_counts: dict, context: dict) -> None:
    """Execute une phase verte d'axe et observe en continu l'axe oppose (au rouge)."""
    active_lanes = AXIS_LANES[active_axis_name]
    opposite_lanes = AXIS_LANES[opposite_axis_name]

    active_axis_counts = aggregate_axis_counts(
        observed_counts[active_lanes[0]],
        observed_counts[active_lanes[1]],
    )

    camera_active = is_axis_camera_active(active_axis_name, context)
    green_duration = run_traffic_cycle(
        lane_name=active_axis_name,
        vehicle_counts=active_axis_counts,
        camera_active=camera_active,
    )

    print("\n============================================================")
    print(f"[PHASE VERTE] Axe actif: {active_axis_name}")
    print(f"[ETAT FEUX] {active_lanes[0]}=VERT | {active_lanes[1]}=VERT")
    print(f"[ETAT FEUX] {opposite_lanes[0]}=ROUGE | {opposite_lanes[1]}=ROUGE")
    print(f"[COMPTAGES AXE ACTIF] {active_axis_name}: {active_axis_counts}")
    print(
        f"[DUREE VERTE] {active_axis_name}: {green_duration}s "
        f"(bornes config: T_MIN={TIME_LIMITS['T_MIN']}s, T_MAX={TIME_LIMITS['T_MAX']}s)"
    )
    if not camera_active:
        print(f"[FAILSAFE] Vision indisponible sur {active_axis_name}. Duree de repli appliquee.")

    # L'axe qui passe au vert vide sa file; l'observation repart de zero pour son prochain tour rouge.
    clear_axis_buffer(observed_counts, active_lanes)

    for remaining in range(green_duration, 0, -1):
        observe_red_lanes(observed_counts, opposite_lanes, context)
        pending_opposite = aggregate_axis_counts(
            observed_counts[opposite_lanes[0]],
            observed_counts[opposite_lanes[1]],
        )
        print(
            f"[VERT {active_axis_name}] restant={remaining:02d}s | "
            f"[OBSERVATION {opposite_axis_name}] charge en attente: {pending_opposite}"
        )
        time.sleep(1)


def run_transition_phase(active_axis_name: str, opposite_axis_name: str, observed_counts: dict, context: dict) -> None:
    """Applique la transition de securite et continue l'observation des axes au rouge."""
    active_lanes = AXIS_LANES[active_axis_name]
    opposite_lanes = AXIS_LANES[opposite_axis_name]
    all_lanes = active_lanes + opposite_lanes

    print("\n------------------------------------------------------------")
    print(f"[TRANSITION] Fin de {active_axis_name}: passage au JAUNE")
    print(f"[ETAT FEUX] {active_lanes[0]}=JAUNE | {active_lanes[1]}=JAUNE")
    print(f"[ETAT FEUX] {opposite_lanes[0]}=ROUGE | {opposite_lanes[1]}=ROUGE")

    for remaining in range(YELLOW_SECONDS, 0, -1):
        observe_red_lanes(observed_counts, opposite_lanes, context)
        print(f"[JAUNE {active_axis_name}] restant={remaining:02d}s")
        time.sleep(1)

    print("[SECURITE] Tous au ROUGE pour degager integralement le carrefour")
    print("[ETAT FEUX] NORD=ROUGE | SUD=ROUGE | EST=ROUGE | OUEST=ROUGE")

    for remaining in range(ALL_RED_SECONDS, 0, -1):
        observe_red_lanes(observed_counts, all_lanes, context)
        print(f"[TOUS ROUGE] restant={remaining:02d}s")
        time.sleep(1)


def bootstrap_initial_observation(observed_counts: dict) -> None:
    """Charge initiale pour eviter un premier cycle artificiellement vide."""
    observed_counts["Voie Nord"].update({"moto": 10, "tricycle_passager": 4, "voiture": 5, "camion": 1})
    observed_counts["Voie Sud"].update({"moto": 14, "tricycle_passager": 3, "tricycle_cargo": 2, "voiture": 6, "bus": 1, "camion": 1})
    observed_counts["Voie Est"].update({"moto": 7, "tricycle_passager": 2, "voiture": 4, "camion": 1})
    observed_counts["Voie Ouest"].update({"moto": 8, "tricycle_passager": 2, "tricycle_cargo": 1, "voiture": 5, "minibus": 1, "camion": 1})


def main() -> None:
    print("=== Demarrage du systeme de regulation intelligente - Smart Traffic Lome ===")
    print("Mode de controle: phases synchronisees + observation croisee en continu")

    observed_counts = create_empty_observation_buffer()
    bootstrap_initial_observation(observed_counts)
    vision_context = create_vision_context()

    try:
        while True:
            # Phase 1: Axe Nord-Sud au vert, Axe Est-Ouest observe au rouge.
            run_green_phase("Axe Nord-Sud", "Axe Est-Ouest", observed_counts, vision_context)

            # Phase 2: Transition de securite, l'axe oppose continue a etre observe.
            run_transition_phase("Axe Nord-Sud", "Axe Est-Ouest", observed_counts, vision_context)

            # Phase 3: Axe Est-Ouest au vert, Axe Nord-Sud observe au rouge.
            run_green_phase("Axe Est-Ouest", "Axe Nord-Sud", observed_counts, vision_context)

            # Phase 4: Transition de securite, puis on reboucle.
            run_transition_phase("Axe Est-Ouest", "Axe Nord-Sud", observed_counts, vision_context)

    except KeyboardInterrupt:
        print("\n[INFO] Arret securise du systeme demande par l'operateur.")
    finally:
        release_vision_context(vision_context)


if __name__ == "__main__":
    main()