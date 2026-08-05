from enum import Enum

class OrderState(str, Enum):
    """Estados del ciclo de vida de una orden"""
    NEW = "NEW"
    CONFIRMED = "CONFIRMED"
    IN_PREP = "IN_PREP"
    READY = "READY"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED" 
