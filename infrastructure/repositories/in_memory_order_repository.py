from typing import Dict, Optional, List
from uuid import UUID
from application.ports.order_repository import OrderRepository
from domain.entities.order import Order

class InMemoryOrderRepository(OrderRepository):
    """Implementación en memoria para testing"""
    
    def __init__(self):
        self._orders: Dict[UUID, Order] = {}
    
    def save(self, order: Order) -> None:
        self._orders[order.id] = order
    
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        return self._orders.get(order_id)
    
    def list_by_customer(self, customer_id: UUID) -> List[Order]:
        return [o for o in self._orders.values() if o.customer_id == customer_id]
