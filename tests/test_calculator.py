"""Tests for the calculator module."""

from __future__ import annotations

from config import SAFETY_RULES
from modules.calculator import calculate_green_duration, calculate_pcu_score


def test_calculate_pcu_score_uses_expected_coefficients() -> None:
    counts = {"car": 3, "motorcycle": 4, "truck": 1}

    score = calculate_pcu_score(counts)

    assert score == 6.0


def test_calculate_green_duration_respects_lower_bound() -> None:
    duration = calculate_green_duration(1.0, SAFETY_RULES)

    assert duration >= SAFETY_RULES.min_green_seconds


def test_calculate_green_duration_respects_upper_bound() -> None:
    duration = calculate_green_duration(100.0, SAFETY_RULES)

    assert duration <= SAFETY_RULES.max_green_seconds


def test_calculate_green_duration_falls_back_when_score_is_zero() -> None:
    duration = calculate_green_duration(0.0, SAFETY_RULES)

    assert duration == SAFETY_RULES.fallback_green_seconds