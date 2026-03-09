from config import COST_COMMERCIAL, COST_INDUSTRIAL, COST_RESIDENTIAL, COST_ROAD
from sim.city import CityState
from sim.grid import (
    ZONE_COMMERCIAL,
    ZONE_EMPTY,
    ZONE_INDUSTRIAL,
    ZONE_RESIDENTIAL,
    ZONE_ROAD,
)

_ZONE_COSTS = {
    ZONE_ROAD: COST_ROAD,
    ZONE_RESIDENTIAL: COST_RESIDENTIAL,
    ZONE_COMMERCIAL: COST_COMMERCIAL,
    ZONE_INDUSTRIAL: COST_INDUSTRIAL,
}


def filter_untargeted_tiles(
    tiles: list[tuple[int, int]],
    targeted_tiles: set[tuple[int, int]],
) -> list[tuple[int, int]]:
    return [tile for tile in tiles if tile not in targeted_tiles]


def can_afford_affordability_aware_action(remaining_budget: float) -> bool:
    return remaining_budget >= COST_ROAD


def get_connectivity_info(state: CityState) -> dict[str, int | list[tuple[int, int]]]:
    height = len(state.grid)
    if height == 0:
        return {
            "empty_with_road": [],
            "empty_without_road": [],
            "connected_residential": 0,
            "connected_commercial": 0,
            "connected_industrial": 0,
            "total_empty": 0,
        }

    empty_with_road: list[tuple[int, int]] = []
    empty_without_road: list[tuple[int, int]] = []
    connected_residential = 0
    connected_commercial = 0
    connected_industrial = 0

    for y in range(height):
        row_width = len(state.grid[y])
        for x in range(row_width):
            tile = state.grid[y][x]
            if tile.zone == ZONE_EMPTY:
                if tile.disabled:
                    continue
                has_road_neighbor = False
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if not 0 <= ny < height:
                        continue
                    neighbor_row = state.grid[ny]
                    if not 0 <= nx < len(neighbor_row):
                        continue
                    neighbor = neighbor_row[nx]
                    if neighbor.zone == ZONE_ROAD and not neighbor.disabled:
                        has_road_neighbor = True
                        break
                if has_road_neighbor:
                    empty_with_road.append((x, y))
                else:
                    empty_without_road.append((x, y))
            elif tile.connected:
                if tile.zone == ZONE_RESIDENTIAL:
                    connected_residential += 1
                elif tile.zone == ZONE_COMMERCIAL:
                    connected_commercial += 1
                elif tile.zone == ZONE_INDUSTRIAL:
                    connected_industrial += 1

    return {
        "empty_with_road": empty_with_road,
        "empty_without_road": empty_without_road,
        "connected_residential": connected_residential,
        "connected_commercial": connected_commercial,
        "connected_industrial": connected_industrial,
        "total_empty": len(empty_with_road) + len(empty_without_road),
    }


def get_zone_cost(zone: str) -> int:
    try:
        return _ZONE_COSTS[zone]
    except KeyError as exc:
        raise ValueError(f"Unknown zone '{zone}'.") from exc
