from __future__ import annotations

from agents.heuristic_agent import HeuristicAgent
from agents.random_agent import RandomAgent
from sim.city import CityState
from sim.grid import TileState, VALID_ZONES, ZONE_ROAD


def _empty_state(tick: int) -> CityState:
    grid = [[TileState(x=x, y=y) for x in range(10)] for y in range(10)]
    return CityState(
        tick=tick,
        budget=2000.0,
        population=0,
        revenue_per_tick=0.0,
        expenses_per_tick=0.0,
        livability=1.0,
        pollution_avg=0.0,
        grid=grid,
        recent_events=[],
        metrics_delta={},
        last_action_outcomes=[],
    )


def test_random_agent_generates_bounded_valid_actions() -> None:
    agent = RandomAgent(seed=123)
    actions = agent.decide(_empty_state(tick=0))

    assert 1 <= len(actions) <= 5
    for action in actions:
        assert action.type == "zone"
        assert 0 <= action.x < 10
        assert 0 <= action.y < 10
        assert action.zone in (VALID_ZONES - {"E"})


def test_heuristic_agent_starts_with_road_spine() -> None:
    agent = HeuristicAgent()
    actions = agent.decide(_empty_state(tick=0))

    assert len(actions) == 1
    assert actions[0].zone == ZONE_ROAD
    assert actions[0].x == 1
    assert actions[0].y == 0
