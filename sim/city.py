from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Any

from config import (
    COST_CLEAR,
    COST_COMMERCIAL,
    COST_INDUSTRIAL,
    COST_RESIDENTIAL,
    COST_ROAD,
    MAX_ACTIONS_PER_TURN,
    STARTING_BUDGET,
    STARTING_POPULATION,
)
from sim.disasters import DisasterManager
from sim.grid import (
    Grid,
    TileState,
    VALID_ZONES,
    ZONE_COMMERCIAL,
    ZONE_EMPTY,
    ZONE_INDUSTRIAL,
    ZONE_RESIDENTIAL,
    ZONE_ROAD,
)
from sim.mechanics import (
    advance_population,
    compute_expenses,
    compute_livability,
    compute_pollution_avg,
    compute_revenue,
    compute_target_population,
    spread_pollution,
)


@dataclass
class Action:
    type: str
    x: int
    y: int
    zone: str


@dataclass
class CityState:
    tick: int
    budget: float
    population: int
    revenue_per_tick: float
    expenses_per_tick: float
    livability: float
    pollution_avg: float
    grid: list[list[TileState]]
    recent_events: list[str]
    metrics_delta: dict[str, float]
    last_action_outcomes: list[dict[str, Any]]


class City:
    def __init__(self, seed: int) -> None:
        self.rng = Random(seed)
        self.grid = Grid()
        self.disasters = DisasterManager()

        self.tick_count = 0
        self.budget = float(STARTING_BUDGET)
        self.population = int(STARTING_POPULATION)
        self.revenue_per_tick = 0.0
        self.expenses_per_tick = 0.0
        self.livability = 1.0
        self.pollution_avg = 0.0
        self.recent_events: list[str] = []
        self.metrics_delta = self._zero_metrics_delta()

        self._last_action_outcomes: list[dict[str, Any]] = []
        self._last_budget_spent = 0.0
        self._last_disaster_rolls: list[dict[str, Any]] = []

    def _zero_metrics_delta(self) -> dict[str, float]:
        return {
            "budget": 0.0,
            "population": 0.0,
            "revenue_per_tick": 0.0,
            "expenses_per_tick": 0.0,
            "livability": 0.0,
            "pollution_avg": 0.0,
        }

    def _tile_cost(self, current_zone: str, target_zone: str) -> int:
        if current_zone == target_zone:
            return 0
        if target_zone == ZONE_EMPTY:
            return COST_CLEAR if current_zone != ZONE_EMPTY else 0

        build_cost = {
            ZONE_ROAD: COST_ROAD,
            ZONE_RESIDENTIAL: COST_RESIDENTIAL,
            ZONE_COMMERCIAL: COST_COMMERCIAL,
            ZONE_INDUSTRIAL: COST_INDUSTRIAL,
        }[target_zone]
        if current_zone != ZONE_EMPTY:
            return COST_CLEAR + build_cost
        return build_cost

    def _snapshot_grid(self) -> list[list[TileState]]:
        rows: list[list[TileState]] = []
        for y in range(self.grid.size):
            row: list[TileState] = []
            for x in range(self.grid.size):
                tile = self.grid.get_tile(x, y)
                row.append(
                    TileState(
                        x=tile.x,
                        y=tile.y,
                        zone=tile.zone,
                        pollution=tile.pollution,
                        connected=tile.connected,
                        disabled=tile.disabled,
                    )
                )
            rows.append(row)
        return rows

    def get_state(self) -> CityState:
        return CityState(
            tick=self.tick_count,
            budget=self.budget,
            population=self.population,
            revenue_per_tick=self.revenue_per_tick,
            expenses_per_tick=self.expenses_per_tick,
            livability=self.livability,
            pollution_avg=self.pollution_avg,
            grid=self._snapshot_grid(),
            recent_events=list(self.recent_events),
            metrics_delta=dict(self.metrics_delta),
            last_action_outcomes=list(self._last_action_outcomes),
        )

    def get_last_action_outcomes(self) -> list[dict[str, Any]]:
        return list(self._last_action_outcomes)

    def get_last_budget_spent(self) -> float:
        return self._last_budget_spent

    def get_last_disaster_rolls(self) -> list[dict[str, Any]]:
        return list(self._last_disaster_rolls)

    def apply_actions(self, actions: list[Action]) -> None:
        self._last_action_outcomes = []
        self._last_budget_spent = 0.0

        limited_actions = actions[:MAX_ACTIONS_PER_TURN]
        for dropped in actions[MAX_ACTIONS_PER_TURN:]:
            self._last_action_outcomes.append(
                {
                    "action": self._action_to_dict(dropped),
                    "applied": False,
                    "reason": "exceeded_max_actions",
                }
            )

        for action in limited_actions:
            if action.type != "zone":
                self._last_action_outcomes.append(
                    {
                        "action": self._action_to_dict(action),
                        "applied": False,
                        "reason": "invalid_action_type",
                    }
                )
                continue
            if not self.grid.in_bounds(action.x, action.y):
                self._last_action_outcomes.append(
                    {
                        "action": self._action_to_dict(action),
                        "applied": False,
                        "reason": "out_of_bounds",
                    }
                )
                continue
            if action.zone not in VALID_ZONES:
                self._last_action_outcomes.append(
                    {
                        "action": self._action_to_dict(action),
                        "applied": False,
                        "reason": "invalid_zone",
                    }
                )
                continue

            current_tile = self.grid.get_tile(action.x, action.y)
            cost = self._tile_cost(current_tile.zone, action.zone)
            if self.budget < cost:
                self._last_action_outcomes.append(
                    {
                        "action": self._action_to_dict(action),
                        "applied": False,
                        "reason": "insufficient_budget",
                        "cost": cost,
                    }
                )
                continue

            if cost > 0:
                self.budget -= cost
                self._last_budget_spent += cost
            self.grid.set_zone(action.x, action.y, action.zone)
            self._last_action_outcomes.append(
                {
                    "action": self._action_to_dict(action),
                    "applied": True,
                    "cost": cost,
                }
            )

    def tick(self) -> list[dict[str, Any]]:
        previous_metrics = {
            "budget": self.budget,
            "population": float(self.population),
            "revenue_per_tick": self.revenue_per_tick,
            "expenses_per_tick": self.expenses_per_tick,
            "livability": self.livability,
            "pollution_avg": self.pollution_avg,
        }

        self.grid.recompute_connectivity()

        ongoing_messages = self.disasters.update_active_disasters(self.grid)
        new_messages, triggered = self.disasters.roll_new_disasters(self.rng, self.grid)
        self._last_disaster_rolls = triggered

        self.grid.recompute_connectivity()

        spread_pollution(self.grid)

        self.pollution_avg = compute_pollution_avg(self.grid)
        self.revenue_per_tick = compute_revenue(
            self.grid, recession_count=self.disasters.active_recession_count()
        )
        self.expenses_per_tick = compute_expenses(self.grid)
        self.budget += self.revenue_per_tick - self.expenses_per_tick
        self.livability = compute_livability(self.grid, self.pollution_avg)

        connected_residential = sum(
            1
            for tile in self.grid.iter_tiles()
            if tile.zone == ZONE_RESIDENTIAL and tile.connected
        )
        target_pop = compute_target_population(
            connected_residential,
            self.livability,
            self.disasters.active_demand_surge_divisor(),
        )
        self.population = advance_population(
            current_population=float(self.population),
            target_population=target_pop,
            bankrupt=self.budget < 0,
        )

        self.recent_events = ongoing_messages + new_messages
        self.tick_count += 1

        self.metrics_delta = {
            "budget": self.budget - previous_metrics["budget"],
            "population": float(self.population) - previous_metrics["population"],
            "revenue_per_tick": self.revenue_per_tick - previous_metrics["revenue_per_tick"],
            "expenses_per_tick": self.expenses_per_tick - previous_metrics["expenses_per_tick"],
            "livability": self.livability - previous_metrics["livability"],
            "pollution_avg": self.pollution_avg - previous_metrics["pollution_avg"],
        }
        return triggered

    def _action_to_dict(self, action: Action) -> dict[str, Any]:
        return {"type": action.type, "x": action.x, "y": action.y, "zone": action.zone}
