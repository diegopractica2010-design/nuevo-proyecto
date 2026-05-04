"""Celery task package.

Legacy task imports are kept here so existing code can continue using
``from backend.tasks import ...`` after moving from ``backend/tasks.py``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from backend.celery_app import celery_app, debug_task
from backend.scraper import NoResultsError, ScraperError, search_lider
from backend.scraper_jumbo import search_jumbo

logger = logging.getLogger(__name__)

__all__ = [
    "backup_database",
    "celery_app",
    "cleanup_cache",
    "debug_task",
    "monitor_parser_changes",
    "monitor_scraper_health",
    "schedule_backups",
    "scrape_lider",
    "search_jumbo_async",
    "search_lider_async",
]


@celery_app.task(bind=True, max_retries=3, name="backend.tasks.search_lider_async")
def search_lider_async(self, query: str, limit: int = 36) -> dict:
    try:
        result = search_lider(query=query, limit=limit)
        return {
            "status": "success",
            "query": result.query,
            "applied_query": result.applied_query,
            "products": [p.__dict__ if hasattr(p, "__dict__") else p for p in result.products],
            "source_url": result.source_url,
            "fetch_strategy": result.fetch_strategy,
            "parse_strategy": result.parse_strategy,
            "suggestions": result.suggestions,
            "warning": result.warning,
        }
    except NoResultsError as exc:
        return {"status": "no_results", "query": query, "suggestions": exc.suggestions, "error": str(exc)}
    except ScraperError as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=5)
        return {"status": "error", "query": query, "error": str(exc)}
    except Exception as exc:
        logger.error("Unexpected Lider task error: %s", exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=10)
        return {"status": "error", "query": query, "error": str(exc)}


@celery_app.task(bind=True, max_retries=3, name="backend.tasks.search_jumbo_async")
def search_jumbo_async(self, query: str, limit: int = 36) -> dict:
    try:
        result = search_jumbo(query=query, limit=limit)
        return {
            "status": "success",
            "query": result.query,
            "applied_query": result.applied_query,
            "products": [p if isinstance(p, dict) else p.__dict__ for p in result.products],
            "source_url": result.source_url,
            "fetch_strategy": result.fetch_strategy,
            "parse_strategy": result.parse_strategy,
        }
    except NoResultsError as exc:
        return {"status": "no_results", "query": query, "error": str(exc)}
    except ScraperError as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=5)
        return {"status": "error", "query": query, "error": str(exc)}
    except Exception as exc:
        logger.error("Unexpected Jumbo task error: %s", exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=10)
        return {"status": "error", "query": query, "error": str(exc)}


@celery_app.task(bind=True, name="backend.tasks.backup_database")
def backup_database(self) -> dict:
    try:
        from backend.backup import BackupManager

        manager = BackupManager()
        results = manager.backup_all()
        logger.info("Backup completado: %s", results)
        return {
            "status": "success",
            "timestamp": datetime.now(UTC).isoformat(),
            "results": results,
        }
    except Exception as exc:
        logger.error("Backup fallido: %s", exc, exc_info=True)
        return {
            "status": "error",
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(exc),
        }


@celery_app.task(bind=True, name="backend.tasks.monitor_parser_changes")
def monitor_parser_changes(self) -> dict:
    try:
        from backend.parser_monitor import monitor_html_changes

        return monitor_html_changes()
    except Exception as exc:
        logger.error("Parser monitoring task failed: %s", exc, exc_info=True)
        return {"status": "error", "error": str(exc)}


@celery_app.task(bind=True, name="backend.tasks.cleanup_cache")
def cleanup_cache(self) -> dict:
    try:
        from backend.infrastructure.cache.cache import _get_client

        client = _get_client()
        pattern = "api:search:*"
        keys = client.keys(pattern)
        deleted = client.delete(*keys) if keys else 0
        logger.info("Cache limpiado: %d claves eliminadas", deleted)
        return {
            "status": "success",
            "timestamp": datetime.now(UTC).isoformat(),
            "deleted_keys": int(deleted),
        }
    except Exception as exc:
        logger.error("Cleanup de cache fallido: %s", exc, exc_info=True)
        return {
            "status": "error",
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(exc),
        }


def schedule_backups() -> None:
    logger.info("Backup scheduling is configured through Celery beat.")


from backend.tasks.scrape_tasks import monitor_scraper_health, scrape_lider  # noqa: E402,F401
