"""Attack targeting validation for the battle system."""

from typing import List, Tuple, Set, Optional

from .models import Unit, Attack, AttackType, Side
from .grid import Grid, get_column_distance, get_mirror_column, GRID_WIDTH, GRID_HEIGHT


def get_valid_targets(unit: Unit, attack: Attack, enemy_grid: Grid) -> List[Tuple[int, int]]:
    """
    Get all valid target cells for an attack.

    Returns list of (x, y) tuples on the enemy grid that can be targeted.
    """
    if attack.attack_type == AttackType.MELEE:
        return get_valid_melee_targets(unit, enemy_grid)
    elif attack.attack_type == AttackType.RANGED:
        return get_valid_ranged_targets(unit, attack, enemy_grid)
    else:  # MAGIC
        return get_valid_magic_targets(unit, enemy_grid)


def get_valid_melee_targets(unit: Unit, enemy_grid: Grid) -> List[Tuple[int, int]]:
    """
    Get valid melee targets.

    Melee attacks target the closest enemy in the attacker's row(s).
    For multi-row units, any row the unit occupies can be used.
    Returns the cell(s) of the closest enemy that can be targeted.
    """
    valid_targets = []
    seen_units: Set[str] = set()

    # Check each row the unit occupies
    for row in range(unit.y, unit.y + unit.height):
        closest = enemy_grid.get_closest_enemy_in_row(row, from_column=3)
        if closest and closest.unit_id not in seen_units:
            seen_units.add(closest.unit_id)
            # Return the reference cell of the closest enemy
            ref_x, ref_y = closest.get_reference_cell()
            if (ref_x, ref_y) not in valid_targets:
                valid_targets.append((ref_x, ref_y))

    return valid_targets


def get_valid_ranged_targets(unit: Unit, attack: Attack,
                              enemy_grid: Grid) -> List[Tuple[int, int]]:
    """
    Get valid ranged targets.

    Ranged attacks can target any cell within range_min to range_max column distance.
    Row does not affect validity.
    """
    valid_targets = []

    for x in range(GRID_WIDTH):
        # Calculate column distance
        dist = get_column_distance(unit, x, enemy_grid.side)

        if attack.range_min <= dist <= attack.range_max:
            # All rows are valid for this column
            for y in range(GRID_HEIGHT):
                valid_targets.append((x, y))

    return valid_targets


def get_valid_magic_targets(unit: Unit, enemy_grid: Grid) -> List[Tuple[int, int]]:
    """
    Get valid magic targets.

    Magic targets the mirror column (same depth index) on the enemy side.
    Magic hits all units in that column.
    """
    valid_targets = []

    # Get the depth of the unit's reference cell
    ref_x, _ = unit.get_reference_cell()
    # For magic, we use the unit's column position relative to front/back
    # Player column 0 (back) mirrors to enemy column 0 (back)
    # Player column 3 (front) mirrors to enemy column 3 (front)

    # Actually, the ruleset says "same depth index"
    # Depth 0 = back (column 0), Depth 3 = front (column 3)
    mirror_col = get_mirror_column(ref_x)

    # Return all cells in the mirror column
    for y in range(GRID_HEIGHT):
        valid_targets.append((mirror_col, y))

    return valid_targets


def validate_melee_target(unit: Unit, target_x: int, target_y: int,
                          enemy_grid: Grid) -> bool:
    """
    Validate a melee attack target.

    The target must be the closest enemy in one of the attacker's rows.
    """
    # Check each row the unit occupies
    for row in range(unit.y, unit.y + unit.height):
        closest = enemy_grid.get_closest_enemy_in_row(row, from_column=3)
        if closest:
            # Check if target cell is part of this closest enemy
            ref_x, ref_y = closest.get_reference_cell()
            if target_x == ref_x and target_y == ref_y:
                return True
            # Also accept any cell the closest unit occupies
            if (target_x, target_y) in closest.get_occupied_cells():
                return True

    return False


def validate_ranged_target(unit: Unit, attack: Attack,
                           target_x: int, target_y: int,
                           enemy_grid: Grid) -> bool:
    """
    Validate a ranged attack target.

    Target column must be within range_min to range_max distance.
    """
    dist = get_column_distance(unit, target_x, enemy_grid.side)
    return attack.range_min <= dist <= attack.range_max


def validate_magic_target(unit: Unit, target_x: int,
                          enemy_grid: Grid) -> bool:
    """
    Validate a magic attack target.

    Target must be in the mirror column (same depth index).
    """
    ref_x, _ = unit.get_reference_cell()
    mirror_col = get_mirror_column(ref_x)
    return target_x == mirror_col


def validate_target(unit: Unit, attack: Attack, target_x: int, target_y: int,
                    enemy_grid: Grid) -> bool:
    """Validate any attack target."""
    if attack.attack_type == AttackType.MELEE:
        return validate_melee_target(unit, target_x, target_y, enemy_grid)
    elif attack.attack_type == AttackType.RANGED:
        return validate_ranged_target(unit, attack, target_x, target_y, enemy_grid)
    else:  # MAGIC
        return validate_magic_target(unit, target_x, enemy_grid)


def get_units_hit(attack: Attack, target_x: int, target_y: int,
                  enemy_grid: Grid) -> List[str]:
    """
    Get the unit IDs that would be hit by an attack at target cell.

    - Melee: hits the unit at the target cell (if any)
    - Ranged: hits the unit at the target cell (if any)
    - Magic: hits ALL units in the target column
    """
    hit_unit_ids = []

    if attack.attack_type == AttackType.MAGIC:
        # Magic hits all units in the column
        units = enemy_grid.get_units_in_column(target_x)
        for unit in units:
            if unit.is_alive:
                hit_unit_ids.append(unit.unit_id)
    else:
        # Melee and ranged hit the unit at the target cell
        unit_id = enemy_grid.get_unit_at(target_x, target_y)
        if unit_id:
            unit = enemy_grid.get_unit(unit_id)
            if unit and unit.is_alive:
                hit_unit_ids.append(unit_id)

    return hit_unit_ids


def calculate_damage(attack: Attack, target: Unit) -> int:
    """
    Calculate damage dealt by an attack to a target.

    Formula: max(1, attack_damage - relevant_defense)
    """
    if attack.attack_type == AttackType.MELEE:
        defense = target.defense
    elif attack.attack_type == AttackType.RANGED:
        defense = target.dodge
    else:  # MAGIC
        defense = target.resistance

    return max(1, attack.damage - defense)
