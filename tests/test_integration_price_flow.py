from __future__ import annotations

from datetime import UTC

import anyio
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.infrastructure.db.models import PriceRecord
from backend.scraper import ScrapedSearchResult
from backend.search_service import clear_search_cache


def _scraped_result(query: str, products: list[dict]) -> ScrapedSearchResult:
    return ScrapedSearchResult(
        query=query,
        applied_query=query,
        products=products,
        source_url=f"https://super.lider.cl/search?q={query}",
        fetch_strategy="mock",
        parse_strategy="test",
    )


@pytest.mark.asyncio
async def test_search_persists_prices_and_history_is_readable(client, db_session: Session, monkeypatch):
    clear_search_cache()
    monkeypatch.setattr("backend.search_service._get_db_search_response", lambda query, store, limit: (None, None))

    scraped_products = [
        {
            "id": "lider-arroz-1",
            "name": "Arroz Tucapel Grado 1 1 kg",
            "brand": "Tucapel",
            "price": 1000.0,
            "in_stock": True,
        },
        {
            "id": "lider-arroz-2",
            "name": "Arroz Miraflores Integral 1 kg",
            "brand": "Miraflores",
            "price": 1200.0,
            "in_stock": True,
        },
        {
            "id": "lider-arroz-3",
            "name": "Arroz Banquete Grano Largo 1 kg",
            "brand": "Banquete",
            "price": 1400.0,
            "in_stock": True,
        },
    ]

    async def fake_lider_search(self, query: str, limit: int):
        return _scraped_result(query, scraped_products)

    monkeypatch.setattr("backend.infrastructure.scrapers.lider.LiderScraper.search", fake_lider_search)

    response = await client.post("/search", params={"q": "arroz", "store": "lider"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 3

    await anyio.sleep(0.1)

    records = list(db_session.scalars(select(PriceRecord).order_by(PriceRecord.value)).all())
    assert len(records) == 3
    assert [record.value for record in records] == [1000.0, 1200.0, 1400.0]

    first_product_id = payload["results"][0]["sku"]
    history_response = await client.get(f"/price-history/{first_product_id}", params={"store": "lider"})

    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload["history"]
    assert history_payload["trends"]["current_price"] == scraped_products[0]["price"]


@pytest.mark.asyncio
async def test_search_price_history_grows_for_repeated_live_scrapes(client, db_session: Session, monkeypatch):
    clear_search_cache()
    monkeypatch.setattr("backend.search_service._get_db_search_response", lambda query, store, limit: (None, None))

    prices = [1000.0, 1200.0]

    async def fake_lider_search(self, query: str, limit: int):
        price = prices.pop(0)
        return _scraped_result(
            query,
            [
                {
                    "id": "lider-arroz-hist-1",
                    "name": "Arroz Historial 1 kg",
                    "price": price,
                    "in_stock": True,
                }
            ],
        )

    monkeypatch.setattr("backend.infrastructure.scrapers.lider.LiderScraper.search", fake_lider_search)

    first_response = await client.post("/search", params={"q": "arroz historial", "store": "lider"})
    assert first_response.status_code == 200
    first_payload = first_response.json()
    product_id = first_payload["results"][0]["sku"]

    await anyio.sleep(0.1)
    clear_search_cache()
    await anyio.sleep(0.01)

    second_response = await client.post("/search", params={"q": "arroz historial", "store": "lider"})
    assert second_response.status_code == 200

    await anyio.sleep(0.1)

    records = list(db_session.scalars(select(PriceRecord).order_by(PriceRecord.observed_at)).all())
    assert len(records) == 2
    assert [record.value for record in records] == [1000.0, 1200.0]
    assert records[0].observed_at <= records[1].observed_at
    assert records[0].observed_at.tzinfo is None or records[0].observed_at.tzinfo == UTC

    history_response = await client.get(f"/price-history/{product_id}", params={"store": "lider"})
    assert history_response.status_code == 200
    history_payload = history_response.json()

    assert [entry["price"] for entry in history_payload["history"]] == [1000.0, 1200.0]
    assert history_payload["trends"]["current_price"] == 1200.0
    assert history_payload["trends"]["trend"] == "increasing"
