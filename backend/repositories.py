from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.db_models import BasketItemRecord, BasketRecord, PriceHistoryRecord, UserRecord


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_username(self, username: str) -> Optional[UserRecord]:
        return self.session.get(UserRecord, username)

    def get_by_email(self, email: str) -> Optional[UserRecord]:
        return self.session.scalar(select(UserRecord).where(UserRecord.email == email))

    def create(self, username: str, email: str, hashed_password: str) -> UserRecord:
        user = UserRecord(
            username=username,
            email=email,
            hashed_password=hashed_password,
            created_at=datetime.now(),
            is_active=True,
        )
        self.session.add(user)
        return user


class BasketRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, basket_id: str, name: str, user_id: Optional[str]) -> BasketRecord:
        basket = BasketRecord(
            id=basket_id,
            name=name,
            user_id=user_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.session.add(basket)
        return basket

    def get(self, basket_id: str) -> Optional[BasketRecord]:
        return self.session.scalar(
            select(BasketRecord)
            .where(BasketRecord.id == basket_id)
            .options(selectinload(BasketRecord.items))
        )

    def list_for_user(self, user_id: Optional[str] = None) -> list[BasketRecord]:
        statement = select(BasketRecord).options(selectinload(BasketRecord.items))
        if user_id is not None:
            statement = statement.where(BasketRecord.user_id == user_id)
        return list(self.session.scalars(statement).all())

    def add_item(
        self,
        basket: BasketRecord,
        *,
        product_id: str,
        name: str,
        price: float,
        quantity: int,
        store: str,
    ) -> None:
        existing_item = next(
            (item for item in basket.items if item.product_id == product_id),
            None,
        )
        if existing_item:
            existing_item.quantity += quantity
        else:
            basket.items.append(
                BasketItemRecord(
                    product_id=product_id,
                    name=name,
                    price=price,
                    quantity=quantity,
                    store=store,
                    added_at=datetime.now(),
                )
            )
        basket.updated_at = datetime.now()

    def remove_item(self, basket: BasketRecord, product_id: str) -> bool:
        item = next((item for item in basket.items if item.product_id == product_id), None)
        if not item:
            return False

        self.session.delete(item)
        basket.updated_at = datetime.now()
        return True

    def update_item_quantity(self, basket: BasketRecord, product_id: str, quantity: int) -> bool:
        item = next((item for item in basket.items if item.product_id == product_id), None)
        if not item:
            return False

        if quantity <= 0:
            self.session.delete(item)
        else:
            item.quantity = quantity
        basket.updated_at = datetime.now()
        return True

    def delete(self, basket: BasketRecord) -> None:
        self.session.delete(basket)


class PriceHistoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def latest_for_product(self, product_id: str, store: str) -> Optional[PriceHistoryRecord]:
        return self.session.scalar(
            select(PriceHistoryRecord)
            .where(
                PriceHistoryRecord.product_id == product_id,
                PriceHistoryRecord.store == store,
            )
            .order_by(PriceHistoryRecord.date.desc())
            .limit(1)
        )

    def create(
        self,
        *,
        product_id: str,
        store: str,
        price: float,
        url: Optional[str],
    ) -> PriceHistoryRecord:
        record = PriceHistoryRecord(
            product_id=product_id,
            store=store,
            price=price,
            date=datetime.now(),
            url=url,
        )
        self.session.add(record)
        return record

    def list_for_product(self, product_id: str, store: str, limit: int = 30) -> list[PriceHistoryRecord]:
        return list(
            self.session.scalars(
                select(PriceHistoryRecord)
                .where(
                    PriceHistoryRecord.product_id == product_id,
                    PriceHistoryRecord.store == store,
                )
                .order_by(PriceHistoryRecord.date.asc())
                .limit(limit)
            ).all()
        )
