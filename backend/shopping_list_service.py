from __future__ import annotations

import asyncio
import inspect
import re
from dataclasses import dataclass
from typing import Any

from backend.domain.constants import CHARCOAL_TERMS, QUERY_STOPWORDS
from backend.domain.normalization.matching import canonicalize
from backend.domain.normalization.text import normalize_text
from backend.application.use_cases.normalize_product import find_competitor_price
from backend.search_service import search_products


from backend.store_adapters import comparable_stores

UNIT_WORDS = {
    "kg",
    "kilo",
    "kilos",
    "kilogramo",
    "kilogramos",
    "g",
    "gr",
    "gramo",
    "gramos",
    "l",
    "lt",
    "lts",
    "litro",
    "litros",
    "ml",
    "cc",
}

async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value
    return value


@dataclass(slots=True)
class ShoppingListItem:
    query: str
    quantity: int = 1


def normalize_compare_text(value: Any) -> str:
    text = normalize_text(str(value or "")).replace("yoghurt", "yogurt")
    text = re.sub(r"[.,]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _canonical_token(token: str) -> str:
    replacements = {
        "tallarines": "tallarin",
        "tallarin": "tallarin",
        "yoghurt": "yogurt",
    }
    return replacements.get(token, token)


def _query_tokens(query: str) -> list[str]:
    tokens = normalize_compare_text(query).split()
    return [
        _canonical_token(token)
        for token in tokens
        if token not in QUERY_STOPWORDS
        and token not in UNIT_WORDS
        and not token.isdigit()
        and len(token) > 1
    ]


def _word_matches(token: str, words: set[str]) -> bool:
    token = _canonical_token(token)
    words = {_canonical_token(word) for word in words}
    if token in words:
        return True
    if token.endswith("s") and token[:-1] in words:
        return True
    return f"{token}s" in words


def _unit_requirement(query: str) -> str | None:
    text = normalize_compare_text(query)
    if re.search(r"\b(1|uno|una)\s*(kg|kilo|kilos|kilogramo|kilogramos)\b", text):
        return "1kg"
    if re.search(r"\b1000\s*(g|gr|gramo|gramos)\b", text):
        return "1kg"
    if re.search(r"\b(1|uno|una)\s*(l|lt|lts|litro|litros)\b", text):
        return "1l"
    if re.search(r"\b1000\s*(ml|cc)\b", text):
        return "1l"
    return None


def _matches_unit(product_text: str, unit: str | None) -> bool:
    if unit is None:
        return True
    if unit == "1kg":
        return bool(
            re.search(r"\b1\s*(kg|kilo|kilogramo)\b", product_text)
            or re.search(r"\b1000\s*(g|gr|gramos?)\b", product_text)
        )
    if unit == "1l":
        return bool(
            re.search(r"\b1\s*(l|lt|lts|litro)\b", product_text)
            or re.search(r"\b1000\s*(ml|cc)\b", product_text)
        )
    return True


def _has_charcoal_intent(query: str) -> bool:
    text = normalize_compare_text(query)
    words = set(text.split())
    return "carbon" in words and bool(words & {"saco", "bolsa", "parrilla", "asado", "quincho"})


def _is_charcoal_product(product_text: str) -> bool:
    words = product_text.split()
    word_set = set(words)
    return "carbon" in word_set and (
        bool(word_set & CHARCOAL_TERMS)
        or (bool(words) and words[0] == "carbon")
    )


def score_product_for_query(product: dict[str, Any], query: str) -> int:
    tokens = _query_tokens(query)
    if not tokens:
        return 0

    haystack = normalize_compare_text(
        " ".join(
            str(product.get(key) or "")
            for key in ("name", "brand", "category", "seller")
        )
    )

    words = {_canonical_token(word) for word in haystack.split()}
    matched_tokens = [token for token in tokens if _word_matches(token, words)]
    score = 0
    for token in tokens:
        if _word_matches(token, words):
            score += 12

    if all(token in matched_tokens for token in tokens):
        score += 28

    phrase = " ".join(tokens)
    if phrase and phrase in haystack:
        score += 18

    unit = _unit_requirement(query)
    if unit:
        score += 35 if _matches_unit(haystack, unit) else -50

    if _has_charcoal_intent(query):
        score += 35 if _is_charcoal_product(haystack) else -80

    if product.get("in_stock"):
        score += 4

    return score


def _product_to_dict(product: Any) -> dict[str, Any]:
    if hasattr(product, "model_dump"):
        return product.model_dump()
    return dict(product)


def _format_unit_price(price: float, quantity_value: float | None, quantity_unit: str | None) -> str | None:
    if not quantity_value or not quantity_unit:
        return None
    if quantity_unit == "g":
        return f"${round(price / quantity_value * 1000):,.0f}/kg".replace(",", ".")
    if quantity_unit == "ml":
        return f"${round(price / quantity_value * 1000):,.0f}/l".replace(",", ".")
    return None


def _ensure_unit_price(product: dict[str, Any] | None) -> dict[str, Any] | None:
    if not product or product.get("unit_price"):
        return product
    try:
        canonical = canonicalize(
            " ".join(
                value
                for value in [str(product.get("name") or ""), str(product.get("brand") or "")]
                if value
            )
        )
        product["unit_price"] = _format_unit_price(
            float(product.get("price") or 0),
            canonical.quantity_value,
            canonical.quantity_unit,
        )
    except Exception:
        product["unit_price"] = None
    return product


def select_best_products(products: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    scored = [
        {**product, "_match_score": score_product_for_query(product, query)}
        for product in products
        if product.get("price") is not None
    ]
    required_tokens = [token for token in _query_tokens(query) if len(token) >= 4]
    if required_tokens:
        filtered = []
        for product in scored:
            haystack = normalize_compare_text(
                " ".join(
                    str(product.get(key) or "")
                    for key in ("name", "brand", "category", "seller")
                )
            )
            words = set(haystack.split())
            if all(_word_matches(token, words) for token in required_tokens):
                filtered.append(product)
        scored = filtered

    unit = _unit_requirement(query)
    if unit:
        scored = [
            product
            for product in scored
            if _matches_unit(
                normalize_compare_text(
                    " ".join(
                        str(product.get(key) or "")
                        for key in ("name", "brand", "category", "seller")
                    )
                ),
                unit,
            )
        ]

    if _has_charcoal_intent(query):
        scored = [
            product
            for product in scored
            if _is_charcoal_product(
                normalize_compare_text(
                    " ".join(
                        str(product.get(key) or "")
                        for key in ("name", "brand", "category", "seller")
                    )
                )
            )
        ]

    scored = [product for product in scored if product["_match_score"] > 0]
    if not scored:
        return []

    max_score = max(product["_match_score"] for product in scored)
    threshold = max(24, int(max_score * 0.85))
    shortlisted = [product for product in scored if product["_match_score"] >= threshold]
    shortlisted.sort(key=lambda product: (float(product.get("price") or 0), -product["_match_score"]))
    return shortlisted


def is_specific_query(query: str) -> bool:
    tokens = _query_tokens(query)
    return bool(_unit_requirement(query)) or len(tokens) >= 2


async def compare_shopping_list(items: list[ShoppingListItem], *, limit_per_store: int = 10) -> dict[str, Any]:
    compare_stores = comparable_stores()
    indexed_items = list(enumerate(items))
    results_by_item: dict[int, list[dict[str, Any]]] = {index: [] for index, _ in indexed_items}

    async def compare_store(index: int, item: ShoppingListItem, store: str) -> tuple[int, dict[str, Any]]:
        try:
            # 10s caps the slow HTML stores (Lider's fallback chain can run 18-20s)
            # while still letting well-formed single-word queries through (~6-8s).
            response = await asyncio.wait_for(
                _maybe_await(search_products(item.query, limit=limit_per_store, store=store)),
                timeout=10,
            )
            products = [_product_to_dict(product) for product in response.results]
            best_options = select_best_products(products, item.query)
            best_options = [_ensure_unit_price(product) for product in best_options]
            best_product = best_options[0] if best_options else None
            return index, {
                "store": store,
                "count": len(products),
                "matched_count": len(best_options),
                "best": best_product,
                "alternatives": best_options[1:4],
                "warning": response.warning,
                "applied_query": response.applied_query,
            }
        except Exception as exc:
            return index, {
                "store": store,
                "count": 0,
                "matched_count": 0,
                "best": None,
                "alternatives": [],
                "warning": None,
                "applied_query": item.query,
                "error": str(exc),
            }

    store_results = await asyncio.gather(
        *(
            compare_store(index, item, store)
            for index, item in indexed_items
            for store in compare_stores
        )
    )
    for index, store_result in store_results:
        results_by_item[index].append(store_result)

    compared_items: list[dict[str, Any]] = []
    for index, item in indexed_items:
        store_results = sorted(
            results_by_item[index],
            key=lambda result: compare_stores.index(result["store"]),
        )

        candidates = [
            result["best"]
            for result in store_results
            if result.get("best") and result["best"].get("price") is not None
        ]
        cheapest = min(candidates, key=lambda product: float(product.get("price") or 0), default=None)
        canonical_keys = [
            canonicalize(
                " ".join(
                    value
                    for value in [
                        str(result["best"].get("name") or ""),
                        str(result["best"].get("brand") or ""),
                    ]
                    if value
                )
            ).canonical_key
            for result in store_results
            if result.get("best")
        ]
        same_product = len(canonical_keys) >= 2 and len(set(canonical_keys)) == 1

        # Add competitor_price to each store result using canonicalize matching
        for result in store_results:
            own_store = result.get("store", "")
            best = result.get("best")
            if best:
                best_name = " ".join(
                    str(best.get(k) or "") for k in ("name", "brand") if best.get(k)
                )
                result["competitor_price"] = find_competitor_price(
                    best_name, store_results, own_store
                )
            else:
                result["competitor_price"] = None

        compared_items.append(
            {
                "query": item.query,
                "quantity": item.quantity,
                "stores": store_results,
                "cheapest": cheapest,
                "same_product": same_product,
                "status": "matched" if cheapest else "not_found",
            }
        )

    total = sum(
        float(item["cheapest"]["price"]) * int(item.get("quantity") or 1)
        for item in compared_items
        if item.get("cheapest")
    )

    return {
        "items": compared_items,
        "count": len(compared_items),
        "matched_count": sum(1 for item in compared_items if item["status"] == "matched"),
        "estimated_total": total,
    }


def parse_shopping_items(payload_items: list[Any]) -> list[ShoppingListItem]:
    items: list[ShoppingListItem] = []
    seen: set[str] = set()

    for raw in payload_items:
        if isinstance(raw, str):
            query = raw
            quantity = 1
        elif isinstance(raw, dict):
            query = str(raw.get("query") or raw.get("name") or "")
            quantity = int(raw.get("quantity") or 1)
        else:
            continue

        query = re.sub(r"\s+", " ", query).strip()
        key = query.lower()
        if not query or key in seen:
            continue
        seen.add(key)
        items.append(ShoppingListItem(query=query, quantity=max(1, quantity)))

    return items
