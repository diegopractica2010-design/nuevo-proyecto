from dataclasses import dataclass

from backend.domain.normalization.text import normalize_text


@dataclass(frozen=True)
class Product:
    canonical_name: str
    brand: str | None
    quantity_value: float | None
    quantity_unit: str | None

    @property
    def canonical_key(self) -> str:
        brand = normalize_text(self.brand) if self.brand else "sin-marca"
        name = normalize_text(self.canonical_name)
        quantity = "sin-cantidad"
        if self.quantity_value is not None and self.quantity_unit:
            value = float(self.quantity_value)
            normalized_value = int(value) if value.is_integer() else value
            quantity = f"{normalized_value}{normalize_text(self.quantity_unit)}"
        return "|".join([brand, name, str(quantity)])
