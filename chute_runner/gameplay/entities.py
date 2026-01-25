"""
Factory entities: Belt, Machine, Injector, Source, Splitter.
NO UI DEPENDENCIES.
"""
from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING, Callable
from abc import ABC, abstractmethod
from enum import Enum, auto

from .items import ItemType, MachineType, SourceType, Recipe, RECIPES, SOURCE_OUTPUTS
from .grid import Direction, Grid
from .constants import BELT_SPEED, INJECTOR_CYCLE, SOURCE_RATE

if TYPE_CHECKING:
    from .chutes import ChuteBank


class Entity(ABC):
    """Base class for all grid entities."""

    def __init__(self):
        self.x: int = 0
        self.y: int = 0
        self.grid: Optional[Grid] = None

    @abstractmethod
    def update(self, dt: float) -> None:
        """Update entity state. dt is delta time in seconds."""
        pass

    @abstractmethod
    def can_accept_item(self, item: ItemType) -> bool:
        """Check if this entity can accept an item."""
        pass

    @abstractmethod
    def accept_item(self, item: ItemType) -> bool:
        """
        Try to accept an item into this entity.
        Returns True if accepted, False if rejected.
        """
        pass

    @abstractmethod
    def get_output_item(self) -> Optional[ItemType]:
        """Get the item available for output, or None."""
        pass

    @abstractmethod
    def take_output_item(self) -> Optional[ItemType]:
        """Remove and return the output item, or None if nothing available."""
        pass


class Belt(Entity):
    """
    A conveyor belt that moves items in a direction.
    Holds at most one item at a time.
    """

    def __init__(self, direction: Direction):
        super().__init__()
        self.direction = direction
        self.item: Optional[ItemType] = None
        self.progress: float = 0.0  # 0 to 1, item position along belt

    def update(self, dt: float) -> None:
        if self.item is None:
            self.progress = 0.0
            return

        # Move item along belt
        self.progress += dt * BELT_SPEED

        # If item reached end, try to transfer to next entity
        if self.progress >= 1.0:
            self._try_transfer()

    def _try_transfer(self) -> None:
        """Try to transfer item to the next entity."""
        if self.grid is None or self.item is None:
            return

        next_entity = self.grid.get_neighbor_entity(self.x, self.y, self.direction)

        if next_entity is not None and next_entity.can_accept_item(self.item):
            if next_entity.accept_item(self.item):
                self.item = None
                self.progress = 0.0
        else:
            # Item stuck at end of belt
            self.progress = 1.0

    def can_accept_item(self, item: ItemType) -> bool:
        return self.item is None

    def accept_item(self, item: ItemType) -> bool:
        if self.item is not None:
            return False
        self.item = item
        self.progress = 0.0
        return True

    def get_output_item(self) -> Optional[ItemType]:
        # Belt output is only available when item is at the end
        if self.item is not None and self.progress >= 1.0:
            return self.item
        return None

    def take_output_item(self) -> Optional[ItemType]:
        if self.progress >= 1.0 and self.item is not None:
            item = self.item
            self.item = None
            self.progress = 0.0
            return item
        return None

    def __repr__(self) -> str:
        return f"Belt({self.direction.name}, item={self.item})"


class Source(Entity):
    """
    A resource source that produces raw materials.
    Has an internal buffer that fills over time.
    """

    def __init__(self, source_type: SourceType):
        super().__init__()
        self.source_type = source_type
        self.output_type = SOURCE_OUTPUTS[source_type]
        self.buffer: int = 0
        self.max_buffer: int = 5
        self.production_progress: float = 0.0

    def update(self, dt: float) -> None:
        if self.buffer >= self.max_buffer:
            # Buffer full, don't produce more
            self.production_progress = 0.0
            return

        self.production_progress += dt * SOURCE_RATE
        while self.production_progress >= 1.0 and self.buffer < self.max_buffer:
            self.buffer += 1
            self.production_progress -= 1.0

    def can_accept_item(self, item: ItemType) -> bool:
        # Sources don't accept items
        return False

    def accept_item(self, item: ItemType) -> bool:
        return False

    def get_output_item(self) -> Optional[ItemType]:
        if self.buffer > 0:
            return self.output_type
        return None

    def take_output_item(self) -> Optional[ItemType]:
        if self.buffer > 0:
            self.buffer -= 1
            return self.output_type
        return None

    def __repr__(self) -> str:
        return f"Source({self.source_type.name}, buffer={self.buffer})"


class Machine(Entity):
    """
    A machine that transforms items according to a recipe.
    """

    def __init__(self, machine_type: MachineType):
        super().__init__()
        self.machine_type = machine_type
        self.recipe: Recipe = RECIPES[machine_type]

        # Input slots (one per recipe input)
        self.input_slots: List[Optional[ItemType]] = [None] * len(self.recipe.inputs)

        # Output slot
        self.output_item: Optional[ItemType] = None

        # Crafting state
        self.crafting_progress: float = 0.0
        self.is_crafting: bool = False

    def update(self, dt: float) -> None:
        # If output is full, can't do anything
        if self.output_item is not None:
            return

        # Check if we can start crafting
        if not self.is_crafting:
            if self._has_all_inputs():
                self._consume_inputs()
                self.is_crafting = True
                self.crafting_progress = 0.0
            else:
                return  # No inputs, nothing to do

        # Progress crafting (continues in same frame after starting)
        self.crafting_progress += dt
        if self.crafting_progress >= self.recipe.time:
            self.output_item = self.recipe.output
            self.is_crafting = False
            self.crafting_progress = 0.0

    def _has_all_inputs(self) -> bool:
        """Check if all input slots are filled with correct items."""
        for i, required in enumerate(self.recipe.inputs):
            if self.input_slots[i] != required:
                return False
        return True

    def _consume_inputs(self) -> None:
        """Clear all input slots."""
        for i in range(len(self.input_slots)):
            self.input_slots[i] = None

    def can_accept_item(self, item: ItemType) -> bool:
        """Check if there's an empty slot for this item type."""
        for i, required in enumerate(self.recipe.inputs):
            if required == item and self.input_slots[i] is None:
                return True
        return False

    def accept_item(self, item: ItemType) -> bool:
        """Accept item into the appropriate input slot."""
        for i, required in enumerate(self.recipe.inputs):
            if required == item and self.input_slots[i] is None:
                self.input_slots[i] = item
                return True
        return False

    def get_output_item(self) -> Optional[ItemType]:
        return self.output_item

    def take_output_item(self) -> Optional[ItemType]:
        if self.output_item is not None:
            item = self.output_item
            self.output_item = None
            return item
        return None

    def __repr__(self) -> str:
        return f"Machine({self.machine_type.name}, crafting={self.is_crafting})"


class Injector(Entity):
    """
    Moves items between entities.
    Pulls from source_direction, pushes to target_direction.
    Can also push to chutes.
    """

    def __init__(self, source_dir: Direction, target_dir: Direction):
        super().__init__()
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.held_item: Optional[ItemType] = None
        self.cycle_progress: float = 0.0
        self.chute_bank: Optional['ChuteBank'] = None  # Set if targeting a chute
        self.target_chute_type: Optional[ItemType] = None  # Which chute to target

    def set_chute_target(self, chute_bank: 'ChuteBank', item_type: ItemType) -> None:
        """Configure this injector to push to a chute instead of grid."""
        self.chute_bank = chute_bank
        self.target_chute_type = item_type

    def update(self, dt: float) -> None:
        self.cycle_progress += dt

        if self.cycle_progress >= INJECTOR_CYCLE:
            self.cycle_progress = 0.0
            self._do_transfer()

    def _do_transfer(self) -> None:
        """Perform one transfer cycle."""
        if self.grid is None:
            return

        # If not holding an item, try to pick one up
        if self.held_item is None:
            source = self.grid.get_neighbor_entity(self.x, self.y, self.source_dir)
            if source is not None:
                item = source.take_output_item()
                if item is not None:
                    self.held_item = item
            return

        # Holding an item, try to deliver it
        delivered = False

        # Check if targeting a chute
        if self.chute_bank is not None and self.target_chute_type is not None:
            if self.held_item == self.target_chute_type:
                if self.chute_bank.add_item(self.target_chute_type):
                    delivered = True

        # Otherwise try grid target
        if not delivered:
            target = self.grid.get_neighbor_entity(self.x, self.y, self.target_dir)
            if target is not None and target.can_accept_item(self.held_item):
                if target.accept_item(self.held_item):
                    delivered = True

        if delivered:
            self.held_item = None

    def can_accept_item(self, item: ItemType) -> bool:
        # Injectors don't accept items from other entities
        return False

    def accept_item(self, item: ItemType) -> bool:
        return False

    def get_output_item(self) -> Optional[ItemType]:
        # Injectors don't output to the normal flow
        return None

    def take_output_item(self) -> Optional[ItemType]:
        return None

    def __repr__(self) -> str:
        return f"Injector({self.source_dir.name}->{self.target_dir.name}, item={self.held_item})"


class Splitter(Entity):
    """
    Splits incoming items between two output directions.
    Alternates between outputs.
    """

    def __init__(self, input_dir: Direction, output1_dir: Direction, output2_dir: Direction):
        super().__init__()
        self.input_dir = input_dir
        self.output1_dir = output1_dir
        self.output2_dir = output2_dir
        self.item: Optional[ItemType] = None
        self.next_output: int = 0  # 0 or 1

    def update(self, dt: float) -> None:
        if self.item is None:
            return

        # Try to output item
        outputs = [self.output1_dir, self.output2_dir]

        # Try preferred output first, then the other
        for i in range(2):
            output_idx = (self.next_output + i) % 2
            output_dir = outputs[output_idx]

            if self.grid is not None:
                target = self.grid.get_neighbor_entity(self.x, self.y, output_dir)
                if target is not None and target.can_accept_item(self.item):
                    if target.accept_item(self.item):
                        self.item = None
                        self.next_output = (output_idx + 1) % 2
                        return

    def can_accept_item(self, item: ItemType) -> bool:
        return self.item is None

    def accept_item(self, item: ItemType) -> bool:
        if self.item is not None:
            return False
        self.item = item
        return True

    def get_output_item(self) -> Optional[ItemType]:
        return None  # Splitters push, they don't get pulled from

    def take_output_item(self) -> Optional[ItemType]:
        return None

    def __repr__(self) -> str:
        return f"Splitter({self.input_dir.name}->{self.output1_dir.name}/{self.output2_dir.name})"
