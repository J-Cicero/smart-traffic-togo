# modules/detector.py - Module de vision par ordinateur (YOLOv8 + ROI + Tracking)

from config import EMERGENCY_CLASSES, ROI_CONFIG, VISION_CONFIG


def load_yolo_model(model_path: str = "yolov8n.pt"):
    """
    Charge le modele YOLOv8 pre-entraine ou affine.
    """
    from ultralytics import YOLO

    model = YOLO(model_path)
    return model


def is_inside_roi(box_norm: tuple[float, float, float, float], roi: list[float] | None) -> bool:
    """
    Verifie si le centre d'une boite englobante [xmin, ymin, xmax, ymax] normalisee (0..1)
    se trouve a l'interieur de la Zone d'Interet (ROI) [ymin, xmin, ymax, xmax].
    """
    if not roi or len(roi) != 4:
        return True  # Pas de ROI configuree, on conserve toutes les detections

    xmin, ymin, xmax, ymax = box_norm
    center_x = (xmin + xmax) / 2.0
    center_y = (ymin + ymax) / 2.0

    roi_ymin, roi_xmin, roi_ymax, roi_xmax = roi
    return (roi_xmin <= center_x <= roi_xmax) and (roi_ymin <= center_y <= roi_ymax)


def map_yolo_class_name(class_name: str) -> str | None:
    """
    Mappe le nom de classe extrait de YOLO vers la taxonomie locale de Lome.
    Gere aussi bien les labels du modele re-entraine (ex: moto, tricycle_cargo)
    que les noms COCO standards en fallback (ex: motorcycle, car, bus).
    """
    name = class_name.lower().strip()

    # Match direct avec la taxonomie locale (pour le modele re-entraine)
    exact_classes = [
        "urgence",
        "moto",
        "tricycle_cargo",
        "tricycle_passager",
        "voiture",
        "minibus",
        "bus",
        "camion",
    ]
    if name in exact_classes:
        return name

    # Match d'urgence
    if any(em in name for em in EMERGENCY_CLASSES):
        return "urgence"

    # Fallback COCO / mots-cles
    if "motorcycle" in name or "bike" in name or "scooter" in name:
        return "moto"
    if "tricycle_cargo" in name:
        return "tricycle_cargo"
    if "tricycle" in name or "rickshaw" in name:
        return "tricycle_passager"
    if "car" in name or "taxi" in name:
        return "voiture"
    if "minibus" in name or "van" in name:
        return "minibus"
    if "bus" in name:
        return "bus"
    if "truck" in name or "camion" in name:
        return "camion"

    return None


def detect_and_count_vehicles(
    frame,
    model,
    lane_name: str | None = None,
    conf_threshold: float | None = None,
) -> dict:
    """
    Analyse une frame video avec YOLOv8, applique le filtrage par confiance et ROI,
    et retourne le comptage par categorie de vehicule.
    """
    if conf_threshold is None:
        conf_threshold = VISION_CONFIG.get("CONF_THRESHOLD", 0.35)

    roi = ROI_CONFIG.get(lane_name) if lane_name else None

    counts = {
        "moto": 0,
        "tricycle_passager": 0,
        "tricycle_cargo": 0,
        "voiture": 0,
        "minibus": 0,
        "bus": 0,
        "camion": 0,
        "urgence": 0,
    }

    # Execution de l'inference YOLO
    results = model(frame, verbose=False, conf=conf_threshold)

    height, width = frame.shape[:2] if hasattr(frame, "shape") and len(frame.shape) >= 2 else (1, 1)

    for r in results:
        boxes = r.boxes
        for box in boxes:
            conf = float(box.conf[0]) if hasattr(box, "conf") and len(box.conf) > 0 else 1.0
            if conf < conf_threshold:
                continue

            cls_id = int(box.cls[0])
            class_name = str(model.names.get(cls_id, "")).lower()
            mapped_class = map_yolo_class_name(class_name)

            if mapped_class is None:
                continue

            # Extraire coordonnées bounding box normalisées [xmin, ymin, xmax, ymax]
            xyxy = box.xyxy[0].tolist() if hasattr(box, "xyxy") and len(box.xyxy) > 0 else [0, 0, width, height]
            box_norm = (
                xyxy[0] / max(1, width),
                xyxy[1] / max(1, height),
                xyxy[2] / max(1, width),
                xyxy[3] / max(1, height),
            )

            # Filtrage ROI
            if is_inside_roi(box_norm, roi):
                counts[mapped_class] += 1

    return counts