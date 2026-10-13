"""Adversarial source, time and double-counting controls for descriptive 3Y subgroups."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scripts.vt31_ce_touch_subgroup_decision_20261013 import (
    collect_opens,
    events_from_original,
    needed_opens,
    signed_return,
    stamp,
    summarize,
)


def test_15m_next_open_arithmetic_does_not_use_ce_midpoint() -> None:
    start = datetime(2025, 1, 6, 15, 0, tzinfo=UTC)
    e = {"formed": start, "touch": start + timedelta(minutes=4), "side": 1}
    prices = {start + timedelta(minutes=i): 30000 + i for i in range(20)}
    assert signed_return(e, e["formed"], prices) == 15
    assert signed_return(e, e["touch"], prices) == 15
    prices[start + timedelta(minutes=4)] = 29950
    assert signed_return(e, e["formed"], prices) == 15
    assert signed_return(e, e["touch"], prices) == 69


def test_missing_contiguous_m1_must_not_fill_price_or_count_trade() -> None:
    start = datetime(2025, 1, 6, 15, 0, tzinfo=UTC)
    e = {"formed": start, "touch": None, "side": -1}
    prices = {start + timedelta(minutes=i): 30100 - i for i in range(16)}
    assert signed_return(e, start, prices) == 15
    del prices[start + timedelta(minutes=7)]
    assert signed_return(e, start, prices) is None
    assert signed_return(e, None, prices) is None


def test_only_strict_original_2140_event_ledger_admitted() -> None:
    with pytest.raises(ValueError, match="ledger identity"):
        events_from_original({
            "source_fvg_hypothesis_count": 2139,
            "market_m1_count": 1059784,
            "trader_id": "VT31",
            "paper_fills_proven": 0, "live_fills_proven": 0,
        })


def test_double_count_original_first_touch_and_posthoc_future_window() -> None:
    start = datetime(2025, 1, 6, 15, 0, tzinfo=UTC)
    data = [
        {"formed": start, "touch": start + timedelta(minutes=12)},
        {"formed": start, "touch": None},
    ]
    needed = needed_opens(data)
    assert start + timedelta(minutes=27) in needed
    assert start + timedelta(minutes=15) in needed
    assert len(needed) == 28
    # Touch is a later observed M1, never known at FVG formation.
    assert data[0]["touch"] > data[0]["formed"]


def test_market_rejects_gaps_in_order_or_bad_ohlc_duration() -> None:
    start = datetime(2025, 1, 6, 15, 0, tzinfo=UTC)
    def bar(minute: int, duration: int = 1) -> dict[str, str]:
        o = start + timedelta(minutes=minute)
        return {
            "opened_at": o.isoformat(),
            "closed_at": (o + timedelta(minutes=duration)).isoformat(),
            "open": "30000", "high": "30001", "low": "29999", "close": "30000",
        }
    with pytest.raises(ValueError, match="M1 count drift"):
        collect_opens([bar(0)], {start}, expected_n=2)
    with pytest.raises(ValueError, match="out-of-order"):
        collect_opens([bar(0), bar(0)], {start}, expected_n=2)
    with pytest.raises(ValueError, match="not M1"):
        collect_opens([bar(0, 2)], {start}, expected_n=1)


def test_invalid_timestamps_and_positive_cluster_non_profit() -> None:
    with pytest.raises(ValueError, match="timezone-less"):
        stamp("2025-10-01T00:00:00")
    s = summarize([{"pts": 10., "week": "2024-W01"}], 1)
    assert s["mean_gross_pts"] == 10
    assert s["weekly_boot_ci95"] == [10.0, 10.0]
    assert s["posthoc_subgroup_not_confirmatory"] is True
    assert s["not_independent_holdout"] is True
