import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app


class APITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_index_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])

    @patch("backend.main.search_products")
    def test_search_endpoint_success(self, mock_search):
        mock_search.return_value = {
            "query": "leche",
            "applied_query": "leche",
            "products": [
                {
                    "name": "Leche Entera",
                    "price": 1000.0,
                    "brand": "Test",
                    "source": "lider"
                }
            ],
            "stats": {
                "min_price": 1000.0,
                "max_price": 1000.0,
                "average_price": 1000.0,
                "offer_count": 0,
                "in_stock_count": 1
            },
            "facets": {
                "brands": [],
                "categories": [],
                "price_range": {"min": None, "max": None}
            },
            "cached": False,
            "warning": None,
            "fetched_at": "2024-01-01T00:00:00Z",
            "source_url": "https://super.lider.cl/search?q=leche",
            "strategy": "search:browser"
        }

        response = self.client.get("/search?query=leche&limit=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["query"], "leche")
        self.assertEqual(len(data["products"]), 1)

    def test_search_endpoint_invalid_query(self):
        response = self.client.get("/search?query=&limit=10")
        self.assertEqual(response.status_code, 422)  # Validation error

    def test_search_endpoint_invalid_store(self):
        response = self.client.get("/search?query=leche&limit=10&store=invalid")
        self.assertEqual(response.status_code, 400)  # Bad request for invalid store


if __name__ == "__main__":
    unittest.main()