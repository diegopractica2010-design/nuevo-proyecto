import os
import unittest

import pytest

from backend.auth import AuthService
from backend.basket_service import BasketService, PriceHistoryService
from backend.db import reset_db

# ---------------------------------------------------------------------------
# PostgreSQL integration tests — skipped unless DATABASE_URL points to Postgres
# ---------------------------------------------------------------------------
_DB_URL = os.getenv("DATABASE_URL", "")
_IS_POSTGRES = _DB_URL.startswith("postgresql")


@pytest.mark.skipif(not _IS_POSTGRES, reason="Requires DATABASE_URL=postgresql://...")
class TestPostgresIntegration:
    """Run Alembic migrations and basic CRUD against a real PostgreSQL instance."""

    def test_migrations_run_cleanly(self):
        from alembic import command
        from alembic.config import Config

        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", _DB_URL)
        command.upgrade(cfg, "head")

    def test_tables_exist_after_migration(self):
        from sqlalchemy import create_engine, inspect as sa_inspect

        engine = create_engine(_DB_URL)
        try:
            tables = sa_inspect(engine).get_table_names()
        finally:
            engine.dispose()

        for expected in ("users", "baskets", "basket_items", "price_history"):
            assert expected in tables, f"Table '{expected}' missing after migration"

    def test_role_column_exists_on_users(self):
        from sqlalchemy import create_engine, inspect as sa_inspect

        engine = create_engine(_DB_URL)
        try:
            cols = {c["name"] for c in sa_inspect(engine).get_columns("users")}
        finally:
            engine.dispose()

        assert "role" in cols, "Column 'role' missing from users table"

    def test_create_and_fetch_user(self):
        from backend.db import reset_db

        reset_db()
        user = AuthService.create_user("pg_user", "pg@test.com", "secret123")
        loaded = AuthService.get_user("pg_user")
        assert loaded is not None
        assert loaded.email == "pg@test.com"
        assert loaded.role == "user"


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
        paginated = BasketService.get_user_baskets("paula")

        self.assertTrue(added)
        self.assertIsNotNone(loaded)
        self.assertEqual(len(loaded.items), 1)
        self.assertEqual(loaded.items[0].quantity, 2)
        self.assertEqual(paginated.items[0].total_price, 2000)

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
