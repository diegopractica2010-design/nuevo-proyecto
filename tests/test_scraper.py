import unittest
from unittest.mock import patch

from backend.scraper import NoResultsError, ScrapedSearchResult, search_lider


class ScraperTests(unittest.TestCase):
    @patch("backend.scraper.fetch_autocomplete_terms")
    @patch("backend.scraper._execute_catalog_query")
    def test_search_lider_uses_suggestion_when_direct_query_has_no_results(
        self,
        mock_execute_catalog_query,
        mock_fetch_autocomplete_terms,
    ):
        mock_fetch_autocomplete_terms.return_value = ["lech", "leche", "leche descremada"]
        mock_execute_catalog_query.side_effect = [
            NoResultsError("lech"),
            ScrapedSearchResult(
                query="leche",
                applied_query="leche",
                products=[
                    {
                        "name": "Leche Entera 1 L Lider",
                        "price": 1000.0,
                    }
                ],
                source_url="https://super.lider.cl/search?q=leche",
                fetch_strategy="search:browser",
                parse_strategy="next_data",
            ),
        ]

        result = search_lider("lech", limit=24)

        self.assertEqual(result.applied_query, "leche")
        self.assertEqual(result.suggestions, ["lech", "leche", "leche descremada"])
        self.assertIn('No hubo coincidencias directas para "lech"', result.warning)


if __name__ == "__main__":
    unittest.main()
