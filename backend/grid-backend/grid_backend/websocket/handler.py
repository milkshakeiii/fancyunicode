"""
WebSocket message handler for Grid Backend.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from grid_backend.models.zone import Zone
from grid_backend.websocket.manager import ConnectionInfo, ConnectionManager

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """
    Handles WebSocket messages for a connected player.
    """

    def __init__(
        self,
        manager: ConnectionManager,
        info: ConnectionInfo,
        db_session_factory,
    ) -> None:
        self.manager = manager
        self.info = info
        self.db_session_factory = db_session_factory
        self._running = True

    async def handle_connection(self) -> None:
        """Main message loop for a WebSocket connection."""
        try:
            while self._running:
                message = await self.info.websocket.receive_json()
                await self._handle_message(message)
        except WebSocketDisconnect:
            logger.info(f"Player {self.info.player_id} disconnected")
        except Exception as e:
            logger.error(f"Error in WebSocket handler: {e}")
            await self._send_error(f"Internal error: {str(e)}")
        finally:
            await self.manager.disconnect(self.info.player_id)

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Route incoming messages to appropriate handlers."""
        msg_type = message.get("type")

        if msg_type is None:
            await self._send_error("Missing message type")
            return

        handlers = {
            "subscribe": self._handle_subscribe,
            "intent": self._handle_intent,
        }

        handler = handlers.get(msg_type)
        if handler is None:
            await self._send_error(f"Unknown message type: {msg_type}")
            return

        await handler(message)

    async def _handle_subscribe(self, message: dict[str, Any]) -> None:
        """Handle zone subscription request."""
        zone_id_str = message.get("zone_id")

        if zone_id_str is None:
            await self._send_error("Missing zone_id")
            return

        try:
            zone_id = UUID(zone_id_str)
        except ValueError:
            await self._send_error("Invalid zone_id format")
            return

        # Verify zone exists
        async with self.db_session_factory() as db:
            result = await db.execute(
                select(Zone).where(Zone.id == zone_id)
            )
            zone = result.scalar_one_or_none()

            if zone is None:
                await self._send_error("Zone not found")
                return

        # Subscribe to zone
        success = await self.manager.subscribe_to_zone(self.info.player_id, zone_id)

        if success:
            await self.info.websocket.send_json({
                "type": "subscribed",
                "zone_id": str(zone_id),
            })
            logger.info(f"Player {self.info.player_id} subscribed to zone {zone_id}")
        else:
            await self._send_error("Failed to subscribe to zone")

    async def _handle_intent(self, message: dict[str, Any]) -> None:
        """Handle player intent submission."""
        if self.info.zone_id is None:
            await self._send_error("Must subscribe to a zone first")
            return

        intent_data = message.get("data")
        if intent_data is None:
            await self._send_error("Missing intent data")
            return

        # Queue intent for processing
        from grid_backend.tick_engine import get_tick_engine

        engine = get_tick_engine()
        if engine is None:
            await self._send_error("Tick engine not available")
            return

        engine.queue_intent(
            zone_id=self.info.zone_id,
            player_id=self.info.player_id,
            data=intent_data,
        )

        # Acknowledge intent receipt
        await self.info.websocket.send_json({
            "type": "intent_received",
        })

    async def _send_error(self, message: str) -> None:
        """Send error message to client."""
        try:
            await self.info.websocket.send_json({
                "type": "error",
                "message": message,
            })
        except Exception:
            pass  # Connection might be closed

    def stop(self) -> None:
        """Stop the message handler."""
        self._running = False
