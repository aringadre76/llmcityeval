from __future__ import annotations

from sim.city import City
from sim.disasters import ActiveDisaster, DISASTER_DEMAND_SURGE
from sim.runtime_config import SimConfig


def test_city_uses_overridden_starting_values() -> None:
    sim_config = SimConfig(starting_budget=1234.0, starting_population=7)

    city = City(seed=1, sim_config=sim_config)

    assert city.budget == 1234.0
    assert city.population == 7


def test_city_disaster_manager_uses_overridden_demand_surge_divisor() -> None:
    sim_config = SimConfig(demand_surge_divisor=3.0)
    city = City(seed=1, sim_config=sim_config)
    city.disasters._active = [  # noqa: SLF001
        ActiveDisaster(disaster_type=DISASTER_DEMAND_SURGE, ticks_remaining=2, metadata={})
    ]

    assert city.disasters.active_demand_surge_divisor() == 3.0

