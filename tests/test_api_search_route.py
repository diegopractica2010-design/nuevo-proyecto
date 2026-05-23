import unittest

from fastapi.testclient import TestClient

from backend.main import app


class ApiSearchRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_api_search_route_was_removed(self):
        response = self.client.get("/api/search?q=arroz")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
