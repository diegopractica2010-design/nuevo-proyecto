from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import logging
from threading import Lock
from typing import Any

from backend.config import CACHE_TTL_SECONDS, MAX_RESULTS, STALE_CACHE_TTL_SECONDS
from backend.compliance import ComplianceError
from backend.infrastructure.cache.cache import cache_get, cache_set
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
    return f"search:{store}:{query}::{limit}"


def _redis_cache_key(store: str, query: str, limit: int, kind: str) -> str:
    return f"search:{kind}:{store}:{query}::{limit}"


def _clone_response(response: SearchResponse, *, cached: bool, warning: str | None = None) -> SearchResponse:
    cloned = response.model_copy(deep=True)
    cloned.cached = cached
    cloned.warning = warning or cloned.warning
    return cloned


def _get_redis_cache(store: str, query: str, limit: int, *, kind: str) -> SearchResponse | None:
    try:
        payload = cache_get(_redis_cache_key(store, query, limit, kind))
    except Exception as exc:
        logger.debug("Redis cache get failed for %s/%s: %s", store, query, exc)
        return None
    if not isinstance(payload, dict):
        return None
    try:
        return _clone_response(SearchResponse.model_validate(payload), cached=True)
    except Exception as exc:
        logger.debug("Redis cache payload invalid for %s/%s: %s", store, query, exc)
        return None


def _get_cache(store: str, query: str, limit: int, *, allow_stale: bool) -> SearchResponse | None:
    fresh = _get_redis_cache(store, query, limit, kind="fresh")
    if fresh:
        return fresh

    if allow_stale:
        stale = _get_redis_cache(store, query, limit, kind="stale")
        if stale:
            return stale

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


def _set_redis_cache(store: str, query: str, limit: int, response: SearchResponse) -> None:
    payload = response.model_dump(mode="json")
    payload["cached"] = False
    try:
        cache_set(_redis_cache_key(store, query, limit, "fresh"), payload, ttl=CACHE_TTL_SECONDS)
        cache_set(_redis_cache_key(store, query, limit, "stale"), payload, ttl=STALE_CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.debug("Redis cache set failed for %s/%s: %s", store, query, exc)


def _set_cache(store: str, query: str, limit: int, response: SearchResponse):
    _set_redis_cache(store, query, limit, response)
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
        brands=[FacetValue(name=name, count=count) for name, count in brand_counts.most_common(8)],
        categories=[FacetValue(name=name, count=count) for name, count in category_counts.most_common(8)],
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
    store: str = "lider",
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
        source=store,
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

    logger.info("Ejecutando busqueda en vivo para query=%s, store=%s", normalized_query, store)
    try:
        results = adapter.search(normalized_query, limit)
        if results and results.products:
            response = _build_response_from_scrape(
                query=normalized_query,
                results=results.products,
                store=store,
                applied_query=results.applied_query,
                warning=getattr(results, "warning", None),
                source_url=results.source_url,
                strategy=f"{results.fetch_strategy}:{results.parse_strategy}",
                suggestions=getattr(results, "suggestions", []),
            )
            _set_cache(store, normalized_query, limit, response)
            logger.info("Busqueda exitosa: %d productos encontrados", len(response.results))
            return response

        logger.warning("Busqueda sin resultados para query=%s", normalized_query)
        return _empty_response(normalized_query, store=store)

    except ComplianceError as exc:
        logger.warning("Busqueda bloqueada por cumplimiento: %s", exc)
        return _empty_response(normalized_query, warning=str(exc), store=store)
    except Exception as exc:
        logger.error("Error en busqueda: %s", exc, exc_info=True)
        stale = _get_cache(store, normalized_query, limit, allow_stale=True)
        if stale and stale.results:
            stale.warning = f"Error en busqueda fresca. Mostrando resultados anteriores del {stale.fetched_at}"
            return stale
        return _empty_response(
            normalized_query,
            warning=f"No se pudo completar la busqueda: {str(exc)}",
            store=store,
        )


def _product_to_dict(product: Any, store: str) -> dict[str, Any]:
    if hasattr(product, "product"):
        raw = product.product
        price = float(product.price)
    else:
        raw = product
        price = float((raw.get("price") if isinstance(raw, dict) else getattr(raw, "price", 0)) or 0)

    if hasattr(raw, "model_dump"):
        product_dict = raw.model_dump()
    elif isinstance(raw, dict):
        product_dict = dict(raw)
    else:
        product_dict = {
            "id": getattr(raw, "id", None),
            "name": getattr(raw, "name", ""),
            "brand": getattr(raw, "brand", None),
            "category": getattr(raw, "category", None),
            "is_offer": bool(getattr(raw, "is_offer", False)),
            "in_stock": bool(getattr(raw, "in_stock", True)),
            "url": getattr(raw, "url", None),
        }

    product_dict["price"] = price
    product_dict["source"] = store
    return product_dict


def _build_response_from_scrape(
    query: str,
    results: list,
    store: str,
    *,
    applied_query: str | None = None,
    warning: str | None = None,
    source_url: str | None = None,
    strategy: str | None = None,
    suggestions: list[str] | None = None,
) -> SearchResponse:
    from backend.shopping_list_service import is_specific_query, select_best_products

    product_dicts = [_product_to_dict(product, store) for product in results]
    if is_specific_query(query):
        refined_products = select_best_products(product_dicts, query)
        if refined_products:
            product_dicts = refined_products

    products = [Product.model_validate(product) for product in product_dicts]
    return SearchResponse(
        query=query,
        applied_query=applied_query or query,
        results=products,
        count=len(products),
        stats=_build_stats(products),
        facets=_build_facets(products),
        suggestions=suggestions or [],
        cached=False,
        warning=warning,
        fetched_at=datetime.now(UTC).isoformat(),
        source=store,
        source_url=source_url,
        strategy=strategy or "search:sync",
    )
