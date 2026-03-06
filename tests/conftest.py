from __future__ import annotations

from typing import Any

import pytest

from sim.city import City
from sim.grid import Grid


@pytest.fixture
def grid3() -> Grid:
    return Grid(size=3)


@pytest.fixture
def city_seed_1() -> City:
    return City(seed=1)


@pytest.fixture
def valid_run_log_payload() -> dict[str, Any]:
    return {
        "agent": "test-model",
        "seed": 123,
        "turns": [
            {
                "turn": 0,
                "state": {"population": 10},
                "actions": [],
                "action_parse_success": True,
                "action_outcomes": [],
                "budget_spent": 100.0,
                "disaster_events": [],
            }
        ],
        "final_state": {"population": 25},
        "scores": {
            "population": 1.0,
            "efficiency": 2.0,
            "stability": 3.0,
            "resilience": 4.0,
            "composite": 2.5,
        },
    }
