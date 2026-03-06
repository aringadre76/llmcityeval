from __future__ import annotations

import math
from random import Random

from sim.city import Action, City
from sim.runtime_config import SimConfig


class FuzzAgent:
    def __init__(self, seed: int) -> None:
        self._rng = Random(seed)

    def decide(self, grid_size: int) -> list[Action]:
        count = self._rng.randint(1, 10)
        zones = ("R", "C", "I", "O")
        return [
            Action(
                type="zone",
                x=self._rng.randrange(grid_size),
                y=self._rng.randrange(grid_size),
                zone=self._rng.choice(zones),
            )
            for _ in range(count)
        ]


def test_random_stress_invariants_hold_under_extreme_config() -> None:
    sim_config = SimConfig(
        disaster_recession_prob=0.5,
        disaster_demand_surge_prob=0.5,
        disaster_infra_fail_prob=0.5,
        disaster_pollution_prob=0.5,
        disaster_recession_duration=8,
        disaster_demand_surge_duration=8,
        disaster_infra_fail_duration=8,
        pollution_event_increment=0.8,
    )
    city = City(seed=123, sim_config=sim_config)
    agent = FuzzAgent(seed=99)
    grid_size = city.grid.size

    for _ in range(200):
        actions = agent.decide(grid_size)
        city.apply_actions(actions)
        budget_before_tick = city.budget

        city.tick()
        state = city.get_state()

        expected_budget = budget_before_tick + state.revenue_per_tick - state.expenses_per_tick
        assert math.isclose(city.budget, expected_budget, rel_tol=1e-9, abs_tol=1e-9)

        for tile in city.grid.iter_tiles():
            assert 0.0 <= tile.pollution <= 1.0


def test_city_is_deterministic_for_fixed_seed_config_and_actions() -> None:
    sim_config = SimConfig(
        disaster_recession_prob=0.4,
        disaster_demand_surge_prob=0.4,
        disaster_infra_fail_prob=0.4,
        disaster_pollution_prob=0.4,
    )
    city_one = City(seed=77, sim_config=sim_config)
    city_two = City(seed=77, sim_config=sim_config)

    action_sequence = [
        [Action(type="zone", x=1, y=turn % 10, zone="O"), Action(type="zone", x=2, y=turn % 10, zone="R")]
        for turn in range(30)
    ]

    for actions in action_sequence:
        city_one.apply_actions(actions)
        city_two.apply_actions(actions)
        events_one = city_one.tick()
        events_two = city_two.tick()

        assert events_one == events_two
        assert city_one.get_last_action_outcomes() == city_two.get_last_action_outcomes()
        assert city_one.get_state() == city_two.get_state()
