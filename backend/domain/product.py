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
        name_parts = [part for part in normalize_text(self.canonical_name).replace(" ", ":").split(":") if part]
        product_type = name_parts[0] if name_parts else "producto"
        variants = name_parts[1:]
        quantity = "sin-cantidad"
        if self.quantity_value is not None and self.quantity_unit:
            value = float(self.quantity_value)
            normalized_value = int(value) if value.is_integer() else value
            quantity = f"{normalized_value}{normalize_text(self.quantity_unit)}"
        return ":".join([product_type, brand, *variants, str(quantity)])
