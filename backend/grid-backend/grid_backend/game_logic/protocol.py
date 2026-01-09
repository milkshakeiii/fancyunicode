"""
Protocol and types for game logic modules.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from grid_backend.models.entity import Entity


@dataclass
class Intent:
    """
    Represents a player intent passed to game logic.
    """

    player_id: UUID
    zone_id: UUID
    data: dict[str, Any]


@dataclass
class EntityCreate:
    """
    Describes a new entity to create.
    """

    x: int
    y: int
    width: int = 0
    height: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityUpdate:
    """
    Describes updates to an existing entity.
    Only non-None fields will be updated.
    """

    id: UUID
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class TickResult:
    """
    Result returned by game logic after processing a tick.

    The framework owns the authoritative entity snapshot. Game modules return:
    - entity_creates/updates/deletes: deltas to apply (persisted by framework)
    - extras: arbitrary non-entity payload (events, notifications, etc.)

    Do NOT include an entity snapshot in extras - the framework builds that
    from post-apply state and passes it to get_player_state for filtering.
    """

    entity_creates: list[EntityCreate] = field(default_factory=list)
    entity_updates: list[EntityUpdate] = field(default_factory=list)
    entity_deletes: list[UUID] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)


class FrameworkAPI:
    """
    API provided to game logic modules for interacting with the framework.
    """

    def __init__(self, db_session_factory) -> None:
        self._db_session_factory = db_session_factory

    async def get_zone_entities(self, zone_id: UUID) -> list[Entity]:
        """Get all entities in a zone."""
        from sqlalchemy import select
        from grid_backend.models.entity import Entity

        async with self._db_session_factory() as db:
            result = await db.execute(
                select(Entity).where(Entity.zone_id == zone_id)
            )
            return list(result.scalars().all())

    async def get_entity(self, entity_id: UUID) -> Entity | None:
        """Get a specific entity by ID."""
        from sqlalchemy import select
        from grid_backend.models.entity import Entity

        async with self._db_session_factory() as db:
            result = await db.execute(
                select(Entity).where(Entity.id == entity_id)
            )
            return result.scalar_one_or_none()


@runtime_checkable
class GameLogicModule(Protocol):
    """
    Protocol that game logic modules must implement.
    """

    def on_init(self, framework: FrameworkAPI) -> None:
        """
        Called once when the module is loaded.
        Use to set up initial state or resources.
        """
        ...

    def on_tick(
        self,
        zone_id: UUID,
        entities: list[Entity],
        intents: list[Intent],
        tick_number: int,
    ) -> TickResult:
        """
        Called each tick for each zone.
        Process intents and return state changes.
        """
        ...

    def get_player_state(
        self,
        zone_id: UUID,
        player_id: UUID,
        full_state: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Filter or transform state for a specific player.
        Canonical fog-of-war/redaction hook.

        full_state contains:
        - zone_id, tick_number
        - entities: framework-built authoritative snapshot (post-apply)
        - any extras from on_tick result

        Return the state to send to this specific player.
        """
        ...
