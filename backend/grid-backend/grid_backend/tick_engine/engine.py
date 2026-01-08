"""
Tick engine implementation for Grid Backend.
Manages the game loop and coordinates zone processing.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from grid_backend.models.zone import Zone
from grid_backend.models.entity import Entity

logger = logging.getLogger(__name__)

# Global tick engine instance
_engine: "TickEngine | None" = None


def get_tick_engine() -> "TickEngine | None":
    """Get the global tick engine instance."""
    return _engine


def set_tick_engine(engine: "TickEngine | None") -> None:
    """Set the global tick engine instance."""
    global _engine
    _engine = engine


@dataclass
class Intent:
    """Represents a player intent."""

    player_id: UUID
    zone_id: UUID
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TickStats:
    """Statistics for tick timing."""

    tick_number: int
    duration_ms: float
    zones_processed: int
    intents_processed: int


class TickEngine:
    """
    Manages the game tick loop.
    Processes zones, handles intents, and broadcasts state updates.
    """

    def __init__(
        self,
        tick_rate_ms: int,
        db_session_factory,
        game_logic_module,
    ) -> None:
        self._tick_rate_ms = tick_rate_ms
        self._db_session_factory = db_session_factory
        self._game_logic = game_logic_module

        self._tick_number = 0
        self._is_running = False
        self._is_paused = False
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

        # Intent queues per zone
        self._intent_queues: dict[UUID, list[Intent]] = {}
        self._intent_lock = asyncio.Lock()

        # Tick statistics
        self._recent_stats: list[TickStats] = []
        self._max_stats_history = 100

    @property
    def tick_number(self) -> int:
        """Current tick number."""
        return self._tick_number

    @property
    def is_running(self) -> bool:
        """Whether the tick engine is actively running (not paused)."""
        return self._is_running and not self._is_paused

    @property
    def is_paused(self) -> bool:
        """Whether the tick engine is paused."""
        return self._is_paused

    async def start(self) -> None:
        """Start the tick engine loop."""
        if self._task is not None:
            return

        self._is_running = True
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Tick engine started (rate: {self._tick_rate_ms}ms)")

    async def stop(self) -> None:
        """Stop the tick engine loop."""
        if self._task is None:
            return

        self._is_running = False
        self._stop_event.set()

        try:
            await asyncio.wait_for(self._task, timeout=5.0)
        except asyncio.TimeoutError:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._task = None
        logger.info("Tick engine stopped")

    def pause(self) -> None:
        """Pause the tick engine."""
        self._is_paused = True
        logger.info(f"Tick engine paused at tick {self._tick_number}")

    def resume(self) -> None:
        """Resume the tick engine."""
        self._is_paused = False
        logger.info(f"Tick engine resumed at tick {self._tick_number}")

    async def step(self) -> None:
        """Execute a single tick (when paused)."""
        if not self._is_paused:
            return

        await self._process_tick()
        logger.info(f"Manual tick step executed: {self._tick_number}")

    def queue_intent(self, zone_id: UUID, player_id: UUID, data: dict[str, Any]) -> None:
        """
        Queue an intent for processing on the next tick.
        Thread-safe.
        """
        intent = Intent(player_id=player_id, zone_id=zone_id, data=data)

        # Use non-async lock for immediate queuing
        if zone_id not in self._intent_queues:
            self._intent_queues[zone_id] = []
        self._intent_queues[zone_id].append(intent)

    async def _run_loop(self) -> None:
        """Main tick loop."""
        while self._is_running:
            tick_start = time.perf_counter()

            if not self._is_paused:
                try:
                    await self._process_tick()
                except Exception as e:
                    logger.error(f"Error in tick loop: {e}", exc_info=True)

            # Calculate sleep time to maintain tick rate
            tick_duration = (time.perf_counter() - tick_start) * 1000
            sleep_time = max(0, (self._tick_rate_ms - tick_duration) / 1000)

            # Wait for either sleep time or stop signal
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=sleep_time,
                )
                # Stop event was set
                break
            except asyncio.TimeoutError:
                # Normal tick interval elapsed
                pass

    async def _process_tick(self) -> None:
        """Process a single tick."""
        tick_start = time.perf_counter()
        self._tick_number += 1
        zones_processed = 0
        intents_processed = 0

        async with self._db_session_factory() as db:
            # Get all zones
            result = await db.execute(
                select(Zone).options(selectinload(Zone.entities))
            )
            zones = result.scalars().all()

            for zone in zones:
                try:
                    zone_intents = await self._process_zone(zone, db)
                    zones_processed += 1
                    intents_processed += zone_intents
                except Exception as e:
                    logger.error(
                        f"Error processing zone {zone.id}: {e}",
                        exc_info=True,
                    )
                    # Continue with other zones (error isolation)

        # Record stats
        tick_duration = (time.perf_counter() - tick_start) * 1000
        stats = TickStats(
            tick_number=self._tick_number,
            duration_ms=tick_duration,
            zones_processed=zones_processed,
            intents_processed=intents_processed,
        )
        self._recent_stats.append(stats)
        if len(self._recent_stats) > self._max_stats_history:
            self._recent_stats.pop(0)

        if tick_duration > self._tick_rate_ms:
            logger.warning(
                f"Tick {self._tick_number} took {tick_duration:.1f}ms "
                f"(target: {self._tick_rate_ms}ms)"
            )

    async def _process_zone(self, zone: Zone, db) -> int:
        """
        Process a single zone.
        Returns the number of intents processed.
        """
        # Get and clear intents for this zone
        async with self._intent_lock:
            intents = self._intent_queues.pop(zone.id, [])

        # Sort intents by timestamp
        intents.sort(key=lambda i: i.timestamp)

        # Call game logic
        if self._game_logic is not None:
            try:
                result = self._game_logic.on_tick(
                    zone_id=zone.id,
                    entities=list(zone.entities),
                    intents=intents,
                    tick_number=self._tick_number,
                )

                # Apply entity changes
                await self._apply_tick_result(zone, result, db)

                # Broadcast state to subscribers
                await self._broadcast_zone_state(zone, result)

            except Exception as e:
                logger.error(
                    f"Game logic error in zone {zone.id}: {e}",
                    exc_info=True,
                )
        else:
            # No game logic - just broadcast basic state
            await self._broadcast_basic_state(zone)

        return len(intents)

    async def _apply_tick_result(self, zone: Zone, result, db) -> None:
        """Apply entity changes from tick result."""
        # Create new entities
        for create in result.entity_creates:
            entity = Entity(
                zone_id=zone.id,
                x=create.x,
                y=create.y,
                width=create.width,
                height=create.height,
                metadata_=create.metadata,
            )
            db.add(entity)

        # Update existing entities
        for update in result.entity_updates:
            for entity in zone.entities:
                if entity.id == update.id:
                    if update.x is not None:
                        entity.x = update.x
                    if update.y is not None:
                        entity.y = update.y
                    if update.width is not None:
                        entity.width = update.width
                    if update.height is not None:
                        entity.height = update.height
                    if update.metadata is not None:
                        entity.metadata_ = update.metadata
                    break

        # Delete entities
        for entity_id in result.entity_deletes:
            for entity in zone.entities:
                if entity.id == entity_id:
                    await db.delete(entity)
                    break

        await db.commit()

    async def _broadcast_zone_state(self, zone: Zone, result) -> None:
        """Broadcast tick state to zone subscribers."""
        from grid_backend.websocket import get_connection_manager

        manager = get_connection_manager()
        if manager is None:
            return

        subscribers = await manager.get_zone_subscribers(zone.id)

        for sub in subscribers:
            # Get player-specific state if game logic supports it
            state = result.broadcast_state
            if self._game_logic is not None:
                try:
                    state = self._game_logic.get_player_state(
                        zone_id=zone.id,
                        player_id=sub.player_id,
                        full_state=result.broadcast_state,
                    )
                except Exception as e:
                    logger.warning(
                        f"Error getting player state for {sub.player_id}: {e}"
                    )

            message = {
                "type": "tick",
                "tick_number": self._tick_number,
                "state": state,
            }

            asyncio.create_task(
                manager._send_to_connection(sub, message)
            )

    async def _broadcast_basic_state(self, zone: Zone) -> None:
        """Broadcast basic state when no game logic is loaded."""
        from grid_backend.websocket import get_connection_manager

        manager = get_connection_manager()
        if manager is None:
            return

        state = {
            "zone_id": str(zone.id),
            "entities": [
                {
                    "id": str(e.id),
                    "x": e.x,
                    "y": e.y,
                    "width": e.width,
                    "height": e.height,
                    "metadata": e.metadata_,
                }
                for e in zone.entities
            ],
        }

        message = {
            "type": "tick",
            "tick_number": self._tick_number,
            "state": state,
        }

        await manager.broadcast_to_zone(zone.id, message)

    def get_recent_stats(self) -> list[TickStats]:
        """Get recent tick statistics."""
        return list(self._recent_stats)
