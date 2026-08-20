"""PCU and signal timing calculations."""

from __future__ import annotations

from collections.abc import Mapping

from config import SAFETY_RULES, PCU_COEFFICIENTS, SafetyRules


def calculate_pcu_score(counts: Mapping[str, int]) -> float:
    """Convert raw detections into a weighted PCU score."""
    score = 0.0
    for label, count in counts.items():
        score += PCU_COEFFICIENTS.get(label, 0.0) * max(0, int(count))
    return score


def calculate_green_duration(pcu_score: float, safety_rules: SafetyRules = SAFETY_RULES) -> int:
    """Map a PCU score to a bounded green duration in seconds."""
    if pcu_score <= 0:
        return safety_rules.fallback_green_seconds

    normalized = safety_rules.min_green_seconds + int(round(pcu_score * 2))
    return max(safety_rules.min_green_seconds, min(safety_rules.max_green_seconds, normalized))