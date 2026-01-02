"""Main battle logic controller."""

from typing import List, Tuple, Optional

from .models import (
    Unit, UnitPrototype, Attack, ActionResult, BattleEvent,
    Side, Direction, ActionType
)
from .battle_state import BattleState
from .actions import ActionExecutor
from .targeting import get_valid_targets


class BattleLogic:
    """
    Main controller for battle logic.

    This class provides the public API for the battle system.
    It manages state and delegates action execution.
    """

    def __init__(self, player_units: List[Unit], enemy_units: List[Unit],
                 player_king_id: str, enemy_king_id: str):
        """
        Initialize a battle.

        Args:
            player_units: List of player units (already positioned)
            enemy_units: List of enemy units (already positioned)
            player_king_id: ID of the player's king unit
            enemy_king_id: ID of the enemy's king unit (control crystal)
        """
        self.state = BattleState()
        self.state.initialize(
            player_units, enemy_units,
            player_king_id, enemy_king_id
        )
        self.executor = ActionExecutor(self.state)

    # =========================================================================
    # Query Methods (for UI)
    # =========================================================================

    def get_current_side(self) -> Side:
        """Get which side's turn it is."""
        return self.state.current_side

    def get_actions_remaining(self) -> int:
        """Get number of action slots remaining this turn."""
        return self.state.actions_remaining

    def get_turn_number(self) -> int:
        """Get the current turn number."""
        return self.state.turn_number

    def is_battle_over(self) -> bool:
        """Check if the battle has ended."""
        return self.state.battle_ended

    def get_winner(self) -> Optional[Side]:
        """Get the winning side, or None if battle is ongoing."""
        return self.state.winner

    def get_unit(self, unit_id: str) -> Optional[Unit]:
        """Get a unit by ID."""
        return self.state.get_unit(unit_id)

    def get_all_units(self, side: Side = None) -> List[Unit]:
        """Get all units, optionally filtered by side."""
        return self.state.get_all_units(side)

    def get_alive_units(self, side: Side = None) -> List[Unit]:
        """Get all living units, optionally filtered by side."""
        return self.state.get_alive_units(side)

    def get_research_pool(self, side: Side) -> int:
        """Get a team's research pool."""
        return self.state.get_team(side).research_pool

    def get_valid_actions_for_unit(self, unit_id: str) -> List[ActionType]:
        """
        Get the types of actions a unit can take.

        Returns empty list if unit can't act (wrong side, dead, etc.)
        """
        unit = self.state.get_unit(unit_id)
        if not unit or not unit.is_alive:
            return []

        unit_side = self.state.get_unit_side(unit_id)
        if unit_side != self.state.current_side:
            return []

        actions = []

        # Can always pass (handled at team level, not unit)

        # Attack - if unit has attacks
        if unit.attacks:
            actions.append(ActionType.ATTACK)

        # Move - if any direction is valid
        grid = self.state.get_grid(unit_side)
        if grid.get_valid_move_directions(unit):
            actions.append(ActionType.MOVE)

        # Summon charge - if unit can summon and isn't full
        if (unit.prototype.max_summoning_pool > 0 and
            unit.prototype.summon_efficiency > 0 and
            unit.current_summoning_pool < unit.prototype.max_summoning_pool):
            actions.append(ActionType.SUMMON_CHARGE)

        # Summon - checked separately via can_summon()

        return actions

    def get_valid_attack_targets(self, unit_id: str,
                                  attack_idx: int = 0) -> List[Tuple[int, int]]:
        """Get valid target cells for an attack."""
        unit = self.state.get_unit(unit_id)
        if not unit or not unit.is_alive:
            return []

        if attack_idx < 0 or attack_idx >= len(unit.attacks):
            return []

        attack = unit.attacks[attack_idx]
        unit_side = self.state.get_unit_side(unit_id)
        enemy_grid = self.state.get_enemy_grid(unit_side)

        return get_valid_targets(unit, attack, enemy_grid)

    def get_valid_move_directions(self, unit_id: str) -> List[Direction]:
        """Get valid movement directions for a unit."""
        unit = self.state.get_unit(unit_id)
        if not unit or not unit.is_alive:
            return []

        unit_side = self.state.get_unit_side(unit_id)
        if unit_side != self.state.current_side:
            return []

        grid = self.state.get_grid(unit_side)
        return grid.get_valid_move_directions(unit)

    def get_valid_summon_locations(self, summoner_id: str,
                                    prototype: UnitPrototype) -> List[Tuple[int, int]]:
        """Get valid spawn locations for summoning a prototype."""
        summoner = self.state.get_unit(summoner_id)
        if not summoner or not summoner.is_alive:
            return []

        summoner_side = self.state.get_unit_side(summoner_id)
        grid = self.state.get_grid(summoner_side)

        return grid.get_adjacent_spawn_locations(
            summoner, prototype.width, prototype.height
        )

    def can_summon(self, summoner_id: str, prototype: UnitPrototype) -> bool:
        """Check if a summoner can summon a prototype (has resources)."""
        summoner = self.state.get_unit(summoner_id)
        if not summoner or not summoner.is_alive:
            return False

        summoner_side = self.state.get_unit_side(summoner_id)
        if summoner_side != self.state.current_side:
            return False

        if summoner.prototype.max_summoning_pool <= 0:
            return False

        # Check research requirement
        team = self.state.get_team(summoner_side)
        if team.research_pool < prototype.research_requirement:
            return False

        # Check summoning pool cost
        if summoner.current_summoning_pool < prototype.summoning_cost:
            return False

        # Check if there's a valid spawn location
        locations = self.get_valid_summon_locations(summoner_id, prototype)
        return len(locations) > 0

    def get_units_with_research(self) -> List[Unit]:
        """Get units on current team that can contribute to research."""
        units = []
        for unit in self.state.get_current_grid().get_alive_units():
            if unit.prototype.research_efficiency > 0:
                units.append(unit)
        return units

    def get_potential_research(self) -> int:
        """Get how much research the current team would gain from a Research action."""
        total = 0
        for unit in self.get_units_with_research():
            total += unit.prototype.research_efficiency
        return total

    # =========================================================================
    # Action Methods
    # =========================================================================

    def do_attack(self, unit_id: str, target_x: int, target_y: int,
                  attack_idx: int = 0) -> ActionResult:
        """Execute an attack action."""
        if self.state.battle_ended:
            return ActionResult.failure("Battle has ended")
        if self.state.actions_remaining <= 0:
            return ActionResult.failure("No actions remaining")

        return self.executor.execute_attack(unit_id, target_x, target_y, attack_idx)

    def do_move(self, unit_id: str, direction: Direction) -> ActionResult:
        """Execute a move action."""
        if self.state.battle_ended:
            return ActionResult.failure("Battle has ended")
        if self.state.actions_remaining <= 0:
            return ActionResult.failure("No actions remaining")

        return self.executor.execute_move(unit_id, direction)

    def do_research(self) -> ActionResult:
        """Execute a research action (team-wide)."""
        if self.state.battle_ended:
            return ActionResult.failure("Battle has ended")
        if self.state.actions_remaining <= 0:
            return ActionResult.failure("No actions remaining")

        return self.executor.execute_research()

    def do_summon_charge(self, unit_id: str) -> ActionResult:
        """Execute a summon charge action."""
        if self.state.battle_ended:
            return ActionResult.failure("Battle has ended")
        if self.state.actions_remaining <= 0:
            return ActionResult.failure("No actions remaining")

        return self.executor.execute_summon_charge(unit_id)

    def do_summon(self, summoner_id: str, prototype: UnitPrototype,
                  spawn_x: int, spawn_y: int) -> ActionResult:
        """Execute a summon action."""
        if self.state.battle_ended:
            return ActionResult.failure("Battle has ended")
        if self.state.actions_remaining <= 0:
            return ActionResult.failure("No actions remaining")

        return self.executor.execute_summon(summoner_id, prototype, spawn_x, spawn_y)

    def do_pass(self) -> ActionResult:
        """Execute a pass action (skip one action slot)."""
        if self.state.battle_ended:
            return ActionResult.failure("Battle has ended")
        if self.state.actions_remaining <= 0:
            return ActionResult.failure("No actions remaining")

        return self.executor.execute_pass()

    def end_turn(self) -> ActionResult:
        """End the current turn and switch to the other team."""
        if self.state.battle_ended:
            return ActionResult.failure("Battle has ended")

        return self.executor.end_turn()

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def auto_end_turn_if_needed(self) -> Optional[ActionResult]:
        """
        Automatically end turn if no actions remain.

        Returns ActionResult if turn was ended, None otherwise.
        """
        if self.state.actions_remaining <= 0 and not self.state.battle_ended:
            return self.end_turn()
        return None
