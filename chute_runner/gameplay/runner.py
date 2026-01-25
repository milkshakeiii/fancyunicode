"""
Runner and gate system for the top lane.
NO UI DEPENDENCIES.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum, auto
from abc import ABC, abstractmethod

from .items import ItemType
from .chutes import ChuteBank
from .constants import (
    RUNNER_HP, RUNNER_SPEED, TOP_LANE_LENGTH, GATE_ZONE_WIDTH,
    TRAP_DAMAGE_PER_MISSING
)


class GateState(Enum):
    """State of a gate in the sequence."""
    UPCOMING = auto()   # Not yet reached
    ACTIVE = auto()     # Runner is in gate zone, consuming resources
    PASSED = auto()     # Gate resolved (passed or failed)


class GateType(Enum):
    """Types of gates in the MVP."""
    MONSTER = auto()  # Consumes swords, unspent monster HP = runner damage
    TRAP = auto()     # Consumes shields, 5 damage per missing
    DOOR = auto()     # Consumes keys, instant fail if unmet


@dataclass
class GateResult:
    """Result of resolving a gate."""
    success: bool
    damage_taken: int
    items_consumed: Dict[ItemType, int]
    items_missing: Dict[ItemType, int]
    instant_death: bool = False


@dataclass
class Gate:
    """
    A gate that the runner must pass.
    """
    gate_type: GateType
    position: float  # Position along the lane (0 to TOP_LANE_LENGTH)
    demands: Dict[ItemType, int]  # What items are needed
    state: GateState = GateState.UPCOMING

    def resolve(self, chute_bank: ChuteBank) -> GateResult:
        """
        Resolve this gate by consuming from chutes.
        Returns the result of passing through the gate.
        """
        items_consumed: Dict[ItemType, int] = {}
        items_missing: Dict[ItemType, int] = {}

        # Consume items from chutes
        for item_type, needed in self.demands.items():
            removed = chute_bank.remove_items(item_type, needed)
            items_consumed[item_type] = removed
            missing = needed - removed
            if missing > 0:
                items_missing[item_type] = missing

        # Calculate damage based on gate type
        damage = 0
        instant_death = False
        success = True

        if self.gate_type == GateType.MONSTER:
            # Monster: unspent monster HP becomes damage
            missing_swords = items_missing.get(ItemType.SWORD, 0)
            damage = missing_swords
            success = missing_swords == 0

        elif self.gate_type == GateType.TRAP:
            # Trap: 5 damage per missing shield
            missing_shields = items_missing.get(ItemType.SHIELD, 0)
            damage = missing_shields * TRAP_DAMAGE_PER_MISSING
            success = missing_shields == 0

        elif self.gate_type == GateType.DOOR:
            # Door: instant death if any keys missing
            missing_keys = items_missing.get(ItemType.KEY, 0)
            if missing_keys > 0:
                instant_death = True
                success = False

        self.state = GateState.PASSED

        return GateResult(
            success=success,
            damage_taken=damage,
            items_consumed=items_consumed,
            items_missing=items_missing,
            instant_death=instant_death
        )

    @property
    def zone_start(self) -> float:
        """Start of the gate's activation zone."""
        return self.position

    @property
    def zone_end(self) -> float:
        """End of the gate's activation zone."""
        return self.position + GATE_ZONE_WIDTH


def create_gate(gate_type: GateType, position: float, **demands: int) -> Gate:
    """Convenience function to create gates."""
    demand_dict: Dict[ItemType, int] = {}

    # Map keyword args to item types
    if 'swords' in demands:
        demand_dict[ItemType.SWORD] = demands['swords']
    if 'shields' in demands:
        demand_dict[ItemType.SHIELD] = demands['shields']
    if 'keys' in demands:
        demand_dict[ItemType.KEY] = demands['keys']

    return Gate(gate_type=gate_type, position=position, demands=demand_dict)


class Runner:
    """
    The hero that runs through the gate sequence.
    """

    def __init__(self):
        self.hp: int = RUNNER_HP
        self.max_hp: int = RUNNER_HP
        self.position: float = 0.0  # Position along the lane
        self.speed: float = RUNNER_SPEED
        self.is_alive: bool = True
        self.finished: bool = False

    def update(self, dt: float) -> None:
        """Advance the runner."""
        if not self.is_alive or self.finished:
            return

        self.position += self.speed * dt

        if self.position >= TOP_LANE_LENGTH:
            self.position = TOP_LANE_LENGTH
            self.finished = True

    def take_damage(self, amount: int) -> None:
        """Apply damage to the runner."""
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.is_alive = False

    def kill(self) -> None:
        """Instant death (e.g., from failed door)."""
        self.hp = 0
        self.is_alive = False

    @property
    def hp_ratio(self) -> float:
        """Return HP as 0.0 to 1.0."""
        return self.hp / self.max_hp if self.max_hp > 0 else 0.0

    @property
    def progress_ratio(self) -> float:
        """Return position as 0.0 to 1.0."""
        return self.position / TOP_LANE_LENGTH if TOP_LANE_LENGTH > 0 else 0.0


class GateSequence:
    """
    Manages the sequence of gates the runner must pass.
    """

    def __init__(self, gates: List[Gate]):
        # Sort gates by position
        self.gates = sorted(gates, key=lambda g: g.position)
        self.current_index: int = 0

    def get_current_gate(self) -> Optional[Gate]:
        """Get the next gate that hasn't been passed yet."""
        for gate in self.gates:
            if gate.state != GateState.PASSED:
                return gate
        return None

    def get_upcoming_gates(self, count: int = 3) -> List[Gate]:
        """Get the next N gates (for preview display)."""
        upcoming = []
        for gate in self.gates:
            if gate.state != GateState.PASSED:
                upcoming.append(gate)
                if len(upcoming) >= count:
                    break
        return upcoming

    def check_and_resolve(self, runner: Runner, chute_bank: ChuteBank) -> Optional[GateResult]:
        """
        Check if runner has entered a gate zone and resolve it.
        Returns the result if a gate was resolved, None otherwise.
        """
        for gate in self.gates:
            if gate.state != GateState.UPCOMING:
                continue

            # Check if runner entered gate zone
            if runner.position >= gate.zone_start:
                gate.state = GateState.ACTIVE
                result = gate.resolve(chute_bank)

                # Apply results to runner
                if result.instant_death:
                    runner.kill()
                elif result.damage_taken > 0:
                    runner.take_damage(result.damage_taken)

                return result

        return None

    def all_passed(self) -> bool:
        """Check if all gates have been passed."""
        return all(g.state == GateState.PASSED for g in self.gates)

    @property
    def total_gates(self) -> int:
        return len(self.gates)

    @property
    def gates_passed(self) -> int:
        return sum(1 for g in self.gates if g.state == GateState.PASSED)
