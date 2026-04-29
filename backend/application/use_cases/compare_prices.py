from __future__ import annotations

from collections import defaultdict
from typing import Any


def compare_prices(products: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for product in products:
        grouped[product["canonical_key"]].append(product)

    ranked_options: list[dict[str, Any]] = []
    for alternatives in grouped.values():
        ranked = sorted(alternatives, key=lambda item: (item["price"], item["store_name"]))
        ranked_options.extend(ranked)

    ranked_options.sort(key=lambda item: (item["price"], item["canonical_name"]))

    best_option = ranked_options[0] if ranked_options else {}
    alternatives = ranked_options[1:]
    return {
        "best_option": best_option,
        "alternatives": alternatives,
    }
