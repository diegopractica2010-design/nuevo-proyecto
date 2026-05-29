from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from backend.scraper import ScrapedSearchResult
from backend.infrastructure.scrapers.lider import LiderScraper
from backend.scraper_jumbo import search_jumbo


SearchFn = Callable[[str, int], Awaitable[ScrapedSearchResult]]


@dataclass(frozen=True, slots=True)
class StoreAdapter:
    name: str
    display_name: str
    search: SearchFn
    experimental: bool = False


async def _lider_search(query: str, limit: int) -> ScrapedSearchResult:
    return await LiderScraper().search(query, limit=limit)


async def _jumbo_search(query: str, limit: int) -> ScrapedSearchResult:
    return await search_jumbo(query, limit=limit)


STORE_ADAPTERS: dict[str, StoreAdapter] = {
    "lider": StoreAdapter(name="lider", display_name="Lider", search=_lider_search),
    "jumbo": StoreAdapter(
        name="jumbo",
        display_name="Jumbo",
        search=_jumbo_search,
        experimental=True,
    ),
}


def get_store_adapter(store: str) -> StoreAdapter | None:
    return STORE_ADAPTERS.get((store or "lider").strip().lower())


def list_stores() -> list[StoreAdapter]:
    return list(STORE_ADAPTERS.values())
