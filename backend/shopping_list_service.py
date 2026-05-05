from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from unicodedata import normalize as unicode_normalize

from backend.search_service import search_products


COMPARE_STORES = ("lider", "jumbo")

STOPWORDS = {
    "de",
    "del",
    "la",
    "las",
    "el",
    "los",
    "un",
    "una",
    "en",
    "para",
    "por",
    "con",
    "y",
    "o",
    "mas",
    "barato",
    "barata",
    "opcion",
    "saco",
    "bolsa",
    "paquete",
    "pack",
    "fideo",
    "fideos",
}

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

CHARCOAL_TERMS = {"briqueta", "briquetas", "vegetal", "quincho", "quebracho", "espino", "parrilla"}


@dataclass(slots=True)
class ShoppingListItem:
    query: str
    quantity: int = 1


def normalize_compare_text(value: Any) -> str:
    text = unicode_normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("yoghurt", "yogurt")
    text = re.sub(r"[^a-z0-9]+", " ", text)
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
        if token not in STOPWORDS
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


def select_best_products(products: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    scored = [
        {**product, "_match_score": score_product_for_query(product, query)}
        for product in products
        if product.get("price") is not None
    ]
    required_tokens = [token for token in _query_tokens(query) if len(token) >= 5]
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
    threshold = max(12, int(max_score * 0.75))
    shortlisted = [product for product in scored if product["_match_score"] >= threshold]
    shortlisted.sort(key=lambda product: (float(product.get("price") or 0), -product["_match_score"]))
    return shortlisted


def is_specific_query(query: str) -> bool:
    tokens = _query_tokens(query)
    return bool(_unit_requirement(query)) or len(tokens) >= 2


def compare_shopping_list(items: list[ShoppingListItem], *, limit_per_store: int = 80) -> dict[str, Any]:
    compared_items: list[dict[str, Any]] = []

    for item in items:
        store_results: list[dict[str, Any]] = []
        for store in COMPARE_STORES:
            response = search_products(item.query, limit=limit_per_store, store=store)
            products = [_product_to_dict(product) for product in response.results]
            best_options = select_best_products(products, item.query)
            best_product = best_options[0] if best_options else None
            store_results.append(
                {
                    "store": store,
                    "count": len(products),
                    "matched_count": len(best_options),
                    "best": best_product,
                    "alternatives": best_options[1:4],
                    "warning": response.warning,
                    "applied_query": response.applied_query,
                }
            )

        candidates = [
            result["best"]
            for result in store_results
            if result.get("best") and result["best"].get("price") is not None
        ]
        cheapest = min(candidates, key=lambda product: float(product.get("price") or 0), default=None)

        compared_items.append(
            {
                "query": item.query,
                "quantity": item.quantity,
                "stores": store_results,
                "cheapest": cheapest,
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
