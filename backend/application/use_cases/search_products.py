from __future__ import annotations

import logging
from datetime import datetime
from threading import Thread
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.application.use_cases.compare_prices import compare_prices
from backend.db import SessionLocal
from backend.domain.normalization.matching import canonicalize
from backend.infrastructure.cache.cache import cache_get, cache_set
from backend.infrastructure.db.models import PriceRecord, ProductRecord
from backend.tasks.scrape_tasks import scrape_lider


logger = logging.getLogger(__name__)


def search_products(query: str) -> dict[str, Any]:
    normalized_query = query.strip()
    if not normalized_query:
        return {"best_option": {}, "alternatives": []}

    cache_key = f"api:search:{normalized_query.lower()}"
    cached = _safe_cache_get(cache_key)
    if cached is not None:
        return cached

    with SessionLocal() as session:
        candidates = _search_db(session, normalized_query)

    if not candidates:
        _enqueue_scrape(normalized_query)
        result = {"best_option": {}, "alternatives": []}
        _safe_cache_set(cache_key, result, ttl=60)
        return result

    result = compare_prices(candidates)
    _safe_cache_set(cache_key, result)
    return result


def _search_db(session: Session, query: str) -> list[dict[str, Any]]:
    canonical = canonicalize(query)
    terms = [term for term in canonical.canonical_name.split() if term]

    statement = (
        select(ProductRecord)
        .options(selectinload(ProductRecord.prices).selectinload(PriceRecord.store))
        .order_by(ProductRecord.canonical_name)
    )

    filters = []
    if canonical.brand:
        filters.append(ProductRecord.brand == canonical.brand)
    filters.extend(ProductRecord.canonical_name.ilike(f"%{term}%") for term in terms)
    if filters:
        from sqlalchemy import or_

        statement = statement.where(or_(*filters))
    else:
        statement = statement.where(ProductRecord.canonical_name.ilike(f"%{query.lower()}%"))

    records = list(session.scalars(statement).all())
    return _product_price_options(records)


def _product_price_options(records: list[ProductRecord]) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    for product in records:
        latest_by_store: dict[str, PriceRecord] = {}
        for price in product.prices:
            store_key = str(price.store_id)
            current = latest_by_store.get(store_key)
            if current is None or price.observed_at > current.observed_at:
                latest_by_store[store_key] = price

        for price in latest_by_store.values():
            options.append(
                {
                    "product_id": str(product.id),
                    "canonical_key": product.canonical_key,
                    "canonical_name": product.canonical_name,
                    "brand": product.brand,
                    "quantity_value": product.quantity_value,
                    "quantity_unit": product.quantity_unit,
                    "store_id": str(price.store_id),
                    "store_name": price.store.name if price.store else "",
                    "price": price.value,
                    "observed_at": _format_datetime(price.observed_at),
                }
            )
    return options


def _enqueue_scrape(query: str) -> None:
    thread = Thread(target=_publish_scrape_task, args=(query,), daemon=True)
    thread.start()


def _publish_scrape_task(query: str) -> None:
    try:
        scrape_lider.apply_async(args=(query,), retry=False)
    except Exception as exc:
        logger.warning("Failed to enqueue scrape for query=%s: %s", query, exc)


def _safe_cache_get(key: str):
    try:
        return cache_get(key)
    except Exception as exc:
        logger.debug("Cache get failed for %s: %s", key, exc)
        return None


def _safe_cache_set(key: str, value: dict[str, Any], ttl: int = 600) -> None:
    try:
        cache_set(key, value, ttl=ttl)
    except Exception as exc:
        logger.debug("Cache set failed for %s: %s", key, exc)


def _format_datetime(value: datetime) -> str:
    return value.isoformat()

