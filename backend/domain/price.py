from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Price:
    product_key: str
    store_id: str
    value: float
    observed_at: datetime

