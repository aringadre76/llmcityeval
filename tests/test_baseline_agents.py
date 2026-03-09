from __future__ import annotations

import pytest

import agents.heuristic_agent as heuristic_agent_module
import agents.random_agent as random_agent_module
from agents.heuristic_agent import (
    ConnectivityAwareHeuristicAgent,
    HeuristicAgent,
    HybridBudgetConnectivityAgent,
)
from agents.random_agent import (
    BudgetAwareRandomAgent,
    ConnectivityAwareRandomAgent,
    RandomAgent,
)
from agents.utils import get_connectivity_info, get_zone_cost
from config import (
    COST_COMMERCIAL,
    COST_INDUSTRIAL,
    COST_RESIDENTIAL,
    COST_ROAD,
    MAX_ACTIONS_PER_TURN,
)
from sim.city import CityState
from sim.grid import (
    TileState,
    VALID_ZONES,
    ZONE_EMPTY,
    ZONE_COMMERCIAL,
    ZONE_INDUSTRIAL,
    ZONE_RESIDENTIAL,
    ZONE_ROAD,
)


def _empty_state(tick: int, budget: float = 2000.0, size: int = 10) -> CityState:
    grid = [[TileState(x=x, y=y) for x in range(size)] for y in range(size)]
    return CityState(
        tick=tick,
        budget=budget,
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


def _state_with_active_road(tick: int, budget: float = 2000.0, size: int = 5) -> CityState:
    state = _empty_state(tick=tick, budget=budget, size=size)
    road_x = min(1, size - 1)
    state.grid[1][road_x].zone = ZONE_ROAD
    return state


def _jagged_state(tick: int, budget: float = 2000.0) -> CityState:
    grid = [
        [TileState(x=0, y=0), TileState(x=1, y=0)],
        [TileState(x=0, y=1, zone=ZONE_ROAD)],
    ]
    return CityState(
        tick=tick,
        budget=budget,
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


class _FixedUpperBoundRng:
    def randint(self, lower: int, upper: int) -> int:
        assert lower == 1
        assert upper == random_agent_module.MAX_ACTIONS_PER_TURN
        return upper

    def randrange(self, upper: int) -> int:
        return 0

    def choice(self, options):
        return options[0]

    def random(self) -> float:
        return 0.0

    def shuffle(self, items: list[tuple[int, int]] | list[str]) -> None:
        return None


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
    agent = HeuristicAgent(seed=42)
    actions = agent.decide(_empty_state(tick=0))

    assert len(actions) == 1
    assert actions[0].zone == ZONE_ROAD
    assert actions[0].x == 1
    assert actions[0].y == 0


def test_heuristic_agent_keeps_default_seed_constructor() -> None:
    agent = HeuristicAgent()

    actions = agent.decide(_empty_state(tick=0))

    assert len(actions) == 1
    assert actions[0].zone == ZONE_ROAD


@pytest.mark.parametrize(
    ("agent_factory", "tick"),
    [
        (lambda: BudgetAwareRandomAgent(seed=1), 0),
        (lambda: ConnectivityAwareRandomAgent(seed=1), 0),
        (lambda: HeuristicAgent(), 0),
        (lambda: ConnectivityAwareHeuristicAgent(seed=1), 0),
        (lambda: HybridBudgetConnectivityAgent(seed=1), 0),
    ],
)
def test_affordability_aware_agents_return_no_actions_with_zero_budget(
    agent_factory, tick: int
) -> None:
    state = _empty_state(tick=tick, budget=0.0)

    actions = agent_factory().decide(state)

    assert actions == []


@pytest.mark.parametrize(
    ("agent_factory", "tick"),
    [
        (lambda: BudgetAwareRandomAgent(seed=2), 0),
        (lambda: ConnectivityAwareRandomAgent(seed=2), 0),
        (lambda: HeuristicAgent(), 0),
        (lambda: ConnectivityAwareHeuristicAgent(seed=2), 0),
        (lambda: HybridBudgetConnectivityAgent(seed=2), 0),
    ],
)
def test_affordability_aware_agents_return_no_actions_below_road_cost(
    agent_factory, tick: int
) -> None:
    state = _empty_state(tick=tick, budget=float(COST_ROAD - 1))

    actions = agent_factory().decide(state)

    assert actions == []


def test_connectivity_aware_random_agent_builds_road_when_zone_is_unaffordable() -> None:
    state = _state_with_active_road(tick=8, budget=float(COST_ROAD), size=5)
    agent = ConnectivityAwareRandomAgent(seed=7)

    actions = agent.decide(state)

    assert len(actions) == 1
    assert actions[0].zone == ZONE_ROAD
    assert (actions[0].x, actions[0].y) in set(
        get_connectivity_info(state)["empty_with_road"]
    )


def test_connectivity_info_excludes_disabled_empty_tiles() -> None:
    state = _state_with_active_road(tick=12, budget=500.0, size=4)
    state.grid[1][2].disabled = True

    connectivity = get_connectivity_info(state)

    assert (2, 1) not in connectivity["empty_with_road"]


def test_connectivity_info_handles_jagged_grids_without_index_errors() -> None:
    state = _jagged_state(tick=4)

    connectivity = get_connectivity_info(state)

    assert connectivity["empty_with_road"] == [(0, 0)]
    assert connectivity["empty_without_road"] == [(1, 0)]
    assert connectivity["total_empty"] == 2


@pytest.mark.parametrize(
    ("zone", "expected_cost"),
    [
        (ZONE_ROAD, COST_ROAD),
        (ZONE_RESIDENTIAL, COST_RESIDENTIAL),
        (ZONE_COMMERCIAL, COST_COMMERCIAL),
        (ZONE_INDUSTRIAL, COST_INDUSTRIAL),
    ],
)
def test_get_zone_cost_returns_shared_zone_prices(zone: str, expected_cost: int) -> None:
    assert get_zone_cost(zone) == expected_cost


def test_get_zone_cost_rejects_unknown_zones() -> None:
    with pytest.raises(ValueError, match="Unknown zone"):
        get_zone_cost(ZONE_EMPTY)


def test_connectivity_aware_random_agent_skips_disabled_and_occupied_tiles() -> None:
    state = _state_with_active_road(tick=12, budget=500.0, size=4)
    state.grid[0][1].zone = ZONE_RESIDENTIAL
    state.grid[1][2].disabled = True
    agent = ConnectivityAwareRandomAgent(seed=11)

    actions = agent.decide(state)

    targeted_tiles = {(action.x, action.y) for action in actions}
    assert (1, 0) not in targeted_tiles
    assert (2, 1) not in targeted_tiles


def test_hybrid_agent_does_not_target_same_tile_twice_in_late_game() -> None:
    state = _state_with_active_road(tick=45, budget=1000.0, size=5)
    agent = HybridBudgetConnectivityAgent(seed=3)

    actions = agent.decide(state)

    targeted_tiles = [(action.x, action.y) for action in actions]
    assert len(targeted_tiles) == len(set(targeted_tiles))


@pytest.mark.parametrize(
    ("agent", "state"),
    [
        (BudgetAwareRandomAgent(seed=5), _empty_state(tick=0, budget=2000.0)),
        (
            ConnectivityAwareRandomAgent(seed=5),
            _state_with_active_road(tick=10, budget=2000.0, size=6),
        ),
        (ConnectivityAwareHeuristicAgent(seed=5), _state_with_active_road(tick=25)),
        (HybridBudgetConnectivityAgent(seed=5), _state_with_active_road(tick=35)),
    ],
)
def test_agents_stay_within_action_limit_on_high_budget(agent, state: CityState) -> None:
    actions = agent.decide(state)

    assert len(actions) <= MAX_ACTIONS_PER_TURN
    assert len(actions) > 1
    for action in actions:
        assert action.zone in (
            ZONE_ROAD,
            ZONE_RESIDENTIAL,
            ZONE_COMMERCIAL,
            ZONE_INDUSTRIAL,
        )


@pytest.mark.parametrize(
    "agent_factory",
    [
        lambda: RandomAgent(seed=0),
        lambda: BudgetAwareRandomAgent(seed=0),
        lambda: ConnectivityAwareRandomAgent(seed=0),
    ],
)
def test_random_agents_use_shared_action_limit_constant(agent_factory, monkeypatch) -> None:
    monkeypatch.setattr(random_agent_module, "MAX_ACTIONS_PER_TURN", 3, raising=False)
    agent = agent_factory()
    agent._rng = _FixedUpperBoundRng()
    state = _state_with_active_road(tick=12, budget=1000.0, size=6)

    actions = agent.decide(state)

    assert len(actions) == 3


@pytest.mark.parametrize(
    ("agent", "state"),
    [
        (HeuristicAgent(seed=0), _state_with_active_road(tick=30, budget=2000.0, size=6)),
        (
            ConnectivityAwareHeuristicAgent(seed=0),
            _state_with_active_road(tick=25, budget=2000.0, size=6),
        ),
        (
            HybridBudgetConnectivityAgent(seed=0),
            _state_with_active_road(tick=35, budget=2000.0, size=6),
        ),
    ],
)
def test_heuristic_agents_use_shared_action_limit_constant(agent, state, monkeypatch) -> None:
    monkeypatch.setattr(heuristic_agent_module, "MAX_ACTIONS_PER_TURN", 2, raising=False)

    actions = agent.decide(state)

    assert len(actions) == 2
