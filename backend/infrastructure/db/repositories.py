from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.domain.normalization.matching import canonicalize
from backend.domain.price import Price
from backend.domain.product import Product
from backend.infrastructure.db.models import PriceRecord, ProductRecord, StoreRecord


class ProductRepo:
    def __init__(self, session: Session):
        self.session = session

    def upsert(self, product: Product) -> ProductRecord:
        existing = self.session.scalar(
            select(ProductRecord).where(ProductRecord.canonical_key == product.canonical_key)
        )
        if existing:
            existing.canonical_name = product.canonical_name
            existing.brand = product.brand
            existing.quantity_value = product.quantity_value
            existing.quantity_unit = product.quantity_unit
            return existing

        record = ProductRecord(
            canonical_key=product.canonical_key,
            canonical_name=product.canonical_name,
            brand=product.brand,
            quantity_value=product.quantity_value,
            quantity_unit=product.quantity_unit,
        )
        self.session.add(record)
        return record

    def search_similar(self, query: str, limit: int = 10) -> list[ProductRecord]:
        product = canonicalize(query)
        terms = [term for term in product.canonical_name.split() if term]

        filters = []
        if product.brand:
            filters.append(ProductRecord.brand == product.brand)
        filters.extend(ProductRecord.canonical_name.ilike(f"%{term}%") for term in terms)

        statement = select(ProductRecord).order_by(ProductRecord.canonical_name).limit(limit)
        if filters:
            statement = statement.where(or_(*filters))
        return list(self.session.scalars(statement).all())


class PriceRepo:
    def __init__(self, session: Session):
        self.session = session

    def insert(self, price: Price) -> PriceRecord:
        product = self.session.scalar(
            select(ProductRecord).where(ProductRecord.canonical_key == price.product_key)
        )
        if product is None:
            raise ValueError(f"Product not found for key: {price.product_key}")

        store_id = _as_uuid(price.store_id)
        if self.session.get(StoreRecord, store_id) is None:
            raise ValueError(f"Store not found for id: {price.store_id}")

        record = PriceRecord(
            product_id=product.id,
            store_id=store_id,
            value=price.value,
            observed_at=price.observed_at,
        )
        self.session.add(record)
        return record


def _as_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))
