from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderIntent,
    OrderIntentId,
    OrderIntentValidationError,
    OrderPrice,
    OrderQuantity,
    OrderSide,
    OrderType,
)
from qore.infrastructure.ports import ExternalRequestMetadata

_NOW = datetime(2026, 8, 8, 6, 30, tzinfo=UTC)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("ae000000-0000-0000-0000-000000000001")),
    causation_id=CausationId(UUID("ae000000-0000-0000-0000-000000000002")),
)


def _intent(
    *,
    order_type: OrderType = OrderType.MARKET,
    limit_price: OrderPrice | None = None,
) -> OrderIntent:
    return OrderIntent(
        intent_id=OrderIntentId(UUID("ae000000-0000-0000-0000-000000000003")),
        idempotency_key=ExecutionIdempotencyKey(
            UUID("ae000000-0000-0000-0000-000000000004")
        ),
        instrument=ExecutionInstrument("EURUSD"),
        side=OrderSide.BUY,
        order_type=order_type,
        quantity=OrderQuantity(Decimal("1.25")),
        created_at=_NOW,
        metadata=_METADATA,
        limit_price=limit_price,
    )


def test_market_intent_is_declarative_and_decimal_based() -> None:
    intent = _intent()

    assert intent.order_type is OrderType.MARKET
    assert intent.quantity.value == Decimal("1.25")
    assert intent.limit_price is None


def test_limit_intent_requires_positive_decimal_price() -> None:
    intent = _intent(
        order_type=OrderType.LIMIT,
        limit_price=OrderPrice(Decimal("1.1000")),
    )

    assert intent.limit_price == OrderPrice(Decimal("1.1000"))


def test_market_intent_rejects_limit_price() -> None:
    with pytest.raises(OrderIntentValidationError):
        _intent(limit_price=OrderPrice(Decimal("1.1000")))


def test_limit_intent_rejects_missing_price() -> None:
    with pytest.raises(OrderIntentValidationError):
        _intent(order_type=OrderType.LIMIT)


def test_quantity_and_price_reject_float_non_finite_and_non_positive() -> None:
    with pytest.raises(OrderIntentValidationError):
        OrderQuantity(1.0)  # type: ignore[arg-type]
    for value in (Decimal("0"), Decimal("-1"), Decimal("NaN")):
        with pytest.raises(OrderIntentValidationError):
            OrderQuantity(value)
    for value in (Decimal("0"), Decimal("Infinity")):
        with pytest.raises(OrderIntentValidationError):
            OrderPrice(value)


def test_instrument_requires_canonical_uppercase_identity() -> None:
    with pytest.raises(OrderIntentValidationError):
        ExecutionInstrument("eurusd")


def test_intent_requires_timezone_aware_created_at() -> None:
    with pytest.raises(OrderIntentValidationError):
        OrderIntent(
            intent_id=OrderIntentId(
                UUID("ae000000-0000-0000-0000-000000000003")
            ),
            idempotency_key=ExecutionIdempotencyKey(
                UUID("ae000000-0000-0000-0000-000000000004")
            ),
            instrument=ExecutionInstrument("EURUSD"),
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=OrderQuantity(Decimal("1")),
            created_at=datetime(2026, 8, 8, 6, 30),
            metadata=_METADATA,
        )


def test_logical_values_are_stable_and_include_no_generated_identity() -> None:
    intent = _intent()

    assert intent.logical_values()[2:7] == (
        ("EURUSD",),
        "buy",
        "market",
        ("1.25",),
        _NOW.isoformat(),
    )
