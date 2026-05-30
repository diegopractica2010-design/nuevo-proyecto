import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field, field_validator, model_validator

DEVELOPMENT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8001",
]


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = ConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    FRONTEND_DIR: Path = BASE_DIR / "frontend"
    DATA_DIR: Path = BASE_DIR / "data"

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8001")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'radar_precios.db'}")

    # Redis - FASE A
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")

    # Celery - FASE A
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    CELERY_TIMEZONE: str = os.getenv("CELERY_TIMEZONE", "UTC")
    CELERY_ENABLE_UTC: bool = os.getenv("CELERY_ENABLE_UTC", "true").lower() == "true"

    # Rate Limiting - FASE A
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
    AUTH_RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(
        os.getenv("AUTH_RATE_LIMIT_REQUESTS_PER_MINUTE", "120")
    )
    RATE_LIMIT_BURST_SIZE: int = int(os.getenv("RATE_LIMIT_BURST_SIZE", "15"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # CORS
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ORIGINS_RAW: str = Field(default="", validation_alias="CORS_ORIGINS")
    CORS_ORIGINS: list[str] = Field(
        default_factory=list,
        validation_alias="CORS_ORIGINS_LIST",
    )

    @model_validator(mode="after")
    def validate_cors_security(self) -> "Settings":
        configured_origins = _parse_csv(self.CORS_ORIGINS_RAW)
        self.CORS_ORIGINS = configured_origins or DEVELOPMENT_CORS_ORIGINS.copy()
        if self.ENVIRONMENT == "production" and not configured_origins:
            raise RuntimeError("CORS_ORIGINS must be set explicitly in production")
        if self.CORS_ALLOW_CREDENTIALS and "*" in self.CORS_ORIGINS:
            raise ValueError("Wildcard origins cannot be used with credentials")
        return self

    # Search & Scraping
    SEARCH_URL: str = "https://super.lider.cl/search?q={query}"
    SLUG_URL: str = "https://super.lider.cl/v/{slug}"
    AUTOCOMPLETE_URL: str = "https://super.lider.cl/api/autocomplete/v2"
    PRODUCT_BASE_URL: str = "https://super.lider.cl"

    JUMBO_SEARCH_URL: str = "https://www.jumbo.cl/busqueda?ft={query}"
    JUMBO_PRODUCT_BASE_URL: str = "https://www.jumbo.cl"
    JUMBO_API_KEY: str = os.getenv("JUMBO_API_KEY", "")

    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "18"))
    STORE_SSL_VERIFY: bool = os.getenv("STORE_SSL_VERIFY", "false").lower() == "true"
    MAX_RESULTS: int = int(os.getenv("MAX_RESULTS", "200"))
    AUTOCOMPLETE_LIMIT: int = int(os.getenv("AUTOCOMPLETE_LIMIT", "6"))
    SUGGESTION_FALLBACK_LIMIT: int = int(os.getenv("SUGGESTION_FALLBACK_LIMIT", "3"))

    # Legal/compliance guardrails. Strict robots/permission checks are opt-in for
    # local live-price comparisons; enable them in regulated deployments.
    COMPLIANCE_STRICT_MODE: bool = os.getenv("COMPLIANCE_STRICT_MODE", "false").lower() == "true"
    LIVE_STORE_QUERIES_ENABLED: bool = (
        os.getenv("LIVE_STORE_QUERIES_ENABLED", "true").lower() == "true"
    )
    STORE_CRAWLING_ENABLED: bool = os.getenv("STORE_CRAWLING_ENABLED", "false").lower() == "true"
    STORE_ROBOTS_ALLOW_ON_ERROR: bool = (
        os.getenv("STORE_ROBOTS_ALLOW_ON_ERROR", "true").lower() == "true"
    )
    STORE_ACCESS_CONTACT: str = os.getenv("STORE_ACCESS_CONTACT", "")

    # Cache
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "600"))
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
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    )
    ALT_USER_AGENT: str = os.getenv(
        "ALT_USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    )
    CURL_CFFI_USER_AGENT: str = os.getenv(
        "CURL_CFFI_USER_AGENT",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    )

    BROWSER_HEADERS: dict[str, str] = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        "Sec-CH-UA": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    MINIMAL_HEADERS: dict[str, str] = {
        "User-Agent": ALT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }

    API_HEADERS: dict[str, str] = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
        "Content-Type": "application/json",
        "Origin": "https://super.lider.cl",
        "Referer": "https://super.lider.cl/",
        "Sec-CH-UA": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    CURL_CFFI_HEADERS: dict[str, str] = {
        **BROWSER_HEADERS,
        "User-Agent": CURL_CFFI_USER_AGENT,
        "Sec-CH-UA": '"Google Chrome";v="123", "Chromium";v="123", "Not.A/Brand";v="8"',
        "Sec-CH-UA-Platform": '"Linux"',
    }

    HTML_HEADER_PROFILES: tuple = (
        ("minimal", MINIMAL_HEADERS),
        ("browser", BROWSER_HEADERS),
        ("curl_cffi", CURL_CFFI_HEADERS),
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
BASE_URL = settings.BASE_URL
CORS_ORIGINS = settings.CORS_ORIGINS
CORS_ALLOW_CREDENTIALS = settings.CORS_ALLOW_CREDENTIALS
SEARCH_URL = settings.SEARCH_URL
SLUG_URL = settings.SLUG_URL
AUTOCOMPLETE_URL = settings.AUTOCOMPLETE_URL
PRODUCT_BASE_URL = settings.PRODUCT_BASE_URL
JUMBO_SEARCH_URL = settings.JUMBO_SEARCH_URL
JUMBO_PRODUCT_BASE_URL = settings.JUMBO_PRODUCT_BASE_URL
JUMBO_API_KEY = settings.JUMBO_API_KEY
REQUEST_TIMEOUT = settings.REQUEST_TIMEOUT
MAX_RESULTS = settings.MAX_RESULTS
AUTOCOMPLETE_LIMIT = settings.AUTOCOMPLETE_LIMIT
SUGGESTION_FALLBACK_LIMIT = settings.SUGGESTION_FALLBACK_LIMIT
COMPLIANCE_STRICT_MODE = settings.COMPLIANCE_STRICT_MODE
LIVE_STORE_QUERIES_ENABLED = settings.LIVE_STORE_QUERIES_ENABLED
STORE_CRAWLING_ENABLED = settings.STORE_CRAWLING_ENABLED
STORE_ROBOTS_ALLOW_ON_ERROR = settings.STORE_ROBOTS_ALLOW_ON_ERROR
STORE_ACCESS_CONTACT = settings.STORE_ACCESS_CONTACT
STORE_SSL_VERIFY = settings.STORE_SSL_VERIFY
CACHE_TTL_SECONDS = settings.CACHE_TTL_SECONDS
STALE_CACHE_TTL_SECONDS = settings.STALE_CACHE_TTL_SECONDS
REDIS_URL = settings.REDIS_URL
REDIS_PASSWORD = settings.REDIS_PASSWORD
RATE_LIMIT_REQUESTS_PER_MINUTE = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
AUTH_RATE_LIMIT_REQUESTS_PER_MINUTE = settings.AUTH_RATE_LIMIT_REQUESTS_PER_MINUTE
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
