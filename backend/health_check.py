"""
Healthcheck service - FASE A

Proporciona endpoints para verificar salud del sistema:
- /health/live: ¿Está vivo?
- /health/ready: ¿Está listo para requests?
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import redis
from sqlalchemy import text

from backend.config import REDIS_URL, DATABASE_URL
from backend.db import SessionLocal

logger = logging.getLogger(__name__)


class HealthChecker:
    """Check system health (Redis, Database, Scraper connectivity)."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis client for health checks."""
        try:
            pool = redis.ConnectionPool.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_keepalive=True,
            )
            self.redis_client = redis.Redis(connection_pool=pool)
            self.redis_client.ping()
        except Exception as e:
            logger.error(f"Redis client init failed: {e}")
            self.redis_client = None
    
    def check_redis(self) -> dict:
        """Check Redis connectivity and basic operations."""
        try:
            if not self.redis_client:
                return {
                    "status": "error",
                    "error": "Redis client not initialized",
                }
            
            # Ping
            self.redis_client.ping()
            
            # Info
            info = self.redis_client.info()
            
            return {
                "status": "ok",
                "connected": True,
                "memory_used_mb": info.get("used_memory", 0) / 1024 / 1024,
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    def check_database(self) -> dict:
        """Check database connectivity."""
        try:
            with SessionLocal() as session:
                # Execute simple query
                result = session.execute(text("SELECT 1")).scalar()
                return {
                    "status": "ok",
                    "connected": True,
                    "database_url": self._mask_url(DATABASE_URL),
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    def check_scraper_connectivity(self) -> dict:
        """Check if we can reach Lider/Jumbo."""
        try:
            import requests
            
            # Try Lider
            start = time.time()
            try:
                response = requests.get(
                    "https://super.lider.cl/",
                    timeout=5,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                lider_time = time.time() - start
                lider_status = "ok" if response.status_code == 200 else "error"
            except Exception as e:
                lider_status = "error"
                lider_time = None
            
            # Try Jumbo
            start = time.time()
            try:
                response = requests.get(
                    "https://www.jumbo.cl/",
                    timeout=5,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                jumbo_time = time.time() - start
                jumbo_status = "ok" if response.status_code == 200 else "error"
            except Exception as e:
                jumbo_status = "error"
                jumbo_time = None
            
            return {
                "status": "ok",
                "lider": {
                    "status": lider_status,
                    "response_time_ms": int(lider_time * 1000) if lider_time else None,
                },
                "jumbo": {
                    "status": jumbo_status,
                    "response_time_ms": int(jumbo_time * 1000) if jumbo_time else None,
                },
            }
        except Exception as e:
            logger.error(f"Scraper connectivity check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    def check_live(self) -> dict:
        """Liveness check (¿está vivo?)"""
        return {
            "status": "ok",
            "timestamp": time.time(),
        }
    
    def check_ready(self) -> dict:
        """Readiness check (¿está listo para requests?)"""
        redis_health = self.check_redis()
        db_health = self.check_database()
        
        # Sistema listo si Redis y Database OK
        ready = (
            redis_health.get("status") == "ok" and
            db_health.get("status") == "ok"
        )
        
        return {
            "status": "ok" if ready else "degraded",
            "ready": ready,
            "components": {
                "redis": redis_health,
                "database": db_health,
            },
        }
    
    def check_full(self) -> dict:
        """Full system health check."""
        return {
            "status": "ok",
            "timestamp": time.time(),
            "checks": {
                "liveness": self.check_live(),
                "readiness": self.check_ready(),
                "scraper": self.check_scraper_connectivity(),
            },
        }
    
    @staticmethod
    def _mask_url(url: str) -> str:
        """Mask sensitive parts of URL."""
        # Mask password in URL
        if "://" in url and "@" in url:
            scheme, rest = url.split("://", 1)
            user_pass, host = rest.split("@", 1)
            return f"{scheme}://***@{host}"
        return url


# Singleton
_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get health checker instance."""
    global _checker
    if _checker is None:
        _checker = HealthChecker()
    return _checker
