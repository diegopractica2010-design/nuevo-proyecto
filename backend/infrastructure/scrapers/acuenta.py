"""Acuenta scraper — Walmart Chile discount brand (same Oracle Commerce platform as Lider)."""
from __future__ import annotations

from backend.infrastructure.scrapers.lider import LiderScraper
from backend.scraper import ScrapedSearchResult


class AcuentaScraper(LiderScraper):
    """
    Inherits all fetch + parse logic from LiderScraper.
    Walmart CL platform is identical across Lider and Acuenta — only URLs differ.
    """
    SEARCH_URL_TEMPLATE = "https://www.acuenta.cl/search?q={query}"
    SLUG_URL_TEMPLATE = "https://www.acuenta.cl/v/{slug}"
    STORE_NAME = "acuenta"


async def search_acuenta(query: str, limit: int = 40) -> ScrapedSearchResult:
    return await AcuentaScraper().search(query, limit=limit)
