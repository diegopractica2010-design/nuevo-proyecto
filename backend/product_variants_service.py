"""
Servicio para detectar y resolver variantes de productos con diferentes cantidades.
Cuando un producto existe en múltiples tamaños/cantidades, pregunta al usuario cuál quiere.
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProductVariant:
    """Variante de un producto (ej: mismo nombre, distinto tamaño)."""
    id: str
    name: str
    brand: Optional[str]
    price: float
    quantity_value: Optional[float]
    quantity_unit: Optional[str]
    in_stock: bool
    url: Optional[str] = None
    
    def display_name(self) -> str:
        """Nombre para mostrar al usuario."""
        quantity_str = ""
        if self.quantity_value and self.quantity_unit:
            quantity_str = f" {self.quantity_value}{self.quantity_unit}"
        return f"{self.name}{quantity_str} - ${self.price:,.0f}".replace(",", ".")
    
    def canonical_quantity(self) -> Optional[tuple[float, str]]:
        """Devuelve (valor, unidad) normalizado para comparar."""
        if not self.quantity_value or not self.quantity_unit:
            return None
        
        # Normalizar a kg/l
        value = self.quantity_value
        unit = self.quantity_unit.lower()
        
        if unit in ("g", "gr"):
            return (value / 1000, "kg")
        if unit in ("ml", "cc"):
            return (value / 1000, "l")
        
        return (value, unit)
    
    def to_dict(self) -> dict[str, Any]:
        """Convierte a dict para respuesta JSON."""
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "price": self.price,
            "quantity": {
                "value": self.quantity_value,
                "unit": self.quantity_unit,
            } if self.quantity_value and self.quantity_unit else None,
            "in_stock": self.in_stock,
            "url": self.url,
            "display_name": self.display_name(),
        }


def _normalize_product_name(product: dict[str, Any]) -> str:
    """Extrae nombre normalizado sin la cantidad."""
    name = (product.get("name") or "").strip()
    brand = (product.get("brand") or "").strip()
    
    if not name:
        return ""
    
    # Eliminar cantidad del final: "Arroz Integral 1kg" -> "Arroz Integral"
    import re
    cleaned = re.sub(r"\s*\d+\.?\d*\s*(kg|kilo|kilos|g|gr|l|lt|lts|ml|cc|unidad|unidades)\s*$", "", name, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    
    # Usar brand como diferenciador si existe
    if brand:
        return f"{brand} {cleaned}".lower()
    return cleaned.lower()


def detect_product_variants(products: list[dict[str, Any]]) -> dict[str, list[ProductVariant]]:
    """
    Agrupa productos por nombre base. Devuelve dict donde cada key es el nombre
    normalizado y el value es una lista de variantes (diferentes cantidades).
    """
    variants_map: dict[str, list[ProductVariant]] = {}
    
    for product in products:
        if not product.get("name"):
            continue
        
        base_name = _normalize_product_name(product)
        if not base_name:
            continue
        
        variant = ProductVariant(
            id=product.get("id", ""),
            name=product.get("name", ""),
            brand=product.get("brand"),
            price=float(product.get("price") or 0),
            quantity_value=product.get("quantity_value"),
            quantity_unit=product.get("quantity_unit"),
            in_stock=product.get("in_stock", True),
            url=product.get("url"),
        )
        
        if base_name not in variants_map:
            variants_map[base_name] = []
        variants_map[base_name].append(variant)
    
    return variants_map


def has_variants(products: list[dict[str, Any]]) -> bool:
    """Chequea si hay productos con múltiples variantes."""
    variants = detect_product_variants(products)
    return any(len(v) > 1 for v in variants.values())


def get_variants_for_selection(
    products: list[dict[str, Any]],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Agrupa variantes y devuelve respuesta especial si hay múltiples tamaños.
    
    Respuesta:
    {
        "has_variants": true,
        "groups": [
            {
                "product_name": "Arroz Integral",
                "variants": [
                    {"id": "...", "display_name": "Arroz Integral 1kg - $2,490", ...},
                    {"id": "...", "display_name": "Arroz Integral 5kg - $11,990", ...},
                ],
            }
        ]
    }
    """
    variants_map = detect_product_variants(products)
    
    # Filtrar grupos con múltiples variantes
    multi_variant_groups = {
        name: variants
        for name, variants in variants_map.items()
        if len(variants) > 1
    }
    
    if not multi_variant_groups:
        # Sin variantes, devolver productos normales
        return products[:limit]
    
    # Agrupar variantes para presentación
    groups = []
    for product_name, variants in sorted(multi_variant_groups.items())[:limit]:
        # Ordenar por cantidad (para que vaya de menor a mayor)
        sorted_variants = sorted(
            variants,
            key=lambda v: (v.canonical_quantity() or (float('inf'), '')),
        )
        
        groups.append({
            "product_name": product_name,
            "count": len(sorted_variants),
            "variants": [v.to_dict() for v in sorted_variants],
        })
    
    return {
        "has_variants": True,
        "groups": groups,
        "total_variants": sum(len(v) for v in multi_variant_groups.values()),
    }


def resolve_variant_selection(
    variant_id: str,
    products: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Resuelve la selección del usuario a un producto específico."""
    for product in products:
        if product.get("id") == variant_id:
            return product
    return None
