"""
Input Handler - Translates key presses to gameplay commands.
This is a THIN ADAPTER - no game logic here.
"""
import pygame

from gameplay.game import Game, GamePhase
from gameplay.grid import Direction
from gameplay.items import ItemType, MachineType, SourceType
from ui.renderer import Renderer


# Key mappings for building placement
BUILDING_KEYS = {
    pygame.K_1: ('belt', Direction.RIGHT),
    pygame.K_2: ('belt', Direction.LEFT),
    pygame.K_3: ('belt', Direction.UP),
    pygame.K_4: ('belt', Direction.DOWN),
    pygame.K_5: ('splitter', None),
    pygame.K_6: ('injector', None),
    pygame.K_7: ('machine', MachineType.SMELTER),
    pygame.K_8: ('machine', MachineType.PRESS),
    pygame.K_9: ('machine', MachineType.LOOM),
    pygame.K_0: ('machine', MachineType.FORGE),
    pygame.K_MINUS: ('machine', MachineType.ARMORY),
    pygame.K_EQUALS: ('machine', MachineType.LOCKBENCH),
    pygame.K_q: ('source', SourceType.ORE_MINE),
    pygame.K_w: ('source', SourceType.FIBER_GARDEN),
    pygame.K_e: ('source', SourceType.OIL_WELL),
}


class InputHandler:
    """
    Handles keyboard input and translates to game commands.

    The input handler:
    - Reads key presses
    - Updates renderer state (cursor, selection)
    - Calls game methods to modify game state
    """

    def __init__(self, game: Game, renderer: Renderer):
        self.game = game
        self.renderer = renderer

        # Injector placement state
        self.placing_injector = False
        self.injector_source_dir = None
        self.injector_target_dir = None
        self.injector_chute_target = None

    def handle_key(self, key: int) -> bool:
        """
        Handle a single key press.
        Returns True if the game should quit.
        """
        # Quit
        if key == pygame.K_ESCAPE:
            return True

        # Phase-specific handling
        if self.game.phase == GamePhase.WON or self.game.phase == GamePhase.LOST:
            if key == pygame.K_r:
                # Restart would go here
                pass
            return False

        # Cursor movement
        if key == pygame.K_UP:
            self.renderer.move_cursor(0, -1)
        elif key == pygame.K_DOWN:
            self.renderer.move_cursor(0, 1)
        elif key == pygame.K_LEFT:
            self.renderer.move_cursor(-1, 0)
        elif key == pygame.K_RIGHT:
            self.renderer.move_cursor(1, 0)

        # Building selection
        elif key in BUILDING_KEYS:
            building_type, param = BUILDING_KEYS[key]
            self._select_building(building_type, param)

        # Place building
        elif key == pygame.K_SPACE or key == pygame.K_RETURN:
            self._place_building()

        # Delete building
        elif key == pygame.K_x or key == pygame.K_DELETE:
            self._delete_building()

        # Start run early
        elif key == pygame.K_s:
            if self.game.phase == GamePhase.PRE_RUN:
                self.game.start_run()

        # Chute targeting for injectors
        elif key == pygame.K_t:
            self._cycle_chute_target()

        return False

    def _select_building(self, building_type: str, param):
        """Select a building type for placement."""
        self.renderer.selected_building = building_type

        if building_type == 'belt':
            self._selected_direction = param
        elif building_type == 'machine':
            self._selected_machine_type = param
        elif building_type == 'source':
            self._selected_source_type = param
        elif building_type == 'injector':
            # Start injector placement flow
            self.placing_injector = True
            self.injector_source_dir = Direction.LEFT  # Default
            self.injector_target_dir = Direction.RIGHT  # Default
            self.injector_chute_target = None

    def _place_building(self):
        """Place the selected building at cursor position."""
        if self.renderer.selected_building is None:
            return

        x = self.renderer.cursor_x
        y = self.renderer.cursor_y
        building = self.renderer.selected_building

        success = False

        if building == 'belt':
            success = self.game.place_belt(x, y, self._selected_direction)

        elif building == 'machine':
            success = self.game.place_machine(x, y, self._selected_machine_type)

        elif building == 'source':
            success = self.game.place_source(x, y, self._selected_source_type)

        elif building == 'injector':
            success = self.game.place_injector(
                x, y,
                self.injector_source_dir,
                self.injector_target_dir,
                chute_target=self.injector_chute_target
            )

        elif building == 'splitter':
            # Default splitter: input from left, outputs up and down
            success = self.game.place_splitter(
                x, y,
                Direction.LEFT,
                Direction.UP,
                Direction.DOWN
            )

        # Visual/audio feedback could go here
        if not success:
            pass  # Cell occupied or invalid

    def _delete_building(self):
        """Delete building at cursor position."""
        x = self.renderer.cursor_x
        y = self.renderer.cursor_y
        self.game.remove_entity(x, y)

    def _cycle_chute_target(self):
        """Cycle through chute targets for injector placement."""
        if self.renderer.selected_building != 'injector':
            return

        targets = [None, ItemType.SWORD, ItemType.SHIELD, ItemType.KEY]
        current_idx = targets.index(self.injector_chute_target) if self.injector_chute_target in targets else 0
        next_idx = (current_idx + 1) % len(targets)
        self.injector_chute_target = targets[next_idx]

    def handle_held_keys(self, dt: float):
        """
        Handle continuously held keys.
        Called every frame for smooth movement.
        """
        keys = pygame.key.get_pressed()

        # Could add held-key cursor movement here for faster navigation
        pass
