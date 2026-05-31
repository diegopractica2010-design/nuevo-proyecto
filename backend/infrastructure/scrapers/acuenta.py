"""Acuenta scraper — Walmart Chile discount brand (same platform as Lider).

Acuenta.cl carga productos via client-side rendering: el HTML inicial no contiene
productos en __NEXT_DATA__. Se usa el mismo GraphQL de Lider (catálogo compartido)
con Origin/Referer de Acuenta para indicar el contexto correcto.
"""
from __future__ import annotations

from urllib.parse import quote_plus

from backend.infrastructure.scrapers.lider import LiderScraper, LIDER_GRAPHQL_URL
from backend.scraper import ScrapedSearchResult, NoResultsError, normalize_query
from backend.config import REQUEST_TIMEOUT


class AcuentaScraper(LiderScraper):
    """
    Walmart CL platform compartido entre Lider y Acuenta.
    Acuenta no expone productos en SSR/NEXT_DATA, usa el mismo GraphQL de Lider.
    """
    SEARCH_URL_TEMPLATE = "https://www.acuenta.cl/search?q={query}"
    SLUG_URL_TEMPLATE = "https://www.acuenta.cl/v/{slug}"
    STORE_NAME = "acuenta"

    # Acuenta usa el mismo GraphQL de Lider (catálogo compartido Walmart CL).
    # El servidor GraphQL solo acepta Origin: super.lider.cl, no www.acuenta.cl.
    # → No se override _fetch_graphql_page; se hereda la implementación de LiderScraper.


async def search_acuenta(query: str, limit: int = 40) -> ScrapedSearchResult:
    return await AcuentaScraper().search(query, limit=limit)
