from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional, List
from domain.entities.order import Order

class OrderRepository(ABC):
    """Puerto - Define COMO guardar órdenes sin decir DONDE"""
    
    @abstractmethod
    def save(self, order: Order) -> None:
        """Guardar o actualizar una orden"""
        pass
    
    @abstractmethod
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """Buscar orden por ID"""
        pass
    
    @abstractmethod
    def list_by_customer(self, customer_id: UUID) -> List[Order]:
        """Listar todas las órdenes de un cliente"""
        pass
