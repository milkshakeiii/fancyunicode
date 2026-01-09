"""Action execution for the battle system."""

from typing import List, Optional
import uuid

from .models import (
    Unit, UnitPrototype, Attack, ActionResult, BattleEvent,
    Side, Direction, ActionType
)
from .battle_state import BattleState
from .targeting import validate_target, get_units_hit, calculate_damage


class ActionExecutor:
    """Executes battle actions and returns results."""

    def __init__(self, state: BattleState):
        self.state = state

    def execute_attack(self, unit_id: str, target_x: int, target_y: int,
                       attack_idx: int = 0) -> ActionResult:
        """
        Execute an attack action.

        Args:
            unit_id: The attacking unit's ID
            target_x: Target column on enemy grid
            target_y: Target row on enemy grid
            attack_idx: Which attack to use (if unit has multiple)

        Returns:
            ActionResult with damage events
        """
        # Get the unit
        unit = self.state.get_unit(unit_id)
        if not unit:
            return ActionResult.failure(f"Unit {unit_id} not found")

        if not unit.is_alive:
            return ActionResult.failure(f"Unit {unit.name} is dead")

        # Verify unit belongs to current team
        unit_side = self.state.get_unit_side(unit_id)
        if unit_side != self.state.current_side:
            return ActionResult.failure("Cannot control enemy units")

        # Get the attack
        if attack_idx < 0 or attack_idx >= len(unit.attacks):
            return ActionResult.failure("Invalid attack index")

        attack = unit.attacks[attack_idx]

        # Get enemy grid
        enemy_grid = self.state.get_enemy_grid(unit_side)

        # Validate target
        if not validate_target(unit, attack, target_x, target_y, enemy_grid):
            return ActionResult.failure("Invalid target for this attack type")

        # Get units that will be hit
        hit_unit_ids = get_units_hit(attack, target_x, target_y, enemy_grid)

        events = []

        # Apply damage to each hit unit
        for hit_id in hit_unit_ids:
            target = enemy_grid.get_unit(hit_id)
            if target and target.is_alive:
                damage = calculate_damage(attack, target)
                target.current_hp -= damage

                events.append(BattleEvent("damage", {
                    "unit_id": hit_id,
                    "attacker_id": unit_id,
                    "amount": damage,
                    "attack_type": attack.attack_type.name,
                    "new_hp": target.current_hp,
                }))

                # Check for death
                if not target.is_alive:
                    events.append(BattleEvent("death", {
                        "unit_id": hit_id,
                    }))

        # Use action slot
        self.state.use_action()

        # Remove dead units
        self.state.remove_dead_units()

        # Check win condition
        winner = self.state.check_win_condition()
        if winner:
            events.append(BattleEvent("battle_end", {"winner": winner.name}))

        return ActionResult.ok(events)

    def execute_move(self, unit_id: str, direction: Direction) -> ActionResult:
        """
        Execute a move action.

        Args:
            unit_id: The moving unit's ID
            direction: Direction to move

        Returns:
            ActionResult with move/displacement events
        """
        unit = self.state.get_unit(unit_id)
        if not unit:
            return ActionResult.failure(f"Unit {unit_id} not found")

        if not unit.is_alive:
            return ActionResult.failure(f"Unit {unit.name} is dead")

        unit_side = self.state.get_unit_side(unit_id)
        if unit_side != self.state.current_side:
            return ActionResult.failure("Cannot control enemy units")

        grid = self.state.get_grid(unit_side)

        # Try to move with displacement
        displacements = grid.try_move_with_displacement(unit, direction)
        if displacements is None:
            return ActionResult.failure("Cannot move in that direction")

        events = []

        # Record all movements
        for disp in displacements:
            if disp.unit_id == unit_id:
                events.append(BattleEvent("move", {
                    "unit_id": disp.unit_id,
                    "from_x": disp.from_x,
                    "from_y": disp.from_y,
                    "to_x": disp.to_x,
                    "to_y": disp.to_y,
                }))
            else:
                events.append(BattleEvent("displacement", {
                    "unit_id": disp.unit_id,
                    "from_x": disp.from_x,
                    "from_y": disp.from_y,
                    "to_x": disp.to_x,
                    "to_y": disp.to_y,
                }))

        # Apply the displacements
        grid.apply_displacements(displacements)

        # Use action slot
        self.state.use_action()

        return ActionResult.ok(events)

    def execute_research(self) -> ActionResult:
        """
        Execute a research action.

        All units with research_efficiency > 0 contribute to team research pool.

        Returns:
            ActionResult with research event
        """
        team = self.state.get_current_team()
        grid = self.state.get_current_grid()

        total_research = 0
        for unit in grid.get_alive_units():
            if unit.prototype.research_efficiency > 0:
                total_research += unit.prototype.research_efficiency

        new_total = team.add_research(total_research)

        events = [BattleEvent("research", {
            "side": self.state.current_side.name,
            "amount": total_research,
            "new_total": new_total,
        })]

        # Use action slot
        self.state.use_action()

        return ActionResult.ok(events)

    def execute_summon_charge(self, unit_id: str) -> ActionResult:
        """
        Execute a summon charge action.

        The unit adds summon_efficiency to its current_summoning_pool.

        Args:
            unit_id: The unit charging its summon pool

        Returns:
            ActionResult with summon_charge event
        """
        unit = self.state.get_unit(unit_id)
        if not unit:
            return ActionResult.failure(f"Unit {unit_id} not found")

        if not unit.is_alive:
            return ActionResult.failure(f"Unit {unit.name} is dead")

        unit_side = self.state.get_unit_side(unit_id)
        if unit_side != self.state.current_side:
            return ActionResult.failure("Cannot control enemy units")

        if unit.prototype.max_summoning_pool <= 0:
            return ActionResult.failure(f"{unit.name} cannot summon")

        if unit.prototype.summon_efficiency <= 0:
            return ActionResult.failure(f"{unit.name} has no summon efficiency")

        # Add to summoning pool
        old_pool = unit.current_summoning_pool
        unit.current_summoning_pool = min(
            unit.prototype.max_summoning_pool,
            unit.current_summoning_pool + unit.prototype.summon_efficiency
        )
        amount = unit.current_summoning_pool - old_pool

        events = [BattleEvent("summon_charge", {
            "unit_id": unit_id,
            "amount": amount,
            "new_total": unit.current_summoning_pool,
            "max_pool": unit.prototype.max_summoning_pool,
        })]

        # Use action slot
        self.state.use_action()

        return ActionResult.ok(events)

    def execute_summon(self, summoner_id: str, prototype: UnitPrototype,
                       spawn_x: int, spawn_y: int) -> ActionResult:
        """
        Execute a summon action.

        Args:
            summoner_id: The summoning unit's ID
            prototype: Prototype of unit to summon
            spawn_x: Spawn column
            spawn_y: Spawn row

        Returns:
            ActionResult with summon event
        """
        summoner = self.state.get_unit(summoner_id)
        if not summoner:
            return ActionResult.failure(f"Summoner {summoner_id} not found")

        if not summoner.is_alive:
            return ActionResult.failure(f"Summoner {summoner.name} is dead")

        summoner_side = self.state.get_unit_side(summoner_id)
        if summoner_side != self.state.current_side:
            return ActionResult.failure("Cannot control enemy units")

        if summoner.prototype.max_summoning_pool <= 0:
            return ActionResult.failure(f"{summoner.name} cannot summon")

        # Check research requirement
        team = self.state.get_team(summoner_side)
        if team.research_pool < prototype.research_requirement:
            return ActionResult.failure(
                f"Need {prototype.research_requirement} research "
                f"(have {team.research_pool})"
            )

        # Check summoning pool cost
        if summoner.current_summoning_pool < prototype.summoning_cost:
            return ActionResult.failure(
                f"Need {prototype.summoning_cost} summoning pool "
                f"(have {summoner.current_summoning_pool})"
            )

        # Check spawn location
        grid = self.state.get_grid(summoner_side)
        valid_locations = grid.get_adjacent_spawn_locations(
            summoner, prototype.width, prototype.height
        )
        if (spawn_x, spawn_y) not in valid_locations:
            return ActionResult.failure("Invalid spawn location")

        # Pay the summoning cost
        summoner.current_summoning_pool -= prototype.summoning_cost

        # Create the new unit
        new_id = f"{prototype.name}_{uuid.uuid4().hex[:8]}"
        new_unit = prototype.create_unit(new_id, spawn_x, spawn_y, summoner_side)

        # Place on grid
        if not grid.place_unit(new_unit):
            # This shouldn't happen since we validated, but just in case
            summoner.current_summoning_pool += prototype.summoning_cost
            return ActionResult.failure("Failed to place summoned unit")

        events = [BattleEvent("summon", {
            "summoner_id": summoner_id,
            "new_unit_id": new_id,
            "prototype_name": prototype.name,
            "x": spawn_x,
            "y": spawn_y,
        })]

        # Use action slot
        self.state.use_action()

        return ActionResult.ok(events)

    def execute_pass(self) -> ActionResult:
        """
        Execute a pass action (skip one action slot).

        Returns:
            ActionResult (always succeeds)
        """
        self.state.use_action()
        return ActionResult.ok([BattleEvent("pass", {
            "side": self.state.current_side.name,
        })])

    def end_turn(self) -> ActionResult:
        """
        End the current turn.

        Processes status effects, reduces cooldowns, switches sides.

        Returns:
            ActionResult with turn_end event
        """
        events = []

        # Add turn end event
        events.append(BattleEvent("turn_end", {
            "side": self.state.current_side.name,
        }))

        # TODO: Process status effects
        # TODO: Reduce cooldowns

        # Switch turns
        self.state.switch_turn()

        # Add turn start event
        events.append(BattleEvent("turn_start", {
            "side": self.state.current_side.name,
            "turn_number": self.state.turn_number,
        }))

        return ActionResult.ok(events)
