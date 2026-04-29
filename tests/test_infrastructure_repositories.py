import unittest
from datetime import datetime

from backend.db import SessionLocal, reset_db
from backend.domain.normalization.matching import canonicalize
from backend.domain.price import Price
from backend.infrastructure.db.models import ProductRecord, StoreRecord
from backend.infrastructure.db.repositories import PriceRepo, ProductRepo


class InfrastructureRepositoryTests(unittest.TestCase):
    def setUp(self):
        reset_db()

    def test_product_upsert_does_not_duplicate_products(self):
        with SessionLocal() as session:
            repo = ProductRepo(session)

            first = repo.upsert(canonicalize("Arroz Tucapel 1kg"))
            session.flush()
            second = repo.upsert(canonicalize("arroz 1000 g tucapel"))
            session.commit()

            self.assertEqual(first.id, second.id)
            self.assertEqual(session.query(ProductRecord).count(), 1)

    def test_search_similar_finds_matching_products(self):
        with SessionLocal() as session:
            repo = ProductRepo(session)
            repo.upsert(canonicalize("Arroz Tucapel 1kg"))
            repo.upsert(canonicalize("Leche Soprole 1 L"))
            session.commit()

            matches = repo.search_similar("arroz 1000 g tucapel")

            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0].canonical_key, "tucapel|arroz|1000g")

    def test_price_insert_links_product_and_store(self):
        with SessionLocal() as session:
            product = ProductRepo(session).upsert(canonicalize("Arroz Tucapel 1kg"))
            store = StoreRecord(name="Lider")
            session.add(store)
            session.flush()

            record = PriceRepo(session).insert(
                Price(
                    product_key=product.canonical_key,
                    store_id=str(store.id),
                    value=1290,
                    observed_at=datetime(2026, 4, 29, 12, 0, 0),
                )
            )
            session.commit()

            self.assertEqual(record.product_id, product.id)
            self.assertEqual(record.store_id, store.id)
            self.assertEqual(record.value, 1290)


if __name__ == "__main__":
    unittest.main()
