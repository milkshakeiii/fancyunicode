"""
Example game logic module demonstrating the module interface.

This module implements a simple movement system where players can move
entities around the grid via intents.
"""

import logging
from typing import Any
from uuid import UUID

from grid_backend.models.entity import Entity
from grid_backend.game_logic.protocol import (
    FrameworkAPI,
    GameLogicModule,
    Intent,
    TickResult,
    EntityUpdate,
    EntityCreate,
)

logger = logging.getLogger(__name__)


class ExampleGameModule:
    """
    Example game module with basic movement.

    Supported intents:
    - {"action": "move", "entity_id": "...", "dx": 1, "dy": 0}
    - {"action": "create_entity", "x": 0, "y": 0, "width": 1, "height": 1}
    - {"action": "delete_entity", "entity_id": "..."}
    """

    def __init__(self) -> None:
        self._framework: FrameworkAPI | None = None

    def on_init(self, framework: FrameworkAPI) -> None:
        """Initialize the module."""
        self._framework = framework
        logger.info("Example game module initialized")

    def on_tick(
        self,
        zone_id: UUID,
        entities: list[Entity],
        intents: list[Intent],
        tick_number: int,
    ) -> TickResult:
        """
        Process a tick for a zone.
        Handles movement and entity creation intents.
        """
        updates: list[EntityUpdate] = []
        creates: list[EntityCreate] = []
        deletes: list[UUID] = []
        entity_map = {e.id: e for e in entities}

        for intent in intents:
            try:
                action = intent.data.get("action")

                if action == "move":
                    update = self._handle_move(
                        intent=intent,
                        entity_map=entity_map,
                    )
                    if update is not None:
                        updates.append(update)

                elif action == "create_entity":
                    create = self._handle_create_entity(intent)
                    if create is not None:
                        creates.append(create)

                elif action == "delete_entity":
                    entity_id = self._handle_delete_entity(intent, entity_map)
                    if entity_id is not None:
                        deletes.append(entity_id)

            except Exception as e:
                logger.warning(
                    f"Error processing intent from {intent.player_id}: {e}"
                )

        # Build broadcast state
        state = {
            "zone_id": str(zone_id),
            "tick": tick_number,
            "entities": [
                {
                    "id": str(e.id),
                    "x": e.x,
                    "y": e.y,
                    "width": e.width,
                    "height": e.height,
                    "metadata": e.metadata_,
                }
                for e in entities
            ],
        }

        return TickResult(
            entity_creates=creates,
            entity_updates=updates,
            entity_deletes=deletes,
            broadcast_state=state,
        )

    def _handle_move(
        self,
        intent: Intent,
        entity_map: dict[UUID, Entity],
    ) -> EntityUpdate | None:
        """Handle a movement intent."""
        entity_id_str = intent.data.get("entity_id")
        if entity_id_str is None:
            return None

        try:
            entity_id = UUID(entity_id_str)
        except ValueError:
            return None

        entity = entity_map.get(entity_id)
        if entity is None:
            return None

        dx = intent.data.get("dx", 0)
        dy = intent.data.get("dy", 0)

        if not isinstance(dx, int) or not isinstance(dy, int):
            return None

        # Calculate new position
        new_x = entity.x + dx
        new_y = entity.y + dy

        # Basic bounds check (game logic can enforce zone-specific rules)
        if new_x < 0 or new_y < 0:
            return None

        # Apply the update
        entity.x = new_x
        entity.y = new_y

        return EntityUpdate(
            id=entity_id,
            x=new_x,
            y=new_y,
        )

    def _handle_delete_entity(
        self,
        intent: Intent,
        entity_map: dict[UUID, Entity],
    ) -> UUID | None:
        """Handle an entity deletion intent."""
        entity_id_str = intent.data.get("entity_id")
        if entity_id_str is None:
            return None

        try:
            entity_id = UUID(entity_id_str)
        except ValueError:
            return None

        # Verify entity exists
        if entity_id not in entity_map:
            return None

        return entity_id

    def _handle_create_entity(self, intent: Intent) -> EntityCreate | None:
        """Handle an entity creation intent."""
        x = intent.data.get("x", 0)
        y = intent.data.get("y", 0)
        width = intent.data.get("width", 1)
        height = intent.data.get("height", 1)
        metadata = intent.data.get("metadata", {})

        if not all(isinstance(v, int) for v in [x, y, width, height]):
            return None

        if x < 0 or y < 0 or width < 0 or height < 0:
            return None

        return EntityCreate(
            x=x,
            y=y,
            width=width,
            height=height,
            metadata=metadata,
        )

    def get_player_state(
        self,
        zone_id: UUID,
        player_id: UUID,
        full_state: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Get player-specific state.
        Adds player_id to state to demonstrate per-player filtering.
        In a real game, this could implement fog-of-war or hide certain entities.
        """
        # Copy state and add player-specific info
        player_state = dict(full_state)
        player_state["viewer_id"] = str(player_id)
        return player_state


# Module instance for the loader
game_module = ExampleGameModule()
