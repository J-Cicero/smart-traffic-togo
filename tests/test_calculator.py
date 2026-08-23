"""Tests pour le module calculator (PCU, urgence, lissage)."""

from __future__ import annotations

from config import EMERGENCY_GREEN_TIME, TIME_LIMITS
from modules.calculator import (
    calculate_green_light_duration,
    check_emergency_priority,
    compute_smoothed_load,
    compute_traffic_load,
)


def test_compute_traffic_load_uses_expected_coefficients() -> None:
    counts = {"moto": 10, "voiture": 3, "camion": 1}
    score = compute_traffic_load(counts)
    # 10*0.30 + 3*1.00 + 1*3.50 = 9.5
    assert score == 9.5


def test_emergency_priority_detection() -> None:
    normal_counts = {"moto": 10, "voiture": 2}
    has_em, duration = check_emergency_priority(normal_counts)
    assert not has_em
    assert duration == 0

    emergency_counts = {"moto": 5, "ambulance": 1}
    has_em, duration = check_emergency_priority(emergency_counts)
    assert has_em
    assert duration == EMERGENCY_GREEN_TIME


def test_calculate_green_light_duration_respects_lower_bound() -> None:
    counts = {"moto": 0, "voiture": 0, "camion": 0}
    duration, meta = calculate_green_light_duration(counts)
    assert duration >= TIME_LIMITS["T_MIN"]
    assert meta["applied_rule"] == "STANDARD_PCU_DYNAMIC"


def test_calculate_green_light_duration_respects_upper_bound() -> None:
    counts = {"moto": 1000, "voiture": 1000, "camion": 1000}
    duration, meta = calculate_green_light_duration(counts)
    assert duration <= TIME_LIMITS["T_MAX"]


def test_calculate_green_light_duration_applies_formula_inside_bounds() -> None:
    counts = {"moto": 10, "voiture": 2, "camion": 0}
    duration, meta = calculate_green_light_duration(counts)
    # charge = (10*0.30) + (2*1.00) = 5.0
    # T = 10 + 5.0*2.5 = 22.5 -> int(...) = 22
    assert duration == 22


def test_compute_smoothed_load() -> None:
    current_counts = {"moto": 10}  # charge = 3.0
    previous_load = 10.0
    smoothed = compute_smoothed_load(current_counts, previous_load, alpha=0.5)
    # 0.5 * 3.0 + 0.5 * 10.0 = 6.5
    assert smoothed == 6.5