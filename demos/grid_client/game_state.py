"""Thread-safe game state management."""

import threading
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Entity:
    """Client-side entity representation."""
    id: str
    x: int
    y: int
    width: int = 0
    height: int = 0
    owner_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class ClientState:
    """Thread-safe client state container."""

    def __init__(self):
        # Connection state
        self.connected: bool = False
        self.authenticated: bool = False
        self.subscribed_zone: Optional[str] = None

        # Player identity
        self.player_id: Optional[str] = None
        self.my_entity_id: Optional[str] = None
        self.session_token: Optional[str] = None

        # Game state (from server ticks)
        self.tick_number: int = 0
        self.entities: dict[str, Entity] = {}

        # UI state
        self.status_message: str = "Disconnected"

        # Lock for thread safety
        self._lock = threading.Lock()

    def update_from_tick(self, tick_data: dict) -> None:
        """Update state from server tick message."""
        with self._lock:
            self.tick_number = tick_data.get("tick_number", 0)
            state = tick_data.get("state", {})

            # Clear and rebuild entities
            self.entities.clear()
            for e in state.get("entities", []):
                entity = Entity(
                    id=e["id"],
                    x=e["x"],
                    y=e["y"],
                    width=e.get("width", 0),
                    height=e.get("height", 0),
                    owner_id=e.get("owner_id"),
                    metadata=e.get("metadata", {})
                )
                self.entities[e["id"]] = entity

    def get_entities_snapshot(self) -> list[Entity]:
        """Get a thread-safe copy of entities."""
        with self._lock:
            return list(self.entities.values())

    def get_my_entity(self) -> Optional[Entity]:
        """Get this player's entity if it exists."""
        with self._lock:
            if self.my_entity_id:
                return self.entities.get(self.my_entity_id)
            return None

    def set_status(self, msg: str) -> None:
        """Thread-safe status update."""
        with self._lock:
            self.status_message = msg

    def get_status(self) -> str:
        """Thread-safe status read."""
        with self._lock:
            return self.status_message
