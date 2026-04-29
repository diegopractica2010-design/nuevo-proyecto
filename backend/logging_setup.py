"""Centralized logging configuration (Fase A)."""

from __future__ import annotations

import logging
import logging.config
import sys
import json
from datetime import datetime
from pathlib import Path

from backend.config import LOG_LEVEL, ENVIRONMENT, DATA_DIR, SENTRY_DSN, SENTRY_ENVIRONMENT


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": ENVIRONMENT,
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging():
    """Configure logging for the application."""
    
    # Create logs directory
    logs_dir = DATA_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Logging configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "json": {
                "()": JSONFormatter,
            },
            "detailed": {
                "format": (
                    "%(asctime)s - %(name)s - %(levelname)s - "
                    "[%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s"
                )
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": LOG_LEVEL,
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": LOG_LEVEL,
                "formatter": "json",
                "filename": logs_dir / "app.log",
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 10,
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": logs_dir / "errors.log",
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 5,
            },
            "scraper_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": logs_dir / "scraper.log",
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 10,
            },
        },
        "loggers": {
            "backend": {
                "level": LOG_LEVEL,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "backend.scraper": {
                "level": LOG_LEVEL,
                "handlers": ["console", "scraper_file", "error_file"],
                "propagate": False,
            },
            "backend.scraper_jumbo": {
                "level": LOG_LEVEL,
                "handlers": ["console", "scraper_file", "error_file"],
                "propagate": False,
            },
            "backend.search_service": {
                "level": LOG_LEVEL,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "backend.rate_limiter": {
                "level": LOG_LEVEL,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "backend.celery_app": {
                "level": LOG_LEVEL,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "celery": {
                "level": LOG_LEVEL,
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
        "root": {
            "level": LOG_LEVEL,
            "handlers": ["console", "file", "error_file"],
        },
    }
    
    logging.config.dictConfig(config)
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Environment: {ENVIRONMENT}, Level: {LOG_LEVEL}")
    
    # Setup Sentry (if DSN provided)
    if SENTRY_DSN:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
            from sentry_sdk.integrations.celery import CeleryIntegration
            from sentry_sdk.integrations.logging import LoggingIntegration
            
            sentry_sdk.init(
                dsn=SENTRY_DSN,
                environment=SENTRY_ENVIRONMENT,
                integrations=[
                    FastApiIntegration(),
                    SqlalchemyIntegration(),
                    CeleryIntegration(),
                    LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
                ],
                traces_sample_rate=0.1,
                send_default_pii=False,
            )
            logger.info("Sentry initialized")
        except ImportError:
            logger.warning("Sentry SDK not installed. Skipping Sentry integration.")
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
