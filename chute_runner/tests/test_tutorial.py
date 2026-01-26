"""
Tests for the tutorial system.
"""
import pytest
from gameplay.tutorial import (
    TutorialState, TutorialStep, create_tutorial,
    has_source, has_belt, has_machine, has_injector_with_chute_target,
    has_splitter, chute_has_items, TUTORIAL_STEPS
)
from gameplay.game import Game, GamePhase
from gameplay.grid import Direction
from gameplay.items import ItemType, MachineType, SourceType
from gameplay.level import create_tutorial_level


class TestTutorialState:
    """Tests for TutorialState class."""

    def test_initial_state(self):
        """Tutorial starts at step 0, not completed."""
        tutorial = create_tutorial()
        assert tutorial.current_step == 0
        assert not tutorial.completed
        assert not tutorial.is_complete()

    def test_get_instruction(self):
        """Can get current instruction."""
        tutorial = create_tutorial()
        instruction = tutorial.get_instruction()
        assert isinstance(instruction, str)
        assert len(instruction) > 0

    def test_get_unlocked_buildings(self):
        """Can get unlocked buildings for current step."""
        tutorial = create_tutorial()
        unlocked = tutorial.get_unlocked_buildings()
        assert isinstance(unlocked, set)
        # First step should only unlock ore source
        assert 'source_ore' in unlocked

    def test_gates_disabled_initially(self):
        """Gates are disabled until step 5."""
        tutorial = create_tutorial()
        # Steps 0-3 have gates disabled
        for i in range(4):
            tutorial.current_step = i
            assert not tutorial.are_gates_enabled(), f"Step {i} should have gates disabled"
        # Step 4 (index) enables gates
        tutorial.current_step = 4
        assert tutorial.are_gates_enabled()

    def test_step_number_display(self):
        """Step number is 1-indexed for display."""
        tutorial = create_tutorial()
        assert tutorial.get_step_number() == 1
        tutorial.current_step = 2
        assert tutorial.get_step_number() == 3

    def test_total_steps(self):
        """Total steps matches TUTORIAL_STEPS length."""
        tutorial = create_tutorial()
        assert tutorial.get_total_steps() == len(TUTORIAL_STEPS)


class TestTutorialObjectives:
    """Tests for tutorial objective helper functions."""

    def test_has_source_empty_grid(self):
        """has_source returns False for empty grid."""
        game = Game()
        assert not has_source(game)

    def test_has_source_with_ore_mine(self):
        """has_source detects ore mine."""
        game = Game()
        game.place_source(0, 0, SourceType.ORE_MINE)
        assert has_source(game)
        assert has_source(game, SourceType.ORE_MINE)
        assert not has_source(game, SourceType.FIBER_GARDEN)

    def test_has_belt_empty_grid(self):
        """has_belt returns False for empty grid."""
        game = Game()
        assert not has_belt(game)

    def test_has_belt_with_belt(self):
        """has_belt detects belt."""
        game = Game()
        game.place_belt(0, 0, Direction.RIGHT)
        assert has_belt(game)

    def test_has_machine_empty_grid(self):
        """has_machine returns False for empty grid."""
        game = Game()
        assert not has_machine(game)

    def test_has_machine_with_smelter(self):
        """has_machine detects smelter."""
        game = Game()
        game.place_machine(0, 0, MachineType.SMELTER)
        assert has_machine(game)
        assert has_machine(game, MachineType.SMELTER)
        assert not has_machine(game, MachineType.FORGE)

    def test_has_injector_with_chute_target(self):
        """has_injector_with_chute_target detects injectors targeting chutes."""
        game = Game()
        # Injector without chute target
        game.place_injector(0, 0, Direction.LEFT, Direction.RIGHT)
        assert not has_injector_with_chute_target(game)

        # Injector with chute target
        game.place_injector(1, 0, Direction.LEFT, Direction.RIGHT, chute_target=ItemType.SWORD)
        assert has_injector_with_chute_target(game)

    def test_chute_has_items(self):
        """chute_has_items checks chute contents."""
        game = Game()
        assert not chute_has_items(game, ItemType.SWORD)

        # Manually add items to chute
        game.chute_bank.add_item(ItemType.SWORD)
        assert chute_has_items(game, ItemType.SWORD)
        assert chute_has_items(game, ItemType.SWORD, count=1)
        assert not chute_has_items(game, ItemType.SWORD, count=2)


class TestTutorialProgression:
    """Tests for tutorial step advancement."""

    def test_advance_on_objective_complete(self):
        """Tutorial advances when objective is met."""
        tutorial = create_tutorial()
        game = Game(tutorial=tutorial)

        # Initially at step 0
        assert tutorial.current_step == 0

        # Place ore mine to complete step 1 objective
        game.place_source(0, 0, SourceType.ORE_MINE)
        game.update(0.1)  # Triggers objective check

        # Should advance to step 1 (belt)
        assert tutorial.current_step == 1

    def test_no_advance_without_objective(self):
        """Tutorial doesn't advance without meeting objective."""
        tutorial = create_tutorial()
        game = Game(tutorial=tutorial)

        # Don't place anything
        game.update(0.1)
        game.update(0.1)
        game.update(0.1)

        # Should still be at step 0
        assert tutorial.current_step == 0

    def test_multiple_steps_advance(self):
        """Can advance through multiple steps."""
        tutorial = create_tutorial()
        game = Game(tutorial=tutorial)

        # Step 1: Place ore mine
        game.place_source(0, 0, SourceType.ORE_MINE)
        game.update(0.1)
        assert tutorial.current_step == 1

        # Step 2: Place belt
        game.place_belt(1, 0, Direction.RIGHT)
        game.update(0.1)
        assert tutorial.current_step == 2

        # Step 3: Place smelter
        game.place_machine(2, 0, MachineType.SMELTER)
        game.update(0.1)
        assert tutorial.current_step == 3


class TestTutorialBuildingRestrictions:
    """Tests for building unlock restrictions in Game."""

    def test_building_allowed_without_tutorial(self):
        """All buildings allowed when no tutorial."""
        game = Game()  # No tutorial
        assert game.is_building_allowed('source_ore')
        assert game.is_building_allowed('belt')
        assert game.is_building_allowed('smelter')
        assert game.is_building_allowed('splitter')

    def test_building_restricted_in_tutorial(self):
        """Only unlocked buildings allowed in tutorial."""
        tutorial = create_tutorial()
        game = Game(tutorial=tutorial)

        # Step 1 only unlocks ore source
        assert game.is_building_allowed('source_ore')
        assert not game.is_building_allowed('belt')
        assert not game.is_building_allowed('smelter')
        assert not game.is_building_allowed('splitter')

    def test_buildings_unlock_with_progression(self):
        """Buildings unlock as tutorial progresses."""
        tutorial = create_tutorial()
        game = Game(tutorial=tutorial)

        # Initially only ore source
        assert not game.is_building_allowed('belt')

        # Advance to step 2 (belt unlocked)
        game.place_source(0, 0, SourceType.ORE_MINE)
        game.update(0.1)

        assert game.is_building_allowed('belt')


class TestTutorialTimerBehavior:
    """Tests for pre-run timer in tutorial mode."""

    def test_timer_paused_before_gates_enabled(self):
        """Pre-run timer doesn't count down until gates enabled."""
        tutorial = create_tutorial()
        game = Game(tutorial=tutorial)

        initial_time = game.pre_run_timer

        # Update several times
        for _ in range(10):
            game.update(1.0)

        # Timer should not have decreased (gates not enabled)
        assert game.pre_run_timer == initial_time

    def test_timer_runs_after_gates_enabled(self):
        """Pre-run timer counts down once gates are enabled."""
        tutorial = create_tutorial()
        # Advance tutorial to step where gates are enabled
        tutorial.current_step = 4  # Step 5 enables gates
        game = Game(tutorial=tutorial)

        initial_time = game.pre_run_timer

        # Update
        game.update(1.0)

        # Timer should have decreased
        assert game.pre_run_timer < initial_time


class TestTutorialInstructions:
    """Tests for tutorial instruction retrieval."""

    def test_get_tutorial_instruction_no_tutorial(self):
        """Returns None when no tutorial active."""
        game = Game()
        assert game.get_tutorial_instruction() is None

    def test_get_tutorial_instruction_with_tutorial(self):
        """Returns instruction string when tutorial active."""
        tutorial = create_tutorial()
        game = Game(tutorial=tutorial)

        instruction = game.get_tutorial_instruction()
        assert instruction is not None
        assert isinstance(instruction, str)

    def test_is_tutorial_active(self):
        """is_tutorial_active reflects tutorial state."""
        game_no_tutorial = Game()
        assert not game_no_tutorial.is_tutorial_active()

        tutorial = create_tutorial()
        game_with_tutorial = Game(tutorial=tutorial)
        assert game_with_tutorial.is_tutorial_active()

        # Complete tutorial
        tutorial.completed = True
        assert not game_with_tutorial.is_tutorial_active()


class TestTutorialStepsDefinition:
    """Tests for the predefined tutorial steps."""

    def test_steps_have_required_fields(self):
        """All tutorial steps have required fields."""
        for i, step in enumerate(TUTORIAL_STEPS):
            assert hasattr(step, 'instruction'), f"Step {i} missing instruction"
            assert hasattr(step, 'unlocked'), f"Step {i} missing unlocked"
            assert hasattr(step, 'objective'), f"Step {i} missing objective"
            assert hasattr(step, 'enable_gates'), f"Step {i} missing enable_gates"

    def test_steps_have_nonempty_instruction(self):
        """All tutorial steps have non-empty instructions."""
        for i, step in enumerate(TUTORIAL_STEPS):
            assert len(step.instruction) > 0, f"Step {i} has empty instruction"

    def test_steps_have_nonempty_unlocked(self):
        """All tutorial steps unlock at least one building."""
        for i, step in enumerate(TUTORIAL_STEPS):
            assert len(step.unlocked) > 0, f"Step {i} unlocks nothing"

    def test_steps_unlocked_cumulative(self):
        """Each step unlocks same or more buildings than previous."""
        prev_unlocked = set()
        for i, step in enumerate(TUTORIAL_STEPS):
            # Current step should include everything from previous
            assert prev_unlocked.issubset(step.unlocked), \
                f"Step {i} doesn't include all previous unlocks"
            prev_unlocked = step.unlocked

    def test_final_step_unlocks_everything(self):
        """Final tutorial step unlocks all buildings."""
        final_step = TUTORIAL_STEPS[-1]
        expected = {
            'source_ore', 'source_fiber', 'source_oil',
            'belt',
            'smelter', 'loom', 'press', 'forge', 'armory', 'lockbench',
            'injector', 'splitter'
        }
        assert final_step.unlocked == expected
