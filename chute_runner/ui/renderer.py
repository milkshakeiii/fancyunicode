"""
Renderer - Reads gameplay state and renders to pyunicodegame windows.
This is a THIN ADAPTER - no game logic here.
"""
import sys
from pathlib import Path

# Add pyunicodegame to path
pyunicodegame_path = Path("/home/henry/Documents/github/pyunicodegame/src")
if pyunicodegame_path.exists():
    sys.path.insert(0, str(pyunicodegame_path))

import pyunicodegame

from gameplay.game import Game, GamePhase
from gameplay.grid import Direction
from gameplay.entities import Belt, Source, Machine, Injector, Splitter
from gameplay.items import ItemType, MachineType, SourceType


# Visual constants
SCREEN_WIDTH = 48
SCREEN_HEIGHT = 24
TOP_LANE_HEIGHT = 6
FACTORY_WIDTH = 32
FACTORY_HEIGHT = 12
CHUTE_BANK_WIDTH = 16

# Colors
COLOR_BELT = (150, 150, 150)
COLOR_BELT_ITEM = (255, 255, 100)
COLOR_SOURCE_ORE = (180, 120, 80)
COLOR_SOURCE_FIBER = (100, 180, 100)
COLOR_SOURCE_OIL = (80, 80, 80)
COLOR_MACHINE = (100, 150, 200)
COLOR_INJECTOR = (200, 200, 100)
COLOR_SPLITTER = (180, 100, 180)

COLOR_RUNNER = (100, 255, 100)
COLOR_GATE_MONSTER = (255, 80, 80)
COLOR_GATE_TRAP = (255, 200, 80)
COLOR_GATE_DOOR = (150, 100, 200)

COLOR_CHUTE_SWORD = (255, 100, 100)
COLOR_CHUTE_SHIELD = (100, 150, 255)
COLOR_CHUTE_KEY = (255, 200, 100)

COLOR_HUD = (200, 200, 200)
COLOR_HP_FULL = (100, 255, 100)
COLOR_HP_EMPTY = (100, 50, 50)

# Direction arrows for belts
BELT_CHARS = {
    Direction.UP: '↑',
    Direction.DOWN: '↓',
    Direction.LEFT: '←',
    Direction.RIGHT: '→',
}

# Machine characters
MACHINE_CHARS = {
    MachineType.SMELTER: 'S',
    MachineType.PRESS: 'P',
    MachineType.LOOM: 'L',
    MachineType.FORGE: 'F',
    MachineType.ARMORY: 'A',
    MachineType.LOCKBENCH: 'K',
}

# Source characters
SOURCE_CHARS = {
    SourceType.ORE_MINE: 'O',
    SourceType.FIBER_GARDEN: 'G',
    SourceType.OIL_WELL: 'W',
}

# Item characters (for items on belts)
ITEM_CHARS = {
    ItemType.ORE: 'o',
    ItemType.FIBER: 'f',
    ItemType.OIL: '~',
    ItemType.PLATE: '▬',
    ItemType.BLADE: '/',
    ItemType.WRAP: '≈',
    ItemType.SWORD: '†',
    ItemType.SHIELD: '◊',
    ItemType.KEY: '⚷',
}


class Renderer:
    """
    Renders game state to pyunicodegame windows.

    This class reads from Game but never modifies it.
    """

    def __init__(self, game: Game):
        self.game = game

        # Windows will be created in init()
        self.factory_window = None
        self.top_lane_window = None
        self.chute_window = None
        self.hud_window = None

        # Cursor state (for building UI)
        self.cursor_x = 0
        self.cursor_y = 0
        self.selected_building = None

    def init_windows(self):
        """Initialize pyunicodegame windows."""
        # Factory grid window (bottom left)
        self.factory_window = pyunicodegame.create_window(
            "factory", 0, TOP_LANE_HEIGHT, FACTORY_WIDTH, FACTORY_HEIGHT,
            z_index=0, bg=(20, 25, 30, 255)
        )

        # Top lane window (gate runner)
        self.top_lane_window = pyunicodegame.create_window(
            "top_lane", 0, 0, SCREEN_WIDTH, TOP_LANE_HEIGHT,
            z_index=0, bg=(15, 15, 25, 255)
        )

        # Chute bank window (right side)
        self.chute_window = pyunicodegame.create_window(
            "chutes", FACTORY_WIDTH, TOP_LANE_HEIGHT, CHUTE_BANK_WIDTH, FACTORY_HEIGHT,
            z_index=0, bg=(25, 20, 30, 255)
        )

        # HUD overlay (fixed, on top)
        self.hud_window = pyunicodegame.create_window(
            "hud", 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT,
            z_index=10, bg=None, fixed=True
        )

    def render(self):
        """Render entire game state."""
        self.render_factory()
        self.render_top_lane()
        self.render_chutes()
        self.render_hud()

    def render_factory(self):
        """Render the factory grid."""
        # Draw grid background (overwrites previous frame)
        for y in range(self.game.grid.height):
            for x in range(self.game.grid.width):
                entity = self.game.grid.get_entity(x, y)

                if entity is None:
                    # Empty cell - draw subtle grid
                    self.factory_window.put(x, y, '·', (40, 40, 50))
                else:
                    self._render_entity(x, y, entity)

        # Draw cursor
        cursor_char = '█' if self.selected_building else '▢'
        self.factory_window.put(self.cursor_x, self.cursor_y, cursor_char, (255, 255, 255))

    def _render_entity(self, x: int, y: int, entity):
        """Render a single entity."""
        if isinstance(entity, Belt):
            char = BELT_CHARS[entity.direction]
            color = COLOR_BELT
            self.factory_window.put(x, y, char, color)

            # Draw item on belt if present
            if entity.item is not None:
                item_char = ITEM_CHARS.get(entity.item, '?')
                self.factory_window.put(x, y, item_char, COLOR_BELT_ITEM)

        elif isinstance(entity, Source):
            char = SOURCE_CHARS[entity.source_type]
            colors = {
                SourceType.ORE_MINE: COLOR_SOURCE_ORE,
                SourceType.FIBER_GARDEN: COLOR_SOURCE_FIBER,
                SourceType.OIL_WELL: COLOR_SOURCE_OIL,
            }
            color = colors[entity.source_type]
            self.factory_window.put(x, y, char, color)

        elif isinstance(entity, Machine):
            char = MACHINE_CHARS[entity.machine_type]
            # Highlight when crafting
            if entity.is_crafting:
                color = (150, 200, 255)
            elif entity.output_item is not None:
                color = (255, 255, 150)
            else:
                color = COLOR_MACHINE
            self.factory_window.put(x, y, char, color)

        elif isinstance(entity, Injector):
            # Show direction with arrow
            char = BELT_CHARS[entity.target_dir]
            color = COLOR_INJECTOR
            if entity.held_item is not None:
                color = (255, 255, 100)
            self.factory_window.put(x, y, char, color)

        elif isinstance(entity, Splitter):
            self.factory_window.put(x, y, 'Y', COLOR_SPLITTER)

    def render_top_lane(self):
        """Render the gate runner lane."""
        # Get runner state
        pos, hp, max_hp, alive = self.game.get_runner_state()

        # Scale position to screen width
        runner_screen_x = int((pos / 100.0) * (SCREEN_WIDTH - 2))

        # Draw runner
        if alive:
            self.top_lane_window.put(runner_screen_x, 3, '▶', COLOR_RUNNER)

            # HP bar above runner
            hp_ratio = hp / max_hp if max_hp > 0 else 0
            hp_bar_width = 5
            filled = int(hp_ratio * hp_bar_width)
            for i in range(hp_bar_width):
                char = '█' if i < filled else '░'
                color = COLOR_HP_FULL if i < filled else COLOR_HP_EMPTY
                self.top_lane_window.put(runner_screen_x - 2 + i, 2, char, color)

        # Draw upcoming gates
        upcoming = self.game.get_upcoming_gates(3)
        for gate in upcoming:
            gate_screen_x = int((gate['position'] / 100.0) * (SCREEN_WIDTH - 2))

            # Gate color by type
            colors = {
                'MONSTER': COLOR_GATE_MONSTER,
                'TRAP': COLOR_GATE_TRAP,
                'DOOR': COLOR_GATE_DOOR,
            }
            color = colors.get(gate['type'], (200, 200, 200))

            # Draw gate
            gate_char = {'MONSTER': 'M', 'TRAP': 'T', 'DOOR': 'D'}.get(gate['type'], '?')
            self.top_lane_window.put(gate_screen_x, 3, gate_char, color)

            # Draw demand above gate
            demands_str = ''
            for item_name, count in gate['demands'].items():
                demands_str += f"{count}{item_name[0]} "
            if demands_str:
                for i, c in enumerate(demands_str[:8]):
                    self.top_lane_window.put(gate_screen_x - 2 + i, 1, c, color)

    def render_chutes(self):
        """Render the chute bank."""
        chute_data = [
            (ItemType.SWORD, 'SWORD', COLOR_CHUTE_SWORD, '†'),
            (ItemType.SHIELD, 'SHIELD', COLOR_CHUTE_SHIELD, '◊'),
            (ItemType.KEY, 'KEY', COLOR_CHUTE_KEY, '⚷'),
        ]

        for i, (item_type, name, color, icon) in enumerate(chute_data):
            x_offset = 1
            y_offset = i * 4

            current, capacity = self.game.get_chute_fill(item_type)
            fill_ratio = current / capacity if capacity > 0 else 0

            # Chute label
            self.chute_window.put_string(x_offset, y_offset, f"{icon} {name}", color)

            # Gauge bar
            bar_width = 12
            filled = int(fill_ratio * bar_width)
            gauge = '█' * filled + '░' * (bar_width - filled)
            self.chute_window.put_string(x_offset, y_offset + 1, gauge, color)

            # Count
            self.chute_window.put_string(x_offset, y_offset + 2, f"{current}/{capacity}", color)

    def render_hud(self):
        """Render HUD overlay."""
        # Clear just the areas we draw on
        phase = self.game.phase

        # Phase indicator
        phase_str = {
            GamePhase.PRE_RUN: "BUILD PHASE",
            GamePhase.RUNNING: "RUNNING",
            GamePhase.WON: "VICTORY!",
            GamePhase.LOST: "GAME OVER",
        }[phase]

        color = (100, 255, 100) if phase in (GamePhase.PRE_RUN, GamePhase.WON) else (255, 100, 100)
        self.hud_window.put_string(1, SCREEN_HEIGHT - 1, phase_str, color)

        # Pre-run timer
        if phase == GamePhase.PRE_RUN:
            remaining = self.game.get_pre_run_time_remaining()
            self.hud_window.put_string(15, SCREEN_HEIGHT - 1, f"Time: {remaining:.1f}s", COLOR_HUD)

        # Selected building indicator
        if self.selected_building:
            self.hud_window.put_string(30, SCREEN_HEIGHT - 1, f"[{self.selected_building}]", COLOR_HUD)

    def move_cursor(self, dx: int, dy: int):
        """Move the build cursor."""
        self.cursor_x = max(0, min(self.game.grid.width - 1, self.cursor_x + dx))
        self.cursor_y = max(0, min(self.game.grid.height - 1, self.cursor_y + dy))

    def select_building(self, building_type: str):
        """Select a building type for placement."""
        self.selected_building = building_type
