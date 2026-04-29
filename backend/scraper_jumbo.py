from __future__ import annotations

from dataclasses import dataclass
from unicodedata import normalize as unicode_normalize
from urllib.parse import quote_plus

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.config import (
    HTML_HEADER_PROFILES,
    JUMBO_PRODUCT_BASE_URL,
    JUMBO_SEARCH_URL,
    REQUEST_TIMEOUT,
)
from backend.parser import parse_catalog_page
from backend.scraper import NoResultsError


@dataclass(slots=True)
class SearchPage:
    query: str
    html: str
    url: str
    strategy: str


@dataclass(slots=True)
class ScrapedSearchResult:
    query: str
    applied_query: str
    products: list[dict]
    source_url: str
    fetch_strategy: str = "search:browser"
    parse_strategy: str = "next_data"


def _create_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _execute_catalog_query(session: requests.Session, query: str, limit: int) -> ScrapedSearchResult:
    """Execute a catalog search query for Jumbo."""
    url = JUMBO_SEARCH_URL.format(query=quote_plus(query))

    attempts: list[str] = []

    for profile_name, headers in HTML_HEADER_PROFILES:
        try:
            response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            parsed = parse_catalog_page(
                response.text,
                limit=limit,
                base_url=JUMBO_PRODUCT_BASE_URL,
            )
            if parsed.products:
                return ScrapedSearchResult(
                    query=query,
                    applied_query=query,
                    products=parsed.products,
                    source_url=response.url,
                    fetch_strategy=f"search:{profile_name}",
                    parse_strategy=parsed.parser or "unknown",
                )
        except Exception as exc:
            attempts.append(f"search:{profile_name}: {exc}")
            continue

    raise NoResultsError(query, attempts=attempts)


def search_jumbo(query: str, limit: int = 24) -> ScrapedSearchResult:
    """Search for products on Jumbo.cl."""
    normalized_query = normalize_query(query)

    with _create_session() as session:
        try:
            return _execute_catalog_query(session, normalized_query, limit)
        except NoResultsError:
            # For Jumbo, we might not have suggestions like Lider, so just re-raise
            raise


def normalize_query(query: str) -> str:
    """Normalize search query."""
    return unicode_normalize("NFC", query.strip().lower())
