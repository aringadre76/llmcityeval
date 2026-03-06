from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Any

from sim.grid import Grid, ZONE_INDUSTRIAL, ZONE_ROAD
from sim.runtime_config import SimConfig

DISASTER_RECESSION = "recession"
DISASTER_DEMAND_SURGE = "demand_surge"
DISASTER_INFRA_FAILURE = "infrastructure_failure"
DISASTER_POLLUTION_EVENT = "pollution_event"


@dataclass
class ActiveDisaster:
    disaster_type: str
    ticks_remaining: int
    metadata: dict[str, Any]


class DisasterManager:
    def __init__(self, sim_config: SimConfig | None = None) -> None:
        self.sim_config = sim_config or SimConfig.from_module()
        self._active: list[ActiveDisaster] = []

    @property
    def active(self) -> list[ActiveDisaster]:
        return list(self._active)

    def update_active_disasters(self, grid: Grid) -> list[str]:
        messages: list[str] = []
        remaining: list[ActiveDisaster] = []
        for disaster in self._active:
            disaster.ticks_remaining -= 1
            if disaster.ticks_remaining <= 0:
                if disaster.disaster_type == DISASTER_INFRA_FAILURE:
                    x, y = disaster.metadata["x"], disaster.metadata["y"]
                    if grid.in_bounds(x, y):
                        tile = grid.get_tile(x, y)
                        tile.disabled = False
                continue

            remaining.append(disaster)
            if disaster.disaster_type == DISASTER_RECESSION:
                messages.append(
                    f"RECESSION ONGOING: {disaster.ticks_remaining} ticks remaining."
                )
            elif disaster.disaster_type == DISASTER_DEMAND_SURGE:
                messages.append(
                    f"DEMAND SURGE ONGOING: {disaster.ticks_remaining} ticks remaining."
                )
            elif disaster.disaster_type == DISASTER_INFRA_FAILURE:
                x, y = disaster.metadata["x"], disaster.metadata["y"]
                messages.append(
                    "INFRASTRUCTURE FAILURE ONGOING: "
                    f"Road at ({x}, {y}) disabled, {disaster.ticks_remaining} tick"
                    f"{'s' if disaster.ticks_remaining != 1 else ''} remaining."
                )
        self._active = remaining
        return messages

    def roll_new_disasters(self, rng: Random, grid: Grid) -> tuple[list[str], list[dict[str, Any]]]:
        messages: list[str] = []
        triggered: list[dict[str, Any]] = []

        if rng.random() < self.sim_config.disaster_recession_prob:
            self._active.append(
                ActiveDisaster(
                    disaster_type=DISASTER_RECESSION,
                    ticks_remaining=self.sim_config.disaster_recession_duration,
                    metadata={},
                )
            )
            messages.append("RECESSION: Revenue halved for 3 ticks.")
            triggered.append({"event": DISASTER_RECESSION, "outcome": "applied"})

        if rng.random() < self.sim_config.disaster_demand_surge_prob:
            self._active.append(
                ActiveDisaster(
                    disaster_type=DISASTER_DEMAND_SURGE,
                    ticks_remaining=self.sim_config.disaster_demand_surge_duration,
                    metadata={},
                )
            )
            messages.append("DEMAND SURGE: Population capacity reduced for 3 ticks.")
            triggered.append({"event": DISASTER_DEMAND_SURGE, "outcome": "applied"})

        if rng.random() < self.sim_config.disaster_infra_fail_prob:
            road_tiles = [t for t in grid.iter_tiles() if t.zone == ZONE_ROAD]
            if not road_tiles:
                triggered.append(
                    {
                        "event": DISASTER_INFRA_FAILURE,
                        "outcome": "skipped",
                        "reason": "no_road_tiles",
                    }
                )
            else:
                target = road_tiles[rng.randrange(len(road_tiles))]
                target.disabled = True
                self._active.append(
                    ActiveDisaster(
                        disaster_type=DISASTER_INFRA_FAILURE,
                        ticks_remaining=self.sim_config.disaster_infra_fail_duration,
                        metadata={"x": target.x, "y": target.y},
                    )
                )
                messages.append(
                    f"INFRASTRUCTURE FAILURE: Road at ({target.x}, {target.y}) disabled for 2 ticks."
                )
                triggered.append(
                    {
                        "event": DISASTER_INFRA_FAILURE,
                        "outcome": "applied",
                        "x": target.x,
                        "y": target.y,
                    }
                )

        if rng.random() < self.sim_config.disaster_pollution_prob:
            candidates = []
            for industrial in grid.iter_tiles():
                if industrial.zone != ZONE_INDUSTRIAL:
                    continue
                for neighbor in grid.moore_neighbors(industrial.x, industrial.y):
                    candidates.append((neighbor.x, neighbor.y))
            unique_candidates = sorted(set(candidates))
            if not unique_candidates:
                triggered.append(
                    {
                        "event": DISASTER_POLLUTION_EVENT,
                        "outcome": "skipped",
                        "reason": "no_industrial_tiles",
                    }
                )
            else:
                x, y = unique_candidates[rng.randrange(len(unique_candidates))]
                tile = grid.get_tile(x, y)
                increment = self.sim_config.pollution_event_increment
                tile.pollution = min(1.0, tile.pollution + increment)
                messages.append(f"POLLUTION EVENT: Tile ({x}, {y}) received +{increment:.1f} pollution.")
                triggered.append(
                    {"event": DISASTER_POLLUTION_EVENT, "outcome": "applied", "x": x, "y": y}
                )

        return messages, triggered

    def active_recession_count(self) -> int:
        return sum(1 for d in self._active if d.disaster_type == DISASTER_RECESSION)

    def active_demand_surge_divisor(self) -> float:
        count = sum(1 for d in self._active if d.disaster_type == DISASTER_DEMAND_SURGE)
        if count == 0:
            return 1.0
        divisor = 1.0
        for _ in range(count):
            divisor *= self.sim_config.demand_surge_divisor
        return divisor
