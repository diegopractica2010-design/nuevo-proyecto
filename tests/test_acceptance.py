import asyncio
import os
import time
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import Product, SearchResponse
from backend.scraper import ScrapedSearchResult


client = TestClient(app)


def _search_response(query: str, store: str, price: float) -> SearchResponse:
    return SearchResponse(
        query=query,
        applied_query=query,
        count=1,
        results=[
            Product(
                name=f"{query} {store} 1 kg",
                price=price,
                source=store,
                in_stock=True,
            )
        ],
        source=store,
    )


@pytest.mark.parametrize("store", ["lider", "jumbo"])
def test_search_endpoint_returns_products_for_store(store):
    with patch(
        "backend.main.search_products",
        new_callable=AsyncMock,
        return_value=_search_response("arroz", store, 1290),
    ):
        response = client.get(f"/search?q=arroz&store={store}")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert data["results"][0]["name"]
    assert data["results"][0]["price"] > 0


def test_compare_shopping_list_basic_completes_under_30s(monkeypatch):
    def fake_search(query, limit, store):
        # Return a fixed price for all stores (new stores added to COMPARE_STORES)
        prices = {"lider": 1200, "jumbo": 1100}
        price = prices.get(store, 1300)
        return _search_response(query, store, price)

    monkeypatch.setattr("backend.shopping_list_service.search_products", fake_search)
    started = time.monotonic()
    response = client.post(
        "/shopping-list/compare",
        json={"items": ["arroz 1 kilo", "leche entera 1 litro", "aceite"]},
    )
    elapsed = time.monotonic() - started

    assert response.status_code == 200
    data = response.json()
    assert elapsed < 30
    assert len(data["items"]) == 3
    for item in data["items"]:
        matched = [s for s in item["stores"] if s.get("best") is not None]
        assert len(matched) > 0, "At least one store should have results"
        prices = [s["best"]["price"] for s in matched]
        assert item["cheapest"]["price"] == min(prices)


def test_compare_list_with_one_store_down(monkeypatch):
    def fake_search(query, limit, store):
        if store == "lider":
            raise RuntimeError("lider down")
        return _search_response(query, store, 1100)

    monkeypatch.setattr("backend.shopping_list_service.search_products", fake_search)
    response = client.post("/shopping-list/compare", json={"items": ["arroz 1 kilo"]})

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert "error" in item["stores"][0]
    assert item["stores"][1]["best"]["price"] > 0
    assert item["cheapest"]["source"] == "jumbo"


def test_scraper_health_canonical_queries_succeed(monkeypatch, tmp_path):
    import backend.parser_monitor as parser_monitor

    monkeypatch.setattr(parser_monitor, "SNAPSHOT_DIR", tmp_path / "parser_snapshots")
    monkeypatch.setattr(parser_monitor, "PRODUCT_SNAPSHOT_DIR", tmp_path / "snapshots")
    monkeypatch.setattr(parser_monitor, "STATE_FILE", tmp_path / "parser_snapshots" / "parser_state.json")

    lider = ScrapedSearchResult(
        query="arroz",
        applied_query="arroz",
        products=[{"name": "Arroz Lider 1 kg", "price": 1500, "source": "lider"}],
        source_url="https://super.lider.cl/search?q=arroz",
        fetch_strategy="search:browser",
        parse_strategy="next_data",
    )
    jumbo = ScrapedSearchResult(
        query="arroz",
        applied_query="arroz",
        products=[{"name": "Arroz Jumbo 1 kg", "price": 1600, "source": "jumbo"}],
        source_url="https://www.jumbo.cl/busqueda?ft=arroz",
        fetch_strategy="catalog_api",
        parse_strategy="vtex_catalog_api",
    )

    async def fake_lider_search(self, query, limit):
        return lider

    async def fake_jumbo_search(query, limit):
        return jumbo

    monkeypatch.setattr("backend.infrastructure.scrapers.lider.LiderScraper.search", fake_lider_search)
    monkeypatch.setattr("backend.scraper_jumbo.search_jumbo", fake_jumbo_search)

    result = parser_monitor.run_full_check()

    assert result["stores"]["lider"]["status"] == "ok"
    assert result["stores"]["lider"]["parse_strategy"] == "next_data"
    assert result["stores"]["jumbo"]["status"] == "ok"
    assert result["stores"]["jumbo"]["parse_strategy"] == "catalog_api"


def test_db_cache_serves_recent_searches(monkeypatch):
    db_response = _search_response("arroz", "lider", 1290)
    db_response.strategy = "db"

    scraper_called = False

    def fake_adapter(_store):
        class Adapter:
            def search(self, query, limit):
                nonlocal scraper_called
                scraper_called = True
                return None

        return Adapter()

    monkeypatch.setattr(
        "backend.search_service._get_db_search_response",
        lambda query, store, limit: (db_response, timedelta(minutes=5)),
    )
    monkeypatch.setattr("backend.search_service.get_store_adapter", fake_adapter)

    from backend.search_service import search_products

    response = asyncio.run(search_products("arroz", store="lider", limit=10))

    assert response.strategy == "db-fresh"
    assert response.results[0].price == 1290
    assert scraper_called is False


def test_canonicalize_unifies_brand_variants():
    from backend.domain.normalization.matching import are_equivalent, canonicalize

    first = canonicalize("Arroz Tucapel S.A. Grado 1 1 kg")
    second = canonicalize("arroz grado uno tucapel 1000 g")

    assert first.canonical_key == "arroz:tucapel:grado1:1000g"
    assert are_equivalent(first, second)


def test_unit_price_calculation(monkeypatch):
    from backend.scraper import ScrapedSearchResult
    from backend.search_service import clear_search_cache, search_products
    from backend.store_adapters import StoreAdapter

    clear_search_cache()
    adapter = StoreAdapter(
        name="lider",
        display_name="Lider",
        search=lambda query, limit: ScrapedSearchResult(
            query=query,
            applied_query=query,
            products=[{"name": "Arroz Tucapel 1 kg", "price": 2000, "source": "lider"}],
            source_url="https://super.lider.cl/search?q=arroz",
            fetch_strategy="search",
            parse_strategy="next_data",
        ),
    )
    monkeypatch.setattr("backend.search_service._get_db_search_response", lambda query, store, limit: (None, None))
    monkeypatch.setattr("backend.search_service.get_store_adapter", lambda store: adapter)

    response = asyncio.run(search_products("arroz", store="lider", limit=10))

    assert response.results[0].unit_price == "$2.000/kg"


def test_compare_marks_same_product_across_stores(monkeypatch):
    def fake_search(query, limit, store):
        names = {
            "lider": "Arroz Tucapel S.A. Grado 1 1 kg",
            "jumbo": "Arroz grado uno Tucapel 1000 g",
        }
        return SearchResponse(
            query=query,
            applied_query=query,
            count=1,
            results=[
                Product(
                    name=names[store],
                    price=1200 if store == "lider" else 1250,
                    source=store,
                    in_stock=True,
                )
            ],
        )

    monkeypatch.setattr("backend.shopping_list_service.search_products", fake_search)

    response = client.post("/shopping-list/compare", json={"items": ["arroz tucapel grado 1 1 kilo"]})

    assert response.status_code == 200
    assert response.json()["items"][0]["same_product"] is True


@pytest.mark.skipif(os.getenv("RUN_LIVE_ACCEPTANCE") != "1", reason="Live store acceptance is opt-in")
@pytest.mark.parametrize("store", ["lider", "jumbo"])
def test_live_search_returns_products(store):
    response = client.get(f"/search?q=arroz&store={store}")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert data["results"][0]["name"]
    assert data["results"][0]["price"] > 0
