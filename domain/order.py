from dataclasses import dataclass
from enum import Enum
from typing import Optional
from decimal import Decimal
from datetime import datetime


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Optional[Decimal]
    status: OrderStatus
    created_at: datetime
    filled_at: Optional[datetime] = None
