from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import UTC, datetime


class BasketItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int = 1
    store: str
    added_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Basket(BaseModel):
    id: str
    name: str
    user_id: Optional[str] = None  # Para futuro sistema de usuarios
    items: List[BasketItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BasketSummary(BaseModel):
    id: str
    name: str
    item_count: int
    total_price: float
    stores: List[str]
    created_at: datetime


class PriceHistory(BaseModel):
    product_id: str
    store: str
    price: float
    date: datetime
    url: Optional[str] = None
