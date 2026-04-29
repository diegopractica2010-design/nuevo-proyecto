from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import logging
from threading import Thread
from threading import Lock

from backend.config import CACHE_TTL_SECONDS, MAX_RESULTS, STALE_CACHE_TTL_SECONDS
from backend.models import (
    FacetValue,
    PriceRange,
    Product,
    SearchFacets,
    SearchResponse,
    SearchStats,
)
from backend.scraper import normalize_query
from backend.store_adapters import get_store_adapter
from backend.tasks import search_jumbo_async
from backend.tasks.scrape_tasks import scrape_lider


logger = logging.getLogger(__name__)


class SearchServiceError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass(slots=True)
class CacheEntry:
    response: SearchResponse
    fresh_until: datetime
    stale_until: datetime


_CACHE: dict[str, CacheEntry] = {}
_CACHE_LOCK = Lock()


def clear_search_cache():
    with _CACHE_LOCK:
        _CACHE.clear()


def _cache_key(store: str, query: str, limit: int) -> str:
    return f"{store}:{query}::{limit}"


def _clone_response(response: SearchResponse, *, cached: bool, warning: str | None = None) -> SearchResponse:
    cloned = response.model_copy(deep=True)
    cloned.cached = cached
    cloned.warning = warning or cloned.warning
    return cloned


def _get_cache(store: str, query: str, limit: int, *, allow_stale: bool) -> SearchResponse | None:
    with _CACHE_LOCK:
        entry = _CACHE.get(_cache_key(store, query, limit))

    if not entry:
        return None

    now = datetime.now(UTC)
    if entry.fresh_until > now:
        return _clone_response(entry.response, cached=True)

    if allow_stale and entry.stale_until > now:
        return _clone_response(entry.response, cached=True)

    return None


def _set_cache(store: str, query: str, limit: int, response: SearchResponse):
    now = datetime.now(UTC)
    with _CACHE_LOCK:
        _CACHE[_cache_key(store, query, limit)] = CacheEntry(
            response=response.model_copy(deep=True),
            fresh_until=now + timedelta(seconds=CACHE_TTL_SECONDS),
            stale_until=now + timedelta(seconds=STALE_CACHE_TTL_SECONDS),
        )


def _build_facets(products: list[Product]) -> SearchFacets:
    price_values = [product.price for product in products]
    brand_counts = Counter(product.brand for product in products if product.brand)
    category_counts = Counter(product.category for product in products if product.category)

    return SearchFacets(
        brands=[
            FacetValue(name=name, count=count)
            for name, count in brand_counts.most_common(8)
        ],
        categories=[
            FacetValue(name=name, count=count)
            for name, count in category_counts.most_common(8)
        ],
        price_range=PriceRange(
            min=min(price_values) if price_values else None,
            max=max(price_values) if price_values else None,
        ),
    )


def _build_stats(products: list[Product]) -> SearchStats:
    price_values = [product.price for product in products]
    if not price_values:
        return SearchStats()

    return SearchStats(
        min_price=min(price_values),
        max_price=max(price_values),
        average_price=round(sum(price_values) / len(price_values), 2),
        offer_count=sum(1 for product in products if product.is_offer),
        in_stock_count=sum(1 for product in products if product.in_stock),
    )


def _empty_response(
    query: str,
    *,
    suggestions: list[str] | None = None,
    applied_query: str | None = None,
    warning: str | None = None,
) -> SearchResponse:
    return SearchResponse(
        query=query,
        applied_query=applied_query or query,
        count=0,
        results=[],
        facets=SearchFacets(),
        stats=SearchStats(),
        suggestions=suggestions or [],
        fetched_at=datetime.now(UTC).isoformat(),
        warning=warning,
    )


def search_products(query: str, limit: int = MAX_RESULTS, store: str = "lider") -> SearchResponse:
    normalized_query = normalize_query(query)
    store = (store or "lider").strip().lower()
    limit = max(1, min(limit, MAX_RESULTS))
    adapter = get_store_adapter(store)
    if not adapter:
        raise SearchServiceError(f"Tienda no soportada: {store}", status_code=400)

    cached = _get_cache(store, normalized_query, limit, allow_stale=False)
    if cached:
        return cached

    stale = _get_cache(store, normalized_query, limit, allow_stale=True)
    _enqueue_scrape(store, normalized_query, limit)
    if stale and stale.results:
        stale.warning = (
            f"Actualizacion de {store.title()} encolada. "
            "Se muestran resultados recientes desde cache."
        )
        return stale

    return _empty_response(
        normalized_query,
        warning=(
            f"Busqueda encolada para {store.title()}. "
            "Los precios se actualizaran en segundo plano."
        ),
    )


def _enqueue_scrape(store: str, query: str, limit: int) -> None:
    task = scrape_lider if store == "lider" else search_jumbo_async
    _start_publish_thread(task, query, limit)


def _start_publish_thread(task, query: str, limit: int) -> None:
    thread = Thread(
        target=_publish_scrape_task,
        args=(task, query, limit),
        daemon=True,
    )
    thread.start()


def _publish_scrape_task(task, query: str, limit: int) -> None:
    try:
        task.apply_async(args=(query,), kwargs={"limit": limit}, retry=False)
    except Exception as exc:
        logger.warning("Failed to publish scrape task for query=%s: %s", query, exc)
