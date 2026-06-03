from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

try:
    import redis
except ImportError:  # pragma: no cover - exercised only in minimal environments.
    redis = None


logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# How long to keep Redis "circuit" open (skip all calls) after a failure, in
# seconds. Without this, every cache call re-attempts a connection that blocks
# the event loop for socket_connect_timeout seconds when Redis is down — which
# serializes all concurrent searches. We probe again only after this window.
_CIRCUIT_COOLDOWN = 60.0

_client = None
# Timestamp until which Redis is considered unavailable. 0 = healthy/unknown.
_circuit_open_until: float = 0.0


def set_cache_client(client) -> None:
    global _client, _circuit_open_until
    _client = client
    _circuit_open_until = 0.0


def _redis_down() -> bool:
    return time.monotonic() < _circuit_open_until


def _trip_circuit(exc: Exception) -> None:
    """Mark Redis as unavailable so subsequent calls skip it for a while."""
    global _circuit_open_until
    if not _redis_down():
        logger.warning(
            "Redis unavailable (%s); skipping cache for %.0fs and using in-memory fallback.",
            exc, _CIRCUIT_COOLDOWN,
        )
    _circuit_open_until = time.monotonic() + _CIRCUIT_COOLDOWN


def cache_get(key: str) -> Any:
    if _redis_down():
        return None
    try:
        client = _get_client()
        value = client.get(key)
    except Exception as exc:
        _trip_circuit(exc)
        return None
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def cache_set(key: str, value: Any, ttl: int = 600) -> bool:
    if _redis_down():
        return False
    try:
        client = _get_client()
        payload = json.dumps(value, ensure_ascii=False)
        return bool(client.set(key, payload, ex=ttl))
    except Exception as exc:
        _trip_circuit(exc)
        return False


def cache_delete(*keys: str) -> int:
    if not keys or _redis_down():
        return 0
    try:
        client = _get_client()
        return int(client.delete(*keys))
    except Exception as exc:
        _trip_circuit(exc)
        return 0


def _get_client():
    global _client
    if _client is not None:
        return _client
    if redis is None:
        raise RuntimeError("redis package is required for cache operations")
    _client = redis.Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    return _client
