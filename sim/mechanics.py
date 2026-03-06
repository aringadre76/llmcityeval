from __future__ import annotations

import math

from config import (
    BANKRUPTCY_POP_PENALTY,
    COMMERCIAL_BONUS,
    CONGESTION_WEIGHT,
    EXPENSE_ROAD,
    EXPENSE_ZONE,
    LIVABILITY_BASE,
    POLLUTION_DECAY,
    POLLUTION_EMISSION,
    POLLUTION_PENALTY,
    POLLUTION_SPREAD_FACTOR,
    POP_CHANGE_RATE,
    POP_PER_RESIDENTIAL,
    REVENUE_COMMERCIAL,
    REVENUE_INDUSTRIAL,
    REVENUE_RESIDENTIAL,
)
from sim.grid import Grid, ZONE_COMMERCIAL, ZONE_EMPTY, ZONE_INDUSTRIAL, ZONE_RESIDENTIAL, ZONE_ROAD


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def compute_revenue(grid: Grid, recession_count: int) -> float:
    revenue = 0.0
    for tile in grid.iter_tiles():
        if not tile.connected:
            continue
        if tile.zone == ZONE_RESIDENTIAL:
            revenue += REVENUE_RESIDENTIAL
        elif tile.zone == ZONE_COMMERCIAL:
            revenue += REVENUE_COMMERCIAL
        elif tile.zone == ZONE_INDUSTRIAL:
            revenue += REVENUE_INDUSTRIAL
    if recession_count > 0:
        revenue *= 0.5 ** recession_count
    return revenue


def compute_expenses(grid: Grid) -> float:
    road_tiles = sum(1 for tile in grid.iter_tiles() if tile.zone == ZONE_ROAD)
    non_empty_tiles = sum(1 for tile in grid.iter_tiles() if tile.zone != ZONE_EMPTY)
    return road_tiles * EXPENSE_ROAD + non_empty_tiles * EXPENSE_ZONE


def compute_pollution_avg(grid: Grid) -> float:
    values = [tile.pollution for tile in grid.iter_tiles()]
    return sum(values) / len(values) if values else 0.0


def compute_livability(grid: Grid, pollution_avg: float) -> float:
    land_use_tiles = sum(
        1 for t in grid.iter_tiles() if t.zone in (ZONE_RESIDENTIAL, ZONE_COMMERCIAL, ZONE_INDUSTRIAL)
    )
    commercial_tiles = sum(1 for t in grid.iter_tiles() if t.zone == ZONE_COMMERCIAL)
    developed_tiles = sum(
        1 for t in grid.iter_tiles() if t.zone in (ZONE_RESIDENTIAL, ZONE_COMMERCIAL, ZONE_INDUSTRIAL)
    )
    road_tiles = sum(1 for t in grid.iter_tiles() if t.zone == ZONE_ROAD)

    commercial_ratio = (commercial_tiles / land_use_tiles) if land_use_tiles > 0 else 0.0
    if developed_tiles == 0:
        congestion_penalty = 0.0
    else:
        congestion_penalty = max(0.0, 1.0 - (road_tiles / developed_tiles)) * CONGESTION_WEIGHT

    livability = (
        LIVABILITY_BASE
        - (pollution_avg * POLLUTION_PENALTY)
        + (commercial_ratio * COMMERCIAL_BONUS)
        - congestion_penalty
    )
    return clamp(livability, 0.0, 1.0)


def compute_target_population(
    connected_residential_tiles: int,
    livability: float,
    demand_surge_divisor: float,
) -> float:
    return (
        connected_residential_tiles
        * POP_PER_RESIDENTIAL
        * (0.5 + livability * 0.5)
        / demand_surge_divisor
    )


def advance_population(current_population: float, target_population: float, bankrupt: bool) -> int:
    next_population = current_population + (target_population - current_population) * POP_CHANGE_RATE
    if bankrupt:
        next_population = next_population * (1 - BANKRUPTCY_POP_PENALTY)
    return max(0, math.floor(next_population))


def spread_pollution(grid: Grid) -> None:
    additions = [[0.0 for _ in range(grid.size)] for _ in range(grid.size)]

    for tile in grid.iter_tiles():
        if tile.zone != ZONE_INDUSTRIAL:
            continue
        additions[tile.y][tile.x] += POLLUTION_EMISSION
        for neighbor in grid.moore_neighbors(tile.x, tile.y):
            additions[neighbor.y][neighbor.x] += POLLUTION_SPREAD_FACTOR

    for tile in grid.iter_tiles():
        tile.pollution += additions[tile.y][tile.x]
        tile.pollution = clamp(tile.pollution - POLLUTION_DECAY, 0.0, 1.0)
