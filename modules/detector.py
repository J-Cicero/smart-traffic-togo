"""Vision module placeholder for frame acquisition and class counting."""

from __future__ import annotations

from collections.abc import Mapping


def detect_vehicle_counts(frame: object | None = None) -> dict[str, int]:
    """Return a placeholder set of counts until video detection is wired."""
    _ = frame
    return {
        "car": 0,
        "motorcycle": 0,
        "truck": 0,
        "bus": 0,
        "bicycle": 0,
        "pedestrian": 0,
    }


def normalize_counts(counts: Mapping[str, int]) -> dict[str, int]:
    """Clamp negative inputs to zero and ensure integer counts."""
    normalized: dict[str, int] = {}
    for label, value in counts.items():
        normalized[label] = max(0, int(value))
    return normalized