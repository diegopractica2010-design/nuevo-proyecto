import unittest

from backend.auth import AuthService
from backend.basket_service import BasketService, PriceHistoryService
from backend.db import reset_db


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        reset_db()

    def test_auth_users_are_persisted(self):
        created = AuthService.create_user("paula", "paula@example.com", "secret123")

        authenticated = AuthService.authenticate_user("paula", "secret123")
        loaded = AuthService.get_user("paula")

        self.assertEqual(created.username, "paula")
        self.assertIsNotNone(authenticated)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.email, "paula@example.com")

    def test_baskets_and_items_are_persisted(self):
        basket = BasketService.create_basket("Semana", user_id="paula")
        added = BasketService.add_to_basket(
            basket.id,
            {
                "id": "sku-1",
                "name": "Leche Entera",
                "price": 1000,
                "source": "lider",
            },
            quantity=2,
        )

        loaded = BasketService.get_basket(basket.id)
        summaries = BasketService.get_user_baskets("paula")

        self.assertTrue(added)
        self.assertIsNotNone(loaded)
        self.assertEqual(len(loaded.items), 1)
        self.assertEqual(loaded.items[0].quantity, 2)
        self.assertEqual(summaries[0].total_price, 2000)

    def test_price_history_is_persisted_and_deduplicates_small_changes(self):
        PriceHistoryService.record_price("sku-1", "lider", 1000, "https://example.com/1")
        PriceHistoryService.record_price("sku-1", "lider", 1005, "https://example.com/1")
        PriceHistoryService.record_price("sku-1", "lider", 1100, "https://example.com/1")

        history = PriceHistoryService.get_price_history("sku-1", "lider")
        trends = PriceHistoryService.get_price_trends("sku-1", "lider")

        self.assertEqual(len(history), 2)
        self.assertEqual(trends["current_price"], 1100)
        self.assertEqual(trends["trend"], "increasing")

    def test_basket_item_quantity_can_be_updated(self):
        basket = BasketService.create_basket("Semana", user_id="paula")
        BasketService.add_to_basket(
            basket.id,
            {"id": "sku-1", "name": "Leche Entera", "price": 1000, "source": "lider"},
            quantity=1,
        )

        updated = BasketService.update_item_quantity(basket.id, "sku-1", 3)
        loaded = BasketService.get_basket(basket.id)

        self.assertTrue(updated)
        self.assertEqual(loaded.items[0].quantity, 3)


if __name__ == "__main__":
    unittest.main()
