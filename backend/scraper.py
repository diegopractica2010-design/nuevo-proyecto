from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unicodedata import normalize as unicode_normalize
from urllib.parse import quote_plus

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.config import (
    API_HEADERS,
    AUTOCOMPLETE_LIMIT,
    AUTOCOMPLETE_URL,
    HTML_HEADER_PROFILES,
    REQUEST_TIMEOUT,
    SEARCH_URL,
    SLUG_URL,
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
    fetch_strategy: str
    parse_strategy: str
    suggestions: list[str] = field(default_factory=list)
    warning: str | None = None


def _build_session(headers: dict[str, str]) -> requests.Session:
    retry_strategy = Retry(
        total=2,
        read=2,
        connect=2,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=4, pool_maxsize=4)

    session = requests.Session()
    session.headers.update(headers)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def normalize_query(query: str) -> str:
    normalized = " ".join((query or "").split()).strip()
    if not normalized:
        raise ScraperError("La consulta está vacía")
    return normalized


def _slugify_query(query: str) -> str:
    ascii_query = unicode_normalize("NFKD", query).encode("ascii", "ignore").decode("ascii")
    return "-".join(part for part in ascii_query.lower().split() if part)


def _is_blocked_page(html: str) -> bool:
    markers = (
        "Robot or human?",
        "px-captcha",
        "Press and hold",
        "Access to this page has been denied",
    )
    return any(marker in html for marker in markers)


def _request_text(url: str, headers: dict[str, str]) -> tuple[str, str]:
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text, response.url


def fetch_autocomplete_terms(query: str) -> list[str]:
    normalized_query = normalize_query(query)
    session = _build_session(API_HEADERS)
    try:
        response = session.get(
            AUTOCOMPLETE_URL,
            params={"term": normalized_query},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload: Any = response.json()
    except Exception:
        return []
    finally:
        session.close()

    if not isinstance(payload, dict):
        return []

    terms = payload.get("terms")
    if not isinstance(terms, list):
        return []

    unique_terms: list[str] = []
    seen: set[str] = set()
    for raw_term in terms:
        term = normalize_query(str(raw_term))
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_terms.append(term)
        if len(unique_terms) >= AUTOCOMPLETE_LIMIT:
            break

    return unique_terms


def _candidate_pages(query: str) -> list[tuple[str, str, dict[str, str]]]:
    slug = _slugify_query(query)
    search_url = SEARCH_URL.format(query=quote_plus(query))
    slug_url = SLUG_URL.format(slug=slug)

    candidates: list[tuple[str, str, dict[str, str]]] = []
    for profile_name, headers in HTML_HEADER_PROFILES:
        candidates.append((f"search:{profile_name}", search_url, headers))

    candidates.append(("slug:browser", slug_url, HTML_HEADER_PROFILES[0][1]))
    return candidates


def _execute_catalog_query(query: str, limit: int) -> ScrapedSearchResult:
    normalized_query = normalize_query(query)
    attempts: list[str] = []
    had_catalog_response = False

    for strategy_name, url, headers in _candidate_pages(normalized_query):
        try:
            html, resolved_url = _request_text(url, headers)
            if _is_blocked_page(html):
                attempts.append(f"{strategy_name}: bloqueado por anti-bot")
                continue

            had_catalog_response = True
            parsed = parse_catalog_page(html, limit=limit)
            if parsed.products:
                return ScrapedSearchResult(
                    query=normalized_query,
                    applied_query=normalized_query,
                    products=parsed.products[:limit],
                    source_url=resolved_url,
                    fetch_strategy=strategy_name,
                    parse_strategy=parsed.parser or "unknown",
                )

            attempts.append(f"{strategy_name}: sin productos parseables")
        except Exception as exc:
            attempts.append(f"{strategy_name}: {exc}")

    if had_catalog_response:
        raise NoResultsError(normalized_query, attempts=attempts)

    raise ScraperError(" | ".join(attempts) or "Lider no respondió con una página utilizable")


def search_lider(query: str, limit: int) -> ScrapedSearchResult:
    normalized_query = normalize_query(query)
    suggestions = fetch_autocomplete_terms(normalized_query)

    try:
        result = _execute_catalog_query(normalized_query, limit)
        result.suggestions = suggestions
        return result
    except NoResultsError as exc:
        fallback_terms = [
            term
            for term in suggestions
            if term.lower() != normalized_query.lower()
        ][:SUGGESTION_FALLBACK_LIMIT]

        for term in fallback_terms:
            try:
                rescued = _execute_catalog_query(term, limit)
                rescued.suggestions = suggestions
                rescued.warning = (
                    f'No hubo coincidencias directas para "{normalized_query}". '
                    f'Se muestran resultados reales para "{term}".'
                )
                rescued.applied_query = term
                return rescued
            except ScraperError:
                continue

        raise NoResultsError(
            normalized_query,
            attempts=exc.attempts,
            suggestions=suggestions,
        ) from exc
