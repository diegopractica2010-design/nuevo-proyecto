import unittest

from backend.domain.normalization.matching import are_equivalent, canonicalize, extract_quantity
from backend.domain.normalization.text import normalize_text
from backend.application.use_cases.normalize_product import (
    normalize_product_name,
    products_are_equivalent,
    find_competitor_price,
)


class NormalizationTests(unittest.TestCase):
    def test_normalize_text_lowercases_removes_accents_and_symbols(self):
        self.assertEqual(normalize_text("Arroz Súper! Tucapel"), "arroz super tucapel")

    def test_extract_quantity_converts_kg_to_g(self):
        self.assertEqual(extract_quantity("Arroz Tucapel 1kg"), (1000.0, "g"))

    def test_canonicalize_detects_brand_quantity_and_base_name(self):
        product = canonicalize("Arroz Tucapel 1kg")

        self.assertEqual(product.canonical_name, "arroz")
        self.assertEqual(product.brand, "tucapel")
        self.assertEqual(product.quantity_value, 1000.0)
        self.assertEqual(product.quantity_unit, "g")
        self.assertEqual(product.canonical_key, "arroz:tucapel:1000g")

    def test_equivalent_products_with_reordered_brand_and_unit(self):
        self.assertTrue(are_equivalent("Arroz Tucapel 1kg", "arroz 1000 g tucapel"))

    # --- 5+ new matching tests ---

    def test_equivalent_milk_brands_with_unit_variants(self):
        """1 litro and 1000 ml are equivalent for the same product."""
        self.assertTrue(are_equivalent("Leche Soprole 1 litro", "soprole leche 1000 ml"))

    def test_non_equivalent_different_brands(self):
        """Same product type but different brands must NOT be equivalent."""
        self.assertFalse(are_equivalent("Arroz Tucapel 1kg", "Arroz Carozzi 1kg"))

    def test_non_equivalent_different_quantities(self):
        """Same brand and type but different quantities must NOT be equivalent."""
        self.assertFalse(are_equivalent("Arroz Tucapel 1kg", "Arroz Tucapel 5kg"))

    def test_equivalent_brand_alias_normalization(self):
        """Alternate brand spellings resolve to the same canonical brand."""
        self.assertTrue(are_equivalent("aceite watts 1l", "Aceite Watt 1 litro"))

    def test_normalize_product_name_use_case_returns_product(self):
        """normalize_product_name use case wraps canonicalize correctly."""
        product = normalize_product_name("Leche Colun 1kg")
        self.assertEqual(product.brand, "colun")
        self.assertIsNotNone(product.canonical_key)

    def test_products_are_equivalent_use_case(self):
        """products_are_equivalent use case delegates to are_equivalent."""
        self.assertTrue(products_are_equivalent("Arroz Tucapel 1kg", "arroz tucapel 1000 g"))

    def test_find_competitor_price_returns_matching_price(self):
        """find_competitor_price returns the competitor price when products match canonically."""
        store_results = [
            {
                "store": "lider",
                "best": {"name": "Arroz Tucapel 1kg", "brand": "tucapel", "price": 1299.0},
            },
            {
                "store": "jumbo",
                "best": {"name": "arroz tucapel 1000 g", "brand": "tucapel", "price": 1350.0},
            },
        ]
        price = find_competitor_price("Arroz Tucapel 1kg", store_results, own_store="lider")
        self.assertEqual(price, 1350.0)

    def test_find_competitor_price_returns_none_when_no_match(self):
        """find_competitor_price returns None when competitor product is different."""
        store_results = [
            {
                "store": "lider",
                "best": {"name": "Arroz Tucapel 1kg", "brand": "tucapel", "price": 1299.0},
            },
            {
                "store": "jumbo",
                "best": {"name": "Arroz Carozzi 1kg", "brand": "carozzi", "price": 1100.0},
            },
        ]
        price = find_competitor_price("Arroz Tucapel 1kg", store_results, own_store="lider")
        self.assertIsNone(price)


if __name__ == "__main__":
    unittest.main()
