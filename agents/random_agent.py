from __future__ import annotations

from random import Random

from agents.base import BaseAgent
from agents.utils import (
    can_afford_affordability_aware_action,
    filter_untargeted_tiles,
    get_connectivity_info,
    get_zone_cost,
)
from config import MAX_ACTIONS_PER_TURN
from sim.city import Action, CityState
from sim.grid import ZONE_COMMERCIAL, ZONE_INDUSTRIAL, ZONE_RESIDENTIAL, ZONE_ROAD


_MIN_NON_ROAD_ZONE_COST = min(
    get_zone_cost(ZONE_RESIDENTIAL),
    get_zone_cost(ZONE_COMMERCIAL),
    get_zone_cost(ZONE_INDUSTRIAL),
)


class RandomAgent(BaseAgent):
    def __init__(self, seed: int, name: str = "random_baseline") -> None:
        super().__init__(name=name)
        self._rng = Random(seed)

    def decide(self, state: CityState) -> list[Action]:
        grid_size = len(state.grid)
        if grid_size <= 0:
            return []
        action_count = self._rng.randint(1, MAX_ACTIONS_PER_TURN)
        zones = (ZONE_RESIDENTIAL, ZONE_COMMERCIAL, ZONE_INDUSTRIAL, ZONE_ROAD)
        actions: list[Action] = []
        for _ in range(action_count):
            actions.append(
                Action(
                    type="zone",
                    x=self._rng.randrange(grid_size),
                    y=self._rng.randrange(grid_size),
                    zone=self._rng.choice(zones),
                )
            )
        return actions


class BudgetAwareRandomAgent(BaseAgent):
    def __init__(
        self,
        seed: int,
        name: str = "budget_aware_random_baseline",
    ) -> None:
        super().__init__(name=name)
        self._rng = Random(seed)

    def decide(self, state: CityState) -> list[Action]:
        grid_size = len(state.grid)
        if grid_size <= 0:
            return []

        remaining_budget = state.budget
        zones = (ZONE_RESIDENTIAL, ZONE_COMMERCIAL, ZONE_INDUSTRIAL, ZONE_ROAD)
        actions: list[Action] = []
        if not can_afford_affordability_aware_action(remaining_budget):
            return []

        max_actions = self._rng.randint(1, MAX_ACTIONS_PER_TURN)

        for _ in range(max_actions):
            if not can_afford_affordability_aware_action(remaining_budget):
                break
            x = self._rng.randrange(grid_size)
            y = self._rng.randrange(grid_size)
            affordable_zones = [
                zone for zone in zones if remaining_budget >= get_zone_cost(zone)
            ]
            if not affordable_zones:
                break
            zone = self._rng.choice(affordable_zones)
            actions.append(Action(type="zone", x=x, y=y, zone=zone))
            remaining_budget -= get_zone_cost(zone)

        return actions


class ConnectivityAwareRandomAgent(BaseAgent):
    def __init__(
        self,
        seed: int,
        name: str = "connectivity_aware_random_baseline",
    ) -> None:
        super().__init__(name=name)
        self._rng = Random(seed)

    def decide(self, state: CityState) -> list[Action]:
        if len(state.grid) <= 0:
            return []

        remaining_budget = state.budget
        zones = (ZONE_RESIDENTIAL, ZONE_COMMERCIAL, ZONE_INDUSTRIAL, ZONE_ROAD)
        actions: list[Action] = []
        targeted_tiles: set[tuple[int, int]] = set()
        connectivity = get_connectivity_info(state)
        empty_with_road = connectivity["empty_with_road"]
        empty_without_road = connectivity["empty_without_road"]

        if not can_afford_affordability_aware_action(remaining_budget):
            return []

        for _ in range(self._rng.randint(1, MAX_ACTIONS_PER_TURN)):
            if not can_afford_affordability_aware_action(remaining_budget):
                break

            empty_with_road = filter_untargeted_tiles(empty_with_road, targeted_tiles)
            empty_without_road = filter_untargeted_tiles(
                empty_without_road,
                targeted_tiles,
            )
            all_empty = empty_with_road + empty_without_road

            if not all_empty:
                break

            if remaining_budget < _MIN_NON_ROAD_ZONE_COST:
                if not empty_with_road:
                    break
                x, y = self._rng.choice(empty_with_road)
                zone = ZONE_ROAD
            else:
                if self._rng.random() < 0.7 and empty_with_road:
                    x, y = self._rng.choice(empty_with_road)
                else:
                    x, y = self._rng.choice(all_empty)

                affordable_zones = [
                    zone for zone in zones if remaining_budget >= get_zone_cost(zone)
                ]
                if not affordable_zones:
                    break
                zone = self._rng.choice(affordable_zones)
            cost = get_zone_cost(zone)

            if remaining_budget >= cost:
                actions.append(Action(type="zone", x=x, y=y, zone=zone))
                remaining_budget -= cost
                targeted_tiles.add((x, y))

        return actions
