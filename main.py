"""Point d'entrée principal du prototype smart-traffic-togo."""

from __future__ import annotations

from config import SAFETY_RULES
from modules.calculator import calculate_green_duration, calculate_pcu_score


def main() -> None:
    """Exécute une démonstration minimale du calcul de durée de vert."""
    sample_counts = {
        "car": 8,
        "motorcycle": 5,
        "truck": 1,
    }
    pcu_score = calculate_pcu_score(sample_counts)
    green_duration = calculate_green_duration(pcu_score, SAFETY_RULES)
    print(f"PCU score: {pcu_score:.2f}")
    print(f"Green duration: {green_duration} seconds")


if __name__ == "__main__":
    main()