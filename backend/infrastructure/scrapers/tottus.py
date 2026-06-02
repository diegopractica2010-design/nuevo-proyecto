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
# Falabella REST API — endpoint legacy ATG
FALABELLA_API = (
    "https://tottus.falabella.com/tottus-cl/rest/model/atg/commerce/catalog/"
    "ProductCatalogActor/getCatalogNav"
)
# VTEX API pública de Tottus (alternativa si el legacy falla)
TOTTUS_VTEX_API = "https://tottus.falabella.com/tottus-cl/api/catalog_system/pub/products/search/"
try:
    from backend.config import PLAYWRIGHT_ENABLED
except ImportError:
    PLAYWRIGHT_ENABLED: bool = os.getenv("PLAYWRIGHT_ENABLED", "false").lower() == "true"


class TottusScraper(BaseScraper):

    async def search(self, query: str, *, limit: int = 40) -> ScrapedSearchResult:
        from backend.compliance import assert_live_store_access_allowed
        from urllib.parse import quote_plus as _qp
        search_url = TOTTUS_SEARCH_URL.format(query=_qp(query))
        assert_live_store_access_allowed("tottus", search_url, purpose="search")

        last_exc: Exception | None = None

        # Estrategia 1: Falabella ATG legacy API
        try:
            return await self._try_api(query, limit)
        except Exception as exc:
            last_exc = exc
            logger.warning("Tottus legacy API failed: %s", exc)

        # Estrategia 2: VTEX API pública
        try:
            return await self._try_vtex_api(query, limit)
        except Exception as exc:
            last_exc = exc
            logger.warning("Tottus VTEX API failed: %s", exc)

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
        prices = raw.get("prices") or []
        price_obj = prices[0] if prices else {}
        price = (
            price_obj.get("originalPrice")
            or price_obj.get("price")
            or price_obj.get("salePrice")
            or 0
        )
        images = raw.get("images") or []
        image_url = images[0].get("url") or "" if images else ""
        return {
            "name": raw.get("displayName") or attrs.get("name") or "",
            "price": float(price),
            "brand": raw.get("brand") or attrs.get("brand") or "",
            "image": image_url,
            "url": f"{TOTTUS_BASE}{raw.get('url') or ''}",
            "sku": raw.get("skuId") or raw.get("id") or "",
            "in_stock": raw.get("availability") != "out_of_stock",
            "source": "tottus",
        }

    async def _try_vtex_api(self, query: str, limit: int) -> ScrapedSearchResult:
        """VTEX API pública de Tottus/Falabella."""
        import httpx
        from backend.config import REQUEST_TIMEOUT, STORE_SSL_VERIFY
        from urllib.parse import quote_plus as _qp

        params = {"ft": query, "_from": 0, "_to": limit - 1}
        headers = {
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
            "Referer": TOTTUS_SEARCH_URL.format(query=_qp(query)),
            "Origin": TOTTUS_BASE,
        }
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            transport=httpx.AsyncHTTPTransport(verify=STORE_SSL_VERIFY, retries=2),
        ) as client:
            resp = await client.get(TOTTUS_VTEX_API, params=params, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        products_raw = data if isinstance(data, list) else (data.get("products") or [])
        if not products_raw:
            raise NoResultsError(query)

        products = [self._normalize_vtex(p) for p in products_raw[:limit]]
        return ScrapedSearchResult(
            query=query,
            applied_query=query,
            products=products,
            source_url=TOTTUS_VTEX_API,
            fetch_strategy="api",
            parse_strategy="tottus_vtex_api",
        )

    def _normalize_vtex(self, raw: dict) -> dict:
        items = raw.get("items") or []
        item = items[0] if items else {}
        sellers = item.get("sellers") or []
        offer = (sellers[0] if sellers else {}).get("commertialOffer") or {}
        price = offer.get("Price") or offer.get("price") or 0
        images = item.get("images") or []
        image_url = images[0].get("imageUrl") or "" if images else ""
        return {
            "name": raw.get("productName") or raw.get("name") or item.get("name") or "",
            "price": float(price),
            "brand": raw.get("brand") or "",
            "image": image_url,
            "url": f"{TOTTUS_BASE}{raw.get('link') or raw.get('linkText') or ''}",
            "sku": raw.get("productId") or item.get("itemId") or "",
            "in_stock": (offer.get("AvailableQuantity") or 0) > 0,
            "source": "tottus",
        }

    async def _scrape_html_playwright(self, query: str, limit: int) -> ScrapedSearchResult:
        from playwright.async_api import async_playwright
        import re as _re

        url = TOTTUS_SEARCH_URL.format(query=quote_plus(query))
        products: list[dict] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
                )
            )
            await page.goto(url, timeout=30000)
            # Intenta varios selectores de card (Falabella puede cambiarlos)
            card_selector = (
                "[data-testid='product-card'], "
                "[class*='product-card'], "
                "article[class*='product']"
            )
            try:
                await page.wait_for_selector(card_selector, timeout=12000)
            except Exception:
                pass
            cards = await page.query_selector_all(card_selector)
            for card in cards[:limit]:
                # Nombre
                name_el = await card.query_selector(
                    "[data-testid='product-name'], [class*='product-name'], "
                    "[class*='title'], h3, h2"
                )
                name = (await name_el.inner_text()).strip() if name_el else ""
                if not name:
                    name = (await card.inner_text()).strip()[:80]

                # Precio
                price_el = await card.query_selector(
                    "[data-testid='product-price'], [class*='price'], "
                    "[aria-label*='$'], span[class*='Price']"
                )
                price_text = (await price_el.inner_text()).strip() if price_el else ""
                price_digits = "".join(c for c in price_text if c.isdigit())
                price = float(price_digits) if price_digits else 0.0

                # Imagen
                img_el = await card.query_selector("img")
                image = (await img_el.get_attribute("src") or "") if img_el else ""

                # URL
                link_el = await card.query_selector("a[href]")
                href = (await link_el.get_attribute("href") or "") if link_el else ""
                url_product = f"{TOTTUS_BASE}{href}" if href.startswith("/") else href

                if name:
                    products.append({
                        "name": name,
                        "price": price,
                        "image": image,
                        "url": url_product,
                        "source": "tottus",
                        "in_stock": True,
                    })
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
