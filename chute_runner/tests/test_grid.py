"""
Tests for the grid system.
"""
import pytest
from gameplay.grid import Grid, Cell, Direction
from gameplay.entities import Belt
from gameplay.items import ItemType


class TestGrid:
    """Tests for Grid class."""

    def test_create_grid(self):
        """Grid initializes with correct dimensions."""
        grid = Grid(10, 5)
        assert grid.width == 10
        assert grid.height == 5

    def test_in_bounds(self):
        """in_bounds correctly identifies valid coordinates."""
        grid = Grid(10, 5)

        # Valid coordinates
        assert grid.in_bounds(0, 0)
        assert grid.in_bounds(9, 4)
        assert grid.in_bounds(5, 2)

        # Invalid coordinates
        assert not grid.in_bounds(-1, 0)
        assert not grid.in_bounds(0, -1)
        assert not grid.in_bounds(10, 0)
        assert not grid.in_bounds(0, 5)

    def test_get_cell(self):
        """get_cell returns correct cell or None."""
        grid = Grid(10, 5)

        cell = grid.get_cell(3, 2)
        assert cell is not None
        assert cell.x == 3
        assert cell.y == 2
        assert cell.is_empty()

        # Out of bounds returns None
        assert grid.get_cell(-1, 0) is None
        assert grid.get_cell(10, 0) is None

    def test_place_entity(self):
        """Entities can be placed on empty cells."""
        grid = Grid(10, 5)
        belt = Belt(Direction.RIGHT)

        # Place succeeds on empty cell
        assert grid.place_entity(3, 2, belt)
        assert belt.x == 3
        assert belt.y == 2
        assert belt.grid is grid

        # Cell is now occupied
        cell = grid.get_cell(3, 2)
        assert cell.entity is belt
        assert not cell.is_empty()

    def test_place_entity_occupied(self):
        """Cannot place entity on occupied cell."""
        grid = Grid(10, 5)
        belt1 = Belt(Direction.RIGHT)
        belt2 = Belt(Direction.LEFT)

        grid.place_entity(3, 2, belt1)

        # Second placement fails
        assert not grid.place_entity(3, 2, belt2)
        assert grid.get_entity(3, 2) is belt1

    def test_place_entity_out_of_bounds(self):
        """Cannot place entity out of bounds."""
        grid = Grid(10, 5)
        belt = Belt(Direction.RIGHT)

        assert not grid.place_entity(-1, 0, belt)
        assert not grid.place_entity(10, 0, belt)

    def test_remove_entity(self):
        """Entities can be removed."""
        grid = Grid(10, 5)
        belt = Belt(Direction.RIGHT)

        grid.place_entity(3, 2, belt)
        removed = grid.remove_entity(3, 2)

        assert removed is belt
        assert belt.grid is None
        assert grid.get_cell(3, 2).is_empty()

    def test_remove_empty(self):
        """Removing from empty cell returns None."""
        grid = Grid(10, 5)
        assert grid.remove_entity(3, 2) is None

    def test_get_neighbor(self):
        """get_neighbor returns correct adjacent cells."""
        grid = Grid(10, 5)

        # Center cell
        cell = grid.get_neighbor(5, 2, Direction.UP)
        assert cell.x == 5 and cell.y == 1

        cell = grid.get_neighbor(5, 2, Direction.DOWN)
        assert cell.x == 5 and cell.y == 3

        cell = grid.get_neighbor(5, 2, Direction.LEFT)
        assert cell.x == 4 and cell.y == 2

        cell = grid.get_neighbor(5, 2, Direction.RIGHT)
        assert cell.x == 6 and cell.y == 2

    def test_get_neighbor_edge(self):
        """get_neighbor returns None at grid edges."""
        grid = Grid(10, 5)

        assert grid.get_neighbor(0, 0, Direction.UP) is None
        assert grid.get_neighbor(0, 0, Direction.LEFT) is None
        assert grid.get_neighbor(9, 4, Direction.DOWN) is None
        assert grid.get_neighbor(9, 4, Direction.RIGHT) is None

    def test_iter_entities(self):
        """iter_entities yields all placed entities."""
        grid = Grid(10, 5)
        belt1 = Belt(Direction.RIGHT)
        belt2 = Belt(Direction.DOWN)

        grid.place_entity(0, 0, belt1)
        grid.place_entity(5, 3, belt2)

        entities = list(grid.iter_entities())
        assert len(entities) == 2
        assert belt1 in entities
        assert belt2 in entities


class TestDirection:
    """Tests for Direction enum."""

    def test_opposite(self):
        """Opposite directions are correct."""
        assert Direction.UP.opposite() == Direction.DOWN
        assert Direction.DOWN.opposite() == Direction.UP
        assert Direction.LEFT.opposite() == Direction.RIGHT
        assert Direction.RIGHT.opposite() == Direction.LEFT

    def test_delta(self):
        """Direction deltas are correct."""
        assert Direction.UP.delta() == (0, -1)
        assert Direction.DOWN.delta() == (0, 1)
        assert Direction.LEFT.delta() == (-1, 0)
        assert Direction.RIGHT.delta() == (1, 0)
