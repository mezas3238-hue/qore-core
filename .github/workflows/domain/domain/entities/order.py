from dataclasses import dataclass, field
from uuid import UUID, uuid4
from typing import List, Optional
from domain.enums.order_state import OrderState
from domain.value_objects.money import Money

@dataclass
class OrderItem:
    product_id: UUID
    quantity: int
    unit_price: Money
    
    @property
    def subtotal(self) -> Money:
        return Money(self.unit_price.amount * self.quantity, self.unit_price.currency)

@dataclass
class Order:
    """Entidad central del dominio - una orden de pedido"""
    id: UUID = field(default_factory=uuid4)
    customer_id: UUID
    items: List[OrderItem] = field(default_factory=list)
    state: OrderState = OrderState.NEW
    total: Money
    notes: Optional[str] = None
    
    def confirm(self) -> None:
        if self.state!= OrderState.NEW:
            raise ValueError("Only NEW orders can be confirmed")
        self.state = OrderState.CONFIRMED
    
    def add_item(self, product_id: UUID, qty: int, price: Money) -> None:
        self.items.append(OrderItem(product_id, qty, price))
        self._recalculate_total()
    
    def _recalculate_total(self) -> None:
        total_amount = sum(item.subtotal.amount for item in self.items)
        self.total = Money(total_amount, self.total.currency)
