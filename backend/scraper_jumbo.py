from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
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
    SUGGESTION_FALLBACK_LIMIT,
)
from backend.parser import parse_catalog_page


class ScraperError(RuntimeError):
    pass


class NoResultsError(ScraperError):
    def __init__(self, query: str, *, attempts: list[str] | None = None, suggestions: list[str] | None = None):
        super().__init__(f'No se encontraron productos para "{query}"')
        self.query = query
        self.attempts = attempts or []
        self.suggestions = suggestions or []


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

    for profile_name, headers in HTML_HEADER_PROFILES:
        try:
            response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            search_page = SearchPage(
                query=query,
                html=response.text,
                url=url,
                strategy=f"search:{profile_name}",
            )

            products = parse_catalog_page(search_page, limit=limit, base_url=JUMBO_PRODUCT_BASE_URL)
            if products:
                return ScrapedSearchResult(
                    query=query,
                    applied_query=query,
                    products=products,
                    source_url=url,
                    fetch_strategy=f"search:{profile_name}",
                    parse_strategy="next_data",  # Assuming similar structure to Lider
                )
        except Exception as exc:
            continue

    raise NoResultsError(query)


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