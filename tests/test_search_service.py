import unittest
from unittest.mock import Mock, patch

from backend.scraper import ScrapedSearchResult
from backend.search_service import clear_search_cache, search_products
from backend.store_adapters import StoreAdapter


class SearchServiceTests(unittest.TestCase):
    def setUp(self):
        clear_search_cache()

    @patch("backend.search_service.get_store_adapter")
    def test_search_products_scrapes_inline_on_first_call(self, mock_get_store_adapter):
        adapter = StoreAdapter(
            name="lider",
            display_name="Lider",
            search=Mock(
                return_value=ScrapedSearchResult(
                    query="leche",
                    applied_query="leche",
                    products=[{"name": "Leche Entera 1 L", "price": 1000.0, "in_stock": True}],
                    source_url="https://super.lider.cl/search?q=leche",
                    fetch_strategy="search:browser",
                    parse_strategy="next_data",
                )
            ),
        )
        mock_get_store_adapter.return_value = adapter

        response = search_products("leche", limit=24)

        self.assertEqual(response.query, "leche")
        self.assertEqual(response.applied_query, "leche")
        self.assertEqual(response.count, 1)
        self.assertFalse(response.cached)
        self.assertIsNone(response.warning)
        adapter.search.assert_called_once_with("leche", 24)


if __name__ == "__main__":
    unittest.main()
