"""Tests pour la gestion dynamique des topologies de carrefour (3 voies vs 4 voies)."""

from config import TOPOLOGY_CONFIGS
from main import create_empty_observation_buffer, aggregate_lane_counts


def test_topology_config_structures() -> None:
    cross = TOPOLOGY_CONFIGS["4_WAY_CROSS"]
    assert len(cross["lanes"]) == 4
    assert len(cross["phases"]) == 2

    t_junction = TOPOLOGY_CONFIGS["3_WAY_T"]
    assert len(t_junction["lanes"]) == 3
    assert len(t_junction["phases"]) == 2


def test_dynamic_observation_buffer_creation() -> None:
    lanes_3way = TOPOLOGY_CONFIGS["3_WAY_T"]["lanes"]
    buffer = create_empty_observation_buffer(lanes_3way)

    assert "Voie Nord" in buffer
    assert "Voie Sud" in buffer
    assert "Voie Est" in buffer
    assert "Voie Ouest" not in buffer


def test_aggregate_lane_counts_supports_variable_lanes() -> None:
    observed_counts = {
        "Voie Nord": {"moto": 5, "voiture": 2},
        "Voie Sud": {"moto": 3, "voiture": 1},
        "Voie Est": {"moto": 10, "camion": 1},
    }

    # Aggregate Nord + Sud (Axe principal)
    agg_main = aggregate_lane_counts(observed_counts, ["Voie Nord", "Voie Sud"])
    assert agg_main["moto"] == 8
    assert agg_main["voiture"] == 3

    # Aggregate Est seule (Voie secondaire en T)
    agg_sec = aggregate_lane_counts(observed_counts, ["Voie Est"])
    assert agg_sec["moto"] == 10
    assert agg_sec["camion"] == 1
