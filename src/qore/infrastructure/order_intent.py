from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.ports import ExternalPortError, ExternalRequestMetadata


class OrderIntentError(ExternalPortError):
    """Base error for canonical controlled order intents."""

    __slots__ = ()


class OrderIntentValidationError(OrderIntentError):
    """Violation of an order-intent invariant."""

    __slots__ = ()


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


@dataclass(frozen=True, slots=True)
class OrderIntentId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise OrderIntentValidationError("order intent id must be UUID")

    def logical_values(self) -> tuple[UUID, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutionIdempotencyKey:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise OrderIntentValidationError("execution idempotency key must be UUID")

    def logical_values(self) -> tuple[UUID, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutionInstrument:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[A-Z0-9][A-Z0-9._-]{1,31}", self.value
        ) is None:
            raise OrderIntentValidationError(
                "execution instrument must use canonical uppercase syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class OrderQuantity:
    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise OrderIntentValidationError("order quantity must be Decimal")
        if not self.value.is_finite() or self.value <= 0:
            raise OrderIntentValidationError(
                "order quantity must be a finite positive Decimal"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (format(self.value, "f"),)


@dataclass(frozen=True, slots=True)
class OrderPrice:
    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise OrderIntentValidationError("order price must be Decimal")
        if not self.value.is_finite() or self.value <= 0:
            raise OrderIntentValidationError(
                "order price must be a finite positive Decimal"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (format(self.value, "f"),)


@dataclass(frozen=True, slots=True)
class OrderIntent:
    """Immutable trading intent. Construction never authorizes or executes it."""

    intent_id: OrderIntentId
    idempotency_key: ExecutionIdempotencyKey
    instrument: ExecutionInstrument
    side: OrderSide
    order_type: OrderType
    quantity: OrderQuantity
    created_at: datetime
    metadata: ExternalRequestMetadata
    limit_price: OrderPrice | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.intent_id, OrderIntentId):
            raise OrderIntentValidationError("intent_id must be OrderIntentId")
        if not isinstance(self.idempotency_key, ExecutionIdempotencyKey):
            raise OrderIntentValidationError(
                "idempotency_key must be ExecutionIdempotencyKey"
            )
        if not isinstance(self.instrument, ExecutionInstrument):
            raise OrderIntentValidationError(
                "instrument must be ExecutionInstrument"
            )
        if not isinstance(self.side, OrderSide):
            raise OrderIntentValidationError("side must be OrderSide")
        if not isinstance(self.order_type, OrderType):
            raise OrderIntentValidationError("order_type must be OrderType")
        if not isinstance(self.quantity, OrderQuantity):
            raise OrderIntentValidationError("quantity must be OrderQuantity")
        if not isinstance(self.created_at, datetime):
            raise OrderIntentValidationError("created_at must be a datetime")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise OrderIntentValidationError("created_at must be timezone-aware")
        if not isinstance(self.metadata, ExternalRequestMetadata):
            raise OrderIntentValidationError(
                "metadata must be ExternalRequestMetadata"
            )
        if self.limit_price is not None and not isinstance(
            self.limit_price, OrderPrice
        ):
            raise OrderIntentValidationError("limit_price must be OrderPrice or None")
        if self.order_type is OrderType.MARKET and self.limit_price is not None:
            raise OrderIntentValidationError(
                "market order intent must not carry limit_price"
            )
        if self.order_type is OrderType.LIMIT and self.limit_price is None:
            raise OrderIntentValidationError(
                "limit order intent requires limit_price"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.intent_id.logical_values(),
            self.idempotency_key.logical_values(),
            self.instrument.logical_values(),
            self.side.value,
            self.order_type.value,
            self.quantity.logical_values(),
            self.created_at.isoformat(),
            self.metadata.logical_values(),
            self.limit_price.logical_values() if self.limit_price is not None else None,
        )
