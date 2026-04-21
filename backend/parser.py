from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from unicodedata import normalize as unicode_normalize
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from backend.config import MAX_RESULTS, PRODUCT_BASE_URL


@dataclass(slots=True)
class ParseResult:
    products: list[dict]
    parser: str | None = None


def parse_price_text(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    cleaned = re.sub(r"[^\d,\.]", "", str(value))
    if not cleaned:
        return None

    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "." in cleaned and "," not in cleaned:
        parts = cleaned.split(".")
        if all(part.isdigit() for part in parts) and all(len(part) == 3 for part in parts[1:]):
            cleaned = "".join(parts)
    elif "," in cleaned and "." not in cleaned:
        parts = cleaned.split(",")
        if all(part.isdigit() for part in parts) and all(len(part) == 3 for part in parts[1:]):
            cleaned = "".join(parts)
        else:
            cleaned = cleaned.replace(",", ".")
    elif cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")

    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, dict):
        return _normalize_text(value.get("name") or value.get("text"))

    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def _strip_tracking(url: str) -> str:
    split = urlsplit(url)
    return urlunsplit((split.scheme, split.netloc, split.path, "", ""))


def _normalize_url(url: str | None) -> str | None:
    normalized = _normalize_text(url)
    if not normalized:
        return None

    if normalized.startswith("//"):
        normalized = f"https:{normalized}"
    elif normalized.startswith("/"):
        normalized = urljoin(PRODUCT_BASE_URL, normalized)

    return _strip_tracking(normalized)


def _normalize_image(url: str | None) -> str | None:
    normalized = _normalize_text(url)
    if not normalized:
        return None

    if normalized.startswith("//"):
        return f"https:{normalized}"

    return normalized


def _normalize_badges(raw_badges: Any) -> list[str]:
    if raw_badges is None:
        return []

    if isinstance(raw_badges, list):
        labels = [_normalize_text(item) for item in raw_badges]
        return [label for label in labels if label]

    if not isinstance(raw_badges, dict):
        label = _normalize_text(raw_badges)
        return [label] if label else []

    labels: list[str] = []
    for collection_name in ("flags", "tags"):
        collection = raw_badges.get(collection_name)
        if not isinstance(collection, Iterable):
            continue
        for badge in collection:
            text = _normalize_text(badge)
            if text and text not in labels:
                labels.append(text)

    return labels


def _normalize_availability(value: Any) -> str | None:
    text = _normalize_text(value)
    if not text:
        return None

    upper = text.upper()
    if "INSTOCK" in upper or "IN_STOCK" in upper:
        return "IN_STOCK"
    if "OUTOFSTOCK" in upper or "OUT_OF_STOCK" in upper:
        return "OUT_OF_STOCK"
    return upper


def _is_in_stock(value: Any) -> bool:
    return _normalize_availability(value) == "IN_STOCK"


def _extract_json_object(source: str, key: str) -> dict | None:
    marker = f'"{key}":'
    start = source.find(marker)
    if start == -1:
        return None

    index = start + len(marker)
    while index < len(source) and source[index].isspace():
        index += 1

    if index >= len(source) or source[index] != "{":
        return None

    depth = 0
    in_string = False
    escape = False

    for current in range(index, len(source)):
        char = source[current]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(source[index : current + 1])
                except json.JSONDecodeError:
                    return None

    return None


def _extract_next_data_search_result(html: str) -> dict | None:
    match = re.search(r"<script id=__NEXT_DATA__[^>]*>(.*?)</script>", html, flags=re.S)
    if not match:
        return None

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None

    page_props = payload.get("props", {}).get("pageProps", {})
    initial_data = page_props.get("initialData") or {}
    search_result = initial_data.get("searchResult")
    return search_result if isinstance(search_result, dict) else None


def _normalize_discount_percent(price: float | None, original_price: float | None) -> int | None:
    if not price or not original_price or original_price <= price:
        return None

    discount = round(((original_price - price) / original_price) * 100)
    return discount if discount > 0 else None


def _get_category(item: dict) -> str | None:
    category = item.get("category") or {}
    path = category.get("path") or []
    if not path:
        return None

    last_segment = path[-1]
    return _normalize_text(last_segment)


def _append_product(products: list[dict], seen: set[str], raw_product: dict):
    if not raw_product.get("name") or raw_product.get("price") is None:
        return

    dedupe_key = (
        raw_product.get("sku")
        or raw_product.get("url")
        or f"{raw_product['name']}::{raw_product['price']}"
    )
    if dedupe_key in seen:
        return

    seen.add(dedupe_key)
    products.append(raw_product)


def _normalize_search_state_item(item: dict, *, position: int) -> dict | None:
    price_info = item.get("priceInfo") or {}
    price = (
        parse_price_text(price_info.get("linePrice"))
        or parse_price_text(price_info.get("itemPrice"))
        or parse_price_text(price_info.get("wasPrice"))
    )
    if price is None:
        return None

    original_price = parse_price_text(price_info.get("itemPrice"))
    was_price = parse_price_text(price_info.get("wasPrice"))
    if original_price is None or original_price <= price:
        original_price = was_price if was_price and was_price > price else None

    savings_amount = parse_price_text(price_info.get("savingsAmt"))
    if savings_amount is None:
        savings_amount = parse_price_text(price_info.get("savings"))
    if savings_amount is None and original_price and original_price > price:
        savings_amount = original_price - price

    image_info = item.get("imageInfo") or {}
    all_images = image_info.get("allImages") or []
    image = image_info.get("thumbnailUrl")
    if not image and all_images:
        first_image = all_images[0]
        if isinstance(first_image, dict):
            image = first_image.get("url")

    availability = item.get("availabilityStatusV2") or {}
    availability_value = availability.get("value") or availability.get("display")
    normalized_availability = _normalize_availability(availability_value)
    normalized_badges = _normalize_badges(item.get("badges"))

    return {
        "id": _normalize_text(item.get("id")),
        "sku": _normalize_text(item.get("usItemId")),
        "name": _normalize_text(item.get("name")),
        "brand": _normalize_text(item.get("brand")),
        "category": _get_category(item),
        "price": price,
        "original_price": original_price,
        "discount_percent": _normalize_discount_percent(price, original_price),
        "savings_amount": savings_amount,
        "savings_text": _normalize_text(price_info.get("savings")),
        "unit_price": _normalize_text(price_info.get("unitPrice")),
        "image": _normalize_image(image or item.get("image")),
        "url": _normalize_url(item.get("canonicalUrl")),
        "availability": normalized_availability,
        "in_stock": _is_in_stock(availability_value),
        "seller": _normalize_text(item.get("sellerName")) or "Lider",
        "badges": normalized_badges,
        "is_offer": bool((savings_amount and savings_amount > 0) or normalized_badges),
        "position": position,
    }


def _parse_search_result(search_result: dict, limit: int) -> list[dict]:
    products: list[dict] = []
    seen: set[str] = set()

    for stack in search_result.get("itemStacks", []):
        items = stack.get("items") or []
        for item in items:
            if not isinstance(item, dict):
                continue

            raw_product = _normalize_search_state_item(item, position=len(products) + 1)
            if raw_product is None:
                continue

            _append_product(products, seen, raw_product)
            if len(products) >= limit:
                return products

    return products


def _normalize_ldjson_offer(offers: Any) -> dict:
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    return offers if isinstance(offers, dict) else {}


def _parse_next_data(html: str, limit: int) -> ParseResult:
    search_result = _extract_next_data_search_result(html)
    if not isinstance(search_result, dict):
        return ParseResult(products=[], parser=None)

    return ParseResult(products=_parse_search_result(search_result, limit), parser="next_data")


def _parse_inline_search_result(html: str, limit: int) -> ParseResult:
    search_result = _extract_json_object(html, "searchResult")
    if not isinstance(search_result, dict):
        return ParseResult(products=[], parser=None)

    return ParseResult(products=_parse_search_result(search_result, limit), parser="inline_search")


def _parse_ld_json(soup: BeautifulSoup, limit: int) -> ParseResult:
    products: list[dict] = []
    seen: set[str] = set()

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "{}")
        except json.JSONDecodeError:
            continue

        if not isinstance(data, dict) or data.get("@type") != "ItemList":
            continue

        for item in data.get("itemListElement", []):
            product = item.get("item") or {}
            offers = _normalize_ldjson_offer(product.get("offers"))
            price = parse_price_text(offers.get("price"))
            if price is None:
                continue

            availability = offers.get("availability")
            raw_product = {
                "id": None,
                "sku": None,
                "name": _normalize_text(product.get("name")),
                "brand": _normalize_text(product.get("brand")),
                "category": None,
                "price": price,
                "original_price": None,
                "discount_percent": None,
                "savings_amount": None,
                "savings_text": None,
                "unit_price": None,
                "image": _normalize_image(product.get("image")),
                "url": _normalize_url(product.get("url")),
                "availability": _normalize_availability(availability),
                "in_stock": _is_in_stock(availability),
                "seller": "Lider",
                "badges": [],
                "is_offer": False,
                "position": len(products) + 1,
            }
            _append_product(products, seen, raw_product)
            if len(products) >= limit:
                return ParseResult(products=products, parser="ld_json")

    return ParseResult(products=products, parser="ld_json" if products else None)


def _slug_like(text: str) -> str:
    ascii_text = unicode_normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def _parse_html_fallback(soup: BeautifulSoup, limit: int) -> ParseResult:
    products: list[dict] = []
    seen: set[str] = set()
    selectors = [
        '[data-testid="list-view"]',
        '[data-testid="search-product-result"]',
        "div.product-card",
        "div.search-result__item",
        "li.product-item",
        "article",
    ]

    for selector in selectors:
        for card in soup.select(selector):
            if len(products) >= limit:
                return ParseResult(products=products, parser="html_fallback")

            name_node = (
                card.select_one('[data-automation-id="product-title"]')
                or card.select_one('[data-testid="product-title"]')
                or card.select_one("span.product-name")
                or card.select_one("h2")
                or card.select_one("h3")
                or card.select_one("a")
            )
            price_node = (
                card.select_one('[itemprop="price"]')
                or card.select_one('[data-automation-id="product-price"]')
                or card.select_one("span.price")
                or card.select_one("span.price__value")
                or card.select_one("div.price")
                or card.select_one("p.price")
            )
            image_node = card.select_one("img")
            link_node = card.select_one("a[href]")

            price_text = price_node.get_text(strip=True) if price_node else None
            if not price_text:
                text = " ".join(card.stripped_strings)
                match = re.search(r"\$\s?[\d\.\,]+", text)
                price_text = match.group(0) if match else None

            name = _normalize_text(name_node.get_text(" ", strip=True) if name_node else None)
            url = _normalize_url(link_node.get("href") if link_node else None)
            if url and not name:
                name = _normalize_text(link_node.get("title"))

            raw_product = {
                "id": None,
                "sku": None,
                "name": name,
                "brand": None,
                "category": None,
                "price": parse_price_text(price_text),
                "original_price": None,
                "discount_percent": None,
                "savings_amount": None,
                "savings_text": None,
                "unit_price": None,
                "image": _normalize_image(image_node.get("src") if image_node else None),
                "url": url,
                "availability": None,
                "in_stock": False,
                "seller": "Lider",
                "badges": [],
                "is_offer": False,
                "position": len(products) + 1,
            }
            _append_product(products, seen, raw_product)

    return ParseResult(products=products, parser="html_fallback" if products else None)


def parse_catalog_page(html: str, limit: int = MAX_RESULTS) -> ParseResult:
    if not html:
        return ParseResult(products=[], parser=None)

    for parser in (_parse_next_data, _parse_inline_search_result):
        parsed = parser(html, limit)
        if parsed.products:
            return parsed

    soup = BeautifulSoup(html, "html.parser")

    parsed = _parse_ld_json(soup, limit)
    if parsed.products:
        return parsed

    return _parse_html_fallback(soup, limit)


def parse_products(html: str, limit: int = MAX_RESULTS) -> list[dict]:
    return parse_catalog_page(html, limit).products
