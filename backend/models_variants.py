"""Modelos Pydantic para respuesta de variantes de productos."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class VariantDTO(BaseModel):
    """Variante individual de un producto."""
    id: str
    name: str
    brand: Optional[str] = None
    price: float
    quantity: Optional[dict[str, Any]] = None  # {"value": 1, "unit": "kg"}
    in_stock: bool = True
    url: Optional[str] = None
    display_name: str


class VariantGroup(BaseModel):
    """Grupo de variantes del mismo producto."""
    product_name: str
    count: int = Field(gt=0)
    variants: list[VariantDTO]


class VariantSelectionResponse(BaseModel):
    """Respuesta cuando hay múltiples variantes."""
    has_variants: bool = True
    groups: list[VariantGroup]
    total_variants: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "has_variants": True,
                "groups": [
                    {
                        "product_name": "arroz integral",
                        "count": 3,
                        "variants": [
                            {
                                "id": "sku-001",
                                "name": "Arroz Integral 1kg",
                                "brand": "Primo",
                                "price": 2490,
                                "quantity": {"value": 1, "unit": "kg"},
                                "in_stock": True,
                                "url": "https://...",
                                "display_name": "Arroz Integral 1kg - $2,490",
                            },
                        ],
                    }
                ],
                "total_variants": 3,
            }
        }
