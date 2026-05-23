import os
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import Product, SearchResponse


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
    with patch("backend.main.search_products", return_value=_search_response("arroz", store, 1290)):
        response = client.get(f"/search?q=arroz&store={store}")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert data["results"][0]["name"]
    assert data["results"][0]["price"] > 0


def test_compare_shopping_list_basic_completes_under_30s(monkeypatch):
    def fake_search(query, limit, store):
        prices = {"lider": 1200, "jumbo": 1100}
        return _search_response(query, store, prices[store])

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
        assert item["stores"][0]["best"]["price"] > 0
        assert item["stores"][1]["best"]["price"] > 0
        prices = [store["best"]["price"] for store in item["stores"]]
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


@pytest.mark.skipif(os.getenv("RUN_LIVE_ACCEPTANCE") != "1", reason="Live store acceptance is opt-in")
@pytest.mark.parametrize("store", ["lider", "jumbo"])
def test_live_search_returns_products(store):
    response = client.get(f"/search?q=arroz&store={store}")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert data["results"][0]["name"]
    assert data["results"][0]["price"] > 0
