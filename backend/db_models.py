from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base


class UserRecord(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(80), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class BasketRecord(Base):
    __tablename__ = "baskets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )
    items: Mapped[list["BasketItemRecord"]] = relationship(
        back_populates="basket",
        cascade="all, delete-orphan",
        order_by="BasketItemRecord.added_at",
    )


class BasketItemRecord(Base):
    __tablename__ = "basket_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    basket_id: Mapped[str] = mapped_column(ForeignKey("baskets.id"), index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    store: Mapped[str] = mapped_column(String(40), default="lider", nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    basket: Mapped[BasketRecord] = relationship(back_populates="items")


class PriceHistoryRecord(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    store: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True, nullable=False)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
