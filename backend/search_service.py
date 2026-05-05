from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import logging
from threading import Thread
from threading import Lock

from backend.config import CACHE_TTL_SECONDS, MAX_RESULTS, STALE_CACHE_TTL_SECONDS
from backend.compliance import ComplianceError
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

    # Intentar obtener del cache fresco primero
    cached = _get_cache(store, normalized_query, limit, allow_stale=False)
    if cached:
        return cached

    if store == "lider" and limit <= 36:
        _start_publish_thread(store, normalized_query, limit)
        return _empty_response(
            normalized_query,
            warning="Busqueda encolada. Vuelve a intentar en unos segundos.",
        )

    # Si no hay cache fresco, intentar traer datos frescos
    logger.info("Ejecutando búsqueda en vivo para query=%s, store=%s", normalized_query, store)
    
    try:
        if store == "lider":
            from backend.scraper import search_lider
            results = search_lider(normalized_query, limit)
        else:
            from backend.scraper_jumbo import search_jumbo
            results = search_jumbo(normalized_query, limit)
        
        # Si tenemos resultados, construir respuesta
        if results and results.products:
            response = _build_response_from_scrape(
                query=normalized_query,
                results=results.products,
                store=store,
            )
            # Guardar en cache para futuras búsquedas
            _set_cache(store, normalized_query, limit, response)
            logger.info("Búsqueda exitosa: %d productos encontrados", len(response.results))
            return response
        else:
            logger.warning("Búsqueda sin resultados para query=%s", normalized_query)
            return _empty_response(normalized_query, warning=None)
            
    except ComplianceError as exc:
        logger.warning("Busqueda bloqueada por cumplimiento: %s", exc)
        return _empty_response(
            normalized_query,
            warning=str(exc),
        )
    except Exception as exc:
        logger.error("Error en búsqueda: %s", exc, exc_info=True)
        
        # Si hay error, intentar obtener del cache viejo
        stale = _get_cache(store, normalized_query, limit, allow_stale=True)
        if stale and stale.results:
            stale.warning = (
                f"Error en búsqueda fresca. Mostrando resultados anteriores del {stale.fetched_at}"
            )
            return stale
        
        # Si nada funcionó, devolver respuesta vacía
        return _empty_response(
            normalized_query,
            warning=f"No se pudo completar la búsqueda: {str(exc)}"
        )


def _enqueue_scrape(store: str, query: str, limit: int) -> None:
    """
    Intenta encolar scraping en Celery.
    Si falla (Redis no disponible), ejecuta de forma síncrona en background.
    """
    if store == "lider":
        task = scrape_lider
    else:
        task = search_jumbo_async
    
    # Intenta modo async primero
    if _try_celery_async(task, query, limit):
        return
    
    # Si Celery falla, ejecuta de forma síncrona en thread background
    _start_sync_scrape_thread(store, query, limit)


def _try_celery_async(task, query: str, limit: int) -> bool:
    """Intenta encolar en Celery. Devuelve True si tuvo éxito."""
    try:
        task.apply_async(args=(query,), kwargs={"limit": limit}, retry=False)
        logger.info("Scrape encolado en Celery para query=%s", query)
        return True
    except Exception as exc:
        logger.debug("Celery no disponible, ejecutando scraper síncrono: %s", exc)
        return False


def _start_sync_scrape_thread(store: str, query: str, limit: int) -> None:
    """Ejecuta scraper de forma síncrona en un thread separado."""
    thread = Thread(
        target=_execute_scrape_sync,
        args=(store, query, limit),
        daemon=True,
    )
    thread.start()


def _start_publish_thread(store: str, query: str, limit: int) -> None:
    _start_sync_scrape_thread(store, query, limit)


def _execute_scrape_sync(store: str, query: str, limit: int) -> None:
    """Ejecuta scraper directamente sin Celery."""
    try:
        logger.info("Ejecutando scraper síncrono para store=%s, query=%s", store, query)
        
        if store == "lider":
            from backend.scraper import search_lider
            results = search_lider(query, limit)
        else:
            from backend.scraper_jumbo import search_jumbo
            results = search_jumbo(query, limit)
        
        # Procesar resultados y guardar en cache
        if results and results.products:
            response = _build_response_from_scrape(
                query=query,
                results=results.products,
                store=store,
            )
            _set_cache(store, normalize_query(query), limit, response)
            logger.info("Scrape completado: %d productos guardados en cache", len(results.products))
        else:
            logger.info("Scrape completado pero sin resultados")
            
    except Exception as exc:
        logger.error("Error en scraper síncrono para store=%s: %s", store, exc, exc_info=True)


def _build_response_from_scrape(query: str, results: list, store: str) -> SearchResponse:
    """Construye SearchResponse a partir de productos scrapeados."""
    from backend.shopping_list_service import is_specific_query, select_best_products
    
    products = []
    min_price = None
    max_price = None
    
    for scraped_product in results:
        # Si es ScrapedProduct (tiene .product), extraer el Product
        if hasattr(scraped_product, 'product'):
            product = scraped_product.product
            price = scraped_product.price
        else:
            # Si es un diccionario
            product = scraped_product
            price = float(product.get('price', 0) or 0)
        
        # Convertir a diccionario si es objeto
        if hasattr(product, 'model_dump'):
            product_dict = product.model_dump()
        elif isinstance(product, dict):
            product_dict = product
        else:
            # Objeto con atributos
            product_dict = {
                'id': getattr(product, 'id', ''),
                'name': getattr(product, 'name', ''),
                'price': price,
                'brand': getattr(product, 'brand', ''),
                'category': getattr(product, 'category', ''),
                'is_offer': bool(getattr(product, 'is_offer', False)),
                'in_stock': bool(getattr(product, 'in_stock', True)),
                'source': store,
                'url': getattr(product, 'url', ''),
            }
        
        # Actualizar precio a lo scrapeado
        product_dict['price'] = price
        product_dict['source'] = store
        
        price = float(product_dict.get('price', 0) or 0)
        if min_price is None or price < min_price:
            min_price = price
        if max_price is None or price > max_price:
            max_price = price
        
        products.append(product_dict)

    if is_specific_query(query):
        refined_products = select_best_products(products, query)
        if refined_products:
            products = refined_products
            min_price = min(float(product.get("price", 0) or 0) for product in products)
            max_price = max(float(product.get("price", 0) or 0) for product in products)
    
    return SearchResponse(
        query=query,
        applied_query=query,
        results=products,
        count=len(products),
        stats=SearchStats(
            min_price=min_price,
            max_price=max_price,
            average_price=sum(p['price'] for p in products) / len(products) if products else None,
            offer_count=sum(1 for p in products if p.get('is_offer')),
            in_stock_count=sum(1 for p in products if p.get('in_stock')),
        ),
        facets=SearchFacets(
            brands=[{"name": v, "count": 0} for v in set(p.get('brand') for p in products if p.get('brand'))],
            categories=[{"name": v, "count": 0} for v in set(p.get('category') for p in products if p.get('category'))],
            price_range=PriceRange(min=min_price, max=max_price),
        ),
        suggestions=[],
        cached=False,
        warning=None,
        fetched_at=datetime.now(UTC).isoformat(),
        source_url=f"https://super.{store}.cl/search?q={query}",
        strategy="search:sync-fallback",
    )
