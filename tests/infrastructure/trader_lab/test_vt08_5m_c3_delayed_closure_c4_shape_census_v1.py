"""Adversarial C3 delayed closure→C4 shape, authoritative timing and DST."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.trader_lab.vt08_5m_c3_delayed_closure_c4_shape_census_v1 import (
    c2_reversal_closure,
    c3_body_closure,
    first_c4_eq_observation,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

NY = ZoneInfo("America/New_York")


def candle(t: datetime, o: str, h: str, low: str, c: str, hours: int = 4) -> Vt08B01Bar:
    return Vt08B01Bar(
        opened_at=t.astimezone(UTC),
        closed_at=(t + timedelta(hours=hours)).astimezone(UTC),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(low),
        close=Decimal(c),
    )


@pytest.mark.parametrize("month", [1, 7])
def test_c3_close_to_c4_not_same_candle_and_ny_clock_stable(month: int) -> None:
    t = datetime(2026, month, 15, 1, tzinfo=NY)
    c2 = candle(t, "100", "105", "95", "98")
    c3 = candle(t + timedelta(hours=4), "97", "104", "96", "103")
    found = c3_body_closure(c2, c3)
    assert len(found) == 1
    assert found[0].side is DemoTradingSetupSide.LONG
    assert found[0].c3_confirmed_at == c3.closed_at
    assert c3.closed_at.astimezone(NY).hour == 9
    assert c3.opened_at.astimezone(NY).hour == 5


def test_bearish_c3_close_inside_c2_extremes() -> None:
    t = datetime(2026, 1, 15, 1, tzinfo=NY)
    c2 = candle(t, "99", "105", "95", "102")
    c3 = candle(t + timedelta(hours=4), "103", "104", "96", "97")
    found = c3_body_closure(c2, c3)
    assert len(found) == 1
    assert found[0].side is DemoTradingSetupSide.SHORT
    assert found[0].body_engulfed is True


def test_c3_sweeping_c2_high_or_low_rejected() -> None:
    t = datetime(2026, 1, 15, 1, tzinfo=NY)
    c2 = candle(t, "100", "105", "95", "98")
    c3_high = candle(t + timedelta(hours=4), "97", "105.1", "96", "103")
    c3_low = candle(t + timedelta(hours=4), "97", "104", "94.9", "103")
    assert c3_body_closure(c2, c3_high) == ()
    assert c3_body_closure(c2, c3_low) == ()


def test_c3_close_not_over_body_no_shape() -> None:
    t = datetime(2026, 1, 15, 1, tzinfo=NY)
    c2 = candle(t, "100", "105", "95", "98")
    at_body = candle(t + timedelta(hours=4), "97", "103", "96", "100")
    assert c3_body_closure(c2, at_body) == ()


def test_c3_incomplete_or_not_contiguous_must_fail() -> None:
    t = datetime(2026, 1, 15, 1, tzinfo=NY)
    c2 = candle(t, "100", "105", "95", "98")
    c3_incomplete = candle(t + timedelta(hours=4), "97", "104", "96", "103", 3)
    with pytest.raises(ValueError, match="must be complete"):
        c3_body_closure(c2, c3_incomplete)
    c3_wrong = candle(t + timedelta(hours=5), "97", "104", "96", "103")
    with pytest.raises(ValueError, match="exactly"):
        c3_body_closure(c2, c3_wrong)


def test_c2_reversal_closure_separate_vs_not_swept() -> None:
    t = datetime(2026, 1, 15, 1, tzinfo=NY)
    c1 = candle(t, "100", "105", "95", "101")
    c2_swept_inside = candle(t + timedelta(hours=4), "100", "106", "96", "102")
    c2_no_sweep = candle(t + timedelta(hours=4), "100", "103", "96", "102")
    c2_both = candle(t + timedelta(hours=4), "100", "106", "94", "102")
    assert c2_reversal_closure(c1, c2_swept_inside) is True
    assert c2_reversal_closure(c1, c2_no_sweep) is False
    assert c2_reversal_closure(c1, c2_both) is False


def test_c4_eq_observed_only_at_first_closed_m15() -> None:
    t = datetime(2026, 1, 15, 1, tzinfo=NY)
    c3 = candle(t, "100", "110", "90", "105")
    unknown = first_c4_eq_observation(
        c3=c3, c4_first=None, side=DemoTradingSetupSide.LONG,
    )
    assert unknown["first_15m_eq_half_respected"] is None
    assert unknown["c4_first_15m_closed_at"] is None
    first = Vt08B01Bar(
        opened_at=c3.closed_at,
        closed_at=c3.closed_at + timedelta(minutes=15),
        open=Decimal("105"),
        high=Decimal("107"),
        low=Decimal("102"),
        close=Decimal("106"),
    )
    measured = first_c4_eq_observation(
        c3=c3, c4_first=first, side=DemoTradingSetupSide.LONG,
    )
    assert measured["eq_level"] == "100"
    assert measured["first_15m_eq_half_respected"] is True
    assert measured["first_15m_wick_reentered_c3_half"] is True
    assert measured["c4_first_15m_closed_at"] > c3.closed_at.isoformat()


def test_c4_eq_reject_earlier_or_not_closed_future() -> None:
    t = datetime(2026, 1, 15, 1, tzinfo=NY)
    c3 = candle(t, "100", "110", "90", "105")
    wrong = Vt08B01Bar(
        opened_at=c3.closed_at - timedelta(minutes=15),
        closed_at=c3.closed_at,
        open=Decimal("105"),
        high=Decimal("107"),
        low=Decimal("101"),
        close=Decimal("106"),
    )
    with pytest.raises(ValueError, match="after completed"):
        first_c4_eq_observation(
            c3=c3, c4_first=wrong, side=DemoTradingSetupSide.LONG,
        )
