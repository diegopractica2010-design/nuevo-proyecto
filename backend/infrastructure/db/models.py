from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import CHAR, TypeDecorator

from backend.db import Base


class UUIDType(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PostgreSQLUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class StoreRecord(Base):
    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    prices: Mapped[list["PriceRecord"]] = relationship(back_populates="store")


class ProductRecord(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    canonical_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(300), index=True, nullable=False)
    brand: Mapped[str | None] = mapped_column(String(160), index=True, nullable=True)
    quantity_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )

    prices: Mapped[list["PriceRecord"]] = relationship(back_populates="product")


class PriceRecord(Base):
    __tablename__ = "prices"
    __table_args__ = (
        Index("ix_prices_product_store_observed", "product_id", "store_id", "observed_at"),
        Index("ix_prices_observed_at", "observed_at"),
        UniqueConstraint(
            "product_id",
            "store_id",
            "observed_at",
            name="uq_prices_product_store_observed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(),
        ForeignKey("products.id"),
        nullable=False,
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(),
        ForeignKey("stores.id"),
        nullable=False,
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    product: Mapped[ProductRecord] = relationship(back_populates="prices")
    store: Mapped[StoreRecord] = relationship(back_populates="prices")

