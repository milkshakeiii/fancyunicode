"""Grid management for the 4x4 battle grids."""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .models import Unit, Side, Direction

# Grid dimensions
GRID_WIDTH = 4
GRID_HEIGHT = 4


@dataclass
class Displacement:
    """Records a unit displacement during a move."""
    unit_id: str
    from_x: int
    from_y: int
    to_x: int
    to_y: int


class Grid:
    """Manages a 4x4 grid for one side of the battlefield."""

    def __init__(self, side: Side):
        self.side = side
        # Map of (x, y) -> unit_id for occupied cells
        self._cells: Dict[Tuple[int, int], str] = {}
        # Map of unit_id -> Unit for quick lookup
        self._units: Dict[str, Unit] = {}

    def place_unit(self, unit: Unit) -> bool:
        """Place a unit on the grid. Returns False if placement is invalid."""
        if not self._can_place_footprint(unit.x, unit.y, unit.width, unit.height):
            return False

        self._units[unit.unit_id] = unit
        for x, y in unit.get_occupied_cells():
            self._cells[(x, y)] = unit.unit_id
        return True

    def remove_unit(self, unit_id: str) -> Optional[Unit]:
        """Remove a unit from the grid. Returns the removed unit or None."""
        if unit_id not in self._units:
            return None

        unit = self._units.pop(unit_id)
        for x, y in unit.get_occupied_cells():
            if self._cells.get((x, y)) == unit_id:
                del self._cells[(x, y)]
        return unit

    def get_unit_at(self, x: int, y: int) -> Optional[str]:
        """Get the unit_id at a cell, or None if empty."""
        return self._cells.get((x, y))

    def get_unit(self, unit_id: str) -> Optional[Unit]:
        """Get a unit by ID."""
        return self._units.get(unit_id)

    def get_all_units(self) -> List[Unit]:
        """Get all units on this grid."""
        return list(self._units.values())

    def get_alive_units(self) -> List[Unit]:
        """Get all living units on this grid."""
        return [u for u in self._units.values() if u.is_alive]

    def is_cell_in_bounds(self, x: int, y: int) -> bool:
        """Check if a cell is within grid bounds."""
        return 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT

    def is_cell_empty(self, x: int, y: int, exclude_unit_id: str = None) -> bool:
        """Check if a cell is empty (optionally excluding a specific unit)."""
        if not self.is_cell_in_bounds(x, y):
            return False
        occupant = self._cells.get((x, y))
        return occupant is None or occupant == exclude_unit_id

    def _can_place_footprint(self, x: int, y: int, width: int, height: int,
                              exclude_unit_id: str = None) -> bool:
        """Check if a footprint can be placed at position."""
        # Check all cells in footprint
        for dx in range(width):
            for dy in range(height):
                cell_x, cell_y = x + dx, y + dy
                if not self.is_cell_in_bounds(cell_x, cell_y):
                    return False
                if not self.is_cell_empty(cell_x, cell_y, exclude_unit_id):
                    return False
        return True

    def can_place_unit(self, unit: Unit, x: int, y: int) -> bool:
        """Check if a unit can be placed at position."""
        return self._can_place_footprint(x, y, unit.width, unit.height, unit.unit_id)

    def get_valid_move_directions(self, unit: Unit) -> List[Direction]:
        """Get list of valid movement directions for a unit."""
        valid = []
        for direction in Direction:
            if self._can_move(unit, direction):
                valid.append(direction)
        return valid

    def _can_move(self, unit: Unit, direction: Direction) -> bool:
        """Check if a unit can move in a direction (with displacement)."""
        result = self.try_move_with_displacement(unit, direction)
        return result is not None

    def try_move_with_displacement(self, unit: Unit, direction: Direction
                                    ) -> Optional[List[Displacement]]:
        """
        Attempt to move a unit, displacing other units if needed.

        Returns list of Displacements if move is valid, None if invalid.
        The first Displacement is always the moving unit itself.
        """
        dx, dy = direction.dx, direction.dy
        new_x, new_y = unit.x + dx, unit.y + dy

        # Check if new footprint is in bounds
        for ddx in range(unit.width):
            for ddy in range(unit.height):
                if not self.is_cell_in_bounds(new_x + ddx, new_y + ddy):
                    return None

        # Find units that would be displaced
        new_cells = set()
        for ddx in range(unit.width):
            for ddy in range(unit.height):
                new_cells.add((new_x + ddx, new_y + ddy))

        old_cells = set(unit.get_occupied_cells())
        cells_to_enter = new_cells - old_cells

        # Find units in cells we're entering
        units_to_displace: Dict[str, Unit] = {}
        for cx, cy in cells_to_enter:
            occupant_id = self._cells.get((cx, cy))
            if occupant_id and occupant_id != unit.unit_id:
                units_to_displace[occupant_id] = self._units[occupant_id]

        displacements = [Displacement(unit.unit_id, unit.x, unit.y, new_x, new_y)]

        # Check if each displaced unit can move in the inverse direction
        inverse_dx, inverse_dy = -dx, -dy
        for displaced_unit in units_to_displace.values():
            disp_new_x = displaced_unit.x + inverse_dx
            disp_new_y = displaced_unit.y + inverse_dy

            # Check displaced unit's new footprint
            for ddx in range(displaced_unit.width):
                for ddy in range(displaced_unit.height):
                    check_x = disp_new_x + ddx
                    check_y = disp_new_y + ddy

                    # Must be in bounds
                    if not self.is_cell_in_bounds(check_x, check_y):
                        return None

                    # Cell must be empty, or part of moving unit's old position,
                    # or part of this displaced unit's current position
                    if (check_x, check_y) in old_cells:
                        continue
                    occupant = self._cells.get((check_x, check_y))
                    if occupant is not None and occupant != displaced_unit.unit_id:
                        # Check if it's another unit being displaced
                        if occupant not in units_to_displace:
                            return None

            displacements.append(Displacement(
                displaced_unit.unit_id,
                displaced_unit.x, displaced_unit.y,
                disp_new_x, disp_new_y
            ))

        return displacements

    def apply_displacements(self, displacements: List[Displacement]) -> None:
        """Apply a list of displacements to the grid."""
        # First, remove all units from cells
        for disp in displacements:
            unit = self._units[disp.unit_id]
            for x, y in unit.get_occupied_cells():
                if self._cells.get((x, y)) == unit.unit_id:
                    del self._cells[(x, y)]

        # Then, update positions and re-place
        for disp in displacements:
            unit = self._units[disp.unit_id]
            unit.x = disp.to_x
            unit.y = disp.to_y
            for x, y in unit.get_occupied_cells():
                self._cells[(x, y)] = unit.unit_id

    def get_units_in_column(self, column: int) -> List[Unit]:
        """Get all units that occupy a given column."""
        units = []
        seen = set()
        for row in range(GRID_HEIGHT):
            unit_id = self._cells.get((column, row))
            if unit_id and unit_id not in seen:
                seen.add(unit_id)
                units.append(self._units[unit_id])
        return units

    def get_units_in_row(self, row: int) -> List[Unit]:
        """Get all units that occupy a given row."""
        units = []
        seen = set()
        for col in range(GRID_WIDTH):
            unit_id = self._cells.get((col, row))
            if unit_id and unit_id not in seen:
                seen.add(unit_id)
                units.append(self._units[unit_id])
        return units

    def get_closest_enemy_in_row(self, row: int, from_column: int) -> Optional[Unit]:
        """Get the closest unit in a row from a given column (looking toward front)."""
        units_in_row = self.get_units_in_row(row)
        if not units_in_row:
            return None

        # For player grid, "front" is column 3
        # For enemy grid being attacked, we look from the front (column 3) backward
        # Actually, melee targets the closest enemy, which depends on perspective

        # Since this is called on the enemy grid, we want the unit closest to column 3
        # (the front of the enemy grid, which is adjacent to the player)
        closest = None
        closest_dist = float('inf')
        for unit in units_in_row:
            # Front-most column of this unit
            unit_front = unit.x + unit.width - 1
            # Distance from the front of the grid (column 3)
            dist = 3 - unit_front  # 0 means at front, 3 means at back
            if dist < closest_dist:
                closest_dist = dist
                closest = unit
        return closest

    def get_adjacent_spawn_locations(self, unit: Unit, proto_width: int,
                                      proto_height: int) -> List[Tuple[int, int]]:
        """Get valid spawn locations adjacent to a unit's footprint."""
        locations = []
        unit_cells = set(unit.get_occupied_cells())

        # Check all cells adjacent to the unit's footprint
        for ux, uy in unit_cells:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                spawn_x, spawn_y = ux + dx, uy + dy

                # Skip if this cell is part of the unit
                if (spawn_x, spawn_y) in unit_cells:
                    continue

                # Check if prototype can fit here
                if self._can_place_footprint(spawn_x, spawn_y, proto_width, proto_height):
                    # Avoid duplicates
                    if (spawn_x, spawn_y) not in locations:
                        locations.append((spawn_x, spawn_y))

        return locations


def get_column_distance(unit_a: Unit, target_col: int, target_side: Side) -> int:
    """
    Calculate column distance between a unit and a target column.

    Uses global column mapping:
    - Player columns 0-3 -> global 0-3
    - Enemy columns 0-3 -> global 7-4
    """
    unit_global = unit_a.get_global_column()

    if target_side == Side.PLAYER:
        target_global = target_col
    else:
        target_global = 7 - target_col

    return abs(unit_global - target_global)


def get_mirror_column(local_col: int) -> int:
    """Get the mirror column for magic attacks (same depth index)."""
    # Column 0 (back) mirrors to column 0 (back)
    # Column 3 (front) mirrors to column 3 (front)
    return local_col
