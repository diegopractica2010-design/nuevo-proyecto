import unittest
from unittest.mock import AsyncMock, patch

from backend.db import SessionLocal, reset_db
from backend.infrastructure.db.models import PriceRecord, ProductRecord, StoreRecord
from backend.infrastructure.scrapers.lider import LiderScraper, ScrapedProduct
from backend.scraper import ScrapedSearchResult
from backend.tasks.scrape_tasks import scrape_lider


class AsyncScraperTests(unittest.TestCase):
    def setUp(self):
        reset_db()

    def test_lider_scraper_parses_mock_html_and_canonicalizes_products(self):
        html = """
        <html>
          <body>
            <article class="product-card">
              <a class="product-name">Arroz Tucapel 1kg</a>
              <span class="price">$1.290</span>
            </article>
          </body>
        </html>
        """

        products = LiderScraper(delay_seconds=0).parse_products(html)

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, "Arroz Tucapel 1kg")
        self.assertEqual(products[0].price, 1290.0)
        self.assertEqual(products[0].product.canonical_key, "arroz:tucapel:1000g")

    @patch("backend.tasks.scrape_tasks.LiderScraper.search")
    def test_scrape_lider_task_inserts_products_and_prices(self, mock_search):
        mock_search.side_effect = AsyncMock(
            return_value=ScrapedSearchResult(
            query="arroz",
            applied_query="arroz",
            products=[{"name": "Arroz Tucapel 1kg", "price": 1290.0}],
            source_url="https://super.lider.cl/search?q=arroz",
            fetch_strategy="search:browser",
            parse_strategy="html_fallback",
            )
        )

        result = scrape_lider.apply(args=("arroz",), kwargs={"limit": 10}, throw=True).get()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["products"], 1)
        self.assertEqual(result["prices_inserted"], 1)

        with SessionLocal() as session:
            self.assertEqual(session.query(StoreRecord).count(), 1)
            self.assertEqual(session.query(ProductRecord).count(), 1)
            self.assertEqual(session.query(PriceRecord).count(), 1)
            product = session.query(ProductRecord).one()
            self.assertEqual(product.canonical_key, "arroz:tucapel:1000g")


if __name__ == "__main__":
    unittest.main()
