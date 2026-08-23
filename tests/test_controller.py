"""Tests pour le module controller (securite, failsafe, urgence)."""

from config import FAILSAFE_CONFIG
from modules.controller import run_traffic_cycle


def test_run_traffic_cycle_failsafe_when_camera_inactive() -> None:
    duration, meta = run_traffic_cycle("Voie Nord", {"moto": 5}, camera_active=False)
    assert meta["is_failsafe"] is True
    assert duration == FAILSAFE_CONFIG["default_duration"]


def test_run_traffic_cycle_emergency_override() -> None:
    emergency_counts = {"moto": 5, "ambulance": 1}
    duration, meta = run_traffic_cycle("Voie Nord", emergency_counts, camera_active=True)
    assert meta["is_emergency"] is True
    assert meta["applied_rule"] == "EMERGENCY_PREEMPTION"
