from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Iterable

from backend.scraper import ScraperError, search_lider
from backend.scraper_jumbo import search_jumbo
from backend.compliance import ComplianceError


DEFAULT_LIDER_SEEDS = [
    "aceite",
    "agua",
    "arroz",
    "azucar",
    "bebida",
    "cafe",
    "carne",
    "cereal",
    "cerveza",
    "chocolate",
    "congelado",
    "detergente",
    "fideos",
    "fruta",
    "galletas",
    "higiene",
    "jugo",
    "lacteos",
    "leche",
    "limpieza",
    "pan",
    "papel",
    "pasta",
    "pollo",
    "queso",
    "shampoo",
    "snack",
    "verdura",
    "vino",
    "yogurt",
]


@dataclass(slots=True)
class CatalogIndexResult:
    store: str
    products: list[dict]
    seed_count: int
    errors: list[str] = field(default_factory=list)
    fetched_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def count(self) -> int:
        return len(self.products)

    def to_dict(self) -> dict:
        return {
            "store": self.store,
            "count": self.count,
            "seed_count": self.seed_count,
            "errors": self.errors,
            "fetched_at": self.fetched_at,
            "products": self.products,
        }


def _product_key(product: dict) -> str:
    return (
        str(product.get("source") or "")
        + "::"
        + (
            str(product.get("sku") or product.get("id") or product.get("url") or "")
            or f"{product.get('name')}::{product.get('price')}"
        )
    )


def _normalize_seeds(seeds: Iterable[str] | None) -> list[str]:
    raw_seeds = list(seeds or DEFAULT_LIDER_SEEDS)
    normalized: list[str] = []
    seen: set[str] = set()
    for seed in raw_seeds:
        value = " ".join(str(seed).split()).strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def index_lider_catalog(
    *,
    seeds: Iterable[str] | None = None,
    per_seed_limit: int = 600,
    max_products: int | None = None,
) -> CatalogIndexResult:
    raise ComplianceError(
        "La indexacion masiva de Lider esta deshabilitada para respetar politicas/robots.txt. "
        "Usa una fuente autorizada o permiso escrito antes de habilitarla."
    )
    products: list[dict] = []
    seen: set[str] = set()
    errors: list[str] = []
    normalized_seeds = _normalize_seeds(seeds)

    for seed in normalized_seeds:
        if max_products is not None and len(products) >= max_products:
            break
        try:
            remaining = per_seed_limit
            if max_products is not None:
                remaining = min(remaining, max_products - len(products))
            result = search_lider(seed, limit=remaining)
        except ScraperError as exc:
            errors.append(f"{seed}: {exc}")
            continue

        for product in result.products:
            product = dict(product)
            product["source"] = "lider"
            key = _product_key(product)
            if key in seen:
                continue
            seen.add(key)
            product["position"] = len(products) + 1
            products.append(product)
            if max_products is not None and len(products) >= max_products:
                break

    return CatalogIndexResult(
        store="lider",
        products=products,
        seed_count=len(normalized_seeds),
        errors=errors,
    )


def index_jumbo_catalog(
    *,
    query: str = "",
    max_products: int = 5000,
) -> CatalogIndexResult:
    raise ComplianceError(
        "La indexacion masiva de Jumbo esta deshabilitada para respetar politicas/robots.txt. "
        "Usa una fuente autorizada o permiso escrito antes de habilitarla."
    )
    result = search_jumbo(query, limit=max_products)
    products: list[dict] = []
    seen: set[str] = set()

    for product in result.products:
        product = dict(product)
        product["source"] = "jumbo"
        key = _product_key(product)
        if key in seen:
            continue
        seen.add(key)
        product["position"] = len(products) + 1
        products.append(product)

    return CatalogIndexResult(
        store="jumbo",
        products=products,
        seed_count=1,
    )


def index_store_catalog(
    store: str,
    *,
    max_products: int | None = None,
    seeds: Iterable[str] | None = None,
) -> CatalogIndexResult:
    normalized_store = (store or "").strip().lower()
    if normalized_store == "lider":
        return index_lider_catalog(seeds=seeds, max_products=max_products)
    if normalized_store == "jumbo":
        return index_jumbo_catalog(max_products=max_products or 5000)
    raise ValueError("store debe ser 'lider' o 'jumbo'")
