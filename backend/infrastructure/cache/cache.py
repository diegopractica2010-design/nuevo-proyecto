from __future__ import annotations

import json
import os
from typing import Any

try:
    import redis
except ImportError:  # pragma: no cover - exercised only in minimal environments.
    redis = None


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


_client = None


def set_cache_client(client) -> None:
    global _client
    _client = client


def cache_get(key: str) -> Any:
    client = _get_client()
    value = client.get(key)
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def cache_set(key: str, value: Any, ttl: int = 600) -> bool:
    client = _get_client()
    payload = json.dumps(value, ensure_ascii=False)
    return bool(client.set(key, payload, ex=ttl))


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
