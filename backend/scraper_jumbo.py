from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unicodedata import normalize as unicode_normalize
from urllib.parse import quote_plus, urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.config import (
    HTML_HEADER_PROFILES,
    JUMBO_PRODUCT_BASE_URL,
    JUMBO_SEARCH_URL,
    REQUEST_TIMEOUT,
)
from backend.parser import parse_catalog_page, parse_price_text
from backend.scraper import NoResultsError


JUMBO_CATALOG_API_URL = "https://sm-web-api.ecomm.cencosud.com/catalog/api/v2/products/search/"
JUMBO_CATALOG_API_KEY = "WlVnnB7c1BblmgUPOfg"


@dataclass(slots=True)
class SearchPage:
    query: str
    html: str
    url: str
    strategy: str


@dataclass(slots=True)
class ScrapedSearchResult:
    query: str
    applied_query: str
    products: list[dict]
    source_url: str
    fetch_strategy: str = "search:browser"
    parse_strategy: str = "next_data"


def _create_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _execute_catalog_query(session: requests.Session, query: str, limit: int) -> ScrapedSearchResult:
    """Execute a catalog search query for Jumbo."""
    url = JUMBO_SEARCH_URL.format(query=quote_plus(query))

    attempts: list[str] = []

    for profile_name, headers in HTML_HEADER_PROFILES:
        try:
            response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            parsed = parse_catalog_page(
                response.text,
                limit=limit,
                base_url=JUMBO_PRODUCT_BASE_URL,
            )
            if parsed.products:
                return ScrapedSearchResult(
                    query=query,
                    applied_query=query,
                    products=parsed.products,
                    source_url=response.url,
                    fetch_strategy=f"search:{profile_name}",
                    parse_strategy=parsed.parser or "unknown",
                )
        except Exception as exc:
            attempts.append(f"search:{profile_name}: {exc}")
            continue

    try:
        result = _execute_catalog_api_query(session, query, limit)
        if result.products:
            return result
    except Exception as exc:
        attempts.append(f"catalog_api: {exc}")

    raise NoResultsError(query, attempts=attempts)


def _execute_catalog_api_query(
    session: requests.Session,
    query: str,
    limit: int,
) -> ScrapedSearchResult:
    """Fetch Jumbo products from the public catalog API used by the frontend."""
    headers = {
        "apiKey": JUMBO_CATALOG_API_KEY,
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.jumbo.cl",
        "Referer": JUMBO_SEARCH_URL.format(query=quote_plus(query)),
        "User-Agent": "Mozilla/5.0",
    }
    response = session.get(
        JUMBO_CATALOG_API_URL,
        params={"ft": query, "page": 1, "sc": 11},
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    payload = response.json()
    raw_products = payload.get("products", []) if isinstance(payload, dict) else payload
    if not isinstance(raw_products, list):
        raw_products = []

    products: list[dict] = []
    seen: set[str] = set()
    for raw in raw_products:
        if len(products) >= limit:
            break
        if not isinstance(raw, dict):
            continue
        product = _normalize_api_product(raw, position=len(products) + 1)
        if not product:
            continue
        key = product.get("sku") or product.get("url") or f"{product['name']}::{product['price']}"
        if key in seen:
            continue
        seen.add(key)
        products.append(product)

    return ScrapedSearchResult(
        query=query,
        applied_query=query,
        products=products,
        source_url=response.url,
        fetch_strategy="catalog_api",
        parse_strategy="vtex_catalog_api",
    )


def _normalize_api_product(raw: dict[str, Any], *, position: int) -> dict | None:
    item = _first_dict(raw.get("items"))
    seller = _first_dict(item.get("sellers") if item else None)
    offer = seller.get("commertialOffer") if seller else {}
    if not isinstance(offer, dict):
        offer = {}

    price = parse_price_text(offer.get("Price"))
    if price is None:
        return None

    original_price = parse_price_text(offer.get("ListPrice"))
    if original_price is not None and original_price <= price:
        original_price = None

    name = raw.get("productName") or (item or {}).get("name")
    if not name:
        return None

    image = _extract_image(item)
    available_quantity = parse_price_text(offer.get("AvailableQuantity")) or 0
    savings_amount = original_price - price if original_price and original_price > price else None
    link_text = raw.get("linkText")

    return {
        "id": _to_text(raw.get("productId")),
        "sku": _to_text((item or {}).get("itemId") or raw.get("productReference")),
        "name": _to_text(name),
        "brand": _to_text(raw.get("brand")),
        "category": _extract_category(raw),
        "price": price,
        "original_price": original_price,
        "discount_percent": _discount_percent(price, original_price),
        "savings_amount": savings_amount,
        "savings_text": None,
        "unit_price": None,
        "image": image,
        "url": urljoin(JUMBO_PRODUCT_BASE_URL, f"/{link_text}/p") if link_text else None,
        "availability": "IN_STOCK" if available_quantity > 0 else "OUT_OF_STOCK",
        "in_stock": available_quantity > 0,
        "seller": _to_text(seller.get("sellerName") if seller else None) or "Jumbo",
        "badges": [],
        "is_offer": bool(savings_amount and savings_amount > 0),
        "position": position,
    }


def _first_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
    return {}


def _extract_image(item: dict[str, Any] | None) -> str | None:
    if not item:
        return None
    image = _first_dict(item.get("images"))
    return _to_text(image.get("imageUrl"))


def _extract_category(raw: dict[str, Any]) -> str | None:
    categories = raw.get("categories")
    if not isinstance(categories, list) or not categories:
        return None
    parts = [part for part in str(categories[0]).split("/") if part]
    return parts[-1] if parts else None


def _discount_percent(price: float | None, original_price: float | None) -> int | None:
    if not price or not original_price or original_price <= price:
        return None
    return round(((original_price - price) / original_price) * 100)


def _to_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def search_jumbo(query: str, limit: int = 24) -> ScrapedSearchResult:
    """Search for products on Jumbo.cl."""
    normalized_query = normalize_query(query)

    with _create_session() as session:
        try:
            return _execute_catalog_query(session, normalized_query, limit)
        except NoResultsError:
            # For Jumbo, we might not have suggestions like Lider, so just re-raise
            raise


def normalize_query(query: str) -> str:
    """Normalize search query."""
    return unicode_normalize("NFC", query.strip().lower())
