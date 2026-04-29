"""Celery tasks for async scraping and maintenance operations."""

from __future__ import annotations

import logging
from datetime import datetime

from backend.celery_app import celery_app
from backend.scraper import search_lider, NoResultsError, ScraperError
from backend.scraper_jumbo import search_jumbo

logger = logging.getLogger(__name__)


# ============================================================================
# SCRAPING TASKS
# ============================================================================

@celery_app.task(bind=True, max_retries=3, name="backend.tasks.search_lider_async")
def search_lider_async(self, query: str, limit: int = 36) -> dict:
    """
    Async task to search products on Lider.
    Called from search_products() when cache misses or on fallback.
    """
    try:
        logger.info(f"[Celery Task] search_lider_async started: query={query}, limit={limit}")
        result = search_lider(query=query, limit=limit)
        logger.info(f"[Celery Task] search_lider_async completed: found {len(result.products)} products")
        return {
            "status": "success",
            "query": result.query,
            "applied_query": result.applied_query,
            "products": [p.__dict__ if hasattr(p, '__dict__') else p for p in result.products],
            "source_url": result.source_url,
            "fetch_strategy": result.fetch_strategy,
            "parse_strategy": result.parse_strategy,
            "suggestions": result.suggestions,
            "warning": result.warning,
        }
    except NoResultsError as e:
        logger.warning(f"[Celery Task] No results for query: {query}. Suggestions: {e.suggestions}")
        return {
            "status": "no_results",
            "query": query,
            "suggestions": e.suggestions,
            "error": str(e),
        }
    except ScraperError as e:
        logger.error(f"[Celery Task] Scraper error: {e}")
        if self.request.retries < self.max_retries:
            logger.info(f"[Celery Task] Retrying... (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=5)  # Retry after 5 seconds
        return {
            "status": "error",
            "query": query,
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"[Celery Task] Unexpected error: {e}", exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=10)
        return {
            "status": "error",
            "query": query,
            "error": str(e),
        }


@celery_app.task(bind=True, max_retries=3, name="backend.tasks.search_jumbo_async")
def search_jumbo_async(self, query: str, limit: int = 36) -> dict:
    """
    Async task to search products on Jumbo.
    Called from search_products() when cache misses or on fallback.
    """
    try:
        logger.info(f"[Celery Task] search_jumbo_async started: query={query}, limit={limit}")
        result = search_jumbo(query=query, limit=limit)
        logger.info(f"[Celery Task] search_jumbo_async completed: found {len(result.products)} products")
        return {
            "status": "success",
            "query": result.query,
            "applied_query": result.applied_query,
            "products": [p if isinstance(p, dict) else p.__dict__ for p in result.products],
            "source_url": result.source_url,
            "fetch_strategy": result.fetch_strategy,
            "parse_strategy": result.parse_strategy,
        }
    except NoResultsError as e:
        logger.warning(f"[Celery Task] No results for Jumbo query: {query}")
        return {
            "status": "no_results",
            "query": query,
            "error": str(e),
        }
    except ScraperError as e:
        logger.error(f"[Celery Task] Jumbo scraper error: {e}")
        if self.request.retries < self.max_retries:
            logger.info(f"[Celery Task] Retrying... (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=5)
        return {
            "status": "error",
            "query": query,
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"[Celery Task] Unexpected error in search_jumbo: {e}", exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=10)
        return {
            "status": "error",
            "query": query,
            "error": str(e),
        }


# ============================================================================
# MAINTENANCE TASKS (placeholder for future implementation)
# ============================================================================

@celery_app.task(bind=True, name="backend.tasks.backup_database")
def backup_database(self) -> dict:
    """
    Periodic task: Backup database (SQLite or PostgreSQL).
    Scheduled: Daily at 2 AM (see celery_app.conf.beat_schedule)
    """
    try:
        logger.info("[Celery Task] backup_database started")
        # TODO: Implement backup logic (S3, GCS, or local backup)
        logger.info("[Celery Task] backup_database completed")
        return {"status": "success", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"[Celery Task] Backup failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


@celery_app.task(bind=True, name="backend.tasks.monitor_parser_changes")
def monitor_parser_changes(self) -> dict:
    """
    Periodic task: Monitor HTML structure changes in Lider/Jumbo.
    Scheduled: Every 6 hours (to be added to beat_schedule)
    
    If HTML structure changes significantly, alerts and marks parser as "needs review".
    """
    try:
        from backend.parser_monitor import monitor_html_changes
        logger.info("[Celery Task] monitor_parser_changes started")
        result = monitor_html_changes()
        logger.info("[Celery Task] monitor_parser_changes completed")
        return result
    except Exception as e:
        logger.error(f"[Celery Task] Parser monitoring failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


@celery_app.task(bind=True, name="backend.tasks.cleanup_cache")
def cleanup_cache(self) -> dict:
    """
    Periodic task: Clean expired cache entries.
    Scheduled: Every hour (to be added to beat_schedule)
    """
    try:
        logger.info("[Celery Task] cleanup_cache started")
        # TODO: Implement Redis cleanup logic
        logger.info("[Celery Task] cleanup_cache completed")
        return {"status": "success", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"[Celery Task] Cache cleanup failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
