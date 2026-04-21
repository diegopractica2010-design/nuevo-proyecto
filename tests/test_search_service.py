import unittest
from unittest.mock import patch

from backend.scraper import ScrapedSearchResult
from backend.search_service import clear_search_cache, search_products


class SearchServiceTests(unittest.TestCase):
    def setUp(self):
        clear_search_cache()

    @patch("backend.search_service.search_lider")
    def test_search_products_builds_facets_stats_and_metadata(self, mock_search_lider):
        mock_search_lider.return_value = ScrapedSearchResult(
            query="leche",
            applied_query="leche",
            source_url="https://super.lider.cl/search?q=leche",
            fetch_strategy="search:browser",
            parse_strategy="next_data",
            suggestions=["leche", "leche sin lactosa"],
            products=[
                {
                    "id": "1",
                    "sku": "sku-1",
                    "name": "Leche Entera 1 L Lider",
                    "brand": "Lider",
                    "category": "Leche",
                    "price": 1000.0,
                    "original_price": None,
                    "discount_percent": None,
                    "savings_amount": None,
                    "savings_text": None,
                    "unit_price": "$1.000 x lt",
                    "image": "https://example.com/leche-1.jpg",
                    "url": "https://super.lider.cl/ip/leche/sku-1",
                    "availability": "IN_STOCK",
                    "in_stock": True,
                    "seller": "Lider",
                    "badges": [],
                    "is_offer": False,
                    "position": 1,
                },
                {
                    "id": "2",
                    "sku": "sku-2",
                    "name": "Leche Descremada 1 L Loncoleche",
                    "brand": "Loncoleche",
                    "category": "Leche",
                    "price": 1090.0,
                    "original_price": 1190.0,
                    "discount_percent": 8,
                    "savings_amount": 100.0,
                    "savings_text": "Ahorra $100",
                    "unit_price": "$1.090 x lt",
                    "image": "https://example.com/leche-2.jpg",
                    "url": "https://super.lider.cl/ip/leche/sku-2",
                    "availability": "IN_STOCK",
                    "in_stock": True,
                    "seller": "Lider",
                    "badges": ["Rebaja"],
                    "is_offer": True,
                    "position": 2,
                },
            ],
        )

        response = search_products("leche", limit=24)

        self.assertEqual(response.query, "leche")
        self.assertEqual(response.applied_query, "leche")
        self.assertEqual(response.count, 2)
        self.assertEqual(response.source_url, "https://super.lider.cl/search?q=leche")
        self.assertEqual(response.strategy, "search:browser/next_data")
        self.assertFalse(response.cached)
        self.assertEqual(response.suggestions, ["leche", "leche sin lactosa"])
        self.assertEqual(response.facets.price_range.min, 1000.0)
        self.assertEqual(response.facets.price_range.max, 1090.0)
        self.assertEqual(response.facets.categories[0].name, "Leche")
        self.assertEqual(response.stats.min_price, 1000.0)
        self.assertEqual(response.stats.max_price, 1090.0)
        self.assertEqual(response.stats.offer_count, 1)
        self.assertEqual(response.stats.in_stock_count, 2)


if __name__ == "__main__":
    unittest.main()
