from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import capitalizer_native_market_context_v1 as ctx


def test_alignment_respects_trade_side() -> None:
    assert ctx._alignment(delta=Decimal("1"), side="LONG") == "ALIGNED"
    assert ctx._alignment(delta=Decimal("-1"), side="LONG") == "OPPOSED"
    assert ctx._alignment(delta=Decimal("-1"), side="SHORT") == "ALIGNED"
    assert ctx._alignment(delta=Decimal("0"), side="SHORT") == "FLAT"


def test_destination_uses_only_confirmed_pivots() -> None:
    class Pivot:
        def __init__(self, kind: str, price: str, confirmed_at: datetime) -> None:
            self.kind = kind
            self.price = Decimal(price)
            self.confirmed_at = confirmed_at

    entry_at = datetime(2026, 1, 1, 12, tzinfo=UTC)
    pivots = (
        Pivot("HIGH", "101", datetime(2026, 1, 1, 11, tzinfo=UTC)),
        Pivot("HIGH", "100.5", datetime(2026, 1, 1, 13, tzinfo=UTC)),
    )
    state, room, confirmed_at = ctx._destination(
        side="LONG",
        entry=Decimal("100"),
        risk=Decimal("0.5"),
        pivots=pivots,
        entry_at=entry_at,
    )
    assert state == "GE_2R"
    assert room == Decimal("2")
    assert confirmed_at == datetime(2026, 1, 1, 11, tzinfo=UTC)
