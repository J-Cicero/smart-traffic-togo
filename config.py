"""Configuration globale du projet smart-traffic-togo."""

from __future__ import annotations

from dataclasses import dataclass


PCU_COEFFICIENTS = {
    "car": 1.0,
    "motorcycle": 0.5,
    "truck": 2.0,
    "bus": 2.5,
    "bicycle": 0.2,
    "pedestrian": 0.1,
}

T_MIN_SECONDS = 15
T_MAX_SECONDS = 60
DEFAULT_GREEN_SECONDS = 30
DEFAULT_CYCLE_SECONDS = 90


@dataclass(frozen=True)
class SafetyRules:
    min_green_seconds: int = T_MIN_SECONDS
    max_green_seconds: int = T_MAX_SECONDS
    fallback_green_seconds: int = DEFAULT_GREEN_SECONDS


SAFETY_RULES = SafetyRules()