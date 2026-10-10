"""Causal tests of explicit TTrades 2026 EQ range distinction."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.trader_lab.vt08_5m_ttrades_c2_c3_source_eq_range_v1 import (
    EqRangeBasis,
    source_eq_after_closure,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

NY = ZoneInfo("America/New_York")


def h4(o: str, h: str, low: str, c: str) -> Vt08B01Bar:
    t = datetime(2026, 10, 8, 5, tzinfo=NY).astimezone(UTC)
    return Vt08B01Bar(
        opened_at=t,
        closed_at=t + timedelta(hours=4),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(low),
        close=Decimal(c),
    )


@pytest.mark.parametrize(
    ("side", "o", "c", "expected_basis", "eq"),
    [
        (DemoTradingSetupSide.LONG, "100", "106", EqRangeBasis.FULL_CANDLE_C2_WITH_SWING, "100"),
        (DemoTradingSetupSide.SHORT, "106", "100", EqRangeBasis.FULL_CANDLE_C2_WITH_SWING, "100"),
        (DemoTradingSetupSide.LONG, "106", "102", EqRangeBasis.CLOSE_TO_EXTREME_C2_AGAINST_SWING, "96"),
        (DemoTradingSetupSide.SHORT, "94", "98", EqRangeBasis.CLOSE_TO_EXTREME_C2_AGAINST_SWING, "104"),
    ],
)
def test_C2_range_depends_on_direction_of_CLOSE(
    side: DemoTradingSetupSide, o: str, c: str, expected_basis: EqRangeBasis, eq: str,
) -> None:
    candle = h4(o, "110", "90", c)
    actual = source_eq_after_closure(
        candle, candle_label="C2", intended_side=side,
        closure_adjudicated=True, decision_at=candle.closed_at,
    )
    assert actual is not None
    assert actual.basis is expected_basis
    assert str(actual.eq) == eq
    assert actual.source_complete_entry is False


def test_C3_always_uses_full_range_after_proven_closure() -> None:
    candle = h4("106", "110", "90", "102")
    actual = source_eq_after_closure(
        candle, candle_label="C3", intended_side=DemoTradingSetupSide.LONG,
        closure_adjudicated=True, decision_at=candle.closed_at,
    )
    assert actual is not None
    assert actual.basis is EqRangeBasis.FULL_CANDLE_C3
    assert actual.eq == Decimal("100")


def test_without_adjudicated_closure_return_unknown_not_guess() -> None:
    candle = h4("100", "110", "90", "106")
    assert source_eq_after_closure(
        candle, candle_label="C2", intended_side=DemoTradingSetupSide.LONG,
        closure_adjudicated=False, decision_at=candle.closed_at,
    ) is None


def test_unclosed_H4_cannot_compute_future_EQ() -> None:
    candle = h4("100", "110", "90", "106")
    with pytest.raises(ValueError, match="unclosed"):
        source_eq_after_closure(
            candle, candle_label="C2", intended_side=DemoTradingSetupSide.LONG,
            closure_adjudicated=True, decision_at=candle.closed_at - timedelta(minutes=15),
        )


def test_doji_C2_not_misclassified_bull_or_bear() -> None:
    candle = h4("100", "110", "90", "100")
    assert source_eq_after_closure(
        candle, candle_label="C2", intended_side=DemoTradingSetupSide.LONG,
        closure_adjudicated=True, decision_at=candle.closed_at,
    ) is None


def test_invalid_timeframe_label_or_naive_time_rejected() -> None:
    candle = h4("100", "110", "90", "106")
    with pytest.raises(ValueError, match="source label"):
        source_eq_after_closure(
            candle, candle_label="C4", intended_side=DemoTradingSetupSide.LONG,
            closure_adjudicated=True, decision_at=candle.closed_at,
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        source_eq_after_closure(
            candle, candle_label="C2", intended_side=DemoTradingSetupSide.LONG,
            closure_adjudicated=True, decision_at=datetime(2026, 10, 8, 9),
        )
