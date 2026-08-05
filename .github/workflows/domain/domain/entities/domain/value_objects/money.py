from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

Currency = Literal["PYG", "USD", "BRL"]

@dataclass(frozen=True)
class Money:
    """Value Object para dinero - inmutable y seguro"""
    amount: Decimal
    currency: Currency = "PYG"
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        # Aseguramos 2 decimales
        object.__setattr__(self, 'amount', self.amount.quantize(Decimal('0.01')))
    
    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)
    
    def __mul__(self, factor: int) -> 'Money':
        return Money(self.amount * factor, self.currency)
