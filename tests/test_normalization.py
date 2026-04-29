import unittest

from backend.domain.normalization.matching import are_equivalent, canonicalize, extract_quantity
from backend.domain.normalization.text import normalize_text


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
        self.assertEqual(product.canonical_key, "tucapel|arroz|1000g")

    def test_equivalent_products_with_reordered_brand_and_unit(self):
        self.assertTrue(are_equivalent("Arroz Tucapel 1kg", "arroz 1000 g tucapel"))


if __name__ == "__main__":
    unittest.main()
