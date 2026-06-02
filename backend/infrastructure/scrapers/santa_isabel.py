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
# VTEX public REST API — no requiere autenticación
SANTA_ISABEL_VTEX_API = "https://www.santaisabel.cl/api/catalog_system/pub/products/search/"


class SantaIsabelScraper(BaseScraper):
    """
    Scraper for Santa Isabel (Cencosud subsidiary).
    Strategy 1: __NEXT_DATA__ (same as Jumbo — Cencosud VTEX platform).
    Strategy 2: Cencosud catalog API.
    """

    async def search(self, query: str, *, limit: int = 40) -> ScrapedSearchResult:
        from backend.compliance import assert_live_store_access_allowed
        normalized = normalize_query(query)
        url = SANTA_ISABEL_SEARCH_URL.format(query=quote_plus(normalized))
        assert_live_store_access_allowed("santa_isabel", url, purpose="search")

        # Estrategia 1: VTEX API pública (sin auth)
        try:
            return await self._try_vtex_api(normalized, limit)
        except Exception as exc:
            logger.warning("Santa Isabel VTEX API failed: %s", exc)

        # Estrategia 2: __NEXT_DATA__ del HTML
        try:
            return await self._try_next_data(normalized, url, limit)
        except Exception as exc:
            logger.warning("Santa Isabel __NEXT_DATA__ strategy failed: %s", exc)

        # Cencosud catalog API requiere auth (401) — no intentar
        raise NoResultsError(query, message="Santa Isabel: no se encontraron resultados (sitio requiere Playwright)")

    async def _try_next_data(self, query: str, url: str, limit: int) -> ScrapedSearchResult:
        import json  # stdlib — always available
        import httpx  # optional heavy dep — deferred import
        from backend.config import HTML_HEADER_PROFILES, REQUEST_TIMEOUT, STORE_SSL_VERIFY
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
        except (KeyError, TypeError):
            return []

        # Rutas conocidas en plataforma Cencosud (VTEX + Next.js)
        candidates = [
            page_props.get("searchData", {}).get("products"),
            page_props.get("products"),
            page_props.get("data", {}).get("products"),
            page_props.get("data", {}).get("search", {}).get("products"),
            page_props.get("initialData", {}).get("products"),
            page_props.get("initialData", {}).get("data", {}).get("products"),
            page_props.get("pageProps", {}).get("products"),
        ]
        for candidate in candidates:
            if isinstance(candidate, list) and candidate:
                return candidate

        # Fallback: React Query dehydrated state (Cencosud puede usarlo)
        queries = page_props.get("dehydratedState", {}).get("queries") or []
        for query_obj in queries:
            state_data = (query_obj.get("state") or {}).get("data") or {}
            products = state_data.get("products") or []
            if products:
                return products

        return []

    async def _try_vtex_api(self, query: str, limit: int) -> ScrapedSearchResult:
        """VTEX public REST API — no requiere autenticación."""
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
            "Referer": SANTA_ISABEL_SEARCH_URL.format(query=_qp(query)),
        }
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            transport=httpx.AsyncHTTPTransport(verify=STORE_SSL_VERIFY, retries=2),
        ) as client:
            resp = await client.get(SANTA_ISABEL_VTEX_API, params=params, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        # VTEX retorna lista directamente o dentro de "products"
        products_raw = data if isinstance(data, list) else (data.get("products") or [])
        if not products_raw:
            raise NoResultsError(query)

        products = [self._normalize_vtex(p) for p in products_raw[:limit]]
        return ScrapedSearchResult(
            query=query,
            applied_query=query,
            products=products,
            source_url=SANTA_ISABEL_VTEX_API,
            fetch_strategy="api",
            parse_strategy="vtex_public_api",
        )

    def _normalize_vtex(self, raw: dict) -> dict:
        """Normaliza un producto del formato VTEX estándar."""
        items = raw.get("items") or [{}]
        item = items[0] if items else {}
        sellers = item.get("sellers") or [{}]
        offer = (sellers[0] if sellers else {}).get("commertialOffer") or {}
        price = offer.get("Price") or offer.get("price") or 0
        images = item.get("images") or [{}]
        return {
            "name": raw.get("productName") or raw.get("name") or item.get("name") or "",
            "price": float(price),
            "brand": raw.get("brand") or "",
            "image": images[0].get("imageUrl") or "" if images else "",
            "url": urljoin(SANTA_ISABEL_BASE_URL, raw.get("link") or raw.get("linkText") or ""),
            "sku": raw.get("productId") or item.get("itemId") or "",
            "in_stock": (offer.get("AvailableQuantity") or 0) > 0,
            "source": "santa_isabel",
        }

    async def _try_catalog_api(self, query: str, limit: int) -> ScrapedSearchResult:
        import httpx
        from backend.config import REQUEST_TIMEOUT, STORE_SSL_VERIFY
        from urllib.parse import quote_plus as _qp

        params = {
            "store": "SI",
            "query": query,
            "from": 0,
            "to": limit - 1,
            "sort": "relevance",
        }
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": SANTA_ISABEL_BASE_URL,
            "Referer": SANTA_ISABEL_SEARCH_URL.format(query=_qp(query)),
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
        }
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            transport=httpx.AsyncHTTPTransport(verify=STORE_SSL_VERIFY, retries=2),
        ) as client:
            resp = await client.get(CENCOSUD_API_URL, params=params, headers=headers)
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
