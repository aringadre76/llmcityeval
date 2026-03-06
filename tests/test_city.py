from __future__ import annotations

from config import COST_RESIDENTIAL, MAX_ACTIONS_PER_TURN
from sim.city import Action, City
from sim.grid import ZONE_EMPTY, ZONE_RESIDENTIAL, ZONE_ROAD


def test_apply_actions_applies_valid_action_and_spends_budget() -> None:
    city = City(seed=1)
    start_budget = city.budget

    city.apply_actions([Action(type="zone", x=1, y=1, zone=ZONE_ROAD)])

    outcomes = city.get_last_action_outcomes()
    assert len(outcomes) == 1
    assert outcomes[0]["applied"] is True
    assert city.grid.get_tile(1, 1).zone == ZONE_ROAD
    assert city.get_last_budget_spent() > 0.0
    assert city.budget < start_budget


def test_apply_actions_rejects_insufficient_budget() -> None:
    city = City(seed=1)
    city.budget = 0.0

    city.apply_actions([Action(type="zone", x=1, y=1, zone=ZONE_RESIDENTIAL)])

    outcomes = city.get_last_action_outcomes()
    assert outcomes[0]["applied"] is False
    assert outcomes[0]["reason"] == "insufficient_budget"
    assert outcomes[0]["cost"] == COST_RESIDENTIAL


def test_apply_actions_rejects_invalid_and_out_of_bounds() -> None:
    city = City(seed=1)

    city.apply_actions(
        [
            Action(type="zone", x=99, y=99, zone=ZONE_ROAD),
            Action(type="zone", x=1, y=1, zone="BAD"),
            Action(type="unknown", x=1, y=1, zone=ZONE_ROAD),
        ]
    )

    reasons = [o["reason"] for o in city.get_last_action_outcomes()]
    assert "out_of_bounds" in reasons
    assert "invalid_zone" in reasons
    assert "invalid_action_type" in reasons


def test_apply_actions_enforces_max_actions() -> None:
    city = City(seed=1)
    actions = [Action(type="zone", x=0, y=0, zone=ZONE_ROAD)] * (MAX_ACTIONS_PER_TURN + 3)

    city.apply_actions(actions)

    outcomes = city.get_last_action_outcomes()
    dropped = [o for o in outcomes if o.get("reason") == "exceeded_max_actions"]
    assert len(dropped) == 3


def test_tile_cost_variants_and_disabled_repair_cost() -> None:
    city = City(seed=1)

    assert city._tile_cost(ZONE_ROAD, ZONE_ROAD) == 0
    assert city._tile_cost(ZONE_EMPTY, ZONE_ROAD) == 50
    assert city._tile_cost(ZONE_ROAD, ZONE_RESIDENTIAL) == COST_RESIDENTIAL + 25

    city.apply_actions([Action(type="zone", x=1, y=1, zone=ZONE_ROAD)])
    tile = city.grid.get_tile(1, 1)
    tile.disabled = True
    before = city.budget

    city.apply_actions([Action(type="zone", x=1, y=1, zone=ZONE_ROAD)])
    outcome = city.get_last_action_outcomes()[0]

    assert outcome["applied"] is True
    assert outcome["cost"] == 50
    assert city.budget == before - 50
    assert city.grid.get_tile(1, 1).disabled is False


def test_tick_updates_state_and_metrics_delta() -> None:
    city = City(seed=1)
    city.apply_actions([Action(type="zone", x=1, y=1, zone=ZONE_ROAD)])
    before_tick = city.tick_count

    city.tick()
    state = city.get_state()

    assert city.tick_count == before_tick + 1
    assert state.tick == city.tick_count
    assert "budget" in state.metrics_delta
    assert "population" in state.metrics_delta


def test_get_state_includes_last_action_outcomes() -> None:
    city = City(seed=1)
    city.budget = 0.0

    city.apply_actions([Action(type="zone", x=0, y=0, zone=ZONE_ROAD)])
    state = city.get_state()

    assert isinstance(state.last_action_outcomes, list)
    assert len(state.last_action_outcomes) == 1
    assert state.last_action_outcomes[0]["reason"] == "insufficient_budget"

