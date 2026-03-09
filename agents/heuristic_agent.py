from __future__ import annotations

from heapq import nlargest
from random import Random

from agents.base import BaseAgent
from agents.utils import filter_untargeted_tiles, get_connectivity_info, get_zone_cost
from config import MAX_ACTIONS_PER_TURN
from sim.city import Action, CityState
from sim.grid import (
    ZONE_COMMERCIAL,
    ZONE_INDUSTRIAL,
    ZONE_RESIDENTIAL,
    ZONE_ROAD,
)


_ZONE_PRIORITY = (ZONE_RESIDENTIAL, ZONE_COMMERCIAL, ZONE_INDUSTRIAL)


def _road_spine_x(grid_size: int) -> int:
    return min(1, grid_size - 1)


def _available_connected_tiles(
    connectivity: dict[str, int | list[tuple[int, int]]],
    targeted_tiles: set[tuple[int, int]],
) -> list[tuple[int, int]]:
    return filter_untargeted_tiles(connectivity["empty_with_road"], targeted_tiles)


def _add_action(
    actions: list[Action],
    targeted_tiles: set[tuple[int, int]],
    remaining_budget: float,
    x: int,
    y: int,
    zone: str,
) -> float:
    cost = get_zone_cost(zone)
    if remaining_budget < cost:
        return remaining_budget
    actions.append(Action(type="zone", x=x, y=y, zone=zone))
    targeted_tiles.add((x, y))
    return remaining_budget - cost


def _fill_connected_tiles(
    actions: list[Action],
    targeted_tiles: set[tuple[int, int]],
    remaining_budget: float,
    candidate_tiles: list[tuple[int, int]],
    zone_priority: list[str] | tuple[str, ...],
    max_actions: int,
) -> float:
    for x, y in candidate_tiles:
        if len(actions) >= max_actions:
            break
        for zone in zone_priority:
            updated_budget = _add_action(
                actions,
                targeted_tiles,
                remaining_budget,
                x,
                y,
                zone,
            )
            if updated_budget != remaining_budget:
                remaining_budget = updated_budget
                break
    return remaining_budget


class BudgetAwareHeuristicAgent(BaseAgent):
    """Build a road spine early, then prioritize connected expansion within budget."""

    def __init__(
        self,
        seed: int = 0,
        name: str = "budget_aware_baseline",
    ) -> None:
        super().__init__(name=name)
        self._rng = Random(seed)

    def decide(self, state: CityState) -> list[Action]:
        grid_size = len(state.grid)
        if grid_size <= 0:
            return []

        actions: list[Action] = []
        targeted_tiles: set[tuple[int, int]] = set()
        remaining_budget = state.budget
        turn = state.tick

        max_actions = min(MAX_ACTIONS_PER_TURN, len(state.grid))

        connectivity = get_connectivity_info(state)

        if turn < 6:
            target_y = min(turn, grid_size - 1)
            remaining_budget = _add_action(
                actions,
                targeted_tiles,
                remaining_budget,
                _road_spine_x(grid_size),
                target_y,
                ZONE_ROAD,
            )
        elif turn < 11:
            target_y = min(turn - 5, grid_size - 1)
            if target_y > 0:
                remaining_budget = _add_action(
                    actions,
                    targeted_tiles,
                    remaining_budget,
                    1,
                    target_y,
                    ZONE_ROAD,
                )
        elif turn < 26 and connectivity["empty_with_road"]:
            remaining_budget = _fill_connected_tiles(
                actions,
                targeted_tiles,
                remaining_budget,
                _available_connected_tiles(connectivity, targeted_tiles),
                _ZONE_PRIORITY,
                max_actions,
            )
        elif connectivity["empty_with_road"]:
            zone_options = list(_ZONE_PRIORITY)
            self._rng.shuffle(zone_options)
            remaining_budget = _fill_connected_tiles(
                actions,
                targeted_tiles,
                remaining_budget,
                _available_connected_tiles(connectivity, targeted_tiles),
                zone_options,
                max_actions,
            )

        return actions


class ConnectivityAwareHeuristicAgent(BaseAgent):
    """Prefer connected tiles so each turn compounds road network coverage."""

    def __init__(
        self,
        seed: int,
        name: str = "connectivity_aware_baseline",
    ) -> None:
        super().__init__(name=name)
        self._rng = Random(seed)

    def decide(self, state: CityState) -> list[Action]:
        grid_size = len(state.grid)
        if grid_size <= 0:
            return []

        actions: list[Action] = []
        targeted_tiles: set[tuple[int, int]] = set()
        remaining_budget = state.budget
        turn = state.tick

        max_actions = min(MAX_ACTIONS_PER_TURN, len(state.grid))

        connectivity = get_connectivity_info(state)

        if turn < 6:
            target_y = min(turn, grid_size - 1)
            remaining_budget = _add_action(
                actions,
                targeted_tiles,
                remaining_budget,
                _road_spine_x(grid_size),
                target_y,
                ZONE_ROAD,
            )
        elif turn < 21 and connectivity["empty_with_road"]:
            candidate_tiles = _available_connected_tiles(connectivity, targeted_tiles)
            self._rng.shuffle(candidate_tiles)
            for x, y in candidate_tiles:
                if len(actions) >= max_actions:
                    break
                updated_budget = _add_action(
                    actions,
                    targeted_tiles,
                    remaining_budget,
                    x,
                    y,
                    ZONE_ROAD,
                )
                if updated_budget != remaining_budget:
                    remaining_budget = updated_budget
                    continue
                remaining_budget = _add_action(
                    actions,
                    targeted_tiles,
                    remaining_budget,
                    x,
                    y,
                    ZONE_RESIDENTIAL,
                )
        elif turn < 36 and connectivity["empty_with_road"]:
            zone_priority = list(_ZONE_PRIORITY)
            self._rng.shuffle(zone_priority)
            remaining_budget = _fill_connected_tiles(
                actions,
                targeted_tiles,
                remaining_budget,
                _available_connected_tiles(connectivity, targeted_tiles),
                zone_priority,
                max_actions,
            )
        elif turn < 40 and connectivity["empty_with_road"]:
            candidate_tiles = _available_connected_tiles(connectivity, targeted_tiles)
            for x, y in candidate_tiles:
                if len(actions) >= max_actions:
                    break
                updated_budget = _add_action(
                    actions,
                    targeted_tiles,
                    remaining_budget,
                    x,
                    y,
                    ZONE_RESIDENTIAL,
                )
                if updated_budget != remaining_budget:
                    remaining_budget = updated_budget
                    continue
                remaining_budget = _add_action(
                    actions,
                    targeted_tiles,
                    remaining_budget,
                    x,
                    y,
                    ZONE_ROAD,
                )
        elif connectivity["empty_with_road"]:
            zone_priority = list(_ZONE_PRIORITY)
            self._rng.shuffle(zone_priority)
            remaining_budget = _fill_connected_tiles(
                actions,
                targeted_tiles,
                remaining_budget,
                _available_connected_tiles(connectivity, targeted_tiles),
                zone_priority,
                max_actions,
            )

        return actions


class HybridBudgetConnectivityAgent(BaseAgent):
    """Mix road-first setup with budget-weighted connected-zone expansion."""

    def __init__(
        self,
        seed: int,
        name: str = "hybrid_budget_connectivity_baseline",
    ) -> None:
        super().__init__(name=name)
        self._rng = Random(seed)

    def decide(self, state: CityState) -> list[Action]:
        grid_size = len(state.grid)
        if grid_size <= 0:
            return []

        actions: list[Action] = []
        targeted_tiles: set[tuple[int, int]] = set()
        remaining_budget = state.budget
        turn = state.tick

        max_actions = min(MAX_ACTIONS_PER_TURN, len(state.grid))

        connectivity = get_connectivity_info(state)

        if turn < 6:
            target_y = min(turn, grid_size - 1)
            remaining_budget = _add_action(
                actions,
                targeted_tiles,
                remaining_budget,
                _road_spine_x(grid_size),
                target_y,
                ZONE_ROAD,
            )
        elif turn < 16:
            target_y = min(turn - 5, grid_size - 1)
            remaining_budget = _add_action(
                actions,
                targeted_tiles,
                remaining_budget,
                1,
                target_y,
                ZONE_ROAD,
            )
        elif turn < 31 and connectivity["empty_with_road"]:
            scored_tiles: list[tuple[float, int, int, str]] = []

            candidate_tiles = _available_connected_tiles(connectivity, targeted_tiles)
            for x, y in candidate_tiles:
                base_score = 1.0
                if turn < 20:
                    base_score = 1.5

                best_zone = None
                best_cost = float("inf")
                for zone in _ZONE_PRIORITY:
                    cost = get_zone_cost(zone)
                    if remaining_budget >= cost and cost < best_cost:
                        best_zone = zone
                        best_cost = cost

                if best_zone:
                    score = base_score * (100 / best_cost)
                    scored_tiles.append((score, x, y, best_zone))

            scored_tiles = nlargest(max_actions, scored_tiles, key=lambda t: t[0])

            for _, x, y, zone in scored_tiles:
                if len(actions) >= max_actions:
                    break
                cost = get_zone_cost(zone)
                if remaining_budget >= cost:
                    actions.append(Action(type="zone", x=x, y=y, zone=zone))
                    targeted_tiles.add((x, y))
                    remaining_budget -= cost

        elif turn < 41 and connectivity["empty_with_road"]:
            zone_priority = list(_ZONE_PRIORITY)
            self._rng.shuffle(zone_priority)
            remaining_budget = _fill_connected_tiles(
                actions,
                targeted_tiles,
                remaining_budget,
                _available_connected_tiles(connectivity, targeted_tiles),
                zone_priority,
                max_actions,
            )
        elif connectivity["empty_with_road"]:
            zone_priority = list(_ZONE_PRIORITY)
            self._rng.shuffle(zone_priority)
            remaining_budget = _fill_connected_tiles(
                actions,
                targeted_tiles,
                remaining_budget,
                _available_connected_tiles(connectivity, targeted_tiles),
                zone_priority,
                max_actions,
            )

        return actions


# Backward compatibility alias with a default seed preserved on the class.
HeuristicAgent = BudgetAwareHeuristicAgent


__all__ = [
    "BudgetAwareHeuristicAgent",
    "ConnectivityAwareHeuristicAgent",
    "HeuristicAgent",
    "HybridBudgetConnectivityAgent",
]
