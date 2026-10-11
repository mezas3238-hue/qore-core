"""Deterministic evidence-frontier tests for V49 source H1 target availability.

Only fully closed M1 candles may invalidate a target before the decision.
These tests intentionally do not evaluate economic results or optimize signals.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    V48AggregatedBar,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    _untouched_h1_target_fast,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)

H1_CLOSED = datetime(2026, 9, 10, 10, tzinfo=UTC)
DECISION = H1_CLOSED + timedelta(minutes=2)
H1_HIGH = Decimal("105")
H1_LOW = Decimal("95")
MID = Decimal("100")


def _h1() -> V48AggregatedBar:
    return V48AggregatedBar(
        opened_at=H1_CLOSED - timedelta(hours=1),
        closed_at=H1_CLOSED,
        source=CapitalizerSourceBar(
            open=MID,
            high=H1_HIGH,
            low=H1_LOW,
            close=MID,
        ),
        minute_count=60,
    )


def _m1(
    *,
    minute: int,
    high: Decimal = Decimal("101"),
    low: Decimal = Decimal("99"),
) -> CapitalizerM1Bar:
    opened = H1_CLOSED + timedelta(minutes=minute)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=MID,
        high=high,
        low=low,
        close=MID,
        volume=None,
        digits=5,
    )


def _target(
    direction: CapitalizerSourceDirection,
    bars: tuple[CapitalizerM1Bar, ...],
) -> Decimal | None:
    return _untouched_h1_target_fast(
        (_h1(),),
        bars,
        tuple(row.opened_at for row in bars),
        decision_at=DECISION,
        decision_price=MID,
        direction=direction,
    )


@pytest.mark.parametrize(
    ("direction", "target", "future_high", "future_low"),
    [
        (CapitalizerSourceDirection.BULLISH, H1_HIGH, H1_HIGH, Decimal("99")),
        (CapitalizerSourceDirection.BEARISH, H1_LOW, Decimal("101"), H1_LOW),
    ],
)
def test_future_bar_opening_at_decision_cannot_invalidate_target(
    direction: CapitalizerSourceDirection,
    target: Decimal,
    future_high: Decimal,
    future_low: Decimal,
) -> None:
    # At 10:02, the candle 10:02–10:03 has not closed. Its range is unknowable.
    bars = (
        _m1(minute=0),
        _m1(minute=1),
        _m1(minute=2, high=future_high, low=future_low),
    )
    assert _target(direction, bars) == target


@pytest.mark.parametrize(
    ("direction", "high", "low"),
    [
        (CapitalizerSourceDirection.BULLISH, H1_HIGH, Decimal("99")),
        (CapitalizerSourceDirection.BEARISH, Decimal("101"), H1_LOW),
    ],
)
def test_bar_opening_at_h1_closure_counts_as_known_touch(
    direction: CapitalizerSourceDirection,
    high: Decimal,
    low: Decimal,
) -> None:
    # H1 closes at 10:00; 10:00–10:01 is fully known before 10:02.
    bars = (
        _m1(minute=0, high=high, low=low),
        _m1(minute=1),
        _m1(minute=2),
    )
    assert _target(direction, bars) is None


@pytest.mark.parametrize(
    ("direction", "expected"),
    [
        (CapitalizerSourceDirection.BULLISH, H1_HIGH),
        (CapitalizerSourceDirection.BEARISH, H1_LOW),
    ],
)
def test_valid_untouched_h1_target_remains_available(
    direction: CapitalizerSourceDirection,
    expected: Decimal,
) -> None:
    bars = (_m1(minute=0), _m1(minute=1), _m1(minute=2))
    assert _target(direction, bars) == expected
