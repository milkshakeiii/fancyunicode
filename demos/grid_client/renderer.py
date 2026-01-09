"""PyUnicodeGame rendering logic."""

import pyunicodegame

from .config import GRID_WIDTH, GRID_HEIGHT, PLAYER_CHARS, PLAYER_COLORS, SELF_COLOR, WINDOW_TITLE, BG_COLOR
from .game_state import ClientState, Entity


class Renderer:
    """Handles all PyUnicodeGame rendering."""

    def __init__(self, state: ClientState):
        self.state = state
        self.root = None
        self.game_window = None
        self.hud_window = None

    def init_display(self) -> None:
        """Initialize PyUnicodeGame windows."""
        self.root = pyunicodegame.init(
            WINDOW_TITLE,
            width=GRID_WIDTH,
            height=GRID_HEIGHT,
            bg=BG_COLOR
        )

        # Game layer for entities
        self.game_window = pyunicodegame.create_window(
            "game", 0, 0, GRID_WIDTH, GRID_HEIGHT,
            z_index=5, bg=None
        )

        # Brighter ambient lighting
        self.game_window.set_lighting(enabled=True, ambient=(150, 150, 160))

        # HUD layer for status (fixed, no parallax)
        self.hud_window = pyunicodegame.create_window(
            "hud", 0, 0, GRID_WIDTH, GRID_HEIGHT,
            z_index=10, bg=None, fixed=True
        )

    def render(self) -> None:
        """Main render function called each frame."""
        self._render_grid_lines()
        self._render_entities()
        self._render_hud()

    def _render_grid_lines(self) -> None:
        """Draw faint grid lines for visual reference."""
        grid_color = (30, 30, 45)
        # Vertical lines every 10 cells
        for x in range(0, GRID_WIDTH, 10):
            for y in range(GRID_HEIGHT):
                self.root.put(x, y, "|", grid_color)
        # Horizontal lines every 10 cells
        for y in range(0, GRID_HEIGHT, 10):
            for x in range(GRID_WIDTH):
                char = "+" if x % 10 == 0 else "-"
                self.root.put(x, y, char, grid_color)

    def _render_entities(self) -> None:
        """Render all entities from server state."""
        entities = self.state.get_entities_snapshot()

        # Direct rendering - put characters on the game window each frame
        for entity in entities:
            is_me = entity.id == self.state.my_entity_id
            char, color = self._get_entity_visual(entity, is_me)

            # Draw entity directly on game window
            self.game_window.put(entity.x, entity.y, char, color)

    def _get_entity_visual(self, entity: Entity, is_me: bool) -> tuple[str, tuple]:
        """Determine character and color for an entity."""
        metadata = entity.metadata or {}

        # Use metadata for custom appearance
        if "char" in metadata:
            char = metadata["char"]
        elif is_me:
            char = "@"  # Player's own entity
        else:
            # Hash entity ID to pick a consistent visual
            idx = hash(entity.id) % len(PLAYER_CHARS)
            char = PLAYER_CHARS[idx]

        if "color" in metadata:
            color = tuple(metadata["color"])
        elif is_me:
            color = SELF_COLOR
        else:
            idx = hash(entity.id) % len(PLAYER_COLORS)
            color = PLAYER_COLORS[idx]

        return char, color

    def _render_hud(self) -> None:
        """Render HUD with connection status and controls."""
        hud_color = (150, 150, 180)

        # Status bar
        status = self.state.get_status()
        self.hud_window.put_string(1, 1, f"Status: {status}", hud_color)

        # Tick counter
        self.hud_window.put_string(1, 2, f"Tick: {self.state.tick_number}", hud_color)

        # Entity count
        entity_count = len(self.state.entities)
        self.hud_window.put_string(1, 3, f"Entities: {entity_count}", hud_color)

        # Controls hint
        controls = "Arrow keys: Move | Q: Quit"
        self.hud_window.put_string(1, GRID_HEIGHT - 2, controls, (100, 100, 120))

        # My position
        my_entity = self.state.get_my_entity()
        if my_entity:
            pos_str = f"Position: ({my_entity.x}, {my_entity.y})"
            self.hud_window.put_string(GRID_WIDTH - len(pos_str) - 1, 1, pos_str, (100, 255, 100))
