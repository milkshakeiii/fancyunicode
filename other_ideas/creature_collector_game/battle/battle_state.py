"""Battle state container."""

from typing import Dict, Optional, List
from dataclasses import dataclass, field

from .models import Unit, Side
from .grid import Grid


@dataclass
class Team:
    """Represents one side's team in battle."""
    side: Side
    king_unit_id: str
    research_pool: int = 0

    def add_research(self, amount: int) -> int:
        """Add to research pool. Returns new total."""
        self.research_pool += amount
        return self.research_pool


class BattleState:
    """
    Container for all battle state.

    This class holds the current state of the battle but does not
    contain game logic. Logic is handled by BattleLogic.
    """

    def __init__(self):
        self.player_grid: Optional[Grid] = None
        self.enemy_grid: Optional[Grid] = None
        self.player_team: Optional[Team] = None
        self.enemy_team: Optional[Team] = None

        self.current_side: Side = Side.PLAYER
        self.actions_remaining: int = 3
        self.turn_number: int = 1

        self.battle_ended: bool = False
        self.winner: Optional[Side] = None

    def initialize(self, player_units: List[Unit], enemy_units: List[Unit],
                   player_king_id: str, enemy_king_id: str) -> None:
        """Initialize battle state with units."""
        # Create grids
        self.player_grid = Grid(Side.PLAYER)
        self.enemy_grid = Grid(Side.ENEMY)

        # Create teams
        self.player_team = Team(Side.PLAYER, player_king_id)
        self.enemy_team = Team(Side.ENEMY, enemy_king_id)

        # Place units
        for unit in player_units:
            self.player_grid.place_unit(unit)

        for unit in enemy_units:
            self.enemy_grid.place_unit(unit)

        # Reset turn state
        self.current_side = Side.PLAYER
        self.actions_remaining = 3
        self.turn_number = 1
        self.battle_ended = False
        self.winner = None

    def get_team(self, side: Side) -> Team:
        """Get team by side."""
        if side == Side.PLAYER:
            return self.player_team
        return self.enemy_team

    def get_grid(self, side: Side) -> Grid:
        """Get grid by side."""
        if side == Side.PLAYER:
            return self.player_grid
        return self.enemy_grid

    def get_enemy_grid(self, side: Side) -> Grid:
        """Get the opposing grid for a side."""
        if side == Side.PLAYER:
            return self.enemy_grid
        return self.player_grid

    def get_unit(self, unit_id: str) -> Optional[Unit]:
        """Get a unit by ID from either grid."""
        unit = self.player_grid.get_unit(unit_id)
        if unit:
            return unit
        return self.enemy_grid.get_unit(unit_id)

    def get_unit_side(self, unit_id: str) -> Optional[Side]:
        """Get which side a unit belongs to."""
        if self.player_grid.get_unit(unit_id):
            return Side.PLAYER
        if self.enemy_grid.get_unit(unit_id):
            return Side.ENEMY
        return None

    def get_current_team(self) -> Team:
        """Get the team whose turn it is."""
        return self.get_team(self.current_side)

    def get_current_grid(self) -> Grid:
        """Get the grid for the team whose turn it is."""
        return self.get_grid(self.current_side)

    def get_current_enemy_grid(self) -> Grid:
        """Get the enemy grid for the team whose turn it is."""
        return self.get_enemy_grid(self.current_side)

    def use_action(self) -> int:
        """Use one action slot. Returns remaining actions."""
        self.actions_remaining = max(0, self.actions_remaining - 1)
        return self.actions_remaining

    def switch_turn(self) -> None:
        """Switch to the other team's turn."""
        if self.current_side == Side.PLAYER:
            self.current_side = Side.ENEMY
        else:
            self.current_side = Side.PLAYER
            self.turn_number += 1
        self.actions_remaining = 3

    def check_win_condition(self) -> Optional[Side]:
        """
        Check if the battle has ended.

        Returns the winning Side, or None if battle continues.
        """
        # Check if player king is dead
        player_king = self.player_grid.get_unit(self.player_team.king_unit_id)
        if not player_king or not player_king.is_alive:
            self.battle_ended = True
            self.winner = Side.ENEMY
            return Side.ENEMY

        # Check if enemy king is dead
        enemy_king = self.enemy_grid.get_unit(self.enemy_team.king_unit_id)
        if not enemy_king or not enemy_king.is_alive:
            self.battle_ended = True
            self.winner = Side.PLAYER
            return Side.PLAYER

        return None

    def remove_dead_units(self) -> List[str]:
        """Remove dead units from grids. Returns list of removed unit IDs."""
        removed = []

        for unit in self.player_grid.get_all_units():
            if not unit.is_alive:
                self.player_grid.remove_unit(unit.unit_id)
                removed.append(unit.unit_id)

        for unit in self.enemy_grid.get_all_units():
            if not unit.is_alive:
                self.enemy_grid.remove_unit(unit.unit_id)
                removed.append(unit.unit_id)

        return removed

    def get_all_units(self, side: Side = None) -> List[Unit]:
        """Get all units, optionally filtered by side."""
        units = []
        if side is None or side == Side.PLAYER:
            units.extend(self.player_grid.get_all_units())
        if side is None or side == Side.ENEMY:
            units.extend(self.enemy_grid.get_all_units())
        return units

    def get_alive_units(self, side: Side = None) -> List[Unit]:
        """Get all living units, optionally filtered by side."""
        return [u for u in self.get_all_units(side) if u.is_alive]
