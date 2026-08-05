from dataclasses import dataclass
from uuid import UUID
from typing import List
from decimal import Decimal
from domain.entities.order import Order
from domain.value_objects.money import Money

@dataclass
class CreateOrderCommand:
    customer_id: UUID
    items: List[dict] # [{"product_id": uuid, "qty": 2, "price": 10000}]
    notes: str = None

class CreateOrderHandler:
    def __init__(self, order_repo):
        self.order_repo = order_repo
    
    def handle(self, cmd: CreateOrderCommand) -> Order:
        # 1. Creamos la orden
        total = Money(Decimal('0'), "PYG")
        order = Order(customer_id=cmd.customer_id, total=total, notes=cmd.notes)
        
        # 2. Agregamos items
        for item in cmd.items:
            price = Money(Decimal(str(item["price"])), "PYG")
            order.add_item(item["product_id"], item["qty"], price)
        
        # 3. Guardamos
        self.order_repo.save(order)
        return order
