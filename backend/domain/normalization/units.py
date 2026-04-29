from decimal import Decimal


MASS_UNITS = {
    "kg": Decimal("1000"),
    "g": Decimal("1"),
    "gr": Decimal("1"),
    "gramo": Decimal("1"),
    "gramos": Decimal("1"),
}
VOLUME_UNITS = {
    "l": Decimal("1000"),
    "lt": Decimal("1000"),
    "litro": Decimal("1000"),
    "litros": Decimal("1000"),
    "ml": Decimal("1"),
}
UNIT_ALIASES = {
    "kg": "kg",
    "g": "g",
    "gr": "g",
    "gramo": "g",
    "gramos": "g",
    "l": "l",
    "lt": "l",
    "litro": "l",
    "litros": "l",
    "ml": "ml",
}


def canonical_unit(unit: str) -> str:
    normalized = unit.lower()
    if normalized in MASS_UNITS:
        return "g"
    if normalized in VOLUME_UNITS:
        return "ml"
    return UNIT_ALIASES.get(normalized, normalized)


def convert_quantity(value: float, unit: str) -> tuple[float, str]:
    normalized = unit.lower()
    decimal_value = Decimal(str(value).replace(",", "."))
    if normalized in MASS_UNITS:
        converted = decimal_value * MASS_UNITS[normalized]
        return float(converted), "g"
    if normalized in VOLUME_UNITS:
        converted = decimal_value * VOLUME_UNITS[normalized]
        return float(converted), "ml"
    return float(decimal_value), canonical_unit(normalized)
