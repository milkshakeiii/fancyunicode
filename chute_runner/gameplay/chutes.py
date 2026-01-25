"""
Chute system - vertical channels that feed the top lane.
NO UI DEPENDENCIES.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional

from .items import ItemType, CHUTE_ITEMS
from .constants import CHUTE_CAPACITY


@dataclass
class Chute:
    """
    A single chute that holds action tokens for the runner.

    Chutes are the bridge between the factory and the runner.
    The factory fills them; the gates drain them.
    """
    item_type: ItemType
    capacity: int = CHUTE_CAPACITY
    current: int = 0

    def add_item(self) -> bool:
        """
        Add one item to the chute.
        Returns True if added, False if full.
        """
        if self.current >= self.capacity:
            return False
        self.current += 1
        return True

    def remove_items(self, count: int) -> int:
        """
        Remove up to `count` items from the chute.
        Returns the number actually removed.
        """
        removed = min(count, self.current)
        self.current -= removed
        return removed

    def is_empty(self) -> bool:
        return self.current == 0

    def is_full(self) -> bool:
        return self.current >= self.capacity

    @property
    def fill_ratio(self) -> float:
        """Return fill level as 0.0 to 1.0."""
        return self.current / self.capacity if self.capacity > 0 else 0.0


class ChuteBank:
    """
    Manages all chutes.
    MVP has 3 chutes: Swords, Shields, Keys.
    """

    def __init__(self):
        self.chutes: Dict[ItemType, Chute] = {}

        # Initialize MVP chutes
        for item_type in [ItemType.SWORD, ItemType.SHIELD, ItemType.KEY]:
            self.chutes[item_type] = Chute(item_type=item_type)

    def get_chute(self, item_type: ItemType) -> Optional[Chute]:
        """Get chute for an item type, or None if no such chute."""
        return self.chutes.get(item_type)

    def add_item(self, item_type: ItemType) -> bool:
        """
        Add an item to the appropriate chute.
        Returns True if added, False if no chute exists or chute is full.
        """
        chute = self.chutes.get(item_type)
        if chute is None:
            return False
        return chute.add_item()

    def remove_items(self, item_type: ItemType, count: int) -> int:
        """
        Remove items from a chute.
        Returns the number actually removed.
        """
        chute = self.chutes.get(item_type)
        if chute is None:
            return 0
        return chute.remove_items(count)

    def get_count(self, item_type: ItemType) -> int:
        """Get current count in a chute."""
        chute = self.chutes.get(item_type)
        if chute is None:
            return 0
        return chute.current

    def can_accept(self, item_type: ItemType) -> bool:
        """Check if we can accept more of this item type."""
        chute = self.chutes.get(item_type)
        if chute is None:
            return False
        return not chute.is_full()
