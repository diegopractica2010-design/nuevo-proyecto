import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.db import reset_db


class APITests(unittest.TestCase):
    def setUp(self):
        reset_db()
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
            "count": 1,
            "results": [
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
            "suggestions": [],
            "cached": False,
            "warning": None,
            "fetched_at": "2024-01-01T00:00:00Z",
            "source": "lider",
            "source_url": "https://super.lider.cl/search?q=leche",
            "strategy": "search:browser"
        }

        response = self.client.get("/search?query=leche&limit=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["query"], "leche")
        self.assertEqual(len(data["results"]), 1)

    @patch("backend.main.search_products")
    def test_search_endpoint_accepts_q_alias(self, mock_search):
        mock_search.return_value = {
            "query": "leche",
            "applied_query": "leche",
            "count": 0,
            "results": [],
            "stats": {
                "min_price": None,
                "max_price": None,
                "average_price": None,
                "offer_count": 0,
                "in_stock_count": 0,
            },
            "facets": {
                "brands": [],
                "categories": [],
                "price_range": {"min": None, "max": None},
            },
            "suggestions": [],
            "cached": False,
            "warning": None,
            "fetched_at": "2024-01-01T00:00:00Z",
            "source": "lider",
            "source_url": "https://super.lider.cl/search?q=leche",
            "strategy": "search:browser",
        }

        response = self.client.get("/search?q=leche&limit=10")
        self.assertEqual(response.status_code, 200)
        mock_search.assert_called_once_with(query="leche", limit=10, store="lider")

    def test_search_endpoint_invalid_query(self):
        response = self.client.get("/search?query=&limit=10")
        self.assertEqual(response.status_code, 422)  # Validation error

    def test_search_endpoint_invalid_store(self):
        response = self.client.get("/search?query=leche&limit=10&store=invalid")
        self.assertEqual(response.status_code, 400)  # Bad request for invalid store

    def test_authenticated_baskets_are_scoped_to_current_user(self):
        self.client.post(
            "/auth/register",
            json={"username": "paula", "email": "paula@example.com", "password": "password123"},
        )
        login = self.client.post(
            "/auth/login",
            json={"username": "paula", "password": "password123"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        created = self.client.post("/baskets", json={"name": "Semana"}, headers=headers)
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["user_id"], "paula")

        listed = self.client.get("/baskets", headers=headers)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

    def test_basket_item_quantity_endpoint(self):
        basket = self.client.post("/baskets", json={"name": "Semana"}).json()
        basket_id = basket["id"]

        added = self.client.post(
            f"/baskets/{basket_id}/items",
            json={
                "product": {"id": "sku-1", "name": "Leche", "price": 1000, "source": "lider"},
                "quantity": 1,
            },
        )
        self.assertEqual(added.status_code, 200)

        updated = self.client.patch(
            f"/baskets/{basket_id}/items/sku-1",
            json={"quantity": 4},
        )
        self.assertEqual(updated.status_code, 200)

        loaded = self.client.get(f"/baskets/{basket_id}").json()
        self.assertEqual(loaded["items"][0]["quantity"], 4)


if __name__ == "__main__":
    unittest.main()
