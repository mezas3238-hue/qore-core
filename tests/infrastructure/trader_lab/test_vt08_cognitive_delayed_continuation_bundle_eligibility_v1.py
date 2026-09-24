from decimal import Decimal
from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.vt08_cognitive_delayed_continuation_bundle_eligibility_v1 import (
    _unique_causal_fvg_at_confirmation,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar


def _bar(index: int, *, high: str, low: str, close: str) -> Vt08B01Bar:
    start = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=15 * index)
    return Vt08B01Bar(
        opened_at=start,
        closed_at=start + timedelta(minutes=15),
        open=Decimal(close),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_unique_causal_fvg_requires_confirmation_close_inside() -> None:
    bars = (
        _bar(0, high="100", low="99", close="99.5"),
        _bar(1, high="100", low="99", close="99.5"),
        _bar(2, high="103", low="101", close="102"),
        _bar(3, high="102.5", low="101.5", close="102"),
    )
    poi = _unique_causal_fvg_at_confirmation(
        bars,
        confirmation_index=3,
        side=DemoTradingSetupSide.LONG,
    )
    assert poi is not None
    assert poi[0] == Decimal("100")
    assert poi[1] == Decimal("101")
