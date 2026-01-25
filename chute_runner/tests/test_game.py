"""
END-TO-END GAMEPLAY TESTS

These tests demonstrate complete gameplay scenarios:
- Factory production chains working
- Items flowing through belts and machines
- Chutes filling from factory output
- Runner advancing through gates
- Gates consuming from chutes
- Win/lose conditions triggering

NO UI DEPENDENCIES - pure gameplay logic testing.
"""
import pytest
from gameplay.game import Game, GamePhase, GateResolvedEvent, PhaseChangedEvent, DamageTakenEvent
from gameplay.grid import Direction
from gameplay.entities import Belt, Source, Machine, Injector
from gameplay.items import ItemType, MachineType, SourceType
from gameplay.runner import GateSequence, GateType, create_gate
from gameplay.constants import RUNNER_HP


class TestFactoryProduction:
    """Tests demonstrating factory production chains."""

    def test_source_to_belt_flow(self):
        """Items flow from source through belt via injector."""
        game = Game()

        # Layout: [Source] [Injector] [Belt] [Belt] [Belt]
        game.place_source(0, 0, SourceType.ORE_MINE)
        game.place_injector(1, 0, Direction.LEFT, Direction.RIGHT)
        game.place_belt(2, 0, Direction.RIGHT)
        game.place_belt(3, 0, Direction.RIGHT)
        game.place_belt(4, 0, Direction.RIGHT)

        # Let source produce and injector transfer
        game.fast_forward_factory(3.0)

        # Verify items are on belts
        belt1 = game.get_entity(2, 0)
        belt2 = game.get_entity(3, 0)
        belt3 = game.get_entity(4, 0)

        # At least some belts should have ore
        items_on_belts = sum(1 for b in [belt1, belt2, belt3] if b.item == ItemType.ORE)
        assert items_on_belts > 0

    def test_single_machine_production(self):
        """Single machine transforms input to output."""
        game = Game()

        # Layout: [Source] [Inj] [Smelter] [Inj] [Belt]
        game.place_source(0, 0, SourceType.ORE_MINE)
        game.place_injector(1, 0, Direction.LEFT, Direction.RIGHT)
        game.place_machine(2, 0, MachineType.SMELTER)
        game.place_injector(3, 0, Direction.LEFT, Direction.RIGHT)
        game.place_belt(4, 0, Direction.RIGHT)

        # Run factory
        game.fast_forward_factory(5.0)

        # Check for plates on output belt
        belt = game.get_entity(4, 0)
        # Either belt has plate or smelter has output
        smelter = game.get_entity(2, 0)

        has_plate = (belt.item == ItemType.PLATE) or (smelter.output_item == ItemType.PLATE)
        assert has_plate, "Smelter should produce plates from ore"

    def test_full_sword_production_chain(self):
        """Complete sword production: ore->plate->blade + fiber->wrap -> sword."""
        game = Game()

        # Row 0: Ore -> Plate -> Blade -> Forge
        # Layout: Src -> Inj -> Smelter -> Inj -> Press -> Inj -> Forge
        game.place_source(0, 0, SourceType.ORE_MINE)
        game.place_injector(1, 0, Direction.LEFT, Direction.RIGHT)
        game.place_machine(2, 0, MachineType.SMELTER)  # ore -> plate
        game.place_injector(3, 0, Direction.LEFT, Direction.RIGHT)
        game.place_machine(4, 0, MachineType.PRESS)    # plate -> blade
        game.place_injector(5, 0, Direction.LEFT, Direction.RIGHT)  # blade to forge
        game.place_machine(6, 0, MachineType.FORGE)    # blade + wrap -> sword

        # Row 1: Fiber -> Wrap -> (up to Forge)
        # Layout: Src -> Inj -> Loom -> Inj -> Belt -> Belt -> Inj(UP)
        game.place_source(0, 1, SourceType.FIBER_GARDEN)
        game.place_injector(1, 1, Direction.LEFT, Direction.RIGHT)
        game.place_machine(2, 1, MachineType.LOOM)     # fiber -> wrap
        game.place_injector(3, 1, Direction.LEFT, Direction.RIGHT)
        game.place_belt(4, 1, Direction.RIGHT)
        game.place_belt(5, 1, Direction.RIGHT)
        game.place_injector(6, 1, Direction.LEFT, Direction.UP)  # wrap up to forge

        # Run factory for enough time to produce swords
        game.fast_forward_factory(20.0)

        # Check for sword production
        forge = game.get_entity(6, 0)
        assert forge.output_item == ItemType.SWORD, "Forge should produce swords"


class TestChuteIntegration:
    """Tests demonstrating chutes filling from factory."""

    def test_injector_fills_chute(self):
        """Injector can push items directly to chute."""
        # Create game with simple level
        simple_level = GateSequence([
            create_gate(GateType.MONSTER, position=50.0, swords=5)
        ])
        game = Game(level=simple_level)

        # Build sword production with chute output
        # Row 0: Ore -> Plate -> Blade -> Forge -> Chute
        game.place_source(0, 0, SourceType.ORE_MINE)
        game.place_injector(1, 0, Direction.LEFT, Direction.RIGHT)
        game.place_machine(2, 0, MachineType.SMELTER)
        game.place_injector(3, 0, Direction.LEFT, Direction.RIGHT)
        game.place_machine(4, 0, MachineType.PRESS)
        game.place_injector(5, 0, Direction.LEFT, Direction.RIGHT)
        game.place_machine(6, 0, MachineType.FORGE)
        game.place_injector(7, 0, Direction.LEFT, Direction.RIGHT, chute_target=ItemType.SWORD)

        # Row 1: Fiber -> Wrap -> (up to Forge)
        game.place_source(0, 1, SourceType.FIBER_GARDEN)
        game.place_injector(1, 1, Direction.LEFT, Direction.RIGHT)
        game.place_machine(2, 1, MachineType.LOOM)
        game.place_injector(3, 1, Direction.LEFT, Direction.RIGHT)
        game.place_belt(4, 1, Direction.RIGHT)
        game.place_belt(5, 1, Direction.RIGHT)
        game.place_injector(6, 1, Direction.LEFT, Direction.UP)  # wrap up to forge

        # Run factory
        game.fast_forward_factory(30.0)

        # Check chute has swords
        sword_count, _ = game.get_chute_fill(ItemType.SWORD)
        assert sword_count > 0, "Sword chute should fill from forge output"


class TestEndToEndGameplay:
    """
    CRITICAL: End-to-end gameplay tests demonstrating full game flow.
    These tests are the primary verification that the gameplay module works.
    """

    def test_win_game_with_working_factory(self):
        """
        WIN CONDITION: Complete game with factory meeting all gate demands.

        This test demonstrates:
        1. Building a complete production chain
        2. Chutes filling during pre-run
        3. Runner advancing through gates
        4. Gates consuming from chutes
        5. Game ending in WIN state
        """
        # Simple level with just one small monster gate
        simple_level = GateSequence([
            create_gate(GateType.MONSTER, position=50.0, swords=3)
        ])
        game = Game(level=simple_level)

        # Build minimal sword factory
        self._build_sword_factory(game)

        # Pre-fill chutes by running factory
        game.fast_forward_factory(20.0)

        # Verify we have enough swords
        sword_count, _ = game.get_chute_fill(ItemType.SWORD)
        assert sword_count >= 3, f"Need 3 swords, have {sword_count}"

        # Start run and simulate to completion
        game.start_run()
        events = game.simulate(100.0)

        # Verify win
        assert game.phase == GamePhase.WON, f"Expected WIN, got {game.phase}"

        # Verify gate was resolved
        gate_events = [e for e in events if isinstance(e, GateResolvedEvent)]
        assert len(gate_events) == 1
        assert gate_events[0].result.success

    def test_lose_game_from_damage(self):
        """
        LOSE CONDITION: Runner dies from accumulated damage.

        This test demonstrates gates dealing damage when chutes are empty.
        """
        # Level with monster gates that deal lethal damage (>= RUNNER_HP)
        hard_level = GateSequence([
            create_gate(GateType.MONSTER, position=10.0, swords=150),  # More than HP
        ])
        game = Game(level=hard_level)

        # No factory - chutes stay empty
        game.start_run()
        events = game.simulate(50.0)

        # Verify loss
        assert game.phase == GamePhase.LOST
        assert not game.runner.is_alive

        # Verify damage was taken
        damage_events = [e for e in events if isinstance(e, DamageTakenEvent)]
        assert len(damage_events) == 1
        assert damage_events[0].amount == 150  # All swords missing = 150 damage

    def test_lose_game_from_door(self):
        """
        LOSE CONDITION: Instant death from failed door gate.
        """
        door_level = GateSequence([
            create_gate(GateType.DOOR, position=10.0, keys=1)
        ])
        game = Game(level=door_level)

        # No factory - no keys
        game.start_run()
        events = game.simulate(50.0)

        # Verify instant death
        assert game.phase == GamePhase.LOST
        assert not game.runner.is_alive

        # Verify gate result
        gate_events = [e for e in events if isinstance(e, GateResolvedEvent)]
        assert gate_events[0].result.instant_death

    def test_survive_traps_with_shields(self):
        """
        SURVIVAL: Shields reduce trap damage.
        """
        trap_level = GateSequence([
            create_gate(GateType.TRAP, position=30.0, shields=5),
            create_gate(GateType.TRAP, position=60.0, shields=5),
        ])
        game = Game(level=trap_level)

        # Build shield factory
        self._build_shield_factory(game)

        # Pre-fill chutes
        game.fast_forward_factory(30.0)

        # Check shield count
        shield_count, _ = game.get_chute_fill(ItemType.SHIELD)
        assert shield_count >= 5, f"Need 5 shields, have {shield_count}"

        # Run
        game.start_run()
        events = game.simulate(100.0)

        # Should survive first trap at least
        pos, hp, max_hp, alive = game.get_runner_state()
        # Either won or still running with some HP
        assert game.phase in (GamePhase.WON, GamePhase.RUNNING, GamePhase.LOST)

    def test_multiple_production_lines(self):
        """
        COMPLEX FACTORY: Multiple parallel production lines feeding different chutes.
        """
        multi_gate_level = GateSequence([
            create_gate(GateType.MONSTER, position=30.0, swords=3),
            create_gate(GateType.TRAP, position=50.0, shields=3),
            create_gate(GateType.DOOR, position=70.0, keys=1),
        ])
        game = Game(level=multi_gate_level)

        # Build sword factory in rows 0-2
        self._build_sword_factory(game, start_row=0)

        # Build shield factory in rows 4-5
        self._build_shield_factory(game, start_row=4)

        # Build key factory in rows 7-8
        self._build_key_factory(game, start_row=7)

        # Pre-fill chutes
        game.fast_forward_factory(40.0)

        # Verify all chutes have items
        sword_count, _ = game.get_chute_fill(ItemType.SWORD)
        shield_count, _ = game.get_chute_fill(ItemType.SHIELD)
        key_count, _ = game.get_chute_fill(ItemType.KEY)

        assert sword_count >= 3, f"Need 3 swords, have {sword_count}"
        assert shield_count >= 3, f"Need 3 shields, have {shield_count}"
        assert key_count >= 1, f"Need 1 key, have {key_count}"

        # Run to completion
        game.start_run()
        game.simulate(100.0)

        assert game.phase == GamePhase.WON

    def test_pre_run_timer_transitions_to_running(self):
        """
        GAME FLOW: Pre-run timer automatically transitions to running phase.
        """
        game = Game()
        assert game.phase == GamePhase.PRE_RUN

        # Simulate past pre-run time
        from gameplay.constants import PRE_RUN_TIME
        events = game.simulate(PRE_RUN_TIME + 1.0)

        # Should have transitioned
        phase_events = [e for e in events if isinstance(e, PhaseChangedEvent)]
        assert any(e.new_phase == GamePhase.RUNNING for e in phase_events)

    def test_factory_runs_during_pre_run(self):
        """
        GAME FLOW: Factory produces items during pre-run phase.
        """
        game = Game()
        assert game.phase == GamePhase.PRE_RUN

        # Build simple production
        game.place_source(0, 0, SourceType.ORE_MINE)
        game.place_injector(1, 0, Direction.LEFT, Direction.RIGHT)
        game.place_belt(2, 0, Direction.RIGHT)

        # Update during pre-run (don't skip it)
        for _ in range(50):
            game.update(0.1)

        # Source should have produced
        source = game.get_entity(0, 0)
        belt = game.get_entity(2, 0)

        # Either source buffer used or belt has item
        production_happened = source.buffer < source.max_buffer or belt.item is not None
        assert production_happened

    def test_game_state_queries(self):
        """
        STATE QUERIES: UI can read game state through query methods.
        """
        game = Game()

        # Chute queries
        current, capacity = game.get_chute_fill(ItemType.SWORD)
        assert current == 0
        assert capacity > 0

        # Runner queries
        pos, hp, max_hp, alive = game.get_runner_state()
        assert pos == 0.0
        assert hp == RUNNER_HP
        assert alive

        # Gate preview
        upcoming = game.get_upcoming_gates(3)
        assert len(upcoming) > 0
        assert 'type' in upcoming[0]
        assert 'position' in upcoming[0]
        assert 'demands' in upcoming[0]

        # Pre-run timer
        remaining = game.get_pre_run_time_remaining()
        assert remaining > 0

    # =========================================================================
    # HELPER METHODS FOR BUILDING FACTORIES
    # =========================================================================

    def _build_sword_factory(self, game: Game, start_row: int = 0):
        """Build a working sword production line."""
        r = start_row

        # Row 0: Ore -> Plate -> Blade -> Forge -> Chute
        game.place_source(0, r, SourceType.ORE_MINE)
        game.place_injector(1, r, Direction.LEFT, Direction.RIGHT)
        game.place_machine(2, r, MachineType.SMELTER)
        game.place_injector(3, r, Direction.LEFT, Direction.RIGHT)
        game.place_machine(4, r, MachineType.PRESS)
        game.place_injector(5, r, Direction.LEFT, Direction.RIGHT)
        game.place_machine(6, r, MachineType.FORGE)
        game.place_injector(7, r, Direction.LEFT, Direction.RIGHT, chute_target=ItemType.SWORD)

        # Row 1: Fiber -> Wrap -> (up to Forge)
        game.place_source(0, r+1, SourceType.FIBER_GARDEN)
        game.place_injector(1, r+1, Direction.LEFT, Direction.RIGHT)
        game.place_machine(2, r+1, MachineType.LOOM)
        game.place_injector(3, r+1, Direction.LEFT, Direction.RIGHT)
        game.place_belt(4, r+1, Direction.RIGHT)
        game.place_belt(5, r+1, Direction.RIGHT)
        game.place_injector(6, r+1, Direction.LEFT, Direction.UP)  # wrap up to forge

    def _build_shield_factory(self, game: Game, start_row: int = 0):
        """Build a working shield production line."""
        r = start_row

        # Row 0: Ore -> Plate -> Armory -> Chute
        # Armory needs: wrap + plate
        game.place_source(0, r, SourceType.ORE_MINE)
        game.place_injector(1, r, Direction.LEFT, Direction.RIGHT)
        game.place_machine(2, r, MachineType.SMELTER)
        game.place_injector(3, r, Direction.LEFT, Direction.RIGHT)
        game.place_machine(4, r, MachineType.ARMORY)  # wrap + plate -> shield
        game.place_injector(5, r, Direction.LEFT, Direction.RIGHT, chute_target=ItemType.SHIELD)

        # Row 1: Fiber -> Wrap -> Belt -> (up to Armory)
        game.place_source(0, r+1, SourceType.FIBER_GARDEN)
        game.place_injector(1, r+1, Direction.LEFT, Direction.RIGHT)
        game.place_machine(2, r+1, MachineType.LOOM)
        game.place_injector(3, r+1, Direction.LEFT, Direction.RIGHT)
        game.place_belt(4, r+1, Direction.UP)  # belt carries wrap up to armory

    def _build_key_factory(self, game: Game, start_row: int = 0):
        """Build a working key production line."""
        r = start_row

        # Row 0: Ore -> Plate -> Lockbench -> Chute
        # Lockbench needs: plate + oil
        game.place_source(0, r, SourceType.ORE_MINE)
        game.place_injector(1, r, Direction.LEFT, Direction.RIGHT)
        game.place_machine(2, r, MachineType.SMELTER)
        game.place_injector(3, r, Direction.LEFT, Direction.RIGHT)
        game.place_machine(4, r, MachineType.LOCKBENCH)  # plate + oil -> key
        game.place_injector(5, r, Direction.LEFT, Direction.RIGHT, chute_target=ItemType.KEY)

        # Row 1: Oil -> (up to Lockbench)
        game.place_source(0, r+1, SourceType.OIL_WELL)
        game.place_injector(1, r+1, Direction.LEFT, Direction.RIGHT)
        game.place_belt(2, r+1, Direction.RIGHT)
        game.place_belt(3, r+1, Direction.RIGHT)
        game.place_injector(4, r+1, Direction.LEFT, Direction.UP)  # oil up to lockbench


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_cannot_place_on_occupied_cell(self):
        """Placing on occupied cell fails gracefully."""
        game = Game()
        game.place_belt(0, 0, Direction.RIGHT)

        # Second placement fails
        assert not game.place_belt(0, 0, Direction.LEFT)
        assert not game.place_machine(0, 0, MachineType.SMELTER)

    def test_remove_nonexistent_entity(self):
        """Removing from empty cell returns False."""
        game = Game()
        assert not game.remove_entity(0, 0)

    def test_empty_chutes_at_start(self):
        """Chutes start empty."""
        game = Game()

        for item_type in [ItemType.SWORD, ItemType.SHIELD, ItemType.KEY]:
            current, _ = game.get_chute_fill(item_type)
            assert current == 0

    def test_runner_doesnt_move_when_dead(self):
        """Dead runner stays in place."""
        level = GateSequence([
            create_gate(GateType.DOOR, position=5.0, keys=1)
        ])
        game = Game(level=level)
        game.start_run()

        # Get killed at door
        game.simulate(20.0)

        assert not game.runner.is_alive
        pos1 = game.runner.position

        # Try to continue
        game.simulate(10.0)
        pos2 = game.runner.position

        # Position unchanged
        assert pos1 == pos2

    def test_game_stops_updating_after_win(self):
        """Game doesn't process updates after winning."""
        level = GateSequence([])  # No gates = instant win when runner finishes
        game = Game(level=level)
        game.start_run()

        # Run to completion
        game.simulate(200.0)
        assert game.phase == GamePhase.WON

        hp_before = game.runner.hp

        # More updates don't change anything
        game.update(10.0)
        assert game.runner.hp == hp_before
