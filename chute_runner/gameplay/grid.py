"""
Factory grid system.
NO UI DEPENDENCIES.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple, Iterator, TYPE_CHECKING
from enum import Enum, auto

if TYPE_CHECKING:
    from .entities import Entity


class Direction(Enum):
    """Cardinal directions."""
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()

    def opposite(self) -> 'Direction':
        """Return the opposite direction."""
        opposites = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }
        return opposites[self]

    def delta(self) -> Tuple[int, int]:
        """Return (dx, dy) for this direction."""
        deltas = {
            Direction.UP: (0, -1),
            Direction.DOWN: (0, 1),
            Direction.LEFT: (-1, 0),
            Direction.RIGHT: (1, 0),
        }
        return deltas[self]


@dataclass
class Cell:
    """A single cell in the factory grid."""
    x: int
    y: int
    entity: Optional['Entity'] = None

    def is_empty(self) -> bool:
        return self.entity is None


class Grid:
    """
    The factory grid where machines, belts, and injectors are placed.

    Coordinate system:
    - (0, 0) is top-left
    - x increases to the right
    - y increases downward
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self._cells: Dict[Tuple[int, int], Cell] = {}

        # Initialize all cells
        for y in range(height):
            for x in range(width):
                self._cells[(x, y)] = Cell(x, y)

    def in_bounds(self, x: int, y: int) -> bool:
        """Check if coordinates are within grid bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def get_cell(self, x: int, y: int) -> Optional[Cell]:
        """Get cell at coordinates, or None if out of bounds."""
        if not self.in_bounds(x, y):
            return None
        return self._cells[(x, y)]

    def get_entity(self, x: int, y: int) -> Optional['Entity']:
        """Get entity at coordinates, or None if empty or out of bounds."""
        cell = self.get_cell(x, y)
        if cell is None:
            return None
        return cell.entity

    def place_entity(self, x: int, y: int, entity: 'Entity') -> bool:
        """
        Place an entity at coordinates.
        Returns True if successful, False if cell is occupied or out of bounds.
        """
        cell = self.get_cell(x, y)
        if cell is None or not cell.is_empty():
            return False

        cell.entity = entity
        entity.x = x
        entity.y = y
        entity.grid = self
        return True

    def remove_entity(self, x: int, y: int) -> Optional['Entity']:
        """
        Remove and return entity at coordinates.
        Returns None if no entity or out of bounds.
        """
        cell = self.get_cell(x, y)
        if cell is None or cell.is_empty():
            return None

        entity = cell.entity
        cell.entity = None
        entity.grid = None
        return entity

    def get_neighbor(self, x: int, y: int, direction: Direction) -> Optional[Cell]:
        """Get the neighboring cell in the given direction."""
        dx, dy = direction.delta()
        return self.get_cell(x + dx, y + dy)

    def get_neighbor_entity(self, x: int, y: int, direction: Direction) -> Optional['Entity']:
        """Get the entity in the neighboring cell."""
        cell = self.get_neighbor(x, y, direction)
        if cell is None:
            return None
        return cell.entity

    def iter_entities(self) -> Iterator['Entity']:
        """Iterate over all entities in the grid."""
        for cell in self._cells.values():
            if cell.entity is not None:
                yield cell.entity

    def __repr__(self) -> str:
        return f"Grid({self.width}x{self.height})"
