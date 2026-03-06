# duplicate snapshot marker kept as comment

import pytest

from sim.grid import Grid, VALID_ZONES, ZONE_EMPTY, ZONE_RESIDENTIAL, ZONE_ROAD


def test_initial_state() -> None:
    grid = Grid(size=3)
    tiles = list(grid.iter_tiles())
    assert len(tiles) == 9
    assert all(tile.zone == ZONE_EMPTY for tile in tiles)
    assert all(tile.connected is False for tile in tiles)
    assert all(tile.disabled is False for tile in tiles)


def test_set_zone_valid() -> None:
    grid = Grid(size=2)
    for zone in VALID_ZONES:
        grid.set_zone(0, 0, zone)
        assert grid.get_tile(0, 0).zone == zone


def test_set_zone_invalid() -> None:
    grid = Grid(size=2)
    with pytest.raises(ValueError):
        grid.set_zone(0, 0, "X")


def test_set_zone_clears_disabled_for_non_empty() -> None:
    grid = Grid(size=2)
    tile = grid.get_tile(1, 1)
    tile.disabled = True
    grid.set_zone(1, 1, ZONE_ROAD)
    assert tile.disabled is False


def test_set_zone_empty_clears_connected() -> None:
    grid = Grid(size=2)
    tile = grid.get_tile(1, 1)
    tile.connected = True
    grid.set_zone(1, 1, ZONE_EMPTY)
    assert tile.connected is False


def test_in_bounds_edges() -> None:
    grid = Grid(size=3)
    assert grid.in_bounds(0, 0)
    assert grid.in_bounds(2, 2)
    assert not grid.in_bounds(-1, 0)
    assert not grid.in_bounds(0, 3)


def test_orthogonal_and_moore_neighbor_counts() -> None:
    grid = Grid(size=3)
    assert len(list(grid.orthogonal_neighbors(0, 0))) == 2
    assert len(list(grid.orthogonal_neighbors(1, 1))) == 4
    assert len(list(grid.moore_neighbors(0, 0))) == 3
    assert len(list(grid.moore_neighbors(1, 1))) == 8


def test_connectivity_requires_active_road() -> None:
    grid = Grid(size=3)
    grid.set_zone(1, 1, ZONE_RESIDENTIAL)
    grid.set_zone(1, 0, ZONE_ROAD)
    grid.recompute_connectivity()
    assert grid.get_tile(1, 1).connected is True


def test_disabled_road_breaks_connectivity() -> None:
    grid = Grid(size=3)
    grid.set_zone(1, 1, ZONE_RESIDENTIAL)
    grid.set_zone(1, 0, ZONE_ROAD)
    grid.get_tile(1, 0).disabled = True
    grid.recompute_connectivity()
    assert grid.get_tile(1, 1).connected is False