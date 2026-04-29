import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from backend.db import SessionLocal, reset_db
from backend.domain.normalization.matching import canonicalize
from backend.domain.price import Price
from backend.infrastructure.cache.cache import set_cache_client
from backend.infrastructure.db.models import StoreRecord
from backend.infrastructure.db.repositories import PriceRepo, ProductRepo
from backend.main import app


class FakeRedis:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ex=None):
        self.values[key] = value
        return True


class ApiSearchRouteTests(unittest.TestCase):
    def setUp(self):
        reset_db()
        set_cache_client(FakeRedis())
        self.client = TestClient(app)

    def tearDown(self):
        set_cache_client(None)

    def test_api_search_returns_best_option_and_alternatives_from_db(self):
        with SessionLocal() as session:
            product = ProductRepo(session).upsert(canonicalize("Arroz Tucapel 1kg"))
            lider = StoreRecord(name="Lider")
            jumbo = StoreRecord(name="Jumbo")
            session.add_all([lider, jumbo])
            session.flush()

            price_repo = PriceRepo(session)
            observed_at = datetime(2026, 4, 29, 12, 0, 0)
            price_repo.insert(
                Price(
                    product_key=product.canonical_key,
                    store_id=str(lider.id),
                    value=1290.0,
                    observed_at=observed_at,
                )
            )
            price_repo.insert(
                Price(
                    product_key=product.canonical_key,
                    store_id=str(jumbo.id),
                    value=1190.0,
                    observed_at=observed_at,
                )
            )
            session.commit()

        response = self.client.get("/api/search?q=arroz")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["best_option"]["store_name"], "Jumbo")
        self.assertEqual(data["best_option"]["price"], 1190.0)
        self.assertEqual(data["best_option"]["canonical_key"], "tucapel|arroz|1000g")
        self.assertEqual(len(data["alternatives"]), 1)
        self.assertEqual(data["alternatives"][0]["store_name"], "Lider")


if __name__ == "__main__":
    unittest.main()
