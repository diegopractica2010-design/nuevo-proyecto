import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

SEARCH_URL = "https://super.lider.cl/search?q={query}"
SLUG_URL = "https://super.lider.cl/v/{slug}"
AUTOCOMPLETE_URL = "https://super.lider.cl/api/autocomplete/v2"
PRODUCT_BASE_URL = "https://super.lider.cl"

# Jumbo URLs
JUMBO_SEARCH_URL = "https://www.jumbo.cl/busqueda?ft={query}"
JUMBO_PRODUCT_BASE_URL = "https://www.jumbo.cl"

REQUEST_TIMEOUT = 18
MAX_RESULTS = 48
AUTOCOMPLETE_LIMIT = 6
SUGGESTION_FALLBACK_LIMIT = 3
CACHE_TTL_SECONDS = 180
STALE_CACHE_TTL_SECONDS = 1800

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Celery configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

USER_AGENT = "Mozilla/5.0"

BROWSER_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

MINIMAL_HEADERS = {
    "User-Agent": USER_AGENT,
}

API_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
}

HTML_HEADER_PROFILES = (
    ("minimal", MINIMAL_HEADERS),
    ("browser", BROWSER_HEADERS),
)
