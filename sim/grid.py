from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from config import GRID_SIZE

ZONE_EMPTY = "E"
ZONE_RESIDENTIAL = "R"
ZONE_COMMERCIAL = "C"
ZONE_INDUSTRIAL = "I"
ZONE_ROAD = "O"
VALID_ZONES = {ZONE_EMPTY, ZONE_RESIDENTIAL, ZONE_COMMERCIAL, ZONE_INDUSTRIAL, ZONE_ROAD}


@dataclass
class TileState:
    x: int
    y: int
    zone: str = ZONE_EMPTY
    pollution: float = 0.0
    connected: bool = False
    disabled: bool = False


class Grid:
    def __init__(self, size: int = GRID_SIZE) -> None:
        self.size = size
        self.tiles: list[list[TileState]] = [
            [TileState(x=x, y=y) for x in range(size)] for y in range(size)
        ]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def get_tile(self, x: int, y: int) -> TileState:
        return self.tiles[y][x]

    def set_zone(self, x: int, y: int, zone: str) -> None:
        if zone not in VALID_ZONES:
            raise ValueError(f"Invalid zone '{zone}'.")
        tile = self.get_tile(x, y)
        tile.zone = zone
        if zone != ZONE_EMPTY:
            tile.disabled = False
        if zone == ZONE_EMPTY:
            tile.connected = False

    def iter_tiles(self) -> Iterator[TileState]:
        for row in self.tiles:
            for tile in row:
                yield tile

    def iter_tiles_by_zone(self, zone: str) -> Iterator[TileState]:
        for tile in self.iter_tiles():
            if tile.zone == zone:
                yield tile

    def orthogonal_neighbors(self, x: int, y: int) -> Iterator[TileState]:
        offsets = ((1, 0), (-1, 0), (0, 1), (0, -1))
        for dx, dy in offsets:
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny):
                yield self.get_tile(nx, ny)

    def moore_neighbors(self, x: int, y: int) -> Iterator[TileState]:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if self.in_bounds(nx, ny):
                    yield self.get_tile(nx, ny)

    def has_adjacent_active_road(self, x: int, y: int) -> bool:
        for neighbor in self.orthogonal_neighbors(x, y):
            if neighbor.zone == ZONE_ROAD and not neighbor.disabled:
                return True
        return False

    def recompute_connectivity(self) -> None:
        for tile in self.iter_tiles():
            if tile.zone in (ZONE_EMPTY, ZONE_ROAD):
                tile.connected = False
                continue
            tile.connected = self.has_adjacent_active_road(tile.x, tile.y)
