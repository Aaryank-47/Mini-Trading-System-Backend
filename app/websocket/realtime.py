"""Redis-backed realtime event bridge for WebSocket fanout."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from app.utils.redis_manager import get_redis_client
from app.websocket.events import build_ws_message

logger = logging.getLogger(__name__)

PRICE_UPDATES_CHANNEL = "price_updates"
ORDER_EVENTS_CHANNEL = "order_events"

_bridge_task: Optional[asyncio.Task] = None
_stop_event: Optional[asyncio.Event] = None
_active_manager = None


def publish_realtime_event(channel: str, event: str, data: Dict[str, Any]) -> bool:
    """Publish a structured realtime event to Redis when available."""
    client = get_redis_client()
    if not client:
        return False

    try:
        client.publish(channel, json.dumps(build_ws_message(event, data), default=str))
        return True
    except Exception as exc:
        logger.warning(f"Failed to publish realtime event on {channel}: {exc}")
        return False


async def _forward_payload(channel: str, payload: Dict[str, Any]) -> None:
    if _active_manager is None:
        return

    if channel == ORDER_EVENTS_CHANNEL:
        data = payload.get("data") or {}
        user_id = data.get("user_id")
        if user_id is not None:
            await _active_manager.send_to_user(int(user_id), payload)
            return

    await _active_manager.broadcast(payload)


async def _bridge_loop() -> None:
    client = get_redis_client()
    if not client:
        logger.info("Realtime bridge not started because Redis is unavailable")
        return

    pubsub = client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(PRICE_UPDATES_CHANNEL, ORDER_EVENTS_CHANNEL)
    logger.info(
        "Realtime bridge subscribed to Redis channels: %s, %s",
        PRICE_UPDATES_CHANNEL,
        ORDER_EVENTS_CHANNEL,
    )

    try:
        while _stop_event and not _stop_event.is_set():
            message = await asyncio.to_thread(pubsub.get_message, timeout=1.0)
            if not message or message.get("type") != "message":
                await asyncio.sleep(0.1)
                continue

            channel = message.get("channel")
            raw_payload = message.get("data")

            try:
                payload = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
            except Exception as exc:
                logger.error(f"Invalid realtime payload on {channel}: {exc}")
                continue

            if isinstance(payload, dict):
                await _forward_payload(str(channel), payload)
    except asyncio.CancelledError:
        logger.info("Realtime bridge task cancelled")
        raise
    except Exception as exc:
        logger.error(f"Realtime bridge stopped unexpectedly: {exc}")
    finally:
        try:
            pubsub.close()
        except Exception:
            pass


def start_realtime_bridge(manager) -> None:
    """Start the Redis pub/sub bridge if Redis is available."""
    global _bridge_task, _stop_event, _active_manager

    if _bridge_task and not _bridge_task.done():
        return

    _active_manager = manager
    _stop_event = asyncio.Event()
    _bridge_task = asyncio.create_task(_bridge_loop())


async def stop_realtime_bridge() -> None:
    """Stop the Redis pub/sub bridge cleanly."""
    global _bridge_task, _stop_event

    if _stop_event:
        _stop_event.set()

    if _bridge_task:
        _bridge_task.cancel()
        try:
            await _bridge_task
        except asyncio.CancelledError:
            pass
        finally:
            _bridge_task = None
            _stop_event = None
