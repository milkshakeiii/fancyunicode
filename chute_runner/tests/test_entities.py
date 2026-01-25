"""
Tests for factory entities: Belt, Source, Machine, Injector, Splitter.
"""
import pytest
from gameplay.grid import Grid, Direction
from gameplay.entities import Belt, Source, Machine, Injector, Splitter
from gameplay.items import ItemType, MachineType, SourceType
from gameplay.constants import BELT_SPEED, INJECTOR_CYCLE, SOURCE_RATE


class TestBelt:
    """Tests for Belt entity."""

    def test_belt_accepts_item(self):
        """Belt accepts item when empty."""
        belt = Belt(Direction.RIGHT)
        assert belt.can_accept_item(ItemType.ORE)
        assert belt.accept_item(ItemType.ORE)
        assert belt.item == ItemType.ORE

    def test_belt_rejects_when_full(self):
        """Belt rejects item when occupied."""
        belt = Belt(Direction.RIGHT)
        belt.accept_item(ItemType.ORE)

        assert not belt.can_accept_item(ItemType.FIBER)
        assert not belt.accept_item(ItemType.FIBER)

    def test_belt_moves_item(self):
        """Item progresses along belt over time."""
        belt = Belt(Direction.RIGHT)
        belt.accept_item(ItemType.ORE)

        assert belt.progress == 0.0

        # Move item partway
        belt.update(0.25)  # At BELT_SPEED=2, 0.25s = 0.5 progress
        assert belt.progress == pytest.approx(0.5)

    def test_belt_transfers_to_next_belt(self):
        """Item transfers to next belt when reaching end."""
        grid = Grid(10, 5)
        belt1 = Belt(Direction.RIGHT)
        belt2 = Belt(Direction.RIGHT)

        grid.place_entity(0, 0, belt1)
        grid.place_entity(1, 0, belt2)

        belt1.accept_item(ItemType.ORE)

        # Move item to end of belt1
        belt1.update(0.5)  # progress = 1.0

        # Item should transfer to belt2
        assert belt1.item is None
        assert belt2.item == ItemType.ORE

    def test_belt_stalls_at_blocked_output(self):
        """Item stalls if next entity can't accept it."""
        grid = Grid(10, 5)
        belt1 = Belt(Direction.RIGHT)
        belt2 = Belt(Direction.RIGHT)

        grid.place_entity(0, 0, belt1)
        grid.place_entity(1, 0, belt2)

        # Fill belt2 first
        belt2.accept_item(ItemType.FIBER)

        # Now fill belt1
        belt1.accept_item(ItemType.ORE)
        belt1.update(1.0)  # Should hit end

        # Item stuck on belt1
        assert belt1.item == ItemType.ORE
        assert belt1.progress == 1.0

    def test_belt_output_item(self):
        """get_output_item only returns item at belt end."""
        belt = Belt(Direction.RIGHT)
        belt.accept_item(ItemType.ORE)

        # Not at end yet
        assert belt.get_output_item() is None

        belt.progress = 1.0
        assert belt.get_output_item() == ItemType.ORE

    def test_belt_take_output(self):
        """take_output_item removes item from belt."""
        belt = Belt(Direction.RIGHT)
        belt.accept_item(ItemType.ORE)
        belt.progress = 1.0

        item = belt.take_output_item()
        assert item == ItemType.ORE
        assert belt.item is None
        assert belt.progress == 0.0


class TestSource:
    """Tests for Source entity."""

    def test_source_produces_item(self):
        """Source produces items over time."""
        source = Source(SourceType.ORE_MINE)
        assert source.buffer == 0

        # Produce one item
        source.update(1.0 / SOURCE_RATE)
        assert source.buffer == 1
        assert source.output_type == ItemType.ORE

    def test_source_fills_buffer(self):
        """Source fills buffer up to max."""
        source = Source(SourceType.ORE_MINE)

        # Fill buffer
        source.update(10.0)  # Plenty of time
        assert source.buffer == source.max_buffer

    def test_source_stops_when_full(self):
        """Source stops producing when buffer is full."""
        source = Source(SourceType.ORE_MINE)
        source.buffer = source.max_buffer

        source.update(1.0)
        assert source.buffer == source.max_buffer

    def test_source_output(self):
        """Source provides output from buffer."""
        source = Source(SourceType.FIBER_GARDEN)
        source.buffer = 3

        assert source.get_output_item() == ItemType.FIBER

        item = source.take_output_item()
        assert item == ItemType.FIBER
        assert source.buffer == 2

    def test_source_rejects_input(self):
        """Source doesn't accept items."""
        source = Source(SourceType.OIL_WELL)
        assert not source.can_accept_item(ItemType.ORE)
        assert not source.accept_item(ItemType.ORE)


class TestMachine:
    """Tests for Machine entity."""

    def test_machine_accepts_correct_input(self):
        """Machine accepts items matching recipe inputs."""
        smelter = Machine(MachineType.SMELTER)

        assert smelter.can_accept_item(ItemType.ORE)
        assert smelter.accept_item(ItemType.ORE)
        assert smelter.input_slots[0] == ItemType.ORE

    def test_machine_rejects_wrong_input(self):
        """Machine rejects items not in recipe."""
        smelter = Machine(MachineType.SMELTER)

        assert not smelter.can_accept_item(ItemType.FIBER)
        assert not smelter.accept_item(ItemType.FIBER)

    def test_machine_crafts_single_input(self):
        """Machine crafts with single input recipe."""
        smelter = Machine(MachineType.SMELTER)
        smelter.accept_item(ItemType.ORE)

        # Start crafting
        smelter.update(0.1)
        assert smelter.is_crafting
        assert smelter.input_slots[0] is None  # Consumed

        # Finish crafting
        smelter.update(1.0)  # MACHINE_TIME_SIMPLE = 1.0
        assert not smelter.is_crafting
        assert smelter.output_item == ItemType.PLATE

    def test_machine_crafts_dual_input(self):
        """Machine crafts with dual input recipe."""
        forge = Machine(MachineType.FORGE)

        # Need blade + wrap
        assert forge.can_accept_item(ItemType.BLADE)
        assert forge.can_accept_item(ItemType.WRAP)

        forge.accept_item(ItemType.BLADE)
        forge.accept_item(ItemType.WRAP)

        # Should start crafting
        forge.update(0.1)
        assert forge.is_crafting

        # Finish crafting
        forge.update(1.5)  # MACHINE_TIME_COMPLEX = 1.5
        assert forge.output_item == ItemType.SWORD

    def test_machine_waits_for_all_inputs(self):
        """Machine doesn't craft until all inputs present."""
        forge = Machine(MachineType.FORGE)
        forge.accept_item(ItemType.BLADE)

        forge.update(0.5)
        assert not forge.is_crafting  # Missing wrap

    def test_machine_blocks_when_output_full(self):
        """Machine doesn't craft when output slot is full."""
        smelter = Machine(MachineType.SMELTER)

        # First craft
        smelter.accept_item(ItemType.ORE)
        smelter.update(2.0)
        assert smelter.output_item == ItemType.PLATE

        # Try second craft
        smelter.accept_item(ItemType.ORE)
        smelter.update(2.0)
        assert smelter.input_slots[0] == ItemType.ORE  # Not consumed
        assert not smelter.is_crafting

    def test_machine_take_output(self):
        """Machine output can be taken."""
        smelter = Machine(MachineType.SMELTER)
        smelter.accept_item(ItemType.ORE)
        smelter.update(2.0)

        item = smelter.take_output_item()
        assert item == ItemType.PLATE
        assert smelter.output_item is None


class TestInjector:
    """Tests for Injector entity."""

    def test_injector_transfers_item(self):
        """Injector moves item from source to target."""
        grid = Grid(10, 5)
        source = Source(SourceType.ORE_MINE)
        injector = Injector(Direction.LEFT, Direction.RIGHT)
        belt = Belt(Direction.RIGHT)

        # Layout: [Source] [Injector] [Belt]
        grid.place_entity(0, 0, source)
        grid.place_entity(1, 0, injector)
        grid.place_entity(2, 0, belt)

        source.buffer = 3

        # Run injector cycle
        injector.update(INJECTOR_CYCLE)

        # Should have picked up item
        assert injector.held_item == ItemType.ORE
        assert source.buffer == 2

        # Next cycle delivers
        injector.update(INJECTOR_CYCLE)
        assert injector.held_item is None
        assert belt.item == ItemType.ORE

    def test_injector_waits_for_empty_target(self):
        """Injector holds item if target is full."""
        grid = Grid(10, 5)
        source = Source(SourceType.ORE_MINE)
        injector = Injector(Direction.LEFT, Direction.RIGHT)
        belt = Belt(Direction.RIGHT)

        grid.place_entity(0, 0, source)
        grid.place_entity(1, 0, injector)
        grid.place_entity(2, 0, belt)

        source.buffer = 3
        belt.accept_item(ItemType.FIBER)  # Fill belt

        # Pick up item
        injector.update(INJECTOR_CYCLE)
        assert injector.held_item == ItemType.ORE

        # Can't deliver
        injector.update(INJECTOR_CYCLE)
        assert injector.held_item == ItemType.ORE  # Still holding


class TestSplitter:
    """Tests for Splitter entity."""

    def test_splitter_alternates_outputs(self):
        """Splitter alternates between two outputs."""
        grid = Grid(10, 5)
        splitter = Splitter(Direction.LEFT, Direction.UP, Direction.DOWN)
        belt_up = Belt(Direction.UP)
        belt_down = Belt(Direction.DOWN)

        grid.place_entity(1, 1, splitter)
        grid.place_entity(1, 0, belt_up)
        grid.place_entity(1, 2, belt_down)

        # First item goes to output 1 (UP)
        splitter.accept_item(ItemType.ORE)
        splitter.update(0.1)
        assert belt_up.item == ItemType.ORE
        assert belt_down.item is None

        # Second item goes to output 2 (DOWN)
        splitter.accept_item(ItemType.FIBER)
        splitter.update(0.1)
        assert belt_down.item == ItemType.FIBER

    def test_splitter_skips_blocked_output(self):
        """Splitter uses other output if preferred is blocked."""
        grid = Grid(10, 5)
        splitter = Splitter(Direction.LEFT, Direction.UP, Direction.DOWN)
        belt_up = Belt(Direction.UP)
        belt_down = Belt(Direction.DOWN)

        grid.place_entity(1, 1, splitter)
        grid.place_entity(1, 0, belt_up)
        grid.place_entity(1, 2, belt_down)

        # Block preferred output
        belt_up.accept_item(ItemType.PLATE)

        # Item should go to DOWN instead
        splitter.accept_item(ItemType.ORE)
        splitter.update(0.1)
        assert belt_down.item == ItemType.ORE
