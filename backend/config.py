import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = ConfigDict(env_file=".env", case_sensitive=True)
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    FRONTEND_DIR: Path = BASE_DIR / "frontend"
    DATA_DIR: Path = BASE_DIR / "data"
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{DATA_DIR / 'radar_precios.db'}"
    )
    
    # Redis - FASE A
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    
    # Celery - FASE A
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    CELERY_TIMEZONE: str = os.getenv("CELERY_TIMEZONE", "UTC")
    CELERY_ENABLE_UTC: bool = os.getenv("CELERY_ENABLE_UTC", "true").lower() == "true"
    
    # Rate Limiting - FASE A
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "10"))
    RATE_LIMIT_BURST_SIZE: int = int(os.getenv("RATE_LIMIT_BURST_SIZE", "15"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    
    # CORS
    _CORS_ENV = os.getenv("CORS_ORIGINS", "")
    CORS_ORIGINS: list[str] = (
        [origin.strip() for origin in _CORS_ENV.split(",") if origin.strip()]
        if _CORS_ENV
        else [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:8001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:8001",
        ]
    )
    
    # Search & Scraping
    SEARCH_URL: str = "https://super.lider.cl/search?q={query}"
    SLUG_URL: str = "https://super.lider.cl/v/{slug}"
    AUTOCOMPLETE_URL: str = "https://super.lider.cl/api/autocomplete/v2"
    PRODUCT_BASE_URL: str = "https://super.lider.cl"
    
    JUMBO_SEARCH_URL: str = "https://www.jumbo.cl/busqueda?ft={query}"
    JUMBO_PRODUCT_BASE_URL: str = "https://www.jumbo.cl"
    
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "18"))
    MAX_RESULTS: int = int(os.getenv("MAX_RESULTS", "200"))
    AUTOCOMPLETE_LIMIT: int = int(os.getenv("AUTOCOMPLETE_LIMIT", "6"))
    SUGGESTION_FALLBACK_LIMIT: int = int(os.getenv("SUGGESTION_FALLBACK_LIMIT", "3"))
    
    # Cache
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "180"))
    STALE_CACHE_TTL_SECONDS: int = int(os.getenv("STALE_CACHE_TTL_SECONDS", "1800"))
    
    # Monitoring & Logging - FASE A
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    SENTRY_ENVIRONMENT: str = os.getenv("SENTRY_ENVIRONMENT", ENVIRONMENT)
    SENTRY_TRACE_SAMPLE_RATE: float = float(os.getenv("SENTRY_TRACE_SAMPLE_RATE", "0.1"))
    
    # Backup - FASE A
    BACKUP_ENABLED: bool = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
    BACKUP_INTERVAL_HOURS: int = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
    BACKUP_PATH: str = os.getenv("BACKUP_PATH", "./data/backups")
    
    # FASE 4: Prometheus Metrics
    PROMETHEUS_ENABLED: bool = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"
    PROMETHEUS_PORT: int = int(os.getenv("PROMETHEUS_PORT", "9090"))
    PROMETHEUS_RETENTION_SECONDS: int = int(os.getenv("PROMETHEUS_RETENTION_SECONDS", "604800"))
    
    # FASE 4: AWS (for backups and deployment)
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET", "")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    
    # FASE 4: SMTP for email alerts
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "alerts@radar.com")
    ALERT_EMAIL_RECIPIENTS: list[str] = (
        [email.strip() for email in os.getenv("ALERT_EMAIL_RECIPIENTS", "").split(",")]
        if os.getenv("ALERT_EMAIL_RECIPIENTS")
        else []
    )
    
    # FASE 4: Slack notifications
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    SLACK_CHANNEL: str = os.getenv("SLACK_CHANNEL", "#alerts")
    
    # FASE 4: PagerDuty integration
    PAGERDUTY_INTEGRATION_KEY: str = os.getenv("PAGERDUTY_INTEGRATION_KEY", "")
    
    # Headers for scraping
    USER_AGENT: str = "Mozilla/5.0"
    
    BROWSER_HEADERS: dict[str, str] = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    
    MINIMAL_HEADERS: dict[str, str] = {
        "User-Agent": USER_AGENT,
    }
    
    API_HEADERS: dict[str, str] = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    
    HTML_HEADER_PROFILES: tuple = (
        ("minimal", MINIMAL_HEADERS),
        ("browser", BROWSER_HEADERS),
    )
    
    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return True
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug", "development"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "production"}:
            return False
        return False


# Singleton instance
_settings: Settings | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Legacy module-level exports (for backward compatibility)
settings = get_settings()

BASE_DIR = settings.BASE_DIR
FRONTEND_DIR = settings.FRONTEND_DIR
DATA_DIR = settings.DATA_DIR
DATABASE_URL = settings.DATABASE_URL
ENVIRONMENT = settings.ENVIRONMENT
DEBUG = settings.DEBUG
LOG_LEVEL = settings.LOG_LEVEL
CORS_ORIGINS = settings.CORS_ORIGINS
SEARCH_URL = settings.SEARCH_URL
SLUG_URL = settings.SLUG_URL
AUTOCOMPLETE_URL = settings.AUTOCOMPLETE_URL
PRODUCT_BASE_URL = settings.PRODUCT_BASE_URL
JUMBO_SEARCH_URL = settings.JUMBO_SEARCH_URL
JUMBO_PRODUCT_BASE_URL = settings.JUMBO_PRODUCT_BASE_URL
REQUEST_TIMEOUT = settings.REQUEST_TIMEOUT
MAX_RESULTS = settings.MAX_RESULTS
AUTOCOMPLETE_LIMIT = settings.AUTOCOMPLETE_LIMIT
SUGGESTION_FALLBACK_LIMIT = settings.SUGGESTION_FALLBACK_LIMIT
CACHE_TTL_SECONDS = settings.CACHE_TTL_SECONDS
STALE_CACHE_TTL_SECONDS = settings.STALE_CACHE_TTL_SECONDS
REDIS_URL = settings.REDIS_URL
REDIS_PASSWORD = settings.REDIS_PASSWORD
RATE_LIMIT_REQUESTS_PER_MINUTE = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
RATE_LIMIT_BURST_SIZE = settings.RATE_LIMIT_BURST_SIZE
RATE_LIMIT_WINDOW_SECONDS = settings.RATE_LIMIT_WINDOW_SECONDS
CELERY_BROKER_URL = settings.CELERY_BROKER_URL
CELERY_RESULT_BACKEND = settings.CELERY_RESULT_BACKEND
CELERY_TIMEZONE = settings.CELERY_TIMEZONE
CELERY_ENABLE_UTC = settings.CELERY_ENABLE_UTC
SENTRY_DSN = settings.SENTRY_DSN
SENTRY_ENVIRONMENT = settings.SENTRY_ENVIRONMENT
SENTRY_TRACE_SAMPLE_RATE = settings.SENTRY_TRACE_SAMPLE_RATE
USER_AGENT = settings.USER_AGENT
BROWSER_HEADERS = settings.BROWSER_HEADERS

# FASE 4 exports
BACKUP_ENABLED = settings.BACKUP_ENABLED
BACKUP_INTERVAL_HOURS = settings.BACKUP_INTERVAL_HOURS
BACKUP_PATH = settings.BACKUP_PATH
PROMETHEUS_ENABLED = settings.PROMETHEUS_ENABLED
PROMETHEUS_PORT = settings.PROMETHEUS_PORT
PROMETHEUS_RETENTION_SECONDS = settings.PROMETHEUS_RETENTION_SECONDS
AWS_REGION = settings.AWS_REGION
AWS_S3_BUCKET = settings.AWS_S3_BUCKET
AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY
SMTP_HOST = settings.SMTP_HOST
SMTP_PORT = settings.SMTP_PORT
SMTP_USER = settings.SMTP_USER
SMTP_PASSWORD = settings.SMTP_PASSWORD
SMTP_FROM = settings.SMTP_FROM
ALERT_EMAIL_RECIPIENTS = settings.ALERT_EMAIL_RECIPIENTS
SLACK_WEBHOOK_URL = settings.SLACK_WEBHOOK_URL
SLACK_CHANNEL = settings.SLACK_CHANNEL
PAGERDUTY_INTEGRATION_KEY = settings.PAGERDUTY_INTEGRATION_KEY
MINIMAL_HEADERS = settings.MINIMAL_HEADERS
API_HEADERS = settings.API_HEADERS
HTML_HEADER_PROFILES = settings.HTML_HEADER_PROFILES
