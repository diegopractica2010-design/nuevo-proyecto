"""Tests para product variants service."""

import pytest

from backend.product_variants_service import (
    ProductVariant,
    detect_product_variants,
    has_variants,
    get_variants_for_selection,
    resolve_variant_selection,
    _normalize_product_name,
)


class TestProductVariant:
    """Tests para ProductVariant."""
    
    def test_display_name_without_quantity(self):
        """display_name() sin cantidad."""
        variant = ProductVariant(
            id="sku-001",
            name="Arroz Integral",
            brand="Primo",
            price=2490.0,
            quantity_value=None,
            quantity_unit=None,
            in_stock=True,
        )
        assert variant.display_name() == "Arroz Integral - $2,490"
    
    def test_display_name_with_quantity(self):
        """display_name() con cantidad."""
        variant = ProductVariant(
            id="sku-001",
            name="Arroz Integral",
            brand="Primo",
            price=2490.0,
            quantity_value=1,
            quantity_unit="kg",
            in_stock=True,
        )
        assert "1kg" in variant.display_name()
        assert "2,490" in variant.display_name()
    
    def test_canonical_quantity_normalization(self):
        """canonical_quantity() normaliza unidades."""
        # Gramos a kg
        v1 = ProductVariant(
            id="1", name="Arroz", brand=None, price=100.0,
            quantity_value=1000, quantity_unit="g", in_stock=True
        )
        assert v1.canonical_quantity() == (1.0, "kg")
        
        # ML a L
        v2 = ProductVariant(
            id="2", name="Leche", brand=None, price=100.0,
            quantity_value=1000, quantity_unit="ml", in_stock=True
        )
        assert v2.canonical_quantity() == (1.0, "l")
    
    def test_to_dict(self):
        """to_dict() devuelve dict válido."""
        variant = ProductVariant(
            id="sku-001",
            name="Arroz",
            brand="Primo",
            price=2490.0,
            quantity_value=1,
            quantity_unit="kg",
            in_stock=True,
        )
        d = variant.to_dict()
        assert d["id"] == "sku-001"
        assert d["name"] == "Arroz"
        assert d["price"] == 2490.0
        assert "display_name" in d


class TestNormalizeProductName:
    """Tests para _normalize_product_name()."""
    
    def test_removes_quantity_from_name(self):
        """Elimina cantidad del final del nombre."""
        assert _normalize_product_name({"name": "Arroz Integral 1kg", "brand": None}).lower() == "arroz integral"
        assert _normalize_product_name({"name": "Leche 1l", "brand": None}).lower() == "leche"
    
    def test_includes_brand(self):
        """Incluye brand en normalización."""
        result = _normalize_product_name({"name": "Arroz", "brand": "Primo"})
        assert "primo" in result.lower()
        assert "arroz" in result.lower()
    
    def test_empty_name_returns_empty_string(self):
        """Nombre vacío devuelve string vacío."""
        assert _normalize_product_name({"name": "", "brand": None}) == ""


class TestDetectVariants:
    """Tests para detect_product_variants()."""
    
    def test_groups_same_product_different_quantities(self):
        """Agrupa productos iguales con distintas cantidades."""
        products = [
            {"id": "1", "name": "Arroz Integral 1kg", "brand": "Primo", "price": 2490, "quantity_value": 1, "quantity_unit": "kg", "in_stock": True},
            {"id": "2", "name": "Arroz Integral 5kg", "brand": "Primo", "price": 11990, "quantity_value": 5, "quantity_unit": "kg", "in_stock": True},
        ]
        variants = detect_product_variants(products)
        
        assert len(variants) == 1
        key = list(variants.keys())[0]
        assert len(variants[key]) == 2
    
    def test_different_brands_separate_groups(self):
        """Diferentes marcas crean grupos separados."""
        products = [
            {"id": "1", "name": "Arroz", "brand": "Primo", "price": 2490, "quantity_value": None, "quantity_unit": None, "in_stock": True},
            {"id": "2", "name": "Arroz", "brand": "Maravilla", "price": 2290, "quantity_value": None, "quantity_unit": None, "in_stock": True},
        ]
        variants = detect_product_variants(products)
        assert len(variants) == 2


class TestHasVariants:
    """Tests para has_variants()."""
    
    def test_returns_true_with_multiple_variants(self):
        """Devuelve True cuando hay múltiples variantes."""
        products = [
            {"id": "1", "name": "Arroz 1kg", "brand": None, "price": 2490, "quantity_value": 1, "quantity_unit": "kg", "in_stock": True},
            {"id": "2", "name": "Arroz 5kg", "brand": None, "price": 11990, "quantity_value": 5, "quantity_unit": "kg", "in_stock": True},
        ]
        assert has_variants(products) is True
    
    def test_returns_false_without_variants(self):
        """Devuelve False cuando no hay variantes."""
        products = [
            {"id": "1", "name": "Arroz", "brand": None, "price": 2490, "quantity_value": None, "quantity_unit": None, "in_stock": True},
        ]
        assert has_variants(products) is False


class TestResolveVariant:
    """Tests para resolve_variant_selection()."""
    
    def test_finds_product_by_id(self):
        """Encuentra producto por ID."""
        products = [
            {"id": "sku-001", "name": "Arroz", "price": 2490},
            {"id": "sku-002", "name": "Arroz", "price": 11990},
        ]
        result = resolve_variant_selection("sku-002", products)
        assert result is not None
        assert result["id"] == "sku-002"
        assert result["price"] == 11990
    
    def test_returns_none_when_not_found(self):
        """Devuelve None cuando no encuentra producto."""
        products = [{"id": "sku-001", "name": "Arroz"}]
        result = resolve_variant_selection("nonexistent", products)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
