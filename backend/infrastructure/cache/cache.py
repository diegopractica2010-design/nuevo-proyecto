from __future__ import annotations

import json
import logging
import os
from typing import Any

try:
    import redis
except ImportError:  # pragma: no cover - exercised only in minimal environments.
    redis = None


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
logger = logging.getLogger(__name__)


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


def cache_delete(*keys: str) -> int:
    if not keys:
        return 0
    client = _get_client()
    return int(client.delete(*keys))


def revoke_token(jti: str, ttl_seconds: int) -> None:
    try:
        cache_set(f"jwt:blacklist:{jti}", True, ttl=ttl_seconds)
    except Exception as exc:
        logger.warning("Unable to revoke JWT in Redis: %s", exc)


def is_token_revoked(jti: str) -> bool:
    try:
        return cache_get(f"jwt:blacklist:{jti}") is not None
    except Exception as exc:
        logger.warning("Unable to check JWT blacklist in Redis: %s", exc)
        return False


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
