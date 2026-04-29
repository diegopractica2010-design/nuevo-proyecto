"""Celery application configuration and initialization."""

from __future__ import annotations

import logging
from celery import Celery
from celery.schedules import crontab

from backend.config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    CELERY_TIMEZONE,
    CELERY_ENABLE_UTC,
)

logger = logging.getLogger(__name__)

# Create Celery instance
celery_app = Celery(
    "radar_precios",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["backend.tasks", "backend.tasks.scrape_tasks"],
)

# Configure Celery
celery_app.conf.update(
    timezone=CELERY_TIMEZONE,
    enable_utc=CELERY_ENABLE_UTC,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=30 * 60,  # Hard limit: 30 minutes
    task_soft_time_limit=25 * 60,  # Soft limit: 25 minutes
    worker_prefetch_multiplier=1,  # Don't prefetch multiple tasks
    worker_max_tasks_per_child=1000,  # Recycle worker after 1000 tasks
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_timeout=1,
    broker_connection_max_retries=10,
)

# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    # Placeholder: Add scheduled tasks later (e.g., daily scraping, backups)
    # "backup-database-daily": {
    #     "task": "backend.tasks.backup_database",
    #     "schedule": crontab(hour=2, minute=0),  # 2 AM daily
    # },
}


@celery_app.task(bind=True, max_retries=3)
def debug_task(self):
    """Debug task to verify Celery setup."""
    try:
        logger.info(f"Debug task executed. Request: {self.request}")
        return {"status": "ok", "task_id": self.request.id}
    except Exception as exc:
        logger.error(f"Debug task failed: {exc}")
        raise self.retry(exc=exc, countdown=10)


def init_celery():
    """Initialize Celery (called from main.py)."""
    logger.info("Celery initialized with broker: %s", CELERY_BROKER_URL)
