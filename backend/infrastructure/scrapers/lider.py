from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any
from unicodedata import normalize as unicode_normalize
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from backend.config import (
    AUTOCOMPLETE_LIMIT,
    AUTOCOMPLETE_URL,
    HTML_HEADER_PROFILES,
    REQUEST_TIMEOUT,
    SEARCH_URL,
    SLUG_URL,
    SUGGESTION_FALLBACK_LIMIT,
)
from backend.compliance import assert_live_store_access_allowed
from backend.domain.normalization.matching import canonicalize
from backend.domain.product import Product
from backend.infrastructure.scrapers.base import BaseScraper
from backend.parser import _parse_search_result, parse_catalog_page
from backend.scraper import (
    ScrapedSearchResult,
    NoResultsError,
    ScraperError,
    normalize_query,
    fallback_query_variants,
    rank_products_for_query,
)


logger = logging.getLogger(__name__)

LIDER_GRAPHQL_URL = "https://super.lider.cl/orchestra/graphql"


@dataclass(frozen=True)
class ScrapedProduct:
    name: str
    price: float
    product: Product


class LiderScraper(BaseScraper):
    """
    Unified Scraper de Lider.cl con soporte para múltiples estrategias.

    Subclasses may override SEARCH_URL_TEMPLATE, SLUG_URL_TEMPLATE, and STORE_NAME
    to reuse all parsing logic for other Walmart-family stores (e.g. Acuenta).

    Estrategias de fetching:
    1. GraphQL API (getSearch, getSearchPage)
    2. HTML catalog pages con múltiples header profiles
    3. Slug-based catalog URLs

    Estrategias de parsing:
    1. JSON embebido en <script id="__NEXT_DATA__">
    2. JSON en window.__INITIAL_STATE__
    3. Parseo HTML directo como último recurso

    Fallbacks:
    - Autocomplete para sugerencias
    - Query variants (stopwords, ngrams)
    """

    SEARCH_URL_TEMPLATE: str | None = None  # None → use config.SEARCH_URL
    SLUG_URL_TEMPLATE: str | None = None    # None → use config.SLUG_URL
    STORE_NAME: str = "lider"

    def _get_search_url(self) -> str:
        return self.SEARCH_URL_TEMPLATE or SEARCH_URL

    def _get_slug_url(self) -> str:
        return self.SLUG_URL_TEMPLATE or SLUG_URL

    async def search(self, query: str, limit: int = 100) -> ScrapedSearchResult:
        """Ejecuta búsqueda y retorna ScrapedSearchResult con toda la metadata."""
        normalized_query = normalize_query(query)
        try:
            suggestions = await self._fetch_autocomplete_terms(normalized_query)

            try:
                result = await self._execute_catalog_query(normalized_query, limit)
                result.suggestions = suggestions
                return result
            except NoResultsError as exc:
                # Fallback a términos de autocomplete
                fallback_terms = [
                    term for term in suggestions
                    if term.lower() != normalized_query.lower()
                ][:SUGGESTION_FALLBACK_LIMIT]

                query_variants = fallback_query_variants(normalized_query)
                for term in [*query_variants, *fallback_terms]:
                    try:
                        rescued = await self._execute_catalog_query(term, limit)
                        rescued.suggestions = suggestions
                        rescued.warning = (
                            f'No hubo coincidencias directas para "{normalized_query}". '
                            f'Se muestran resultados reales para "{term}".'
                        )
                        rescued.applied_query = term
                        return rescued
                    except ScraperError:
                        continue

                raise NoResultsError(
                    normalized_query,
                    attempts=exc.attempts,
                    suggestions=suggestions,
                ) from exc
        finally:
            await self.aclose()

    async def _execute_catalog_query(self, query: str, limit: int) -> ScrapedSearchResult:
        """Ejecuta búsqueda en catálogo con paginación."""
        normalized_query = normalize_query(query)
        products: list[dict] = []
        seen: set[str] = set()
        source_url: str | None = None
        fetch_strategies: list[str] = []
        parse_strategy: str | None = None
        page = 1

        while len(products) < limit:
            try:
                page_result = await self._fetch_catalog_page(normalized_query, page, limit)
            except (NoResultsError, ScraperError):
                if products:
                    break
                raise

            page_products = page_result.products
            new_count = 0

            for product in page_products:
                key = self._product_key(product)
                if key in seen:
                    continue
                seen.add(key)
                product = dict(product)
                product["position"] = len(products) + 1
                products.append(product)
                new_count += 1
                if len(products) >= limit:
                    break

            source_url = source_url or page_result.source_url
            fetch_strategies.append(page_result.fetch_strategy)
            parse_strategy = parse_strategy or page_result.parse_strategy

            if not page_products or new_count == 0:
                break
            page += 1

        if not products:
            raise NoResultsError(normalized_query)

        ranked_products = rank_products_for_query(products[:limit], normalized_query)

        return ScrapedSearchResult(
            query=normalized_query,
            applied_query=normalized_query,
            products=ranked_products,
            source_url=source_url or SEARCH_URL.format(query=quote_plus(normalized_query)),
            fetch_strategy=" + ".join(fetch_strategies),
            parse_strategy=parse_strategy or "unknown",
        )

    async def _fetch_catalog_page(self, query: str, page: int, limit: int) -> ScrapedSearchResult:
        """Intenta fetchar una página de catálogo con múltiples estrategias."""
        normalized_query = normalize_query(query)
        attempts: list[str] = []
        had_catalog_response = False

        # Intenta GraphQL primero
        try:
            return await self._fetch_graphql_page(normalized_query, page, limit)
        except NoResultsError as exc:
            attempts.extend(exc.attempts)
        except ScraperError as exc:
            attempts.append(f"graphql: {exc}")

        # Intenta HTML catalog pages
        for strategy_name, url, headers in self._candidate_pages(normalized_query, page):
            try:
                assert_live_store_access_allowed("lider", url, purpose="search")
                html, resolved_url = await self._request_text(url, headers)
                if self._is_blocked_page(html):
                    attempts.append(f"{strategy_name}: bloqueado por anti-bot")
                    continue

                had_catalog_response = True
                parsed = parse_catalog_page(html, limit=limit)
                if parsed.products:
                    return ScrapedSearchResult(
                        query=normalized_query,
                        applied_query=normalized_query,
                        products=parsed.products[:limit],
                        source_url=resolved_url,
                        fetch_strategy=strategy_name,
                        parse_strategy=parsed.parser or "unknown",
                    )

                legacy_products, legacy_strategy = self._parse_legacy_products(html, limit)
                if legacy_products:
                    return ScrapedSearchResult(
                        query=normalized_query,
                        applied_query=normalized_query,
                        products=legacy_products[:limit],
                        source_url=resolved_url,
                        fetch_strategy=strategy_name,
                        parse_strategy=legacy_strategy or "legacy_html",
                    )

                attempts.append(f"{strategy_name}: sin productos parseables")
            except Exception as exc:
                attempts.append(f"{strategy_name}: {exc}")

        if had_catalog_response:
            raise NoResultsError(normalized_query, attempts=attempts)

        raise ScraperError(" | ".join(attempts) or "Lider no respondió con una página utilizable")

    async def _fetch_graphql_page(self, query: str, page: int, limit: int) -> ScrapedSearchResult:
        """Intenta GraphQL queries."""
        normalized_query = normalize_query(query)
        attempts: list[str] = []

        graphql_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://super.lider.cl",
            "Referer": f"https://super.lider.cl/search?q={quote_plus(normalized_query)}",
            "X-Requested-With": "XMLHttpRequest",
        }

        for payload in self._graphql_payloads(normalized_query, page):
            operation = str(payload.get("operationName") or "graphql")
            try:
                assert_live_store_access_allowed("lider", LIDER_GRAPHQL_URL, purpose="search")
                response = await self.session.post(
                    LIDER_GRAPHQL_URL,
                    json=payload,
                    headers=graphql_headers,
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                search_result = self._find_search_result(response.json())
                if not search_result:
                    attempts.append(f"{operation}: sin searchResult")
                    continue
                products = _parse_search_result(search_result, limit)
                if products:
                    return ScrapedSearchResult(
                        query=normalized_query,
                        applied_query=normalized_query,
                        products=products[:limit],
                        source_url=str(response.url),
                        fetch_strategy=f"graphql:{operation}:page:{page}",
                        parse_strategy="lider_graphql",
                    )
                attempts.append(f"{operation}: sin productos parseables")
            except Exception as exc:
                attempts.append(f"{operation}: {exc}")

        raise NoResultsError(normalized_query, attempts=attempts)

    async def _fetch_autocomplete_terms(self, query: str) -> list[str]:
        """Obtiene términos de autocomplete."""
        normalized_query = normalize_query(query)
        try:
            assert_live_store_access_allowed(
                "lider",
                f"{AUTOCOMPLETE_URL}?term={quote_plus(normalized_query)}",
                purpose="search",
            )
            response = await self.session.get(
                AUTOCOMPLETE_URL,
                params={"term": normalized_query},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            payload: Any = response.json()
        except Exception:
            return []

        if not isinstance(payload, dict):
            return []

        terms = payload.get("terms")
        if not isinstance(terms, list):
            return []

        unique_terms: list[str] = []
        seen: set[str] = set()
        for raw_term in terms:
            term = normalize_query(str(raw_term))
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            unique_terms.append(term)
            if len(unique_terms) >= AUTOCOMPLETE_LIMIT:
                break

        return unique_terms

    def _candidate_pages(self, query: str, page: int = 1) -> list[tuple[str, str, dict[str, str]]]:
        """Genera lista de URLs y headers candidates para búsqueda."""
        slug = _slugify_query(query)
        search_url = _with_page(self._get_search_url().format(query=quote_plus(query)), page)
        slug_url = self._get_slug_url().format(slug=slug)

        candidates: list[tuple[str, str, dict[str, str]]] = []
        for profile_name, headers in HTML_HEADER_PROFILES:
            candidates.append((f"search:{profile_name}:page:{page}", search_url, headers))

        if page == 1:
            candidates.append(("slug:browser", slug_url, HTML_HEADER_PROFILES[0][1]))
        return candidates

    def _graphql_payloads(self, query: str, page: int) -> list[dict[str, Any]]:
        """Genera payloads GraphQL.

        El schema actual (investigado 2026-05-30) requiere prg: Prg! (obligatorio).
        La estructura de respuesta es: search → searchResult → itemStacks → items.
        Los campos de priceInfo son objetos anidados — se omiten y se obtiene el
        precio del HTML fallback que ya funciona correctamente.
        """
        # prg es argumento REQUERIDO (tipo Prg!) — confirmado por introspección
        base_vars = {"query": query, "page": page, "prg": "desktop"}

        # Fragment sin priceInfo (los sub-campos de ProductPrice son desconocidos)
        fragment = """
            searchResult {
              itemStacks {
                items {
                  id
                  name
                  brand
                  canonicalUrl
                  sellerName
                  availabilityStatusV2 { value display }
                }
              }
            }
        """
        return [
            {
                "operationName": "getSearch",
                "variables": {**base_vars, "sort": "best_match"},
                "query": (
                    "query getSearch($query: String, $page: Int, $prg: Prg!, $sort: String) "
                    f"{{ search(query: $query, page: $page, prg: $prg, sort: $sort) {{ {fragment} }} }}"
                ),
            },
            {
                "operationName": "getSearch",
                "variables": base_vars,
                "query": (
                    "query getSearch($query: String, $page: Int, $prg: Prg!) "
                    f"{{ search(query: $query, page: $page, prg: $prg) {{ {fragment} }} }}"
                ),
            },
        ]

    def _find_search_result(self, value: Any) -> dict | None:
        """Busca recursivamente el objeto searchResult en respuesta GraphQL."""
        if isinstance(value, dict):
            candidate = value.get("searchResult")
            if isinstance(candidate, dict):
                return candidate
            if isinstance(value.get("itemStacks"), list):
                return value
            for nested in value.values():
                found = self._find_search_result(nested)
                if found:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = self._find_search_result(item)
                if found:
                    return found
        return None

    async def _request_text(self, url: str, headers: dict[str, str]) -> tuple[str, str]:
        """Fetcha URL y retorna (html, resolved_url)."""
        response = await self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text, str(response.url)

    def _is_blocked_page(self, html: str) -> bool:
        """Detecta si la página fue bloqueada por anti-bot."""
        markers = (
            "Robot or human?",
            "px-captcha",
            "Press and hold",
            "Access to this page has been denied",
        )
        return any(marker in html for marker in markers)

    def _product_key(self, product: dict) -> str:
        """Genera clave única para deduplicación de productos."""
        return (
            str(product.get("sku") or product.get("id") or product.get("url") or "")
            or f"{product.get('name')}::{product.get('price')}"
        )

    # Legacy methods for backward compatibility with old JSON parsing
    def parse_products(self, html: str, limit: int = 100) -> list[ScrapedProduct]:
        """Legacy: Parsea HTML y retorna list[ScrapedProduct]."""
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

    def _parse_legacy_products(self, html: str, limit: int) -> tuple[list[dict], str | None]:
        strategies = (
            ("next_data_legacy", self._parse_next_data),
            ("initial_state", self._parse_initial_state),
            ("html_direct_legacy", self._parse_html_direct),
        )
        for strategy, parser in strategies:
            products = parser(html, limit)
            if products:
                normalized_products = [
                    self._legacy_product_to_dict(product, index + 1)
                    for index, product in enumerate(products)
                ]
                return normalized_products, strategy
        return [], None

    def _legacy_product_to_dict(self, product: ScrapedProduct, position: int) -> dict:
        return {
            "id": None,
            "sku": None,
            "name": product.name,
            "brand": None,
            "category": None,
            "price": product.price,
            "original_price": None,
            "discount_percent": None,
            "savings_amount": None,
            "savings_text": None,
            "unit_price": None,
            "image": None,
            "url": None,
            "availability": None,
            "in_stock": False,
            "seller": "Lider",
            "badges": [],
            "is_offer": False,
            "position": position,
        }

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
            # Walmart Chile / Lider / Acuenta — rutas conocidas
            ["props", "pageProps", "searchResult", "products"],
            ["props", "pageProps", "searchResult", "itemStacks"],
            ["props", "pageProps", "data", "search", "products"],
            ["props", "pageProps", "data", "search", "itemStacks"],
            ["props", "pageProps", "initialData", "products"],
            ["props", "pageProps", "initialData", "search", "products"],
            ["props", "pageProps", "products"],
            ["props", "pageProps", "searchData", "products"],
            ["props", "pageProps", "pageProps", "products"],
            # React Query / TanStack Query dehydrated state
            ["props", "pageProps", "dehydratedState", "queries"],
        ]

        for path in candidate_paths:
            node: Any = data
            for key in path:
                if not isinstance(node, dict):
                    break
                node = node.get(key)
            else:
                # Path completed: try to extract products from this node
                # Special case: dehydratedState.queries is a list of query objects
                if isinstance(node, list) and node and isinstance(node[0], dict) and "state" in node[0]:
                    products = self._extract_from_react_query_list(node)
                    if products:
                        return products
                    continue
                products = self._coerce_product_list(node)
                if products:
                    return products

        return self._recursive_find_product_list(data, depth=0, max_depth=8)

    def _extract_from_react_query_list(self, queries: list[dict]) -> list[dict[str, Any]]:
        """Extrae productos de la estructura dehydratedState.queries de React Query."""
        for query_obj in queries:
            state = query_obj.get("state") or {}
            query_data = state.get("data") or {}
            # Busca recursivamente dentro del estado de cada query
            products = self._recursive_find_product_list(query_data, depth=0, max_depth=6)
            if products:
                return products
        return []

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
            "price", "prices", "priceDetail", "listPrice", "normalPrice",
            "offerPrice", "priceText", "priceFormatted",
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


# Helper functions


def _slugify_query(query: str) -> str:
    ascii_query = unicode_normalize("NFKD", query).encode("ascii", "ignore").decode("ascii")
    return "-".join(part for part in ascii_query.lower().split() if part)


def _with_page(url: str, page: int) -> str:
    if page <= 1:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}page={page}"


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
