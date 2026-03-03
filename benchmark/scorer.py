from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import Any

from config import EFFICIENCY_SCALING_FACTOR, THEORETICAL_MAX_POP


def _clamp_0_100(value: float) -> float:
    return max(0.0, min(100.0, value))


def _population_series(run_data: dict[str, Any]) -> list[float]:
    turns = run_data.get("turns", [])
    values = [float((turn.get("state") or {}).get("population", 0.0)) for turn in turns]
    final_state = run_data.get("final_state") or {}
    values.append(float(final_state.get("population", 0.0)))
    return values


def _resilience_score(run_data: dict[str, Any], populations: list[float]) -> float:
    events: list[tuple[int, dict[str, Any]]] = []
    for turn in run_data.get("turns", []):
        turn_index = int(turn.get("turn", 0))
        for event in turn.get("disaster_events", []):
            events.append((turn_index, event))

    if not events:
        return 100.0

    event_scores: list[float] = []
    n = len(populations)
    for turn_index, _event in events:
        before_start = max(0, turn_index - 5)
        before_end = max(0, turn_index)
        before_window = populations[before_start:before_end]
        if not before_window:
            before_window = [populations[max(0, min(turn_index, n - 1))]]

        after_start = min(n, turn_index + 1)
        after_end = min(n, turn_index + 6)
        after_window = populations[after_start:after_end]
        if not after_window:
            after_window = [populations[max(0, min(turn_index, n - 1))]]

        before_avg = mean(before_window)
        after_avg = mean(after_window)
        if before_avg <= 0:
            ratio = 100.0
        else:
            ratio = (after_avg / before_avg) * 100.0
        event_scores.append(_clamp_0_100(ratio))

    return _clamp_0_100(mean(event_scores))


def score_run(run_data: dict[str, Any]) -> dict[str, float]:
    final_population = float((run_data.get("final_state") or {}).get("population", 0.0))
    population = (final_population / THEORETICAL_MAX_POP) * 100.0

    total_budget_spent = sum(float(turn.get("budget_spent", 0.0)) for turn in run_data.get("turns", []))
    if total_budget_spent <= 0:
        efficiency = 0.0
    else:
        efficiency = _clamp_0_100((final_population / total_budget_spent) * EFFICIENCY_SCALING_FACTOR)

    populations = _population_series(run_data)
    population_mean = mean(populations) if populations else 0.0
    if population_mean <= 0:
        stability = 0.0
    else:
        variation = pstdev(populations) if len(populations) > 1 else 0.0
        stability = _clamp_0_100((1.0 - (variation / population_mean)) * 100.0)
        if math.isnan(stability):
            stability = 0.0

    resilience = _resilience_score(run_data, populations)

    composite = (population + efficiency + stability + resilience) / 4.0
    return {
        "population": population,
        "efficiency": efficiency,
        "stability": stability,
        "resilience": resilience,
        "composite": composite,
    }
