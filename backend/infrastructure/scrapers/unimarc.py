"""
Unimarc scraper (SMU — aggressive Cloudflare anti-bot).

Strategy 1: SMU public API probe.
Strategy 2: Playwright headless (only if PLAYWRIGHT_ENABLED=true).
Strategy 3: Raise ScraperError.

To enable Playwright: pip install playwright && playwright install chromium
Set PLAYWRIGHT_ENABLED=true in environment.
"""
from __future__ import annotations

import logging
import os
from urllib.parse import quote_plus

from backend.infrastructure.scrapers.base import BaseScraper
from backend.scraper import ScrapedSearchResult, NoResultsError, ScraperError

logger = logging.getLogger(__name__)

UNIMARC_BASE = "https://www.unimarc.cl"
UNIMARC_SEARCH_URL = "https://www.unimarc.cl/search?text={query}"
UNIMARC_API_URL = "https://api.unimarc.cl/api/search"
PLAYWRIGHT_ENABLED: bool = os.getenv("PLAYWRIGHT_ENABLED", "false").lower() == "true"


class UnimarcScraper(BaseScraper):

    async def search(self, query: str, *, limit: int = 40) -> ScrapedSearchResult:
        from backend.compliance import assert_live_store_access_allowed
        assert_live_store_access_allowed("unimarc", UNIMARC_API_URL, purpose="search")

        try:
            return await self._try_api(query, limit)
        except NoResultsError:
            raise
        except Exception as exc:
            logger.warning("Unimarc API probe failed: %s", exc)

        if PLAYWRIGHT_ENABLED:
            try:
                return await self._scrape_playwright(query, limit)
            except Exception as exc:
                logger.warning("Unimarc Playwright scrape failed: %s", exc)

        raise ScraperError(
            "Unimarc: blocked by anti-bot, enable PLAYWRIGHT_ENABLED=true to use headless browser"
        )

    async def _try_api(self, query: str, limit: int) -> ScrapedSearchResult:
        import httpx
        from backend.config import REQUEST_TIMEOUT, STORE_SSL_VERIFY

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Origin": UNIMARC_BASE,
            "Referer": UNIMARC_BASE + "/",
        }
        params = {"q": query, "limit": limit}
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            transport=httpx.AsyncHTTPTransport(verify=STORE_SSL_VERIFY, retries=2),
        ) as client:
            resp = await client.get(UNIMARC_API_URL, params=params, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        items = data.get("products") or data.get("items") or data.get("results") or []
        if not items:
            raise NoResultsError(query)

        products = [self._normalize(p) for p in items[:limit]]
        return ScrapedSearchResult(
            query=query,
            applied_query=query,
            products=products,
            source_url=UNIMARC_API_URL,
            fetch_strategy="api",
            parse_strategy="unimarc_public_api",
        )

    def _normalize(self, raw: dict) -> dict:
        return {
            "name": raw.get("name") or raw.get("displayName") or "",
            "price": float(raw.get("price") or raw.get("sellingPrice") or 0),
            "brand": raw.get("brand") or "",
            "image": raw.get("imageUrl") or raw.get("image") or "",
            "url": raw.get("url") or "",
            "sku": str(raw.get("id") or raw.get("sku") or ""),
            "in_stock": raw.get("available", True),
            "source": "unimarc",
        }

    async def _scrape_playwright(self, query: str, limit: int) -> ScrapedSearchResult:
        from playwright.async_api import async_playwright

        url = UNIMARC_SEARCH_URL.format(query=quote_plus(query))
        products: list[dict] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
                )
            )
            page = await context.new_page()
            await page.goto(url, timeout=30000)
            try:
                await page.wait_for_selector("[data-testid='product-card']", timeout=10000)
                cards = await page.query_selector_all("[data-testid='product-card']")
                for card in cards[:limit]:
                    name_el = await card.query_selector("[data-testid='product-name']")
                    price_el = await card.query_selector("[data-testid='product-price']")
                    name = await name_el.inner_text() if name_el else ""
                    price_text = await price_el.inner_text() if price_el else "0"
                    price = float("".join(c for c in price_text if c.isdigit()) or "0")
                    img_el = await card.query_selector("img")
                    image = await img_el.get_attribute("src") if img_el else ""
                    products.append({"name": name.strip(), "price": price, "image": image, "source": "unimarc", "in_stock": True})
            finally:
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


async def search_unimarc(query: str, limit: int = 40) -> ScrapedSearchResult:
    return await UnimarcScraper().search(query, limit=limit)
