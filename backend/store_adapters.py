from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from backend.scraper import ScrapedSearchResult
from backend.infrastructure.scrapers.lider import LiderScraper
from backend.infrastructure.scrapers.santa_isabel import search_santa_isabel
from backend.infrastructure.scrapers.acuenta import search_acuenta
from backend.infrastructure.scrapers.tottus import search_tottus
from backend.infrastructure.scrapers.unimarc import search_unimarc
from backend.scraper_jumbo import search_jumbo


SearchFn = Callable[[str, int], Awaitable[ScrapedSearchResult]]


@dataclass(frozen=True, slots=True)
class StoreAdapter:
    name: str
    display_name: str
    search: SearchFn
    experimental: bool = False
    url: str = ""
    logo_url: str = ""
    description: str = ""
    country: str = "CL"
    currency: str = "CLP"
    # Stores whose only working fetch path is a headless browser. They are
    # excluded from multi-store comparisons unless PLAYWRIGHT_ENABLED=true.
    requires_playwright: bool = False


async def _lider_search(query: str, limit: int) -> ScrapedSearchResult:
    return await LiderScraper().search(query, limit=limit)


async def _jumbo_search(query: str, limit: int) -> ScrapedSearchResult:
    return await search_jumbo(query, limit=limit)


async def _santa_isabel_search(query: str, limit: int) -> ScrapedSearchResult:
    return await search_santa_isabel(query, limit=limit)


async def _acuenta_search(query: str, limit: int) -> ScrapedSearchResult:
    return await search_acuenta(query, limit=limit)


async def _tottus_search(query: str, limit: int) -> ScrapedSearchResult:
    return await search_tottus(query, limit=limit)


async def _unimarc_search(query: str, limit: int) -> ScrapedSearchResult:
    return await search_unimarc(query, limit=limit)


STORE_ADAPTERS: dict[str, StoreAdapter] = {
    "lider": StoreAdapter(
        name="lider",
        display_name="Lider",
        search=_lider_search,
        url="https://super.lider.cl",
        logo_url="/static/logos/lider.svg",
        description="Supermercado Walmart Chile",
        country="CL",
        currency="CLP",
    ),
    "jumbo": StoreAdapter(
        name="jumbo",
        display_name="Jumbo",
        search=_jumbo_search,
        experimental=False,
        url="https://www.jumbo.cl",
        logo_url="/static/logos/jumbo.svg",
        description="Supermercado Cencosud Chile",
        country="CL",
        currency="CLP",
    ),
    "santa_isabel": StoreAdapter(
        name="santa_isabel",
        display_name="Santa Isabel",
        search=_santa_isabel_search,
        experimental=False,
        url="https://www.santaisabel.cl",
        logo_url="/static/logos/santa_isabel.svg",
        description="Supermercado Cencosud Chile (descuentos)",
        country="CL",
        currency="CLP",
        # Works over plain HTTP via the BFF catalog/plp API (apiKey in config).
    ),
    "acuenta": StoreAdapter(
        name="acuenta",
        display_name="Acuenta",
        search=_acuenta_search,
        experimental=True,
        url="https://www.acuenta.cl",
        logo_url="/static/logos/acuenta.svg",
        description="Formato descuento Walmart Chile",
        country="CL",
        currency="CLP",
        # acuenta.cl is client-rendered and exposes no products over plain HTTP
        # (its GraphQL is shared with Lider but priced from HTML, which is empty).
        # Only a headless browser can read it.
        requires_playwright=True,
    ),
    "tottus": StoreAdapter(
        name="tottus",
        display_name="Tottus",
        search=_tottus_search,
        experimental=True,
        url="https://tottus.falabella.com",
        logo_url="/static/logos/tottus.svg",
        description="Supermercado Falabella Chile",
        country="CL",
        currency="CLP",
        requires_playwright=True,
    ),
    "unimarc": StoreAdapter(
        name="unimarc",
        display_name="Unimarc",
        search=_unimarc_search,
        experimental=True,
        url="https://www.unimarc.cl",
        logo_url="/static/logos/unimarc.svg",
        description="Supermercado SMU Chile (requiere PLAYWRIGHT_ENABLED para anti-bot)",
        country="CL",
        currency="CLP",
        requires_playwright=True,
    ),
}


def get_store_adapter(store: str) -> StoreAdapter | None:
    return STORE_ADAPTERS.get((store or "lider").strip().lower())


def list_stores() -> list[StoreAdapter]:
    return list(STORE_ADAPTERS.values())


def comparable_stores() -> tuple[str, ...]:
    """Stores usable in a multi-store comparison.

    Only fast HTTP-API stores are included. Playwright-backed stores launch a
    headless browser per query (5-40s each); running them across a multi-item
    shopping list would make the compare unusably slow, so they are excluded
    here and remain available only in the single-store search.
    """
    return tuple(
        name
        for name, adapter in STORE_ADAPTERS.items()
        if not adapter.requires_playwright
    )
