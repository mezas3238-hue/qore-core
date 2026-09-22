from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r119_previous_source_day_alignment as r119,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)


def _bar(open_: str, close: str) -> Vt08IndexC2R1Bar:
    opened = datetime(2026, 1, 1, tzinfo=UTC)
    high = str(max(Decimal(open_), Decimal(close)) + Decimal("1"))
    low = str(min(Decimal(open_), Decimal(close)) - Decimal("1"))
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=15),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_r119_v4_alignment_semantics_are_exact() -> None:
    bullish = _bar("100", "101")
    bearish = _bar("101", "100")
    doji = _bar("100", "100")

    assert r119._body_sign(bullish) == 1
    assert r119._body_sign(bearish) == -1
    assert r119._body_sign(doji) == 0

    assert r119._aligned(bullish, DemoTradingSetupSide.LONG) is True
    assert r119._aligned(bearish, DemoTradingSetupSide.SHORT) is True
    assert r119._aligned(bearish, DemoTradingSetupSide.LONG) is False
    assert r119._aligned(doji, DemoTradingSetupSide.LONG) is False


def test_r119_surface_and_r118_source_are_pinned() -> None:
    assert r119.EXPECTED_STANDARD == {
        "5Y": 1756,
        "2Y": 746,
        "R66": 546,
    }
    assert r119.SOURCE_R118_RUN_ID == 35667373524
    assert r119.SOURCE_R118_ARTIFACT_ID == 10669755410
    assert r119.SOURCE_R118_ARTIFACT_DIGEST == (
        "sha256:0a5fd516e7d3c795171b31f63a0eabf957ddb35ad27a934c6ba2746c7032421a"
    )
