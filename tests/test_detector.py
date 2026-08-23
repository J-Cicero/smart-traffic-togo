"""Tests pour le module detector (ROI, mapping de classes)."""

from modules.detector import is_inside_roi, map_yolo_class_name


def test_is_inside_roi_returns_true_when_no_roi() -> None:
    box_norm = (0.3, 0.3, 0.5, 0.5)
    assert is_inside_roi(box_norm, None) is True


def test_is_inside_roi_filters_correctly() -> None:
    # ROI: [ymin=0.2, xmin=0.2, ymax=0.8, xmax=0.8]
    roi = [0.2, 0.2, 0.8, 0.8]

    # Boite au centre (0.5, 0.5) -> Dedans
    box_inside = (0.4, 0.4, 0.6, 0.6)
    assert is_inside_roi(box_inside, roi) is True

    # Boite hors zone (0.05, 0.05) -> Dehors
    box_outside = (0.0, 0.0, 0.1, 0.1)
    assert is_inside_roi(box_outside, roi) is False


def test_map_yolo_class_name() -> None:
    assert map_yolo_class_name("motorcycle") == "moto"
    assert map_yolo_class_name("car") == "voiture"
    assert map_yolo_class_name("ambulance") == "urgence"
    assert map_yolo_class_name("truck") == "camion"
    assert map_yolo_class_name("unknown_object") is None
