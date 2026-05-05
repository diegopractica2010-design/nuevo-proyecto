from __future__ import annotations

import logging
from functools import lru_cache
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from backend.config import (
    COMPLIANCE_STRICT_MODE,
    LIVE_STORE_QUERIES_ENABLED,
    STORE_CRAWLING_ENABLED,
    STORE_ROBOTS_ALLOW_ON_ERROR,
    USER_AGENT,
)


logger = logging.getLogger(__name__)


class ComplianceError(RuntimeError):
    pass


STORE_TERMS_URLS = {
    "lider": "https://www.lider.cl/landing/static/servicio-al-cliente/ya-compraste.html",
    "jumbo": "https://www.jumbo.cl/institucional/terminos-condiciones",
}


def _robots_url_for(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"


@lru_cache(maxsize=32)
def _load_robots(robots_url: str) -> RobotFileParser | None:
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
    except Exception as exc:
        logger.warning("No se pudo leer robots.txt %s: %s", robots_url, exc)
        return None
    return parser


def robots_allows(url: str) -> bool:
    parser = _load_robots(_robots_url_for(url))
    if parser is None:
        return STORE_ROBOTS_ALLOW_ON_ERROR
    return parser.can_fetch(USER_AGENT, url) and parser.can_fetch("*", url)


def assert_live_store_access_allowed(store: str, url: str, *, purpose: str = "search") -> None:
    if not COMPLIANCE_STRICT_MODE:
        return

    if purpose == "crawl" and not STORE_CRAWLING_ENABLED:
        raise ComplianceError(
            "Indexacion/crawling masivo deshabilitado por cumplimiento. "
            "Requiere autorizacion expresa de la tienda."
        )

    if not LIVE_STORE_QUERIES_ENABLED:
        raise ComplianceError(
            "Consultas live a supermercados deshabilitadas por cumplimiento. "
            "Configura LIVE_STORE_QUERIES_ENABLED=true solo si tienes permiso o una integracion aprobada."
        )

    if not robots_allows(url):
        terms = STORE_TERMS_URLS.get(store, "los terminos de la tienda")
        raise ComplianceError(
            f"robots.txt no permite consultar {url}. Revisa {terms} y usa una fuente autorizada."
        )
