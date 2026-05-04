from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from backend.db import SessionLocal
from backend.db_models import BasketItemRecord, BasketRecord, PriceHistoryRecord
from backend.models_baskets import Basket, BasketItem, BasketSummary, PriceHistory
from backend.repositories import BasketRepository, PriceHistoryRepository


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _to_basket_item(record: BasketItemRecord) -> BasketItem:
    return BasketItem(
        product_id=record.product_id,
        name=record.name,
        price=record.price,
        quantity=record.quantity,
        store=record.store,
        added_at=_as_utc(record.added_at),
    )


def _to_basket(record: BasketRecord) -> Basket:
    return Basket(
        id=record.id,
        name=record.name,
        user_id=record.user_id,
        items=[_to_basket_item(item) for item in record.items],
        created_at=_as_utc(record.created_at),
        updated_at=_as_utc(record.updated_at),
    )


def _to_price_history(record: PriceHistoryRecord) -> PriceHistory:
    return PriceHistory(
        product_id=record.product_id,
        store=record.store,
        price=record.price,
        date=_as_utc(record.date),
        url=record.url,
    )


class BasketService:
    @staticmethod
    def create_basket(name: str, user_id: Optional[str] = None) -> Basket:
        with SessionLocal() as session:
            basket = BasketRepository(session).create(str(uuid.uuid4()), name, user_id)
            session.commit()
            session.refresh(basket)
            return _to_basket(basket)

    @staticmethod
    def get_basket(basket_id: str) -> Optional[Basket]:
        with SessionLocal() as session:
            basket = BasketRepository(session).get(basket_id)
            return _to_basket(basket) if basket else None

    @staticmethod
    def get_user_baskets(user_id: Optional[str] = None) -> list[BasketSummary]:
        with SessionLocal() as session:
            records = BasketRepository(session).list_for_user(user_id)

        summaries: list[BasketSummary] = []
        for basket in records:
            total_price = sum(item.price * item.quantity for item in basket.items)
            stores = sorted({item.store for item in basket.items})
            summaries.append(
                BasketSummary(
                    id=basket.id,
                    name=basket.name,
                    item_count=len(basket.items),
                    total_price=total_price,
                    stores=stores,
                    created_at=basket.created_at,
                )
            )
        return sorted(summaries, key=lambda item: item.created_at, reverse=True)

    @staticmethod
    def add_to_basket(basket_id: str, product_data: dict, quantity: int = 1) -> bool:
        product_id = str(product_data.get("id") or product_data.get("sku") or product_data.get("url") or "")
        if not product_id:
            product_id = str(product_data.get("name") or "")

        with SessionLocal() as session:
            baskets = BasketRepository(session)
            basket = baskets.get(basket_id)
            if not basket:
                return False

            baskets.add_item(
                basket,
                product_id=product_id,
                name=str(product_data.get("name") or ""),
                price=float(product_data.get("price") or 0),
                quantity=quantity,
                store=str(product_data.get("source") or "lider"),
            )
            session.commit()
            return True

    @staticmethod
    def remove_from_basket(basket_id: str, product_id: str) -> bool:
        with SessionLocal() as session:
            baskets = BasketRepository(session)
            basket = baskets.get(basket_id)
            if not basket:
                return False

            if not baskets.remove_item(basket, product_id):
                return False

            session.commit()
            return True

    @staticmethod
    def update_item_quantity(basket_id: str, product_id: str, quantity: int) -> bool:
        with SessionLocal() as session:
            baskets = BasketRepository(session)
            basket = baskets.get(basket_id)
            if not basket:
                return False

            if not baskets.update_item_quantity(basket, product_id, quantity):
                return False

            session.commit()
            return True

    @staticmethod
    def delete_basket(basket_id: str) -> bool:
        with SessionLocal() as session:
            baskets = BasketRepository(session)
            basket = baskets.get(basket_id)
            if not basket:
                return False
            baskets.delete(basket)
            session.commit()
            return True


class PriceHistoryService:
    @staticmethod
    def record_price(product_id: str, store: str, price: float, url: Optional[str] = None):
        with SessionLocal() as session:
            history = PriceHistoryRepository(session)
            latest = history.latest_for_product(product_id, store)

            if latest is not None:
                if latest.price == 0:
                    pass
                elif abs(latest.price - price) / latest.price < 0.01:
                    return

            history.create(product_id=product_id, store=store, price=price, url=url)
            session.commit()

    @staticmethod
    def get_price_history(product_id: str, store: str) -> list[PriceHistory]:
        with SessionLocal() as session:
            records = PriceHistoryRepository(session).list_for_product(product_id, store)
            return [_to_price_history(record) for record in records]

    @staticmethod
    def get_price_trends(product_id: str, store: str, days: int = 30) -> dict:
        history = PriceHistoryService.get_price_history(product_id, store)
        if not history:
            return {"current_price": None, "min_price": None, "max_price": None, "trend": "stable"}

        cutoff = datetime.now(UTC) - timedelta(days=days)
        recent_history = [h for h in history if _as_utc(h.date) > cutoff]
        if not recent_history:
            return {"current_price": None, "min_price": None, "max_price": None, "trend": "stable"}

        current_price = recent_history[-1].price
        min_price = min(h.price for h in recent_history)
        max_price = max(h.price for h in recent_history)

        if len(recent_history) >= 2:
            first_price = recent_history[0].price
            last_price = recent_history[-1].price
            if last_price < first_price * 0.95:
                trend = "decreasing"
            elif last_price > first_price * 1.05:
                trend = "increasing"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return {
            "current_price": current_price,
            "min_price": min_price,
            "max_price": max_price,
            "trend": trend,
            "history_count": len(recent_history),
        }
