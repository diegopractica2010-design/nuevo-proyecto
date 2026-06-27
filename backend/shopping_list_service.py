from __future__ import annotations

import asyncio
import inspect
import re
from dataclasses import dataclass
from typing import Any

from backend.domain.constants import CHARCOAL_TERMS, QUERY_STOPWORDS
from backend.domain.normalization.matching import canonicalize, PRODUCT_TYPES
from backend.domain.normalization.text import normalize_text
from backend.application.use_cases.normalize_product import find_competitor_price
from backend.search_service import search_products


from backend.config import get_settings
from backend.store_adapters import comparable_stores, get_store_adapter

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
    # ponytail: lo a granel se vende por peso variable; no exigir "1kg" en el nombre.
    if "granel" in text:
        return None
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


# ponytail: atributos que cambian el producto; si los pides, el resultado debe tenerlos.
def _required_attributes(query: str) -> list[str]:
    raw = str(query or "").lower()
    text = normalize_compare_text(query)
    found: list[str] = []
    if "sin az" in text or "0%" in raw or "light" in text or "diet" in text or "zero" in text:
        found.append("sin-azucar")
    if "integral" in text:
        found.append("integral")
    return found


def _has_attribute(product_text_raw: str, attribute: str) -> bool:
    raw = product_text_raw.lower()
    text = normalize_compare_text(product_text_raw)
    if attribute == "sin-azucar":
        return "sin az" in text or "0%" in raw or "light" in text or "diet" in text or "zero" in text
    if attribute == "integral":
        return "integral" in text
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

    # ponytail: premia el producto con el atributo pedido (sin azúcar/integral). No
    # castiga al normal: si no existe el especial, select_best_products lo deja como
    # alternativa (fallback). Aquí solo ordena: el especial queda arriba.
    product_text_raw = " ".join(
        str(product.get(key) or "") for key in ("name", "brand", "category", "seller")
    )
    for attribute in _required_attributes(query):
        if _has_attribute(product_text_raw, attribute):
            score += 30

    # ponytail: si pides una marca (ej. Pepsodent), premia esa marca y castiga otras.
    query_brand = canonicalize(query).brand
    if query_brand:
        product_brand = canonicalize(product_text_raw).brand
        if product_brand == query_brand:
            score += 25
        elif product_brand is not None:
            score -= 40

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


# ponytail: el "núcleo" de la búsqueda es el TIPO de producto. Filtramos por él, no
# por cada palabra descriptiva, para que "Arroz Integral Grado 1 Grano Largo Bolsa"
# igual encuentre "Arroz Integral". Sabor/marca/atributos afinan el puntaje, no descartan.
def _core_terms(query: str) -> set[str]:
    product = canonicalize(query)
    type_key = product.canonical_name.split(":")[0] if product.canonical_name else ""
    aliases = PRODUCT_TYPES.get(type_key)
    if aliases:
        return set(aliases)
    tokens = _query_tokens(query)
    return {max(tokens, key=len)} if tokens else set()


def select_best_products(products: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    scored = [
        {**product, "_match_score": score_product_for_query(product, query)}
        for product in products
        if product.get("price") is not None
    ]
    core = _core_terms(query)
    if core:
        filtered = []
        for product in scored:
            haystack = normalize_compare_text(
                " ".join(
                    str(product.get(key) or "")
                    for key in ("name", "brand", "category", "seller")
                )
            )
            words = {_canonical_token(word) for word in haystack.split()}
            if any(_word_matches(term, words) for term in core):
                filtered.append(product)
        scored = filtered

    # ponytail: si pides un atributo (sin azúcar / integral), usa SOLO los que lo
    # tienen; pero si ninguno lo tiene, deja los normales como alternativa.
    required_attrs = _required_attributes(query)
    if required_attrs:
        with_attr = [
            product
            for product in scored
            if all(
                _has_attribute(
                    " ".join(str(product.get(k) or "") for k in ("name", "brand", "category", "seller")),
                    attribute,
                )
                for attribute in required_attrs
            )
        ]
        if with_attr:
            scored = with_attr

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
        adapter = get_store_adapter(store)
        # ponytail: las tiendas sin API pública (Tottus/Unimarc/Acuenta) se marcan
        # "no disponible" al instante, sin gastar llamadas de red que fallarían.
        if adapter and adapter.requires_playwright and not get_settings().PLAYWRIGHT_ENABLED:
            return index, {
                "store": store,
                "count": 0,
                "matched_count": 0,
                "best": None,
                "alternatives": [],
                "warning": None,
                "applied_query": item.query,
                "unavailable": True,
                "error": "Tienda sin API pública disponible (no se puede leer su catálogo)",
            }
        try:
            # ponytail: Líder tiene cadena de fallback lenta (18-20s) y ahora puede
            # reintentar variantes; le damos 25s. Las demás por API, 15s.
            if adapter and adapter.requires_playwright:
                timeout = 45
            elif store == "lider":
                timeout = 25
            else:
                timeout = 15
            response = await asyncio.wait_for(
                _maybe_await(search_products(item.query, limit=limit_per_store, store=store)),
                timeout=timeout,
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

    # ponytail: Lider rechaza varias búsquedas casi simultáneas (anti-bot). Le damos
    # un carril propio de solo 2 a la vez; las demás tiendas (API) van con 8.
    semaphore = asyncio.Semaphore(8)
    lider_semaphore = asyncio.Semaphore(1)

    async def compare_store_limited(index: int, item: ShoppingListItem, store: str):
        async with semaphore:
            if store == "lider":
                async with lider_semaphore:
                    return await compare_store(index, item, store)
            return await compare_store(index, item, store)

    store_results = await asyncio.gather(
        *(
            compare_store_limited(index, item, store)
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


# ponytail: "Jaleas (Frambuesa, Piña, Guinda)" son 3 productos distintos; una sola
# regex expande cada sabor a su propia búsqueda en vez de buscar todo junto.
def _expand_flavor_list(query: str) -> list[str]:
    match = re.search(r"\(([^)]*)\)", query)
    if not match:
        return [query]
    base = query[: match.start()].strip()
    flavors = [part.strip() for part in re.split(r"[,/]| y ", match.group(1)) if part.strip()]
    if len(flavors) <= 1:
        rest = match.group(1).strip()
        return [re.sub(r"\s+", " ", f"{base} {rest}").strip()]
    return [re.sub(r"\s+", " ", f"{base} {flavor}").strip() for flavor in flavors]


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
        if not query:
            continue
        # ponytail: quita la cantidad inicial ("2 Queso..." -> "Queso...") salvo que
        # sea peso ("1 kg Pollo"); el número ensucia la búsqueda y rompe los enlaces de Lider.
        amount_match = re.match(r"^(\d+)\s+(.+)$", query)
        if amount_match and amount_match.group(2).split()[0].lower() not in UNIT_WORDS:
            query = amount_match.group(2)
        for expanded in _expand_flavor_list(query):
            key = expanded.lower()
            if not expanded or key in seen:
                continue
            seen.add(key)
            items.append(ShoppingListItem(query=expanded, quantity=max(1, quantity)))

    return items
