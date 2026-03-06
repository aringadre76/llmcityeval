from __future__ import annotations

from config import (
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
from sim.grid import Grid, ZONE_COMMERCIAL, ZONE_INDUSTRIAL, ZONE_RESIDENTIAL, ZONE_ROAD
from sim.mechanics import (
    advance_population,
    compute_expenses,
    compute_livability,
    compute_pollution_avg,
    compute_revenue,
    compute_target_population,
    spread_pollution,
)


def test_compute_revenue_uses_connected_tiles_and_recession_multiplier() -> None:
    grid = Grid(size=3)
    r = grid.get_tile(0, 0)
    r.zone = ZONE_RESIDENTIAL
    r.connected = True
    c = grid.get_tile(1, 0)
    c.zone = ZONE_COMMERCIAL
    c.connected = True
    i = grid.get_tile(2, 0)
    i.zone = ZONE_INDUSTRIAL
    i.connected = False

    no_recession = compute_revenue(grid, recession_count=0)
    two_recessions = compute_revenue(grid, recession_count=2)

    expected = REVENUE_RESIDENTIAL + REVENUE_COMMERCIAL
    assert no_recession == expected
    assert two_recessions == expected * (0.5**2)


def test_compute_expenses_counts_roads_and_non_empty_tiles() -> None:
    grid = Grid(size=3)
    grid.set_zone(0, 0, ZONE_ROAD)
    grid.set_zone(1, 1, ZONE_RESIDENTIAL)

    expenses = compute_expenses(grid)
    assert expenses == (1 * EXPENSE_ROAD) + (2 * EXPENSE_ZONE)


def test_compute_pollution_avg() -> None:
    grid = Grid(size=3)
    grid.get_tile(0, 0).pollution = 0.3
    grid.get_tile(1, 0).pollution = 0.1

    average = compute_pollution_avg(grid)
    assert average == (0.3 + 0.1) / 9


def test_compute_livability_matches_formula_for_simple_case() -> None:
    grid = Grid(size=3)
    grid.set_zone(0, 0, ZONE_RESIDENTIAL)
    grid.set_zone(1, 0, ZONE_COMMERCIAL)
    grid.set_zone(2, 0, ZONE_ROAD)
    pollution_avg = 0.2

    livability = compute_livability(grid, pollution_avg=pollution_avg)

    commercial_ratio = 1 / 2
    congestion_penalty = max(0.0, 1.0 - (1 / 2)) * CONGESTION_WEIGHT
    expected = (
        LIVABILITY_BASE
        - (pollution_avg * POLLUTION_PENALTY)
        + (commercial_ratio * COMMERCIAL_BONUS)
        - congestion_penalty
    )
    assert livability == expected


def test_target_and_population_advance() -> None:
    target = compute_target_population(
        connected_residential_tiles=2,
        livability=1.0,
        demand_surge_divisor=1.0,
    )
    assert target == 2 * POP_PER_RESIDENTIAL

    next_pop = advance_population(current_population=20, target_population=100, bankrupt=False)
    expected_next = 20 + (100 - 20) * POP_CHANGE_RATE
    assert next_pop == int(expected_next // 1)

    bankrupt_pop = advance_population(current_population=20, target_population=100, bankrupt=True)
    expected_bankrupt = expected_next * (1 - POP_CHANGE_RATE * 0 + 0) * (1 - 0)  # structure only
    assert bankrupt_pop < next_pop


def test_spread_pollution_from_industrial_and_decay() -> None:
    grid = Grid(size=3)
    industrial = grid.get_tile(1, 1)
    industrial.zone = ZONE_INDUSTRIAL

    spread_pollution(grid)

    center = grid.get_tile(1, 1)
    neighbor = grid.get_tile(0, 0)
    expected_center = max(0.0, min(1.0, POLLUTION_EMISSION - POLLUTION_DECAY))
    expected_neighbor = max(0.0, min(1.0, POLLUTION_SPREAD_FACTOR - POLLUTION_DECAY))
    assert center.pollution == expected_center
    assert neighbor.pollution == expected_neighbor

