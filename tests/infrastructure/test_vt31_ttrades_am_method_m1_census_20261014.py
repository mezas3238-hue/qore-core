"""Census sampling must preserve chronology and mutually exclusive days."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    adjudicate_day,
    collect_hours,
    complete_hour,
    run_census,
)

NY = ZoneInfo("America/New_York")


def blocks():
    start = datetime(2025, 7, 1, 9, tzinfo=NY).astimezone(UTC)
    bars = tuple(
        M1Bar(
            start + timedelta(minutes=i),
            start + timedelta(minutes=i + 1),
            Decimal("100"), Decimal("102"), Decimal("98"), Decimal("101"),
        )
        for i in range(120)
    )
    return bars[:60], bars[60:]


def test_no_raid_120_closed_m1_is_no_sweep_no_decision():
    nine, ten = blocks()
    result = adjudicate_day(nine, ten)
    assert result["classification"] == "NO_SWEEP"
    assert result["has_source_cognitive_proposal"] is False
    assert result["method_certified"] is False
    assert result["execution_authorized"] is False
    assert result["as_of"] == ten[-1].closed_at.isoformat()


def test_census_day_count_is_partition_and_incomplete_visible():
    nine, ten = blocks()
    sample = {
        "2025-07-01": {9: nine, 10: ten},
        "2025-07-02": {9: nine[:20], 10: ten[:20]},
    }
    report = run_census(sample)
    assert report["observed_days_total"] == 2
    assert report["state_counts"] == {
        "INCOMPLETE_M1_HOURS": 1,
        "NO_SWEEP": 1,
    }
    assert report["M2_M3_context_only_candidates_not_trades"] == 0
    assert report["trader_certified"] is False
    assert report["economic_PF_drawdown_sharpe"] is None
    assert all(
        row["method_certified"] is False
        for row in report["source_classifications"]
    )


def test_complete_hour_rejects_wrong_clock_or_holes():
    nine, ten = blocks()
    assert complete_hour("2025-07-01", 9, nine)
    assert complete_hour("2025-07-01", 10, ten)
    assert not complete_hour("2025-07-01", 9, nine[1:])
    assert not complete_hour("2025-07-02", 9, nine)


def rows_from_bars(bars):
    for b in bars:
        yield {
            "opened_at": b.opened_at.isoformat(),
            "closed_at": b.closed_at.isoformat(),
            "open": str(b.open),
            "high": str(b.high),
            "low": str(b.low),
            "close": str(b.close),
        }


def test_ingest_120_source_bars_checks_count_and_not_invent_missing():
    nine, ten = blocks()
    groups, count = collect_hours(rows_from_bars(nine + ten), expected_m1=120)
    assert count == 120
    assert len(groups["2025-07-01"][9]) == 60
    assert len(groups["2025-07-01"][10]) == 60
    with pytest.raises(ValueError, match="M1_EXPECTED_121"):
        collect_hours(rows_from_bars(nine + ten), expected_m1=121)


def test_ingest_rejects_duplicate_and_unsorted_candle():
    nine, ten = blocks()
    bars = nine + ten
    with pytest.raises(ValueError, match="SOURCE_M1_DUPLICATE_OR_OUT_OF_ORDER"):
        collect_hours(
            rows_from_bars(bars[:10] + (bars[9],) + bars[10:]),
            expected_m1=121,
        )
    with pytest.raises(ValueError, match="SOURCE_M1_DUPLICATE_OR_OUT_OF_ORDER"):
        collect_hours(
            rows_from_bars((bars[1], bars[0]) + bars[2:]),
            expected_m1=120,
        )
