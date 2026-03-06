from __future__ import annotations

from agents.base import BaseAgent
from sim.city import Action, CityState
from sim.grid import (
    ZONE_COMMERCIAL,
    ZONE_EMPTY,
    ZONE_INDUSTRIAL,
    ZONE_RESIDENTIAL,
    ZONE_ROAD,
)


class HeuristicAgent(BaseAgent):
    def __init__(self, name: str = "heuristic_baseline") -> None:
        super().__init__(name=name)

    def decide(self, state: CityState) -> list[Action]:
        grid_size = len(state.grid)
        if grid_size <= 0:
            return []

        turn = state.tick

        # Phase 1: road spine at x=1.
        if 0 <= turn <= 5:
            y = min(turn, grid_size - 1)
            return [Action(type="zone", x=min(1, grid_size - 1), y=y, zone=ZONE_ROAD)]

        # Phase 2: R/C stripes around the road spine.
        if 6 <= turn <= 15:
            y = min(turn - 6, grid_size - 1)
            actions: list[Action] = []
            if 0 < grid_size:
                actions.append(Action(type="zone", x=0, y=y, zone=ZONE_RESIDENTIAL))
            if 2 < grid_size:
                actions.append(Action(type="zone", x=2, y=y, zone=ZONE_COMMERCIAL))
            return actions

        # Phase 3: keep industrial far from residential at far edge.
        if 16 <= turn <= 25:
            y = min(turn - 16, grid_size - 1)
            x = grid_size - 1
            return [Action(type="zone", x=x, y=y, zone=ZONE_INDUSTRIAL)]

        # Phase 4: fill empty cells next to roads with alternating R/C.
        zone = ZONE_RESIDENTIAL if turn % 2 == 0 else ZONE_COMMERCIAL
        for row in state.grid:
            for tile in row:
                if tile.zone != ZONE_EMPTY:
                    continue
                if self._has_adjacent_road(state, tile.x, tile.y):
                    return [Action(type="zone", x=tile.x, y=tile.y, zone=zone)]
        return []

    def _has_adjacent_road(self, state: CityState, x: int, y: int) -> bool:
        height = len(state.grid)
        width = len(state.grid[0]) if height else 0
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx = x + dx
            ny = y + dy
            if nx < 0 or ny < 0 or nx >= width or ny >= height:
                continue
            neighbor = state.grid[ny][nx]
            if neighbor.zone == ZONE_ROAD and not neighbor.disabled:
                return True
        return False

