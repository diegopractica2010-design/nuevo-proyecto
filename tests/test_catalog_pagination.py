from unittest.mock import patch

from backend.scraper import ScrapedSearchResult, _execute_catalog_query
from backend.scraper_jumbo import _execute_catalog_api_query


def _page(products, page):
    return ScrapedSearchResult(
        query="leche",
        applied_query="leche",
        products=products,
        source_url=f"https://example.test/search?q=leche&page={page}",
        fetch_strategy=f"search:browser:page:{page}",
        parse_strategy="next_data",
    )


def test_lider_search_paginates_until_limit_and_deduplicates():
    with patch("backend.scraper._fetch_catalog_page") as fetch_page:
        fetch_page.side_effect = [
            _page(
                [
                    {"sku": "1", "name": "Leche A", "price": 1000},
                    {"sku": "2", "name": "Leche B", "price": 1200},
                ],
                1,
            ),
            _page(
                [
                    {"sku": "2", "name": "Leche B", "price": 1200},
                    {"sku": "3", "name": "Leche C", "price": 1300},
                ],
                2,
            ),
        ]

        result = _execute_catalog_query("leche", limit=3)

    assert [product["sku"] for product in result.products] == ["1", "2", "3"]
    assert fetch_page.call_count == 2


class _FakeResponse:
    def __init__(self, page_products, url):
        self._page_products = page_products
        self.url = url

    def raise_for_status(self):
        return None

    def json(self):
        return self._page_products


class _FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, params, headers, timeout):
        self.calls.append(params["page"])
        page = params["page"]
        products_by_page = {
            1: [
                {
                    "productId": "1",
                    "productName": "Arroz A",
                    "items": [{"itemId": "sku-1", "sellers": [{"commertialOffer": {"Price": 1000, "AvailableQuantity": 1}}]}],
                }
            ],
            2: [
                {
                    "productId": "2",
                    "productName": "Arroz B",
                    "items": [{"itemId": "sku-2", "sellers": [{"commertialOffer": {"Price": 1200, "AvailableQuantity": 1}}]}],
                }
            ],
        }
        return _FakeResponse(products_by_page.get(page, []), f"{url}?page={page}")


def test_jumbo_api_search_paginates_until_limit():
    session = _FakeSession()

    with patch("backend.scraper_jumbo.assert_live_store_access_allowed"):
        result = _execute_catalog_api_query(session, "arroz", limit=2)

    assert [product["sku"] for product in result.products] == ["sku-1", "sku-2"]
    assert session.calls == [1, 2]
