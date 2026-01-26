"""
Tutorial system for progressive building introduction.
NO UI DEPENDENCIES.
"""
from dataclasses import dataclass, field
from typing import Set, Callable, List, Optional, TYPE_CHECKING

from .items import ItemType, MachineType, SourceType
from .entities import Source, Belt, Machine, Injector, Splitter

if TYPE_CHECKING:
    from .game import Game


@dataclass
class TutorialStep:
    """A single step in the tutorial progression."""
    instruction: str                      # HUD text to display
    unlocked: Set[str]                    # Building keys unlocked (cumulative)
    objective: Callable[['Game'], bool]   # Returns True when step is complete
    enable_gates: bool = False            # If True, gates start appearing


# ============================================================================
# OBJECTIVE HELPER FUNCTIONS
# ============================================================================

def has_source(game: 'Game', source_type: Optional[SourceType] = None) -> bool:
    """Check if game has a source (optionally of specific type)."""
    for entity in game.grid.iter_entities():
        if isinstance(entity, Source):
            if source_type is None or entity.source_type == source_type:
                return True
    return False


def has_belt(game: 'Game') -> bool:
    """Check if game has at least one belt."""
    for entity in game.grid.iter_entities():
        if isinstance(entity, Belt):
            return True
    return False


def has_machine(game: 'Game', machine_type: Optional[MachineType] = None) -> bool:
    """Check if game has a machine (optionally of specific type)."""
    for entity in game.grid.iter_entities():
        if isinstance(entity, Machine):
            if machine_type is None or entity.machine_type == machine_type:
                return True
    return False


def has_injector_with_chute_target(game: 'Game') -> bool:
    """Check if game has an injector targeting a chute."""
    for entity in game.grid.iter_entities():
        if isinstance(entity, Injector):
            if entity.target_chute_type is not None:
                return True
    return False


def has_splitter(game: 'Game') -> bool:
    """Check if game has at least one splitter."""
    for entity in game.grid.iter_entities():
        if isinstance(entity, Splitter):
            return True
    return False


def chute_has_items(game: 'Game', item_type: ItemType, count: int = 1) -> bool:
    """Check if a chute has at least count items."""
    return game.chute_bank.get_count(item_type) >= count


# ============================================================================
# TUTORIAL STEPS DEFINITION
# ============================================================================

TUTORIAL_STEPS: List[TutorialStep] = [
    # Step 1: Place first source
    TutorialStep(
        instruction="[Q] ORE MINE. Arrows+Space to build",
        unlocked={'source_ore'},
        objective=lambda g: has_source(g, SourceType.ORE_MINE),
    ),

    # Step 2: Learn belts
    TutorialStep(
        instruction="[1-4] BELT next to mine",
        unlocked={'source_ore', 'belt'},
        objective=lambda g: has_belt(g),
    ),

    # Step 3: First machine
    TutorialStep(
        instruction="[7] SMELTER at belt end (ore->plate)",
        unlocked={'source_ore', 'belt', 'smelter'},
        objective=lambda g: has_machine(g, MachineType.SMELTER),
    ),

    # Step 4: Learn injectors and chute targeting
    TutorialStep(
        instruction="[6] INJECTOR then [T] target SWORDS",
        unlocked={'source_ore', 'belt', 'smelter', 'injector'},
        objective=lambda g: has_injector_with_chute_target(g),
    ),

    # Step 5: Second production chain - now gates start
    TutorialStep(
        instruction="[W] FIBER [9] LOOM (fiber->wrap)",
        unlocked={'source_ore', 'source_fiber', 'belt', 'smelter', 'loom', 'injector'},
        objective=lambda g: has_machine(g, MachineType.LOOM),
        enable_gates=True,  # Gates start appearing now
    ),

    # Step 6: Multi-input machine (Press + Forge for swords)
    TutorialStep(
        instruction="[8] PRESS [0] FORGE (blade+wrap->sword)",
        unlocked={'source_ore', 'source_fiber', 'belt', 'smelter', 'loom', 'press', 'forge', 'injector'},
        objective=lambda g: has_machine(g, MachineType.FORGE),
        enable_gates=True,
    ),

    # Step 7: Defense items (Armory for shields, Lockbench for keys)
    TutorialStep(
        instruction="[-] ARMORY [E] OIL [=] LOCKBENCH",
        unlocked={'source_ore', 'source_fiber', 'source_oil', 'belt', 'smelter', 'loom',
                  'press', 'forge', 'armory', 'lockbench', 'injector'},
        objective=lambda g: has_machine(g, MachineType.ARMORY) or has_machine(g, MachineType.LOCKBENCH),
        enable_gates=True,
    ),

    # Step 8: Splitter for advanced routing
    TutorialStep(
        instruction="[5] SPLITTER. All unlocked! Beat the level",
        unlocked={'source_ore', 'source_fiber', 'source_oil', 'belt', 'smelter', 'loom',
                  'press', 'forge', 'armory', 'lockbench', 'injector', 'splitter'},
        objective=lambda g: False,  # Never completes - tutorial ends when level won
        enable_gates=True,
    ),
]


class TutorialState:
    """
    Manages tutorial progression.
    Checks objectives and advances through steps.
    """

    def __init__(self):
        self.current_step: int = 0
        self.steps: List[TutorialStep] = TUTORIAL_STEPS
        self.completed: bool = False

    def check_and_advance(self, game: 'Game') -> bool:
        """
        Check if current objective is met and advance if so.
        Returns True if advanced to next step.
        """
        if self.completed:
            return False

        if self.current_step >= len(self.steps):
            self.completed = True
            return False

        step = self.steps[self.current_step]

        if step.objective(game):
            self.current_step += 1
            if self.current_step >= len(self.steps):
                self.completed = True
            return True

        return False

    def get_instruction(self) -> str:
        """Get the current step's instruction text."""
        if self.completed or self.current_step >= len(self.steps):
            return "Tutorial complete! Good luck!"
        return self.steps[self.current_step].instruction

    def get_unlocked_buildings(self) -> Set[str]:
        """Get all currently unlocked building keys."""
        if self.completed or self.current_step >= len(self.steps):
            # All unlocked when tutorial complete
            return self.steps[-1].unlocked if self.steps else set()
        return self.steps[self.current_step].unlocked

    def are_gates_enabled(self) -> bool:
        """Check if gates should be active."""
        if self.completed:
            return True
        if self.current_step >= len(self.steps):
            return True
        return self.steps[self.current_step].enable_gates

    def is_complete(self) -> bool:
        """Check if tutorial is fully complete."""
        return self.completed

    def get_step_number(self) -> int:
        """Get current step number (1-indexed for display)."""
        return min(self.current_step + 1, len(self.steps))

    def get_total_steps(self) -> int:
        """Get total number of tutorial steps."""
        return len(self.steps)


def create_tutorial() -> TutorialState:
    """Create a new tutorial state."""
    return TutorialState()
