from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from backend.db import SessionLocal
from backend.domain.normalization.matching import canonicalize
from backend.domain.price import Price
from backend.infrastructure.db.models import StoreRecord
from backend.infrastructure.db.repositories import PriceRepo, ProductRepo
from backend.infrastructure.scrapers.lider import LiderScraper
from backend.infrastructure.scrapers.acuenta import AcuentaScraper
from backend.infrastructure.scrapers.santa_isabel import SantaIsabelScraper
from backend.infrastructure.scrapers.tottus import TottusScraper
from backend.infrastructure.scrapers.unimarc import UnimarcScraper
from backend.tasks.celery_app import celery_app


logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="backend.tasks.scrape_lider")
def scrape_lider(self, query: str, limit: int = 100) -> dict:
    try:
        return _scrape_and_persist(LiderScraper, "Lider", query, limit)
    except Exception as exc:
        logger.error("Lider scrape task failed for query=%s: %s", query, exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))
        return {"status": "error", "query": query, "error": str(exc)}


def _scrape_and_persist(scraper_cls, store_display_name: str, query: str, limit: int) -> dict:
    """Generic helper — runs any async scraper and persists prices to DB."""
    search_result = asyncio.run(scraper_cls().search(query, limit=limit))
    inserted_prices = 0
    with SessionLocal() as session:
        store = _get_or_create_store(session, store_display_name)
        product_repo = ProductRepo(session)
        price_repo = PriceRepo(session)
        for product_dict in search_result.products:
            name = "<unknown>"
            try:
                name = product_dict.get("name") or product_dict.get("title")
                price_value = product_dict.get("price") or product_dict.get("value")
                if not name or price_value is None:
                    continue
                product = product_repo.upsert(canonicalize(name))
                session.flush()
                price_repo.insert(
                    Price(
                        product_key=product.canonical_key,
                        store_id=str(store.id),
                        value=float(price_value),
                        observed_at=datetime.now(UTC),
                    )
                )
                inserted_prices += 1
            except Exception as exc:
                logger.warning("Skipping scraped product %s: %s", name, exc)
        session.commit()
    return {
        "status": "success",
        "query": query,
        "products": len(search_result.products),
        "prices_inserted": inserted_prices,
    }


@celery_app.task(bind=True, max_retries=3, name="backend.tasks.scrape_santa_isabel")
def scrape_santa_isabel(self, query: str, limit: int = 100) -> dict:
    try:
        return _scrape_and_persist(SantaIsabelScraper, "Santa Isabel", query, limit)
    except Exception as exc:
        logger.error("Santa Isabel scrape failed query=%s: %s", query, exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))
        return {"status": "error", "query": query, "error": str(exc)}


@celery_app.task(bind=True, max_retries=3, name="backend.tasks.scrape_acuenta")
def scrape_acuenta(self, query: str, limit: int = 100) -> dict:
    try:
        return _scrape_and_persist(AcuentaScraper, "Acuenta", query, limit)
    except Exception as exc:
        logger.error("Acuenta scrape failed query=%s: %s", query, exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))
        return {"status": "error", "query": query, "error": str(exc)}


@celery_app.task(bind=True, max_retries=3, name="backend.tasks.scrape_tottus")
def scrape_tottus(self, query: str, limit: int = 100) -> dict:
    try:
        return _scrape_and_persist(TottusScraper, "Tottus", query, limit)
    except Exception as exc:
        logger.error("Tottus scrape failed query=%s: %s", query, exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))
        return {"status": "error", "query": query, "error": str(exc)}


@celery_app.task(bind=True, max_retries=3, name="backend.tasks.scrape_unimarc")
def scrape_unimarc(self, query: str, limit: int = 100) -> dict:
    try:
        return _scrape_and_persist(UnimarcScraper, "Unimarc", query, limit)
    except Exception as exc:
        logger.error("Unimarc scrape failed query=%s: %s", query, exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=5 * (2 ** self.request.retries))
        return {"status": "error", "query": query, "error": str(exc)}


def _get_or_create_store(session, name: str) -> StoreRecord:
    store = session.scalar(select(StoreRecord).where(StoreRecord.name == name))
    if store:
        return store
    store = StoreRecord(name=name)
    session.add(store)
    session.flush()
    return store


@celery_app.task(bind=True, name="backend.tasks.monitor_scraper_health")
def monitor_scraper_health(self) -> dict:
    """
    Tarea periodica que verifica que los scrapers funcionan.
    Si detecta fallos, backend.parser_monitor envia alertas por los canales configurados.
    """
    try:
        from backend.parser_monitor import run_full_check

        result = run_full_check()
        statuses = [
            store.get("status")
            for store in result.get("stores", {}).values()
            if isinstance(store, dict)
        ]
        status = "down" if "down" in statuses else "degraded" if "degraded" in statuses else "ok"
        result["task_status"] = status
        logger.info("Monitor scraper completado: %s", status)
        return result
    except Exception as exc:
        logger.error("monitor_scraper_health fallo: %s", exc, exc_info=True)
        return {"task_status": "error", "error": str(exc)}
