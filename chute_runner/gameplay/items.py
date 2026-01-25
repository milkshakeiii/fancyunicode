"""
Item types and recipes.
NO UI DEPENDENCIES.
"""
from enum import Enum, auto
from dataclasses import dataclass
from typing import Tuple, Optional


class ItemType(Enum):
    """All item types in the game."""
    # Raw materials (from sources)
    ORE = auto()
    FIBER = auto()
    OIL = auto()

    # Intermediate products
    PLATE = auto()
    BLADE = auto()
    WRAP = auto()

    # Action tokens (go into chutes)
    SWORD = auto()
    SHIELD = auto()
    KEY = auto()


# Which items can go into chutes (action tokens)
CHUTE_ITEMS = {ItemType.SWORD, ItemType.SHIELD, ItemType.KEY}


@dataclass(frozen=True)
class Recipe:
    """A crafting recipe for a machine."""
    inputs: Tuple[ItemType, ...]   # Required input items (1 or 2)
    output: ItemType               # Produced item
    time: float                    # Seconds to craft

    @property
    def is_complex(self) -> bool:
        """True if recipe requires multiple inputs."""
        return len(self.inputs) > 1


class MachineType(Enum):
    """Types of machines that can be placed."""
    SMELTER = auto()    # ore -> plate
    PRESS = auto()      # plate -> blade
    LOOM = auto()       # fiber -> wrap
    FORGE = auto()      # blade + wrap -> sword
    ARMORY = auto()     # wrap + plate -> shield
    LOCKBENCH = auto()  # plate + oil -> key


# Recipe definitions for each machine type
RECIPES = {
    MachineType.SMELTER: Recipe(
        inputs=(ItemType.ORE,),
        output=ItemType.PLATE,
        time=1.0
    ),
    MachineType.PRESS: Recipe(
        inputs=(ItemType.PLATE,),
        output=ItemType.BLADE,
        time=1.0
    ),
    MachineType.LOOM: Recipe(
        inputs=(ItemType.FIBER,),
        output=ItemType.WRAP,
        time=1.0
    ),
    MachineType.FORGE: Recipe(
        inputs=(ItemType.BLADE, ItemType.WRAP),
        output=ItemType.SWORD,
        time=1.5
    ),
    MachineType.ARMORY: Recipe(
        inputs=(ItemType.WRAP, ItemType.PLATE),
        output=ItemType.SHIELD,
        time=1.5
    ),
    MachineType.LOCKBENCH: Recipe(
        inputs=(ItemType.PLATE, ItemType.OIL),
        output=ItemType.KEY,
        time=1.5
    ),
}


class SourceType(Enum):
    """Types of resource sources."""
    ORE_MINE = auto()
    FIBER_GARDEN = auto()
    OIL_WELL = auto()


# What each source produces
SOURCE_OUTPUTS = {
    SourceType.ORE_MINE: ItemType.ORE,
    SourceType.FIBER_GARDEN: ItemType.FIBER,
    SourceType.OIL_WELL: ItemType.OIL,
}
