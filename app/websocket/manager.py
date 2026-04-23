"""Thread-safe WebSocket connection manager."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket

from app.websocket.events import build_ws_message, normalize_ws_message

logger = logging.getLogger(__name__)


@dataclass
class ConnectionState:
    websocket: WebSocket
    connected_at: float
    last_seen: float
    message_count: int = 0


class ConnectionManager:
    """Manage active WebSocket connections per user with basic safety controls."""

    def __init__(self) -> None:
        self._connections: Dict[int, Set[WebSocket]] = {}
        self._states: Dict[WebSocket, ConnectionState] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_stop: Optional[asyncio.Event] = None
        self._heartbeat_interval = 25
        self._stale_timeout = 75
        self._max_messages_per_connection = 200

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        """Accept and store a user connection."""
        await websocket.accept()
        now = time.monotonic()

        async with self._lock:
            self._connections.setdefault(user_id, set()).add(websocket)
            self._states[websocket] = ConnectionState(
                websocket=websocket,
                connected_at=now,
                last_seen=now,
            )

        logger.info("WebSocket connected for user %s", user_id)

    async def disconnect(self, user_id: int, websocket: Optional[WebSocket] = None) -> None:
        """Remove one connection or all connections for a user."""
        async with self._lock:
            sockets = self._connections.get(user_id)
            if not sockets:
                return

            targets = {websocket} if websocket else set(sockets)
            for socket in targets:
                sockets.discard(socket)
                self._states.pop(socket, None)

            if not sockets:
                self._connections.pop(user_id, None)

        logger.info("WebSocket disconnected for user %s", user_id)

    async def send_to_user(self, user_id: int, message: Any) -> bool:
        """Send a structured message to one user's active connections."""
        payload = normalize_ws_message(message)

        async with self._lock:
            sockets = list(self._connections.get(user_id, set()))

        if not sockets:
            return False

        delivered = False
        stale_sockets: List[WebSocket] = []
        for websocket in sockets:
            if await self._send_json(websocket, user_id, payload):
                delivered = True
            else:
                stale_sockets.append(websocket)

        for websocket in stale_sockets:
            await self.disconnect(user_id, websocket)

        return delivered

    async def broadcast(self, message: Any) -> int:
        """Broadcast a structured message to all connected users."""
        payload = normalize_ws_message(message)

        async with self._lock:
            targets = [(user_id, list(sockets)) for user_id, sockets in self._connections.items()]

        delivered = 0
        for user_id, sockets in targets:
            for websocket in sockets:
                if await self._send_json(websocket, user_id, payload):
                    delivered += 1
                else:
                    await self.disconnect(user_id, websocket)

        return delivered

    async def mark_activity(self, websocket: WebSocket) -> None:
        """Update the last-seen timestamp for an active connection."""
        async with self._lock:
            state = self._states.get(websocket)
            if state:
                state.last_seen = time.monotonic()

    async def record_client_message(self, websocket: WebSocket) -> int:
        """Increment inbound message count and return the new total."""
        async with self._lock:
            state = self._states.get(websocket)
            if not state:
                return 0

            state.message_count += 1
            state.last_seen = time.monotonic()
            return state.message_count

    async def get_active_users(self) -> List[int]:
        async with self._lock:
            return list(self._connections.keys())

    async def get_connection_count(self, user_id: int) -> int:
        async with self._lock:
            return len(self._connections.get(user_id, set()))

    async def start_heartbeat(self) -> None:
        """Start a background heartbeat loop."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            return

        self._heartbeat_stop = asyncio.Event()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("WebSocket heartbeat task started")

    async def stop_heartbeat(self) -> None:
        """Stop the heartbeat loop."""
        if self._heartbeat_stop:
            self._heartbeat_stop.set()

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            finally:
                self._heartbeat_task = None
                self._heartbeat_stop = None
        logger.info("WebSocket heartbeat task stopped")

    async def _heartbeat_loop(self) -> None:
        while self._heartbeat_stop and not self._heartbeat_stop.is_set():
            await asyncio.sleep(self._heartbeat_interval)
            async with self._lock:
                snapshot = {
                    user_id: list(sockets)
                    for user_id, sockets in self._connections.items()
                }

            now = time.monotonic()
            for user_id, sockets in snapshot.items():
                for websocket in sockets:
                    state = self._states.get(websocket)
                    if state and now - state.last_seen > self._stale_timeout:
                        logger.warning("WebSocket stale for user %s", user_id)
                        await self.disconnect(user_id, websocket)
                        continue

                    await self._send_json(
                        websocket,
                        user_id,
                        build_ws_message("ping", {"user_id": user_id}),
                        touch_activity=False,
                    )

    async def _send_json(
        self,
        websocket: WebSocket,
        user_id: int,
        payload: Dict[str, Any],
        touch_activity: bool = True,
    ) -> bool:
        try:
            await websocket.send_json(payload)
            if touch_activity:
                await self.mark_activity(websocket)
            return True
        except Exception as exc:
            logger.error("WebSocket send failed for user %s: %s", user_id, exc)
            return False

    async def enforce_message_limit(self, websocket: WebSocket) -> bool:
        """Return False when a connection exceeds the basic inbound message limit."""
        count = await self.record_client_message(websocket)
        if count > self._max_messages_per_connection:
            logger.warning("WebSocket message limit exceeded: %s", count)
            return False
        return True


connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    return connection_manager
