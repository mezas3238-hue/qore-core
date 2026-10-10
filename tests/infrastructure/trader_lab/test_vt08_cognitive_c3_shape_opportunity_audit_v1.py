from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_cognitive_c3_shape_opportunity_audit_v1 import (
    is_c3_closure_shape,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar


def _bar(open_: str, high: str, low: str, close: str) -> Vt08B01Bar:
    opened = datetime(2026, 1, 1, tzinfo=UTC)
    return Vt08B01Bar(
        opened_at=opened,
        closed_at=opened.replace(hour=4),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_bull_c3_shape_closes_over_c2_body_without_extreme_sweep() -> None:
    c2 = _bar("100", "110", "90", "95")
    c3 = _bar("96", "109", "91", "101")
    assert is_c3_closure_shape(c2, c3, bias=DemoTradingSetupSide.LONG)


def test_c3_shape_rejects_c2_extreme_sweep() -> None:
    c2 = _bar("100", "110", "90", "95")
    c3 = _bar("96", "111", "91", "101")
    assert not is_c3_closure_shape(c2, c3, bias=DemoTradingSetupSide.LONG)
