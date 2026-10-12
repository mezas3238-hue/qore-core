"""User NDX100 MT5 screenshot spread=1.60 fixed-scenario tests ONLY."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar, Side
from qore.infrastructure.traders.vt31_ict_cleanroom.fixed_spread_quote_scenario import (
    FIXED_SPREAD,
    HALF_SPREAD,
    SCREENSHOT_ASK,
    SCREENSHOT_BID,
    SyntheticM1QuoteBounds,
    screenshot_quote_crosses,
)


def test_exact_user_screenshot_bid_ask_spread_is_1p60() -> None:
    assert SCREENSHOT_BID == Decimal("30853.00")
    assert SCREENSHOT_ASK == Decimal("30854.60")
    assert FIXED_SPREAD == Decimal("1.60")
    assert HALF_SPREAD == Decimal("0.80")


def test_buy_limit_uses_actual_snapshot_ask_not_bid() -> None:
    assert not screenshot_quote_crosses(
        side=Side.LONG, ce_limit=Decimal("30854.00")
    )
    assert screenshot_quote_crosses(
        side=Side.LONG, ce_limit=Decimal("30854.60")
    )


def test_sell_limit_uses_actual_snapshot_bid_not_ask() -> None:
    assert not screenshot_quote_crosses(
        side=Side.SHORT, ce_limit=Decimal("30853.50")
    )
    assert screenshot_quote_crosses(
        side=Side.SHORT, ce_limit=Decimal("30853.00")
    )


def test_synthetic_m1_assumes_mid_and_1p60_total_spread_only() -> None:
    at = datetime(2026, 10, 12, 14, tzinfo=UTC)
    bar = M1Bar(
        opened_at=at, closed_at=at + timedelta(minutes=1),
        open=Decimal("105"), high=Decimal("110"),
        low=Decimal("100"), close=Decimal("107"),
    )
    q = SyntheticM1QuoteBounds.from_mid_m1(bar)
    assert q.spread == Decimal("1.60")
    assert q.bid_low == Decimal("99.20")
    assert q.bid_high == Decimal("109.20")
    assert q.ask_low == Decimal("100.80")
    assert q.ask_high == Decimal("110.80")


def test_m1_long_quote_side_threshold_is_ask_low() -> None:
    at = datetime(2026, 10, 12, 14, tzinfo=UTC)
    q = SyntheticM1QuoteBounds.from_mid_m1(M1Bar(
        at, at + timedelta(minutes=1),
        Decimal("105"), Decimal("110"), Decimal("100"), Decimal("107"),
    ))
    assert not q.eligible_quote_side_reachable(Side.LONG, Decimal("100.00"))
    assert q.eligible_quote_side_reachable(Side.LONG, Decimal("100.80"))


def test_m1_short_quote_side_threshold_is_bid_high() -> None:
    at = datetime(2026, 10, 12, 14, tzinfo=UTC)
    q = SyntheticM1QuoteBounds.from_mid_m1(M1Bar(
        at, at + timedelta(minutes=1),
        Decimal("105"), Decimal("110"), Decimal("100"), Decimal("107"),
    ))
    assert not q.eligible_quote_side_reachable(Side.SHORT, Decimal("109.50"))
    assert q.eligible_quote_side_reachable(Side.SHORT, Decimal("109.20"))
