"""
Tests for chute system.
"""
import pytest
from gameplay.chutes import Chute, ChuteBank
from gameplay.items import ItemType


class TestChute:
    """Tests for Chute class."""

    def test_chute_add_item(self):
        """Items can be added to chute."""
        chute = Chute(ItemType.SWORD, capacity=10)
        assert chute.current == 0

        assert chute.add_item()
        assert chute.current == 1

    def test_chute_full(self):
        """Chute rejects items when full."""
        chute = Chute(ItemType.SWORD, capacity=3)

        chute.add_item()
        chute.add_item()
        chute.add_item()
        assert chute.is_full()

        assert not chute.add_item()
        assert chute.current == 3

    def test_chute_remove_items(self):
        """Items can be removed from chute."""
        chute = Chute(ItemType.SHIELD, capacity=10)
        chute.current = 5

        removed = chute.remove_items(3)
        assert removed == 3
        assert chute.current == 2

    def test_chute_remove_partial(self):
        """Remove returns only what's available."""
        chute = Chute(ItemType.KEY, capacity=10)
        chute.current = 2

        removed = chute.remove_items(5)
        assert removed == 2
        assert chute.current == 0

    def test_chute_fill_ratio(self):
        """Fill ratio is calculated correctly."""
        chute = Chute(ItemType.SWORD, capacity=10)
        assert chute.fill_ratio == 0.0

        chute.current = 5
        assert chute.fill_ratio == 0.5

        chute.current = 10
        assert chute.fill_ratio == 1.0

    def test_chute_is_empty(self):
        """is_empty works correctly."""
        chute = Chute(ItemType.SWORD, capacity=10)
        assert chute.is_empty()

        chute.current = 1
        assert not chute.is_empty()


class TestChuteBank:
    """Tests for ChuteBank class."""

    def test_chute_bank_has_mvp_chutes(self):
        """ChuteBank initializes with MVP chutes."""
        bank = ChuteBank()

        assert bank.get_chute(ItemType.SWORD) is not None
        assert bank.get_chute(ItemType.SHIELD) is not None
        assert bank.get_chute(ItemType.KEY) is not None

    def test_chute_bank_no_raw_chutes(self):
        """ChuteBank doesn't have chutes for raw materials."""
        bank = ChuteBank()

        assert bank.get_chute(ItemType.ORE) is None
        assert bank.get_chute(ItemType.FIBER) is None
        assert bank.get_chute(ItemType.OIL) is None

    def test_chute_bank_add_item(self):
        """ChuteBank routes items to correct chutes."""
        bank = ChuteBank()

        assert bank.add_item(ItemType.SWORD)
        assert bank.get_count(ItemType.SWORD) == 1

        assert bank.add_item(ItemType.SHIELD)
        assert bank.get_count(ItemType.SHIELD) == 1

    def test_chute_bank_rejects_invalid_item(self):
        """ChuteBank rejects items that have no chute."""
        bank = ChuteBank()

        assert not bank.add_item(ItemType.ORE)
        assert not bank.add_item(ItemType.PLATE)

    def test_chute_bank_remove_items(self):
        """ChuteBank removes from correct chute."""
        bank = ChuteBank()
        bank.add_item(ItemType.KEY)
        bank.add_item(ItemType.KEY)
        bank.add_item(ItemType.KEY)

        removed = bank.remove_items(ItemType.KEY, 2)
        assert removed == 2
        assert bank.get_count(ItemType.KEY) == 1

    def test_chute_bank_can_accept(self):
        """can_accept checks chute availability."""
        bank = ChuteBank()

        assert bank.can_accept(ItemType.SWORD)
        assert not bank.can_accept(ItemType.ORE)

        # Fill sword chute
        sword_chute = bank.get_chute(ItemType.SWORD)
        sword_chute.current = sword_chute.capacity

        assert not bank.can_accept(ItemType.SWORD)
