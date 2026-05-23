import re

from backend.domain.normalization.text import normalize_text
from backend.domain.normalization.units import convert_quantity
from backend.domain.product import Product


BRAND_ALIASES = {
    "tucapel": "tucapel",
    "tucapel sa": "tucapel",
    "tucapel s a": "tucapel",
    "lider": "lider",
    "acuenta": "acuenta",
    "loncoleche": "loncoleche",
    "lonco leche": "loncoleche",
    "nestle": "nestle",
    "soprole": "soprole",
    "colun": "colun",
    "lucchetti": "lucchetti",
    "carozzi": "carozzi",
    "ideal": "ideal",
    "watt": "watts",
    "watts": "watts",
    "pf": "pf",
    "miraflores": "miraflores",
    "banquete": "banquete",
    "chef": "chef",
    "natura": "natura",
    "belmont": "belmont",
    "costa": "costa",
    "dos en uno": "dos-en-uno",
    "ambrosoli": "ambrosoli",
    "fruna": "fruna",
    "quillayes": "quillayes",
    "calo": "calo",
    "surlat": "surlat",
    "cuisine co": "cuisine-co",
    "great value": "great-value",
    "selecta": "selecta",
    "sopas maggi": "maggi",
    "maggi": "maggi",
    "hellmanns": "hellmanns",
    "malloa": "malloa",
    "traverso": "traverso",
    "caricia": "caricia",
    "omo": "omo",
    "rinso": "rinso",
    "virginia": "virginia",
    "clorox": "clorox",
    "nova": "nova",
    "elite": "elite",
    "confort": "confort",
    "poett": "poett",
    "colgate": "colgate",
    "pepsodent": "pepsodent",
    "oral b": "oral-b",
    "dove": "dove",
    "nivea": "nivea",
    "gillette": "gillette",
    "purina": "purina",
    "champion": "champion",
}

PRODUCT_TYPES = {
    "arroz": {"arroz"},
    "leche": {"leche"},
    "aceite": {"aceite"},
    "fideo": {"fideo", "fideos", "pasta", "tallarin", "tallarines", "spaghetti", "espagueti"},
    "azucar": {"azucar"},
    "harina": {"harina"},
    "sal": {"sal"},
    "cafe": {"cafe"},
    "te": {"te"},
    "yogurt": {"yogurt", "yoghurt"},
    "queso": {"queso"},
    "mantequilla": {"mantequilla"},
    "margarina": {"margarina"},
    "pan": {"pan"},
    "atun": {"atun"},
    "jurel": {"jurel"},
    "salsa-tomate": {"salsa", "tomate"},
    "mayonesa": {"mayonesa"},
    "ketchup": {"ketchup"},
    "mostaza": {"mostaza"},
    "detergente": {"detergente"},
    "lavalozas": {"lavalozas"},
    "cloro": {"cloro"},
    "papel-higienico": {"papel", "higienico"},
    "toalla-papel": {"toalla", "nova"},
    "shampoo": {"shampoo"},
    "jabon": {"jabon"},
    "pasta-dental": {"pasta", "dental"},
    "desodorante": {"desodorante"},
    "pañal": {"panal", "panales"},
    "galleta": {"galleta", "galletas"},
    "cereal": {"cereal", "cereales"},
    "avena": {"avena"},
    "lenteja": {"lenteja", "lentejas"},
    "poroto": {"poroto", "porotos"},
    "garbanzo": {"garbanzo", "garbanzos"},
    "bebida": {"bebida"},
    "jugo": {"jugo", "nectar"},
    "agua": {"agua"},
    "cerveza": {"cerveza"},
    "vino": {"vino"},
    "pollo": {"pollo"},
    "carne": {"carne"},
    "hamburguesa": {"hamburguesa"},
    "salchicha": {"salchicha", "vienesa"},
    "helado": {"helado"},
    "chocolate": {"chocolate"},
    "mermelada": {"mermelada"},
    "conserva": {"conserva"},
    "carbon": {"carbon", "briqueta", "briquetas"},
}

VARIANT_ALIASES = {
    "grado1": {"grado 1", "grado uno", "gr 1", "g1"},
    "integral": {"integral"},
    "pregraneado": {"pregraneado", "pre graneado"},
    "grano-largo": {"grano largo", "largo"},
    "entera": {"entera", "entero"},
    "descremada": {"descremada", "descremado", "0"},
    "semidescremada": {"semidescremada", "semi descremada", "semidescremado"},
    "sin-lactosa": {"sin lactosa"},
    "maravilla": {"maravilla"},
    "canola": {"canola"},
    "oliva": {"oliva"},
    "vegetal": {"vegetal"},
    "espiral": {"espiral", "espirales"},
    "spaghetti": {"spaghetti", "espagueti"},
    "tallarin": {"tallarin", "tallarines"},
}

STOPWORDS = {
    "de",
    "del",
    "la",
    "el",
    "los",
    "las",
    "un",
    "una",
    "pack",
    "bolsa",
    "sachet",
    "caja",
    "botella",
    "unidad",
    "unidades",
    "x",
}

QUANTITY_PATTERN = re.compile(
    r"(?P<value>\d+(?:[,.]\d+)?)\s*(?P<unit>kg|kilo|kilos|g|gr|gramos?|l|lt|litro|litros|ml|cc)\b"
)


def extract_quantity(text: str) -> tuple[float, str] | None:
    normalized = normalize_text(text)
    match = QUANTITY_PATTERN.search(normalized)
    if not match:
        return None
    unit = match.group("unit")
    if unit in {"kilo", "kilos"}:
        unit = "kg"
    if unit == "cc":
        unit = "ml"
    return convert_quantity(float(match.group("value").replace(",", ".")), unit)


def canonicalize(raw_name: str) -> Product:
    normalized = normalize_text(raw_name)
    quantity = extract_quantity(normalized)
    without_quantity = QUANTITY_PATTERN.sub(" ", normalized)
    brand = _detect_brand(without_quantity)
    product_type = _detect_product_type(without_quantity)
    variants = _detect_variants(without_quantity)

    tokens = [
        token
        for token in without_quantity.split()
        if token not in STOPWORDS and token != brand and token not in _flatten_type_terms(product_type)
    ]
    canonical_name_parts = [product_type or (tokens[0] if tokens else "producto"), *variants]

    quantity_value = quantity[0] if quantity else None
    quantity_unit = quantity[1] if quantity else None

    return Product(
        canonical_name=":".join(dict.fromkeys(canonical_name_parts)),
        brand=brand,
        quantity_value=quantity_value,
        quantity_unit=quantity_unit,
    )


def are_equivalent(a: str | Product, b: str | Product) -> bool:
    first = canonicalize(a) if isinstance(a, str) else a
    second = canonicalize(b) if isinstance(b, str) else b
    return first.canonical_key == second.canonical_key


def _detect_brand(text: str) -> str | None:
    padded = f" {text} "
    for alias, canonical in sorted(BRAND_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if f" {alias} " in padded:
            return canonical
    return None


def _detect_product_type(text: str) -> str | None:
    words = set(text.split())
    for product_type, aliases in PRODUCT_TYPES.items():
        for alias in aliases:
            alias_words = set(alias.split())
            if alias_words and alias_words.issubset(words):
                return product_type
    return None


def _detect_variants(text: str) -> list[str]:
    padded = f" {text} "
    variants: list[str] = []
    for canonical, aliases in VARIANT_ALIASES.items():
        for alias in aliases:
            if f" {alias} " in padded:
                variants.append(canonical)
                break
    return variants


def _flatten_type_terms(product_type: str | None) -> set[str]:
    if not product_type:
        return set()
    terms = set()
    for alias in PRODUCT_TYPES.get(product_type, set()):
        terms.update(alias.split())
    return terms
