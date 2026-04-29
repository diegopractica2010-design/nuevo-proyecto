from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from backend.scraper import ScrapedSearchResult, search_lider
from backend.scraper_jumbo import search_jumbo


SearchFn = Callable[[str, int], ScrapedSearchResult]


@dataclass(frozen=True, slots=True)
class StoreAdapter:
    name: str
    display_name: str
    search: SearchFn
    experimental: bool = False


def _lider_search(query: str, limit: int) -> ScrapedSearchResult:
    return search_lider(query, limit=limit)


def _jumbo_search(query: str, limit: int) -> ScrapedSearchResult:
    return search_jumbo(query, limit=limit)


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
