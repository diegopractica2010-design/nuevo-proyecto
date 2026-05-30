"""
Tottus scraper (Falabella platform).
Strategy 1: Falabella REST API (JSON, usually no anti-bot).
Strategy 2: Playwright HTML scrape (optional, requires PLAYWRIGHT_ENABLED=true).

HTML fallback requires playwright — run: pip install playwright && playwright install chromium
"""
from __future__ import annotations

import logging
import os
from urllib.parse import quote_plus

from backend.infrastructure.scrapers.base import BaseScraper
from backend.scraper import ScrapedSearchResult, NoResultsError, ScraperError

logger = logging.getLogger(__name__)

TOTTUS_BASE = "https://tottus.falabella.com"
TOTTUS_SEARCH_URL = "https://tottus.falabella.com/tottus-cl/search?Ntt={query}"
# Falabella REST API endpoint
FALABELLA_API = (
    "https://tottus.falabella.com/tottus-cl/rest/model/atg/commerce/catalog/"
    "ProductCatalogActor/getCatalogNav"
)
PLAYWRIGHT_ENABLED: bool = os.getenv("PLAYWRIGHT_ENABLED", "false").lower() == "true"


class TottusScraper(BaseScraper):

    async def search(self, query: str, *, limit: int = 40) -> ScrapedSearchResult:
        from backend.compliance import assert_live_store_access_allowed
        assert_live_store_access_allowed("tottus")

        try:
            return await self._try_api(query, limit)
        except NoResultsError:
            raise
        except Exception as exc:
            logger.warning("Tottus API failed: %s", exc)

        if PLAYWRIGHT_ENABLED:
            try:
                return await self._scrape_html_playwright(query, limit)
            except Exception as exc:
                logger.warning("Tottus Playwright scrape failed: %s", exc)

        raise ScraperError(
            "Tottus: API unavailable, HTML scraping requires PLAYWRIGHT_ENABLED=true"
        )

    async def _try_api(self, query: str, limit: int) -> ScrapedSearchResult:
        import httpx
        from backend.config import REQUEST_TIMEOUT, STORE_SSL_VERIFY

        params = {
            "Ntt": query,
            "No": 0,
            "Nrpp": limit,
            "sortBy": "BEST_MATCH",
            "sortOrder": "ASC",
            "site": "TOTTUS",
            "zone": "ZONE_01",
        }
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
        }
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            transport=httpx.AsyncHTTPTransport(verify=STORE_SSL_VERIFY, retries=2),
        ) as client:
            resp = await client.get(FALABELLA_API, params=params, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        records = (
            data.get("records")
            or data.get("products")
            or (data.get("resultList") or {}).get("records")
            or []
        )
        if not records:
            raise NoResultsError(query)

        products = [self._normalize(r) for r in records[:limit]]
        return ScrapedSearchResult(
            query=query,
            applied_query=query,
            products=products,
            source_url=FALABELLA_API,
            fetch_strategy="api",
            parse_strategy="falabella_rest_api",
        )

    def _normalize(self, raw: dict) -> dict:
        attrs = raw.get("attributes") or {}
        prices = raw.get("prices") or [{}]
        price = prices[0].get("originalPrice") or prices[0].get("price") or 0
        images = raw.get("images") or [{}]
        return {
            "name": raw.get("displayName") or attrs.get("name") or "",
            "price": float(price),
            "brand": raw.get("brand") or attrs.get("brand") or "",
            "image": images[0].get("url") or "",
            "url": f"{TOTTUS_BASE}{raw.get('url') or ''}",
            "sku": raw.get("skuId") or raw.get("id") or "",
            "in_stock": raw.get("availability") != "out_of_stock",
            "source": "tottus",
        }

    async def _scrape_html_playwright(self, query: str, limit: int) -> ScrapedSearchResult:
        from playwright.async_api import async_playwright

        url = TOTTUS_SEARCH_URL.format(query=quote_plus(query))
        products: list[dict] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            await page.wait_for_selector("[data-testid='product-card']", timeout=10000)
            cards = await page.query_selector_all("[data-testid='product-card']")
            for card in cards[:limit]:
                name = await card.inner_text()
                products.append({"name": name.strip(), "price": 0, "source": "tottus", "in_stock": True})
            await browser.close()

        if not products:
            raise NoResultsError(query)
        return ScrapedSearchResult(
            query=query,
            applied_query=query,
            products=products,
            source_url=url,
            fetch_strategy="playwright",
            parse_strategy="html_playwright",
        )


async def search_tottus(query: str, limit: int = 40) -> ScrapedSearchResult:
    return await TottusScraper().search(query, limit=limit)
