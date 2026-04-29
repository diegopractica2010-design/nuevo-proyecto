from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

from backend.domain.normalization.matching import canonicalize
from backend.domain.product import Product
from backend.infrastructure.scrapers.base import BaseScraper


LIDER_SEARCH_URL = "https://super.lider.cl/search"


@dataclass(frozen=True)
class ScrapedProduct:
    name: str
    price: float
    product: Product


class LiderScraper(BaseScraper):
    def search(self, query: str, limit: int = 36) -> list[ScrapedProduct]:
        html = self.get(LIDER_SEARCH_URL, params={"q": query})
        return self.parse_products(html, limit=limit)

    def parse_products(self, html: str, limit: int = 36) -> list[ScrapedProduct]:
        soup = BeautifulSoup(html, "html.parser")
        products: list[ScrapedProduct] = []

        for container in self._candidate_containers(soup):
            name = self._extract_name(container)
            price = self._extract_price(container)
            if not name or price is None:
                continue

            products.append(
                ScrapedProduct(
                    name=name,
                    price=price,
                    product=canonicalize(name),
                )
            )
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

    def _extract_name(self, container) -> str | None:
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

    def _extract_price(self, container) -> float | None:
        selectors = [
            "[data-testid*='price']",
            "[class*='price']",
            "[aria-label*='$']",
        ]
        for selector in selectors:
            node = container.select_one(selector)
            if node:
                price = _parse_price(node.get_text(" ", strip=True) or node.get("aria-label", ""))
                if price is not None:
                    return price

        return _parse_price(container.get_text(" ", strip=True))


def _looks_like_price(text: str) -> bool:
    return _parse_price(text) is not None and len(text.split()) <= 4


def _parse_price(text: str) -> float | None:
    match = re.search(r"\$\s*([0-9][0-9.\s]*)", text)
    if not match:
        return None
    raw_value = re.sub(r"\D", "", match.group(1))
    if not raw_value:
        return None
    return float(raw_value)


def search_lider(query: str, limit: int = 36) -> list[ScrapedProduct]:
    return LiderScraper().search(query, limit=limit)
