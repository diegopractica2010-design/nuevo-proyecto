import unittest
from unittest.mock import patch

from backend.search_service import clear_search_cache, search_products


class SearchServiceTests(unittest.TestCase):
    def setUp(self):
        clear_search_cache()

    @patch("backend.search_service._start_publish_thread")
    def test_search_products_enqueues_scraping_without_scraping_inline(self, mock_start_publish):
        response = search_products("leche", limit=24)

        self.assertEqual(response.query, "leche")
        self.assertEqual(response.applied_query, "leche")
        self.assertEqual(response.count, 0)
        self.assertFalse(response.cached)
        self.assertIn("encolada", response.warning)
        self.assertEqual(mock_start_publish.call_args.args[1:], ("leche", 24))


if __name__ == "__main__":
    unittest.main()
