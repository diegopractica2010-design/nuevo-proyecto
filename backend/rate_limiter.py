"""Rate limiting implementation using Redis (Fase A)."""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

import redis
from fastapi import Request

from backend.config import (
    AUTH_RATE_LIMIT_REQUESTS_PER_MINUTE,
    RATE_LIMIT_REQUESTS_PER_MINUTE,
    RATE_LIMIT_WINDOW_SECONDS,
    REDIS_URL,
)

logger = logging.getLogger(__name__)

_TRUSTED_PROXIES: frozenset[str] = frozenset(
    ip.strip() for ip in os.getenv("TRUSTED_PROXY_IPS", "").split(",") if ip.strip()
)


class RateLimiter:
    """Redis-backed rate limiter using sliding window algorithm."""

    def __init__(
        self,
        redis_url: str = REDIS_URL,
        requests_per_minute: int = RATE_LIMIT_REQUESTS_PER_MINUTE,
        auth_requests_per_minute: int = AUTH_RATE_LIMIT_REQUESTS_PER_MINUTE,
    ):
        self.redis_url = redis_url
        self.requests_per_minute = requests_per_minute
        self.auth_requests_per_minute = auth_requests_per_minute
        self.window_seconds = RATE_LIMIT_WINDOW_SECONDS
        self.redis_client: Optional[redis.Redis] = None
        self._connect()

    def _connect(self):
        """Connect to Redis with error handling."""
        try:
            # Parse Redis URL
            pool = redis.ConnectionPool.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                retry_on_timeout=True,
            )
            self.redis_client = redis.Redis(connection_pool=pool)
            self.redis_client.ping()
            logger.info("Rate limiter connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}. Rate limiting DISABLED.")

    def _get_ip(self, request: Request) -> str:
        """
        Obtiene la IP real del cliente.

        Solo confia en X-Forwarded-For si la conexion llega desde un proxy
        configurado como confiable. Sin proxies configurados, usa la IP TCP.
        """
        client_ip = request.client.host if request.client else "unknown"
        if _TRUSTED_PROXIES and client_ip in _TRUSTED_PROXIES:
            forwarded_for = request.headers.get("x-forwarded-for", "").strip()
            if forwarded_for:
                return forwarded_for.split(",")[0].strip()
        return client_ip

    def _get_authenticated_username(self, request: Request) -> str | None:
        authorization = request.headers.get("authorization") or request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None

        try:
            from backend.auth import TokenService

            return TokenService.verify_token(authorization[7:])
        except Exception as exc:
            logger.debug("Falling back to IP rate limit bucket after token parsing failed: %s", exc)
            return None

    def _get_rate_limit_bucket(self, request: Request) -> dict:
        client_ip = self._get_ip(request)
        username = self._get_authenticated_username(request)
        if username:
            return {
                "key": f"rl:user:{username}",
                "limit": self.auth_requests_per_minute,
                "bucket_type": "user",
                "username": username,
                "ip": client_ip,
            }
        return {
            "key": f"rl:ip:{client_ip}",
            "limit": self.requests_per_minute,
            "bucket_type": "ip",
            "ip": client_ip,
        }

    def is_rate_limited(self, request: Request) -> tuple[bool, dict]:
        """
        Check if request is rate limited.

        Returns:
            (is_limited, metadata) tuple
            where metadata contains: {allowed, limit, window, retry_after}
        """
        if not self.redis_client:
            # Redis unavailable: allow request (graceful degradation)
            return False, {"allowed": True, "reason": "redis_unavailable"}

        try:
            bucket = self._get_rate_limit_bucket(request)
            key = bucket["key"]
            limit = bucket["limit"]
            now = time.time()
            window_start = now - self.window_seconds

            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()

            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            pipe.zcard(key)

            # Add current request timestamp
            pipe.zadd(key, {str(now): now})

            # Set expiry (cleanup old keys)
            pipe.expire(key, self.window_seconds + 1)

            results = pipe.execute()
            request_count = results[1]  # Count after cleanup but before adding current

            # Check if limit exceeded
            if request_count >= limit:
                # Get oldest request time to calculate retry_after
                oldest = self.redis_client.zrange(key, 0, 0, withscores=True)
                retry_after = int((oldest[0][1] + self.window_seconds - now)) if oldest else 1

                logger.warning(
                    "Rate limit exceeded for %s bucket %s: %s/%s requests in %ss",
                    bucket["bucket_type"],
                    key,
                    request_count,
                    limit,
                    self.window_seconds,
                )

                return True, {
                    "allowed": False,
                    "limit": limit,
                    "window": self.window_seconds,
                    "retry_after": max(1, retry_after),
                    **bucket,
                }

            # Request allowed
            return False, {
                "allowed": True,
                "limit": limit,
                "window": self.window_seconds,
                "remaining": limit - request_count - 1,
                **bucket,
            }

        except Exception as e:
            logger.error(f"Rate limiter error: {e}. Allowing request (graceful degradation).")
            return False, {"allowed": True, "reason": "rate_limiter_error"}


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
