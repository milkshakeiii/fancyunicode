"""Core data structures for the battle system."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum, auto


class AttackType(Enum):
    """Type of attack, determines which defense stat is used."""
    MELEE = auto()   # Uses defense stat
    RANGED = auto()  # Uses dodge stat
    MAGIC = auto()   # Uses resistance stat


class ActionType(Enum):
    """Types of actions a unit or team can take."""
    ATTACK = auto()
    MOVE = auto()
    RESEARCH = auto()
    SUMMON_CHARGE = auto()
    SUMMON = auto()
    PASS = auto()


class Side(Enum):
    """Which side of the battle a unit belongs to."""
    PLAYER = auto()
    ENEMY = auto()


class Direction(Enum):
    """Movement directions."""
    NORTH = (0, -1)
    SOUTH = (0, 1)
    EAST = (1, 0)
    WEST = (-1, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]


@dataclass
class Attack:
    """An attack that a unit can perform."""
    name: str
    attack_type: AttackType
    damage: int
    range_min: int = 0  # For ranged attacks
    range_max: int = 1  # For ranged attacks (melee uses 0-1 implicitly)

    def get_defense_stat(self) -> str:
        """Return which defense stat this attack checks against."""
        if self.attack_type == AttackType.MELEE:
            return "defense"
        elif self.attack_type == AttackType.RANGED:
            return "dodge"
        else:
            return "resistance"


@dataclass
class UnitPrototype:
    """Template for creating units. Used for summoning and initial setup."""
    name: str
    max_hp: int
    defense: int      # Reduces melee damage
    dodge: int        # Reduces ranged damage
    resistance: int   # Reduces magic damage
    attacks: List[Attack] = field(default_factory=list)
    width: int = 1    # Footprint width (1-4)
    height: int = 1   # Footprint height (1-4)

    # Research and summoning capabilities
    research_efficiency: int = 0       # Added to team research pool per Research action
    max_summoning_pool: int = 0        # Max summoning pool this unit can accumulate
    summon_efficiency: int = 0         # Added to summoning pool per Summon Charge action

    # Summoning requirements (for this prototype to be summoned)
    research_requirement: int = 0      # Team research pool must be >= this
    summoning_cost: int = 0            # Subtracted from summoner's pool

    def create_unit(self, unit_id: str, x: int, y: int, side: Side,
                    is_king: bool = False) -> 'Unit':
        """Create a Unit instance from this prototype."""
        return Unit(
            unit_id=unit_id,
            prototype=self,
            current_hp=self.max_hp,
            x=x,
            y=y,
            side=side,
            current_summoning_pool=0,
            is_king=is_king,
        )


@dataclass
class Unit:
    """An active unit on the battlefield."""
    unit_id: str
    prototype: UnitPrototype
    current_hp: int
    x: int  # Column position (0-3, where 3 is front)
    y: int  # Row position (0-3, top to bottom)
    side: Side
    current_summoning_pool: int = 0
    is_king: bool = False

    # Future expansion
    # status_effects: List[StatusEffect] = field(default_factory=list)
    # cooldowns: Dict[str, int] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.prototype.name

    @property
    def max_hp(self) -> int:
        return self.prototype.max_hp

    @property
    def defense(self) -> int:
        return self.prototype.defense

    @property
    def dodge(self) -> int:
        return self.prototype.dodge

    @property
    def resistance(self) -> int:
        return self.prototype.resistance

    @property
    def width(self) -> int:
        return self.prototype.width

    @property
    def height(self) -> int:
        return self.prototype.height

    @property
    def attacks(self) -> List[Attack]:
        return self.prototype.attacks

    @property
    def is_alive(self) -> bool:
        return self.current_hp > 0

    def get_occupied_cells(self) -> List[tuple]:
        """Return list of (x, y) cells this unit occupies."""
        cells = []
        for dx in range(self.width):
            for dy in range(self.height):
                cells.append((self.x + dx, self.y + dy))
        return cells

    def get_reference_cell(self) -> tuple:
        """Return the reference cell (front-most column, then top-most row)."""
        # Front-most column is x + width - 1, top-most row is y
        return (self.x + self.width - 1, self.y)

    def occupies_row(self, row: int) -> bool:
        """Check if unit occupies a given row."""
        return self.y <= row < self.y + self.height

    def occupies_column(self, col: int) -> bool:
        """Check if unit occupies a given column."""
        return self.x <= col < self.x + self.width

    def get_global_column(self) -> int:
        """Get global column for range calculations.

        Player side: local 0-3 -> global 0-3
        Enemy side: local 0-3 -> global 7-4 (so front columns are adjacent)
        """
        ref_x = self.x + self.width - 1  # Front-most local column
        if self.side == Side.PLAYER:
            return ref_x
        else:
            # Enemy: local 3 -> global 4, local 0 -> global 7
            return 7 - ref_x


@dataclass
class BattleEvent:
    """An event that occurred during battle, for UI to animate."""
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)

    # Event types:
    # "damage" - data: {unit_id, amount, attack_type}
    # "death" - data: {unit_id}
    # "move" - data: {unit_id, from_x, from_y, to_x, to_y}
    # "displacement" - data: {unit_id, from_x, from_y, to_x, to_y}
    # "research" - data: {side, amount, new_total}
    # "summon_charge" - data: {unit_id, amount, new_total}
    # "summon" - data: {summoner_id, new_unit_id, prototype_name, x, y}
    # "turn_start" - data: {side, turn_number}
    # "turn_end" - data: {side}
    # "battle_end" - data: {winner}


@dataclass
class ActionResult:
    """Result of attempting an action."""
    success: bool
    events: List[BattleEvent] = field(default_factory=list)
    error_message: Optional[str] = None

    @staticmethod
    def failure(message: str) -> 'ActionResult':
        return ActionResult(success=False, error_message=message)

    @staticmethod
    def ok(events: List[BattleEvent] = None) -> 'ActionResult':
        return ActionResult(success=True, events=events or [])
