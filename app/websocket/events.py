"""Helpers for structured WebSocket event payloads."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def build_ws_message(event: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build a production-safe WebSocket event envelope."""
    return {
        "event": event,
        "data": data or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def is_structured_message(message: Any) -> bool:
    """Return True when a payload already matches the event envelope shape."""
    return (
        isinstance(message, dict)
        and isinstance(message.get("event"), str)
        and "data" in message
        and "timestamp" in message
    )


def normalize_ws_message(message: Any, default_event: str = "message") -> Dict[str, Any]:
    """Normalize arbitrary payloads into the standard event envelope."""
    if is_structured_message(message):
        return message

    if isinstance(message, dict):
        return build_ws_message(default_event, message)

    return build_ws_message(default_event, {"value": message})
