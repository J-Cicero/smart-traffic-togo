"""Tests for the calculator module."""

from __future__ import annotations

from config import TIME_LIMITS
from modules.calculator import calculate_green_light_duration, compute_traffic_load


def test_compute_traffic_load_uses_expected_coefficients() -> None:
    counts = {"moto": 10, "voiture": 3, "camion": 1}

    score = compute_traffic_load(counts)

    # 10*0.30 + 3*1.00 + 1*3.50 = 9.5
    assert score == 9.5


def test_calculate_green_light_duration_respects_lower_bound() -> None:
    counts = {"moto": 0, "voiture": 0, "camion": 0}
    duration = calculate_green_light_duration(counts)

    assert duration >= TIME_LIMITS["T_MIN"]


def test_calculate_green_light_duration_respects_upper_bound() -> None:
    counts = {"moto": 1000, "voiture": 1000, "camion": 1000}
    duration = calculate_green_light_duration(counts)

    assert duration <= TIME_LIMITS["T_MAX"]


def test_calculate_green_light_duration_applies_formula_inside_bounds() -> None:
    counts = {"moto": 10, "voiture": 2, "camion": 0}
    duration = calculate_green_light_duration(counts)

    # charge = (10*0.30) + (2*1.00) = 5.0
    # T = 10 + 5.0*2.5 = 22.5 -> int(...) = 22
    assert duration == 22