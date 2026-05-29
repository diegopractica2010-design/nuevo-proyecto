"""
Shared utilities for web scrapers.

This module contains the common dataclasses, exceptions, and utility functions
used across scraper implementations (e.g., LiderScraper, JumboScraper).

The scraping logic itself has been consolidated into:
- backend/infrastructure/scrapers/lider.py (LiderScraper class)
- backend/scraper_jumbo.py (Jumbo scraper)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.domain.constants import CHARCOAL_TERMS, QUERY_STOPWORDS
from backend.domain.normalization.text import normalize_text


# Exceptions
class ScraperError(RuntimeError):
    """Base exception for scraper errors."""
    pass


class NoResultsError(ScraperError):
    """Raised when a scraper query returns no results."""
    def __init__(
        self,
        query: str,
        *,
        attempts: list[str] | None = None,
        suggestions: list[str] | None = None,
        message: str | None = None,
    ):
        super().__init__(message or f'No se encontraron productos para "{query}"')
        self.query = query
        self.attempts = attempts or []
        self.suggestions = suggestions or []


# Dataclasses
@dataclass(slots=True)
class SearchPage:
    query: str
    html: str
    url: str
    strategy: str


@dataclass(slots=True)
class ScrapedSearchResult:
    """Result of a scraper search operation."""
    query: str
    applied_query: str
    products: list[dict]
    source_url: str
    fetch_strategy: str
    parse_strategy: str
    suggestions: list[str] = field(default_factory=list)
    warning: str | None = None


# Utility functions
def normalize_query(query: str) -> str:
    """Normalize a search query for consistent processing."""
    normalized = normalize_text(query or "")
    if not normalized:
        raise ScraperError("La consulta está vacía")
    return normalized


def fallback_query_variants(query: str) -> list[str]:
    """Generate fallback query variants for search resilience.
    
    Removes stopwords, extracts last token, and handles special cases like 'tallarines'.
    """
    normalized = normalize_query(query)
    ascii_query = normalize_text(normalized)
    variants: list[str] = []
    seen = {normalized.lower()}

    def add(value: str) -> None:
        cleaned = normalize_query(value)
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            variants.append(cleaned)

    if ascii_query.lower() != normalized.lower():
        add(ascii_query)

    tokens = [token for token in ascii_query.lower().split() if token not in QUERY_STOPWORDS]
    if tokens:
        add(" ".join(tokens))
        if len(tokens) > 1:
            add(tokens[-1])

    if "tallarines" in ascii_query.lower():
        add(ascii_query.lower().replace("tallarines", "tallarin"))
        add("tallarin")

    return variants


def _rank_text(value: Any) -> str:
    """Convert value to normalized ASCII text for ranking."""
    return normalize_text(str(value or ""))


def rank_products_for_query(products: list[dict], query: str) -> list[dict]:
    """Rank products by relevance to the query using token matching."""
    ascii_query = _rank_text(query)
    tokens = [token for token in ascii_query.split() if token not in QUERY_STOPWORDS]
    if not tokens:
        return products

    def score(product: dict) -> int:
        haystack = _rank_text(
            " ".join(
                str(product.get(key) or "")
                for key in ("name", "brand", "category", "seller")
            )
        )
        value = sum(10 for token in tokens if token in haystack)
        if all(token in haystack for token in tokens):
            value += 20
        if "carbon" in tokens and any(term in haystack for term in CHARCOAL_TERMS):
            value += 8
        return value

    return sorted(products, key=score, reverse=True)
