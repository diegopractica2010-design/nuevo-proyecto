from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from backend.models_baskets import Basket, BasketItem, BasketSummary, PriceHistory


# Almacenamiento en memoria (para desarrollo)
_BASKETS: Dict[str, Basket] = {}
_PRICE_HISTORY: Dict[str, List[PriceHistory]] = {}


class BasketService:
    @staticmethod
    def create_basket(name: str, user_id: Optional[str] = None) -> Basket:
        basket_id = str(uuid.uuid4())
        basket = Basket(
            id=basket_id,
            name=name,
            user_id=user_id,
            items=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        _BASKETS[basket_id] = basket
        return basket

    @staticmethod
    def get_basket(basket_id: str) -> Optional[Basket]:
        return _BASKETS.get(basket_id)

    @staticmethod
    def get_user_baskets(user_id: Optional[str] = None) -> List[BasketSummary]:
        baskets = []
        for basket in _BASKETS.values():
            if user_id is None or basket.user_id == user_id:
                total_price = sum(item.price * item.quantity for item in basket.items)
                stores = list(set(item.store for item in basket.items))
                baskets.append(BasketSummary(
                    id=basket.id,
                    name=basket.name,
                    item_count=len(basket.items),
                    total_price=total_price,
                    stores=stores,
                    created_at=basket.created_at
                ))
        return sorted(baskets, key=lambda x: x.created_at, reverse=True)

    @staticmethod
    def add_to_basket(basket_id: str, product_data: dict, quantity: int = 1) -> bool:
        basket = _BASKETS.get(basket_id)
        if not basket:
            return False

        # Verificar si el producto ya está en la canasta
        existing_item = None
        for item in basket.items:
            if item.product_id == product_data.get('id'):
                existing_item = item
                break

        if existing_item:
            existing_item.quantity += quantity
        else:
            item = BasketItem(
                product_id=product_data.get('id', ''),
                name=product_data.get('name', ''),
                price=product_data.get('price', 0),
                quantity=quantity,
                store=product_data.get('source', 'lider')
            )
            basket.items.append(item)

        basket.updated_at = datetime.now()
        return True

    @staticmethod
    def remove_from_basket(basket_id: str, product_id: str) -> bool:
        basket = _BASKETS.get(basket_id)
        if not basket:
            return False

        basket.items = [item for item in basket.items if item.product_id != product_id]
        basket.updated_at = datetime.now()
        return True

    @staticmethod
    def delete_basket(basket_id: str) -> bool:
        return _BASKETS.pop(basket_id, None) is not None


class PriceHistoryService:
    @staticmethod
    def record_price(product_id: str, store: str, price: float, url: Optional[str] = None):
        key = f"{store}:{product_id}"
        history = _PRICE_HISTORY.get(key, [])

        # Solo guardar si el precio cambió significativamente (>1%)
        if history and abs(history[-1].price - price) / history[-1].price < 0.01:
            return

        history.append(PriceHistory(
            product_id=product_id,
            store=store,
            price=price,
            date=datetime.now(),
            url=url
        ))

        # Mantener solo los últimos 30 registros
        _PRICE_HISTORY[key] = history[-30:]

    @staticmethod
    def get_price_history(product_id: str, store: str) -> List[PriceHistory]:
        key = f"{store}:{product_id}"
        return _PRICE_HISTORY.get(key, [])

    @staticmethod
    def get_price_trends(product_id: str, store: str, days: int = 30) -> dict:
        history = PriceHistoryService.get_price_history(product_id, store)
        if not history:
            return {"current_price": None, "min_price": None, "max_price": None, "trend": "stable"}

        recent_history = [h for h in history if h.date > datetime.now() - timedelta(days=days)]
        if not recent_history:
            return {"current_price": None, "min_price": None, "max_price": None, "trend": "stable"}

        current_price = recent_history[-1].price
        min_price = min(h.price for h in recent_history)
        max_price = max(h.price for h in recent_history)

        # Calcular tendencia básica
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
            "history_count": len(recent_history)
        }