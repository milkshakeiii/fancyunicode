"""
Main Game class - orchestrates all gameplay systems.
NO UI DEPENDENCIES.

This is the central gameplay module. It can be fully tested
without any UI framework.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Callable
from enum import Enum, auto

from .grid import Grid, Direction
from .entities import Entity, Belt, Source, Machine, Injector, Splitter
from .items import ItemType, MachineType, SourceType
from .chutes import ChuteBank
from .runner import Runner, GateSequence, GateResult
from .level import create_test_level
from .constants import FACTORY_WIDTH, FACTORY_HEIGHT, PRE_RUN_TIME
from .tutorial import TutorialState


class GamePhase(Enum):
    """Current phase of the game."""
    PRE_RUN = auto()    # Building phase before gates start
    RUNNING = auto()    # Gates active, runner advancing
    WON = auto()        # Runner reached the end
    LOST = auto()       # Runner died


@dataclass
class GameEvent:
    """An event that occurred during gameplay (for UI to react to)."""
    pass


@dataclass
class GateResolvedEvent(GameEvent):
    """A gate was just resolved."""
    result: GateResult
    gate_index: int


@dataclass
class PhaseChangedEvent(GameEvent):
    """Game phase changed."""
    old_phase: GamePhase
    new_phase: GamePhase


@dataclass
class DamageTakenEvent(GameEvent):
    """Runner took damage."""
    amount: int
    new_hp: int


class Game:
    """
    The main game class that orchestrates all gameplay.

    This class is COMPLETELY DECOUPLED from UI.
    It exposes state as plain data and accepts commands as method calls.

    Usage:
        game = Game()
        game.place_entity(x, y, Belt(Direction.RIGHT))
        game.start_run()
        while game.phase == GamePhase.RUNNING:
            events = game.update(dt)
            # UI reads game state and renders
    """

    def __init__(self, level: Optional[GateSequence] = None, tutorial: Optional[TutorialState] = None):
        # Factory grid
        self.grid = Grid(FACTORY_WIDTH, FACTORY_HEIGHT)

        # Chute bank
        self.chute_bank = ChuteBank()

        # Runner and gates
        self.runner = Runner()
        self.gate_sequence = level if level else create_test_level()

        # Tutorial state (optional)
        self.tutorial = tutorial

        # Game state
        self.phase = GamePhase.PRE_RUN
        self.pre_run_timer = PRE_RUN_TIME

        # Event queue for UI notifications
        self._events: List[GameEvent] = []

        # Stats
        self.total_items_produced: Dict[ItemType, int] = {t: 0 for t in ItemType}
        self.total_damage_taken: int = 0

    # =========================================================================
    # BUILDING COMMANDS
    # =========================================================================

    def place_belt(self, x: int, y: int, direction: Direction) -> bool:
        """Place a belt at the given position."""
        belt = Belt(direction)
        return self.grid.place_entity(x, y, belt)

    def place_source(self, x: int, y: int, source_type: SourceType) -> bool:
        """Place a resource source at the given position."""
        source = Source(source_type)
        return self.grid.place_entity(x, y, source)

    def place_machine(self, x: int, y: int, machine_type: MachineType) -> bool:
        """Place a machine at the given position."""
        machine = Machine(machine_type)
        return self.grid.place_entity(x, y, machine)

    def place_injector(
        self,
        x: int,
        y: int,
        source_dir: Direction,
        target_dir: Direction,
        chute_target: Optional[ItemType] = None
    ) -> bool:
        """
        Place an injector at the given position.

        If chute_target is specified, the injector will push matching items
        to that chute instead of to the grid.
        """
        injector = Injector(source_dir, target_dir)
        if chute_target is not None:
            injector.set_chute_target(self.chute_bank, chute_target)

        return self.grid.place_entity(x, y, injector)

    def place_splitter(
        self,
        x: int,
        y: int,
        input_dir: Direction,
        output1_dir: Direction,
        output2_dir: Direction
    ) -> bool:
        """Place a splitter at the given position."""
        splitter = Splitter(input_dir, output1_dir, output2_dir)
        return self.grid.place_entity(x, y, splitter)

    def remove_entity(self, x: int, y: int) -> bool:
        """Remove entity at the given position."""
        entity = self.grid.remove_entity(x, y)
        return entity is not None

    def get_entity(self, x: int, y: int) -> Optional[Entity]:
        """Get entity at position for inspection."""
        return self.grid.get_entity(x, y)

    # =========================================================================
    # GAME FLOW COMMANDS
    # =========================================================================

    def start_run(self) -> None:
        """
        Start the run immediately (skip pre-run timer).
        Useful for testing.
        """
        if self.phase == GamePhase.PRE_RUN:
            old_phase = self.phase
            self.phase = GamePhase.RUNNING
            self._events.append(PhaseChangedEvent(old_phase, self.phase))

    def skip_pre_run(self) -> None:
        """Alias for start_run()."""
        self.start_run()

    # =========================================================================
    # UPDATE LOOP
    # =========================================================================

    def update(self, dt: float) -> List[GameEvent]:
        """
        Update game state by dt seconds.
        Returns list of events that occurred.
        """
        self._events = []

        # Check tutorial progression
        if self.tutorial is not None:
            self.tutorial.check_and_advance(self)

        if self.phase == GamePhase.PRE_RUN:
            self._update_pre_run(dt)
        elif self.phase == GamePhase.RUNNING:
            self._update_running(dt)
        # WON and LOST phases don't update

        return self._events

    def _update_pre_run(self, dt: float) -> None:
        """Update during pre-run phase."""
        # Factory still runs during pre-run
        self._update_factory(dt)

        # In tutorial mode, don't count down until gates are enabled
        if self.tutorial is not None and not self.tutorial.are_gates_enabled():
            return

        # Count down to run start
        self.pre_run_timer -= dt
        if self.pre_run_timer <= 0:
            self.pre_run_timer = 0
            old_phase = self.phase
            self.phase = GamePhase.RUNNING
            self._events.append(PhaseChangedEvent(old_phase, self.phase))

    def _update_running(self, dt: float) -> None:
        """Update during running phase."""
        # Update factory
        self._update_factory(dt)

        # Update runner
        self.runner.update(dt)

        # Check for gate resolution
        result = self.gate_sequence.check_and_resolve(self.runner, self.chute_bank)
        if result is not None:
            gate_index = self.gate_sequence.gates_passed - 1
            self._events.append(GateResolvedEvent(result, gate_index))

            if result.damage_taken > 0:
                self.total_damage_taken += result.damage_taken
                self._events.append(DamageTakenEvent(result.damage_taken, self.runner.hp))

        # Check win/lose conditions
        if not self.runner.is_alive:
            old_phase = self.phase
            self.phase = GamePhase.LOST
            self._events.append(PhaseChangedEvent(old_phase, self.phase))
        elif self.runner.finished and self.gate_sequence.all_passed():
            old_phase = self.phase
            self.phase = GamePhase.WON
            self._events.append(PhaseChangedEvent(old_phase, self.phase))

    def _update_factory(self, dt: float) -> None:
        """Update all factory entities."""
        # Update all entities
        for entity in self.grid.iter_entities():
            entity.update(dt)

    # =========================================================================
    # STATE QUERIES (for UI to read)
    # =========================================================================

    def get_chute_fill(self, item_type: ItemType) -> Tuple[int, int]:
        """Get (current, capacity) for a chute."""
        chute = self.chute_bank.get_chute(item_type)
        if chute is None:
            return (0, 0)
        return (chute.current, chute.capacity)

    def get_runner_state(self) -> Tuple[float, int, int, bool]:
        """Get (position, hp, max_hp, is_alive) for the runner."""
        return (
            self.runner.position,
            self.runner.hp,
            self.runner.max_hp,
            self.runner.is_alive
        )

    def get_upcoming_gates(self, count: int = 3) -> List[dict]:
        """
        Get upcoming gates as plain dicts for UI.
        Returns list of {type, position, demands}.
        """
        gates = self.gate_sequence.get_upcoming_gates(count)
        return [
            {
                'type': g.gate_type.name,
                'position': g.position,
                'demands': {k.name: v for k, v in g.demands.items()},
                'state': g.state.name
            }
            for g in gates
        ]

    def get_pre_run_time_remaining(self) -> float:
        """Get seconds remaining in pre-run phase."""
        return max(0.0, self.pre_run_timer)

    def is_building_allowed(self, building_key: str) -> bool:
        """
        Check if a building key is allowed (for tutorial filtering).
        Returns True if no tutorial or building is unlocked.
        """
        if self.tutorial is None:
            return True
        return building_key in self.tutorial.get_unlocked_buildings()

    def get_tutorial_instruction(self) -> Optional[str]:
        """Get current tutorial instruction, or None if not in tutorial."""
        if self.tutorial is None:
            return None
        return self.tutorial.get_instruction()

    def is_tutorial_active(self) -> bool:
        """Check if tutorial is active and not complete."""
        return self.tutorial is not None and not self.tutorial.is_complete()

    # =========================================================================
    # CONVENIENCE METHODS FOR TESTING
    # =========================================================================

    def simulate(self, seconds: float, dt: float = 0.1) -> List[GameEvent]:
        """
        Simulate the game for a number of seconds.
        Returns all events that occurred.
        """
        all_events = []
        elapsed = 0.0
        while elapsed < seconds and self.phase in (GamePhase.PRE_RUN, GamePhase.RUNNING):
            events = self.update(dt)
            all_events.extend(events)
            elapsed += dt
        return all_events

    def fast_forward_factory(self, seconds: float, dt: float = 0.1) -> None:
        """
        Run only the factory for a number of seconds (don't advance runner).
        Useful for letting production fill chutes before testing gates.
        """
        elapsed = 0.0
        while elapsed < seconds:
            self._update_factory(dt)
            elapsed += dt
