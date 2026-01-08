"""
WebSocket connection manager for Grid Backend.
Handles player connections, zone subscriptions, and message broadcasting.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from grid_backend.models.session import Session as SessionModel

logger = logging.getLogger(__name__)

# Global connection manager instance
_manager: "ConnectionManager | None" = None


def get_connection_manager() -> "ConnectionManager | None":
    """Get the global connection manager instance."""
    return _manager


def set_connection_manager(manager: "ConnectionManager") -> None:
    """Set the global connection manager instance."""
    global _manager
    _manager = manager


@dataclass
class ConnectionInfo:
    """Information about a connected player."""

    player_id: UUID
    username: str
    websocket: WebSocket
    zone_id: UUID | None = None


class ConnectionManager:
    """
    Manages WebSocket connections and zone subscriptions.
    """

    def __init__(self) -> None:
        # Map of player_id -> ConnectionInfo
        self._connections: dict[UUID, ConnectionInfo] = {}
        # Map of zone_id -> set of player_ids subscribed
        self._zone_subscribers: dict[UUID, set[UUID]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def authenticate(
        self,
        websocket: WebSocket,
        token: str,
        db: AsyncSession,
    ) -> ConnectionInfo | None:
        """
        Authenticate a WebSocket connection using session token.
        Returns ConnectionInfo if successful, None if authentication fails.
        """
        from grid_backend.models.player import Player

        # Find session by token
        result = await db.execute(
            select(SessionModel).where(SessionModel.token == token)
        )
        session = result.scalar_one_or_none()

        if session is None or session.is_expired():
            return None

        # Get player
        result = await db.execute(
            select(Player).where(Player.id == session.player_id)
        )
        player = result.scalar_one_or_none()

        if player is None:
            return None

        return ConnectionInfo(
            player_id=player.id,
            username=player.username,
            websocket=websocket,
        )

    async def connect(self, info: ConnectionInfo) -> None:
        """Register a new connection."""
        async with self._lock:
            # Disconnect existing connection for this player if any
            if info.player_id in self._connections:
                await self._disconnect_internal(info.player_id)

            self._connections[info.player_id] = info
            logger.info(f"Player {info.username} ({info.player_id}) connected")

    async def disconnect(self, player_id: UUID) -> None:
        """Unregister a connection."""
        async with self._lock:
            await self._disconnect_internal(player_id)

    async def _disconnect_internal(self, player_id: UUID) -> None:
        """Internal disconnect without lock (called when lock is already held)."""
        if player_id not in self._connections:
            return

        info = self._connections[player_id]

        # Remove from zone subscription
        if info.zone_id is not None:
            if info.zone_id in self._zone_subscribers:
                self._zone_subscribers[info.zone_id].discard(player_id)
                if not self._zone_subscribers[info.zone_id]:
                    del self._zone_subscribers[info.zone_id]

        del self._connections[player_id]
        logger.info(f"Player {info.username} ({player_id}) disconnected")

    async def subscribe_to_zone(self, player_id: UUID, zone_id: UUID) -> bool:
        """
        Subscribe a player to a zone.
        Automatically unsubscribes from previous zone.
        Returns True if successful.
        """
        async with self._lock:
            if player_id not in self._connections:
                return False

            info = self._connections[player_id]

            # Unsubscribe from previous zone
            if info.zone_id is not None:
                if info.zone_id in self._zone_subscribers:
                    self._zone_subscribers[info.zone_id].discard(player_id)
                    if not self._zone_subscribers[info.zone_id]:
                        del self._zone_subscribers[info.zone_id]

            # Subscribe to new zone
            info.zone_id = zone_id
            if zone_id not in self._zone_subscribers:
                self._zone_subscribers[zone_id] = set()
            self._zone_subscribers[zone_id].add(player_id)

            logger.info(f"Player {info.username} subscribed to zone {zone_id}")
            return True

    async def get_zone_subscribers(self, zone_id: UUID) -> list[ConnectionInfo]:
        """Get all players subscribed to a zone."""
        async with self._lock:
            if zone_id not in self._zone_subscribers:
                return []

            return [
                self._connections[player_id]
                for player_id in self._zone_subscribers[zone_id]
                if player_id in self._connections
            ]

    async def broadcast_to_zone(
        self,
        zone_id: UUID,
        message: dict[str, Any],
        exclude_player: UUID | None = None,
    ) -> None:
        """
        Broadcast a message to all subscribers of a zone.
        Non-blocking: slow clients won't block the broadcast.
        """
        subscribers = await self.get_zone_subscribers(zone_id)

        for info in subscribers:
            if exclude_player and info.player_id == exclude_player:
                continue

            # Non-blocking send
            asyncio.create_task(self._send_to_connection(info, message))

    async def _send_to_connection(
        self,
        info: ConnectionInfo,
        message: dict[str, Any],
    ) -> None:
        """Send a message to a specific connection."""
        try:
            await asyncio.wait_for(
                info.websocket.send_json(message),
                timeout=5.0,  # Don't wait more than 5 seconds
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout sending to player {info.player_id}")
        except Exception as e:
            logger.warning(f"Error sending to player {info.player_id}: {e}")
            # Don't disconnect here - let the main handler handle it

    async def send_to_player(self, player_id: UUID, message: dict[str, Any]) -> bool:
        """Send a message to a specific player."""
        async with self._lock:
            if player_id not in self._connections:
                return False

            info = self._connections[player_id]

        try:
            await info.websocket.send_json(message)
            return True
        except Exception as e:
            logger.warning(f"Error sending to player {player_id}: {e}")
            return False

    def get_all_connections(self) -> dict[UUID, ConnectionInfo]:
        """Get all current connections."""
        return dict(self._connections)

    def get_connection(self, player_id: UUID) -> ConnectionInfo | None:
        """Get connection info for a specific player."""
        return self._connections.get(player_id)

    @property
    def connection_count(self) -> int:
        """Number of active connections."""
        return len(self._connections)
