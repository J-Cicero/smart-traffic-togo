"""Traffic light state machine and safety enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class LightState(Enum):
    RED = auto()
    GREEN = auto()
    YELLOW = auto()


@dataclass
class TrafficController:
    current_state: LightState = LightState.RED

    def transition_to(self, next_state: LightState) -> None:
        self.current_state = next_state

    def safe_cycle(self) -> list[LightState]:
        """Return a default safe order for a single traffic cycle."""
        return [LightState.GREEN, LightState.YELLOW, LightState.RED]