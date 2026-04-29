from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select

from backend.db import SessionLocal
from backend.domain.price import Price
from backend.infrastructure.db.models import StoreRecord
from backend.infrastructure.db.repositories import PriceRepo, ProductRepo
from backend.infrastructure.scrapers.lider import LiderScraper
from backend.tasks.celery_app import celery_app


logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="backend.tasks.scrape_lider")
def scrape_lider(self, query: str, limit: int = 36) -> dict:
    try:
        scraped_products = LiderScraper().search(query, limit=limit)
        inserted_prices = 0

        with SessionLocal() as session:
            store = _get_or_create_store(session, "Lider")
            product_repo = ProductRepo(session)
            price_repo = PriceRepo(session)

            for scraped in scraped_products:
                try:
                    product = product_repo.upsert(scraped.product)
                    session.flush()
                    price_repo.insert(
                        Price(
                            product_key=product.canonical_key,
                            store_id=str(store.id),
                            value=scraped.price,
                            observed_at=datetime.now(),
                        )
                    )
                    inserted_prices += 1
                except Exception as exc:
                    logger.warning("Skipping scraped product %s: %s", scraped.name, exc)

            session.commit()

        return {
            "status": "success",
            "query": query,
            "products": len(scraped_products),
            "prices_inserted": inserted_prices,
        }
    except Exception as exc:
        logger.error("Lider scrape task failed for query=%s: %s", query, exc, exc_info=True)
        if self.request.retries < self.max_retries:
            countdown = 5 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)
        return {"status": "error", "query": query, "error": str(exc)}


def _get_or_create_store(session, name: str) -> StoreRecord:
    store = session.scalar(select(StoreRecord).where(StoreRecord.name == name))
    if store:
        return store
    store = StoreRecord(name=name)
    session.add(store)
    session.flush()
    return store

