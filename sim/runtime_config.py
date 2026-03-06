from __future__ import annotations

from dataclasses import dataclass, replace
from types import ModuleType

import config as default_config


@dataclass(frozen=True)
class SimConfig:
    starting_budget: float = float(default_config.STARTING_BUDGET)
    starting_population: int = int(default_config.STARTING_POPULATION)
    demand_surge_divisor: float = float(default_config.DEMAND_SURGE_DIVISOR)
    disaster_recession_prob: float = float(default_config.DISASTER_RECESSION_PROB)
    disaster_demand_surge_prob: float = float(default_config.DISASTER_DEMAND_SURGE_PROB)
    disaster_infra_fail_prob: float = float(default_config.DISASTER_INFRA_FAIL_PROB)
    disaster_pollution_prob: float = float(default_config.DISASTER_POLLUTION_PROB)
    disaster_recession_duration: int = int(default_config.DISASTER_RECESSION_DURATION)
    disaster_demand_surge_duration: int = int(default_config.DISASTER_DEMAND_SURGE_DURATION)
    disaster_infra_fail_duration: int = int(default_config.DISASTER_INFRA_FAIL_DURATION)
    pollution_event_increment: float = 0.4

    @classmethod
    def from_module(cls, config_module: ModuleType = default_config) -> "SimConfig":
        return cls(
            starting_budget=float(config_module.STARTING_BUDGET),
            starting_population=int(config_module.STARTING_POPULATION),
            demand_surge_divisor=float(config_module.DEMAND_SURGE_DIVISOR),
            disaster_recession_prob=float(config_module.DISASTER_RECESSION_PROB),
            disaster_demand_surge_prob=float(config_module.DISASTER_DEMAND_SURGE_PROB),
            disaster_infra_fail_prob=float(config_module.DISASTER_INFRA_FAIL_PROB),
            disaster_pollution_prob=float(config_module.DISASTER_POLLUTION_PROB),
            disaster_recession_duration=int(config_module.DISASTER_RECESSION_DURATION),
            disaster_demand_surge_duration=int(config_module.DISASTER_DEMAND_SURGE_DURATION),
            disaster_infra_fail_duration=int(config_module.DISASTER_INFRA_FAIL_DURATION),
            pollution_event_increment=0.4,
        )

    def with_updates(self, **kwargs: float | int) -> "SimConfig":
        return replace(self, **kwargs)

