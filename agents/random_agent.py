from __future__ import annotations

from random import Random

from agents.base import BaseAgent
from sim.city import Action, CityState
from sim.grid import ZONE_COMMERCIAL, ZONE_INDUSTRIAL, ZONE_RESIDENTIAL, ZONE_ROAD


class RandomAgent(BaseAgent):
    def __init__(self, seed: int, name: str = "random_baseline") -> None:
        super().__init__(name=name)
        self._rng = Random(seed)

    def decide(self, state: CityState) -> list[Action]:
        grid_size = len(state.grid)
        if grid_size <= 0:
            return []
        action_count = self._rng.randint(1, 5)
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
