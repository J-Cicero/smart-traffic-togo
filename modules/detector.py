# modules/detector.py - Module de vision par ordinateur (YOLOv8)


def load_yolo_model(model_path: str = "yolov8n.pt"):
    """
    Charge le modele YOLOv8 pre-entraine (modele de base ou personnalise).
    """
    from ultralytics import YOLO

    model = YOLO(model_path)
    return model


def detect_and_count_vehicles(frame, model) -> dict:
    """
    Analyse une image/frame video, applique l'inference YOLOv8 et
    retourne un dictionnaire contenant le comptage des vehicules par classe.
    """
    # Dictionnaire de comptage initialise a zero pour notre taxonomie locale
    counts = {
        "moto": 0,
        "tricycle_passager": 0,
        "tricycle_cargo": 0,
        "voiture": 0,
        "minibus": 0,
        "bus": 0,
        "camion": 0,
    }

    # Execution de l'inference YOLOv8 sur la frame
    results = model(frame, verbose=False)

    for r in results:
        boxes = r.boxes
        for box in boxes:
            # Recuperation du nom de la classe detectee par YOLO
            cls_id = int(box.cls[0])
            class_name = str(model.names.get(cls_id, "")).lower()

            # Mapping des classes YOLO standard vers notre taxonomie locale
            if "motorcycle" in class_name or "bike" in class_name:
                counts["moto"] += 1
            elif "car" in class_name:
                counts["voiture"] += 1
            elif "bus" in class_name:
                counts["bus"] += 1
            elif "truck" in class_name:
                counts["camion"] += 1
            # Note : Pour affiner avec des tricycles ou minibus specifiques de Lome,
            # on utilisera a terme un modele YOLO reentraine sur notre propre dataset.

    return counts