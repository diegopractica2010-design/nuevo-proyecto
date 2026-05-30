"""Santa Isabel scraper (Cencosud subsidiary, same VTEX/Next.js platform as Jumbo)."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote_plus, urljoin

from backend.infrastructure.scrapers.base import BaseScraper
from backend.scraper import ScrapedSearchResult, NoResultsError, normalize_query

logger = logging.getLogger(__name__)

SANTA_ISABEL_BASE_URL = "https://www.santaisabel.cl"
SANTA_ISABEL_SEARCH_URL = "https://www.santaisabel.cl/busqueda?ft={query}"
CENCOSUD_API_URL = "https://sm-web-api.ecomm.cencosud.com/catalog/api/v2/products/search/"


class SantaIsabelScraper(BaseScraper):
    """
    Scraper for Santa Isabel (Cencosud subsidiary).
    Strategy 1: __NEXT_DATA__ (same as Jumbo — Cencosud VTEX platform).
    Strategy 2: Cencosud catalog API.
    """

    async def search(self, query: str, *, limit: int = 40) -> ScrapedSearchResult:
        from backend.compliance import assert_live_store_access_allowed
        assert_live_store_access_allowed("santa_isabel")

        normalized = normalize_query(query)
        url = SANTA_ISABEL_SEARCH_URL.format(query=quote_plus(normalized))

        try:
            return await self._try_next_data(normalized, url, limit)
        except Exception as exc:
            logger.warning("Santa Isabel __NEXT_DATA__ strategy failed: %s", exc)

        try:
            return await self._try_catalog_api(normalized, limit)
        except Exception as exc:
            logger.warning("Santa Isabel catalog API strategy failed: %s", exc)
            raise NoResultsError(query, message=f"Santa Isabel: no se pudo obtener resultados ({exc})")

    async def _try_next_data(self, query: str, url: str, limit: int) -> ScrapedSearchResult:
        from backend.config import HTML_HEADER_PROFILES, REQUEST_TIMEOUT, STORE_SSL_VERIFY
        import httpx, json
        from bs4 import BeautifulSoup

        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            transport=httpx.AsyncHTTPTransport(verify=STORE_SSL_VERIFY, retries=2),
        ) as client:
            headers = dict(HTML_HEADER_PROFILES[1][1])  # browser profile
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        tag = soup.find("script", id="__NEXT_DATA__")
        if not tag:
            raise ValueError("__NEXT_DATA__ not found")

        data: dict = json.loads(tag.string or "{}")
        products_raw = self._extract_products_from_next_data(data)
        if not products_raw:
            raise NoResultsError(query)

        products = [self._normalize_product(p) for p in products_raw[:limit]]
        return ScrapedSearchResult(
            query=query,
            applied_query=query,
            products=products,
            source_url=url,
            fetch_strategy="html",
            parse_strategy="next_data",
        )

    def _extract_products_from_next_data(self, data: dict) -> list[dict]:
        try:
            page_props = data["props"]["pageProps"]
            results = (
                page_props.get("searchData", {}).get("products")
                or page_props.get("products")
                or []
            )
            return results
        except (KeyError, TypeError):
            return []

    async def _try_catalog_api(self, query: str, limit: int) -> ScrapedSearchResult:
        import httpx
        from backend.config import REQUEST_TIMEOUT, STORE_SSL_VERIFY

        params = {
            "store": "SI",
            "query": query,
            "from": 0,
            "to": limit - 1,
            "sort": "relevance",
        }
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            transport=httpx.AsyncHTTPTransport(verify=STORE_SSL_VERIFY, retries=2),
        ) as client:
            resp = await client.get(CENCOSUD_API_URL, params=params)
            resp.raise_for_status()

        data = resp.json()
        products_raw = data.get("products") or data.get("items") or []
        if not products_raw:
            raise NoResultsError(query)

        products = [self._normalize_product_api(p) for p in products_raw[:limit]]
        return ScrapedSearchResult(
            query=query,
            applied_query=query,
            products=products,
            source_url=CENCOSUD_API_URL,
            fetch_strategy="api",
            parse_strategy="cencosud_catalog_api",
        )

    def _normalize_product(self, raw: dict) -> dict:
        price_info = raw.get("priceRange", {}).get("sellingPrice", {})
        price = price_info.get("lowPrice") or price_info.get("highPrice") or 0
        return {
            "name": raw.get("productName") or raw.get("name") or "",
            "price": float(price),
            "brand": raw.get("brand") or "",
            "image": (raw.get("items") or [{}])[0].get("images", [{}])[0].get("imageUrl") or "",
            "url": urljoin(SANTA_ISABEL_BASE_URL, raw.get("link") or raw.get("linkText") or ""),
            "sku": raw.get("productId") or "",
            "in_stock": raw.get("availability") != "unavailable",
            "source": "santa_isabel",
        }

    def _normalize_product_api(self, raw: dict) -> dict:
        price = raw.get("price") or raw.get("sellingPrice") or 0
        return {
            "name": raw.get("name") or raw.get("productName") or "",
            "price": float(price),
            "brand": raw.get("brand") or "",
            "image": raw.get("imageUrl") or "",
            "url": urljoin(SANTA_ISABEL_BASE_URL, raw.get("link") or ""),
            "sku": raw.get("id") or raw.get("productId") or "",
            "in_stock": True,
            "source": "santa_isabel",
        }


async def search_santa_isabel(query: str, limit: int = 40) -> ScrapedSearchResult:
    return await SantaIsabelScraper().search(query, limit=limit)
