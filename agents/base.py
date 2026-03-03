from __future__ import annotations

from abc import ABC, abstractmethod

from sim.city import Action, CityState


class BaseAgent(ABC):
    def __init__(self, name: str) -> None:
        self.name = name
        self.last_parse_success = True

    @abstractmethod
    def decide(self, state: CityState) -> list[Action]:
        raise NotImplementedError
