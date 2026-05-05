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
from backend.compliance import assert_live_store_access_allowed
from backend.parser import parse_catalog_page


QUERY_STOPWORDS = {
    "de",
    "del",
    "la",
    "las",
    "el",
    "los",
    "un",
    "una",
    "unos",
    "unas",
    "saco",
    "bolsa",
    "paquete",
    "pack",
}

CHARCOAL_TERMS = {"briqueta", "briquetas", "vegetal", "quincho", "quebracho", "espino"}


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


def fallback_query_variants(query: str) -> list[str]:
    normalized = normalize_query(query)
    ascii_query = unicode_normalize("NFKD", normalized).encode("ascii", "ignore").decode("ascii")
    variants: list[str] = []
    seen = {normalized.lower()}

    def add(value: str) -> None:
        cleaned = normalize_query(value)
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            variants.append(cleaned)

    if ascii_query.lower() != normalized.lower():
        add(ascii_query)

    tokens = [token for token in ascii_query.lower().split() if token not in QUERY_STOPWORDS]
    if tokens:
        add(" ".join(tokens))
        if len(tokens) > 1:
            add(tokens[-1])

    if "tallarines" in ascii_query.lower():
        add(ascii_query.lower().replace("tallarines", "tallarin"))
        add("tallarin")

    return variants


def _rank_text(value: Any) -> str:
    text = unicode_normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return text.lower()


def rank_products_for_query(products: list[dict], query: str) -> list[dict]:
    ascii_query = _rank_text(query)
    tokens = [token for token in ascii_query.split() if token not in QUERY_STOPWORDS]
    if not tokens:
        return products

    def score(product: dict) -> int:
        haystack = _rank_text(
            " ".join(
                str(product.get(key) or "")
                for key in ("name", "brand", "category", "seller")
            )
        )
        value = sum(10 for token in tokens if token in haystack)
        if all(token in haystack for token in tokens):
            value += 20
        if "carbon" in tokens and any(term in haystack for term in CHARCOAL_TERMS):
            value += 8
        return value

    return sorted(products, key=score, reverse=True)


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
    assert_live_store_access_allowed(
        "lider",
        f"{AUTOCOMPLETE_URL}?term={quote_plus(normalized_query)}",
        purpose="search",
    )
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


def _with_page(url: str, page: int) -> str:
    if page <= 1:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}page={page}"


def _product_key(product: dict) -> str:
    return (
        str(product.get("sku") or product.get("id") or product.get("url") or "")
        or f"{product.get('name')}::{product.get('price')}"
    )


def _candidate_pages(query: str, page: int = 1) -> list[tuple[str, str, dict[str, str]]]:
    slug = _slugify_query(query)
    search_url = _with_page(SEARCH_URL.format(query=quote_plus(query)), page)
    slug_url = SLUG_URL.format(slug=slug)

    candidates: list[tuple[str, str, dict[str, str]]] = []
    for profile_name, headers in HTML_HEADER_PROFILES:
        candidates.append((f"search:{profile_name}:page:{page}", search_url, headers))

    if page == 1:
        candidates.append(("slug:browser", slug_url, HTML_HEADER_PROFILES[0][1]))
    return candidates


def _fetch_catalog_page(query: str, page: int, limit: int) -> ScrapedSearchResult:
    normalized_query = normalize_query(query)
    attempts: list[str] = []
    had_catalog_response = False

    for strategy_name, url, headers in _candidate_pages(normalized_query, page):
        try:
            assert_live_store_access_allowed("lider", url, purpose="search")
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


def _execute_catalog_query(query: str, limit: int) -> ScrapedSearchResult:
    normalized_query = normalize_query(query)
    products: list[dict] = []
    seen: set[str] = set()
    source_url: str | None = None
    fetch_strategies: list[str] = []
    parse_strategy: str | None = None
    page = 1

    while len(products) < limit:
        try:
            page_result = _fetch_catalog_page(normalized_query, page, limit)
        except (NoResultsError, ScraperError):
            if products:
                break
            raise
        page_products = page_result.products
        new_count = 0

        for product in page_products:
            key = _product_key(product)
            if key in seen:
                continue
            seen.add(key)
            product = dict(product)
            product["position"] = len(products) + 1
            products.append(product)
            new_count += 1
            if len(products) >= limit:
                break

        source_url = source_url or page_result.source_url
        fetch_strategies.append(page_result.fetch_strategy)
        parse_strategy = parse_strategy or page_result.parse_strategy

        if not page_products or new_count == 0:
            break
        page += 1

    if not products:
        raise NoResultsError(normalized_query)

    ranked_products = rank_products_for_query(products[:limit], normalized_query)

    return ScrapedSearchResult(
        query=normalized_query,
        applied_query=normalized_query,
        products=ranked_products,
        source_url=source_url or SEARCH_URL.format(query=quote_plus(normalized_query)),
        fetch_strategy=" + ".join(fetch_strategies),
        parse_strategy=parse_strategy or "unknown",
    )


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

        query_variants = fallback_query_variants(normalized_query)
        for term in [*query_variants, *fallback_terms]:
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
