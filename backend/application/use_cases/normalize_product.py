"""Use case: normalize a raw product name into its canonical form."""
from __future__ import annotations

from backend.domain.normalization.matching import canonicalize, are_equivalent
from backend.domain.product import Product


def normalize_product_name(raw_name: str) -> Product:
    """Return the canonical Product for *raw_name*."""
    return canonicalize(raw_name)


def products_are_equivalent(name_a: str, name_b: str) -> bool:
    """Return True when *name_a* and *name_b* resolve to the same canonical key."""
    return are_equivalent(name_a, name_b)


def find_competitor_price(
    item_name: str,
    store_results: list[dict],
    own_store: str,
) -> float | None:
    """
    Given a list of per-store compare results, return the best price from a
    competitor store whose best product is canonically equivalent to *item_name*.
    Returns None when no equivalent competitor product is found.
    """
    own_canonical = canonicalize(item_name).canonical_key
    for result in store_results:
        if result.get("store") == own_store:
            continue
        best = result.get("best")
        if not best:
            continue
        competitor_name = " ".join(
            str(best.get(k) or "") for k in ("name", "brand") if best.get(k)
        )
        if canonicalize(competitor_name).canonical_key == own_canonical:
            price = best.get("price")
            if price is not None:
                return float(price)
    return None
