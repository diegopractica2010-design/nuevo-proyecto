from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup

from backend.domain.normalization.matching import canonicalize
from backend.domain.product import Product
from backend.infrastructure.scrapers.base import BaseScraper


logger = logging.getLogger(__name__)

LIDER_SEARCH_URL = "https://super.lider.cl/search"


@dataclass(frozen=True)
class ScrapedProduct:
    name: str
    price: float
    product: Product


class LiderScraper(BaseScraper):
    """
    Scraper de Lider.cl.

    Estrategias de extraccion, en orden:
    1. JSON embebido en <script id="__NEXT_DATA__">.
    2. JSON en window.__INITIAL_STATE__.
    3. Parseo HTML directo como ultimo recurso.
    """

    def search(self, query: str, limit: int = 36) -> list[ScrapedProduct]:
        html = self.get(LIDER_SEARCH_URL, params={"q": query})
        products = self.parse_products(html, limit=limit)
        if not products:
            logger.warning(
                "Lider scraper retorno 0 productos para query=%r. "
                "El sitio puede haber cambiado su estructura.",
                query,
            )
        return products

    def parse_products(self, html: str, limit: int = 36) -> list[ScrapedProduct]:
        products = self._parse_next_data(html, limit)
        if products:
            logger.debug("Lider: estrategia __NEXT_DATA__ exitosa (%d productos)", len(products))
            return products

        products = self._parse_initial_state(html, limit)
        if products:
            logger.debug("Lider: estrategia __INITIAL_STATE__ exitosa (%d productos)", len(products))
            return products

        logger.warning(
            "Lider: JSON embebido no encontrado. Usando parseo HTML directo. "
            "Esto indica que el sitio puede haber cambiado."
        )
        products = self._parse_html_direct(html, limit)
        if products:
            logger.debug("Lider: estrategia HTML directa exitosa (%d productos)", len(products))
        return products

    def _parse_next_data(self, html: str, limit: int) -> list[ScrapedProduct]:
        try:
            soup = BeautifulSoup(html, "html.parser")
            script = soup.find("script", {"id": "__NEXT_DATA__"})
            if not script or not script.string:
                return []

            data = json.loads(script.string)
            raw_products = self._extract_products_from_next_data(data)
            return self._normalize_json_products(raw_products, limit) if raw_products else []
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.debug("_parse_next_data fallo: %s", exc)
            return []

    def _extract_products_from_next_data(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        candidate_paths = [
            ["props", "pageProps", "searchResult", "products"],
            ["props", "pageProps", "data", "search", "products"],
            ["props", "pageProps", "initialData", "products"],
            ["props", "pageProps", "products"],
            ["props", "pageProps", "searchData", "products"],
            ["props", "pageProps", "dehydratedState", "queries"],
        ]

        for path in candidate_paths:
            node: Any = data
            for key in path:
                if not isinstance(node, dict):
                    break
                node = node.get(key)
            products = self._coerce_product_list(node)
            if products:
                return products

        return self._recursive_find_product_list(data, depth=0, max_depth=8)

    def _parse_initial_state(self, html: str, limit: int) -> list[ScrapedProduct]:
        match = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*({.*?})\s*</script>",
            html,
            flags=re.DOTALL,
        )
        if not match:
            return []
        try:
            data = json.loads(match.group(1))
            raw_products = self._recursive_find_product_list(data, depth=0, max_depth=8)
            return self._normalize_json_products(raw_products, limit) if raw_products else []
        except json.JSONDecodeError as exc:
            logger.debug("_parse_initial_state fallo: %s", exc)
            return []

    def _coerce_product_list(self, node: Any) -> list[dict[str, Any]]:
        if isinstance(node, list):
            if node and all(isinstance(item, dict) for item in node):
                if self._looks_like_product(node[0]):
                    return node
                for item in node:
                    nested = self._recursive_find_product_list(item, depth=0, max_depth=4)
                    if nested:
                        return nested
        if isinstance(node, dict):
            return self._recursive_find_product_list(node, depth=0, max_depth=4)
        return []

    def _recursive_find_product_list(self, node: Any, depth: int, max_depth: int) -> list[dict[str, Any]]:
        if depth > max_depth:
            return []

        if isinstance(node, list) and node:
            dict_items = [item for item in node if isinstance(item, dict)]
            if len(dict_items) >= 1 and self._looks_like_product(dict_items[0]):
                return dict_items

        if isinstance(node, dict):
            for value in node.values():
                result = self._recursive_find_product_list(value, depth + 1, max_depth)
                if result:
                    return result

        if isinstance(node, list):
            for value in node:
                result = self._recursive_find_product_list(value, depth + 1, max_depth)
                if result:
                    return result

        return []

    def _looks_like_product(self, raw: dict[str, Any]) -> bool:
        keys = set(raw.keys())
        name_keys = {"displayName", "name", "productName", "title", "description", "brand"}
        price_keys = {
            "price",
            "prices",
            "priceDetail",
            "listPrice",
            "normalPrice",
            "offerPrice",
            "priceText",
            "priceFormatted",
        }
        return bool(keys & name_keys) and bool(keys & price_keys)

    def _normalize_json_products(self, raw_products: list[dict[str, Any]], limit: int) -> list[ScrapedProduct]:
        products: list[ScrapedProduct] = []
        seen: set[tuple[str, float]] = set()

        for raw in raw_products:
            if len(products) >= limit:
                break
            try:
                name = self._extract_name_from_json(raw)
                price = self._extract_price_from_json(raw)
                if not name or price is None or price <= 0:
                    continue

                key = (name, price)
                if key in seen:
                    continue
                seen.add(key)

                products.append(ScrapedProduct(name=name, price=price, product=canonicalize(name)))
            except Exception as exc:
                logger.debug("Producto Lider omitido: %s | raw=%s", exc, str(raw)[:200])

        return products

    def _extract_name_from_json(self, raw: dict[str, Any]) -> str | None:
        for key in ("displayName", "name", "productName", "title", "description"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        brand = raw.get("brand")
        if isinstance(brand, dict):
            value = brand.get("name")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _extract_price_from_json(self, raw: dict[str, Any]) -> float | None:
        prices_obj = raw.get("prices") or raw.get("priceDetail") or raw.get("priceInfo") or {}
        if isinstance(prices_obj, dict):
            for key in ("offerPrice", "promotionalPrice", "salePrice", "normalPrice", "listPrice", "price"):
                price = _coerce_price(prices_obj.get(key))
                if price:
                    return price

            nested = self._recursive_find_price(prices_obj, depth=0, max_depth=3)
            if nested:
                return nested

        for key in ("offerPrice", "promotionalPrice", "salePrice", "price", "listPrice", "normalPrice"):
            price = _coerce_price(raw.get(key))
            if price:
                return price

        for key in ("priceText", "priceFormatted"):
            price = _coerce_price(raw.get(key))
            if price:
                return price

        return self._recursive_find_price(raw, depth=0, max_depth=3)

    def _recursive_find_price(self, node: Any, depth: int, max_depth: int) -> float | None:
        if depth > max_depth:
            return None
        price = _coerce_price(node)
        if price:
            return price
        if isinstance(node, dict):
            for key, value in node.items():
                if "price" in str(key).lower() or "precio" in str(key).lower():
                    price = _coerce_price(value)
                    if price:
                        return price
                result = self._recursive_find_price(value, depth + 1, max_depth)
                if result:
                    return result
        if isinstance(node, list):
            for value in node:
                result = self._recursive_find_price(value, depth + 1, max_depth)
                if result:
                    return result
        return None

    def _parse_html_direct(self, html: str, limit: int) -> list[ScrapedProduct]:
        soup = BeautifulSoup(html, "html.parser")
        products: list[ScrapedProduct] = []

        for container in self._candidate_containers(soup):
            name = self._extract_name_from_html(container)
            price = self._extract_price_from_html(container)
            if not name or price is None:
                continue

            products.append(ScrapedProduct(name=name, price=price, product=canonicalize(name)))
            if len(products) >= limit:
                break

        return products

    def _candidate_containers(self, soup: BeautifulSoup):
        selectors = [
            "[data-testid*='product']",
            "[class*='product']",
            "article",
            "li",
        ]
        seen: set[int] = set()
        for selector in selectors:
            for node in soup.select(selector):
                node_id = id(node)
                if node_id not in seen:
                    seen.add(node_id)
                    yield node

    def _extract_name_from_html(self, container) -> str | None:
        selectors = [
            "[data-testid*='product-title']",
            "[data-testid*='product-name']",
            "[class*='title']",
            "[class*='name']",
            "h1",
            "h2",
            "h3",
            "a",
        ]
        for selector in selectors:
            node = container.select_one(selector)
            if node:
                text = node.get_text(" ", strip=True)
                if text and not _looks_like_price(text):
                    return text
        return None

    def _extract_price_from_html(self, container) -> float | None:
        selectors = [
            "[data-testid*='price']",
            "[class*='price']",
            "[aria-label*='$']",
        ]
        for selector in selectors:
            node = container.select_one(selector)
            if node:
                price = _parse_price_string(node.get_text(" ", strip=True) or node.get("aria-label", ""))
                if price is not None:
                    return price

        return _parse_price_string(container.get_text(" ", strip=True))


def _looks_like_price(text: str) -> bool:
    return _parse_price_string(text) is not None and len(text.split()) <= 4


def _coerce_price(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    if isinstance(value, str):
        return _parse_price_string(value)
    if isinstance(value, dict):
        for key in ("amount", "value", "price", "centAmount"):
            price = _coerce_price(value.get(key))
            if price:
                return price
    return None


def _parse_price_string(text: str) -> float | None:
    match = re.search(r"\$\s*([0-9][0-9.\s]*)", text)
    if not match:
        match = re.search(r"\b([0-9]{3,}(?:\.[0-9]{3})*)\b", text)
    if not match:
        return None
    raw_value = re.sub(r"\D", "", match.group(1))
    if not raw_value:
        return None
    return float(raw_value)


def search_lider(query: str, limit: int = 36) -> list[ScrapedProduct]:
    return LiderScraper().search(query, limit=limit)
