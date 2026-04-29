import re

from backend.domain.product import Product
from backend.domain.normalization.text import normalize_text
from backend.domain.normalization.units import convert_quantity


KNOWN_BRANDS = {
    "lider",
    "loncoleche",
    "nestle",
    "soprole",
    "colun",
    "tucapel",
    "lucchetti",
    "carozzi",
    "ideal",
    "watt",
    "watts",
    "pf",
}

QUANTITY_PATTERN = re.compile(
    r"(?P<value>\d+(?:[,.]\d+)?)\s*(?P<unit>kg|g|gr|gramos?|l|lt|litros?|ml)\b"
)


def extract_quantity(text: str) -> tuple[float, str] | None:
    normalized = normalize_text(text)
    match = QUANTITY_PATTERN.search(normalized)
    if not match:
        return None
    return convert_quantity(float(match.group("value").replace(",", ".")), match.group("unit"))


def canonicalize(raw_name: str) -> Product:
    normalized = normalize_text(raw_name)
    quantity = extract_quantity(normalized)
    without_quantity = QUANTITY_PATTERN.sub(" ", normalized)
    tokens = [token for token in without_quantity.split() if token]

    brand = _detect_brand(tokens)
    name_tokens = [token for token in tokens if token != brand]
    canonical_name = " ".join(name_tokens)

    quantity_value = quantity[0] if quantity else None
    quantity_unit = quantity[1] if quantity else None

    return Product(
        canonical_name=canonical_name,
        brand=brand,
        quantity_value=quantity_value,
        quantity_unit=quantity_unit,
    )


def are_equivalent(a: str | Product, b: str | Product) -> bool:
    first = canonicalize(a) if isinstance(a, str) else a
    second = canonicalize(b) if isinstance(b, str) else b
    return first.canonical_key == second.canonical_key


def _detect_brand(tokens: list[str]) -> str | None:
    for token in tokens:
        if token in KNOWN_BRANDS:
            return token
    return None

