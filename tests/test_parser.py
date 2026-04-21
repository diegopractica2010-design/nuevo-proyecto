from pathlib import Path
import unittest

from backend.parser import parse_catalog_page, parse_products


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class ParseProductsTests(unittest.TestCase):
    def test_parse_inline_search_state_fixture(self):
        html = (FIXTURES_DIR / "lider_search_leche.html").read_text(encoding="utf-8")

        parsed = parse_catalog_page(html)
        products = parsed.products

        self.assertEqual(parsed.parser, "inline_search")
        self.assertEqual(len(products), 2)

        first_product = products[0]
        self.assertEqual(
            first_product["name"],
            "Leche Natural Descremada Lonco Leche 1 L Loncoleche",
        )
        self.assertEqual(first_product["brand"], "Loncoleche")
        self.assertEqual(first_product["sku"], "00780291000727")
        self.assertEqual(first_product["price"], 1090.0)
        self.assertEqual(first_product["original_price"], 1190.0)
        self.assertEqual(first_product["discount_percent"], 8)
        self.assertEqual(first_product["savings_amount"], 100.0)
        self.assertEqual(first_product["unit_price"], "$1.090 x lt")
        self.assertEqual(first_product["availability"], "IN_STOCK")
        self.assertTrue(first_product["in_stock"])
        self.assertEqual(first_product["category"], "Leche")
        self.assertEqual(first_product["badges"], ["Rebaja"])
        self.assertEqual(first_product["image"], "https://example.com/leche-1.jpg")
        self.assertTrue(first_product["is_offer"])
        self.assertEqual(
            first_product["url"],
            "https://super.lider.cl/ip/leche/leche-natural-descremada-lonco-leche/00780291000727",
        )

    def test_parse_next_data_payload(self):
        html = """
        <html>
          <body>
            <script id=__NEXT_DATA__ type="application/json">
              {
                "props": {
                  "pageProps": {
                    "initialData": {
                      "searchResult": {
                        "itemStacks": [
                          {
                            "items": [
                              {
                                "id": "abc",
                                "name": "Leche Entera 1 L Lider",
                                "brand": "Lider",
                                "usItemId": "0001",
                                "canonicalUrl": "/ip/leche/leche-entera/0001",
                                "sellerName": "Lider",
                                "availabilityStatusV2": {
                                  "display": "In stock",
                                  "value": "IN_STOCK"
                                },
                                "imageInfo": {
                                  "thumbnailUrl": "https://example.com/leche-next.jpg"
                                },
                                "category": {
                                  "path": [
                                    {"name": "Frescos"},
                                    {"name": "Leche"}
                                  ]
                                },
                                "priceInfo": {
                                  "linePrice": "$1.050",
                                  "itemPrice": "$1.250",
                                  "wasPrice": "$1.250",
                                  "savingsAmt": 200,
                                  "unitPrice": "$1.050 x lt"
                                }
                              }
                            ]
                          }
                        ]
                      }
                    }
                  }
                }
              }
            </script>
          </body>
        </html>
        """

        products = parse_products(html)

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["name"], "Leche Entera 1 L Lider")
        self.assertEqual(products[0]["sku"], "0001")
        self.assertEqual(products[0]["price"], 1050.0)
        self.assertEqual(products[0]["original_price"], 1250.0)
        self.assertEqual(products[0]["discount_percent"], 16)
        self.assertTrue(products[0]["in_stock"])

    def test_parse_ld_json_fallback(self):
        html = """
        <html>
          <body>
            <script type="application/ld+json">
              {
                "@context": "https://schema.org",
                "@type": "ItemList",
                "itemListElement": [
                  {
                    "@type": "ListItem",
                    "position": 1,
                    "item": {
                      "@type": "Product",
                      "name": "Leche Natural Entera Caja 1 L Lider",
                      "brand": {
                        "@type": "Brand",
                        "name": "Lider"
                      },
                      "image": "https://example.com/leche-3.jpg",
                      "url": "https://super.lider.cl/ip/leche/leche-natural-entera-caja/00040000720074?tracking=1",
                      "offers": {
                        "@type": "Offer",
                        "price": "1000",
                        "priceCurrency": "CLP",
                        "availability": "https://schema.org/InStock"
                      }
                    }
                  }
                ]
              }
            </script>
          </body>
        </html>
        """

        products = parse_products(html)

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["name"], "Leche Natural Entera Caja 1 L Lider")
        self.assertEqual(products[0]["brand"], "Lider")
        self.assertEqual(products[0]["price"], 1000.0)
        self.assertEqual(products[0]["image"], "https://example.com/leche-3.jpg")
        self.assertTrue(products[0]["in_stock"])
        self.assertEqual(
            products[0]["url"],
            "https://super.lider.cl/ip/leche/leche-natural-entera-caja/00040000720074",
        )


if __name__ == "__main__":
    unittest.main()
