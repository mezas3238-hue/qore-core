"""Fail-closed read-only topology tests, independent of trading or PnL."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar
from scripts.vt31_m2_gap_topology_20261014 import (
    missing_intervals,
    span_label,
)


def bar(t: datetime) -> M1Bar:
    return M1Bar(
        t, t + timedelta(minutes=1),
        Decimal("100"), Decimal("102"), Decimal("98"), Decimal("100"),
    )


def bars(t: datetime, n: int) -> tuple[M1Bar, ...]:
    return tuple(bar(t + timedelta(minutes=i)) for i in range(n))


def at(y: int, m: int, d: int, hour: int, minute: int = 0) -> datetime:
    return datetime(y, m, d, hour, minute, tzinfo=UTC)


def test_complete_post_confirmation_interval_no_unknown_gap():
    a = at(2025, 7, 1, 7)
    sample = bars(a, 200)
    assert missing_intervals(sample, a, a + timedelta(minutes=200)) == ()


def test_middle_one_minute_not_filled_by_neighbor_bars():
    a = at(2025, 7, 1, 7)
    sample = bars(a, 5)
    missing = sample[:2] + sample[3:]
    assert missing_intervals(missing, a, a + timedelta(minutes=5)) == (
        (a + timedelta(minutes=2), a + timedelta(minutes=3)),
    )


def test_adjacent_missing_minutes_compress_to_one_maximal_gap():
    a = at(2025, 7, 1, 7)
    sample = bars(a, 8)
    gaps = missing_intervals(
        sample[:2] + sample[5:],
        a, a + timedelta(minutes=8),
    )
    assert gaps == ((a+timedelta(minutes=2), a+timedelta(minutes=5)),)
    assert span_label(*gaps[0])["missing_m1_count"] == 3


def test_trailing_and_leading_absences_are_explicit_unknown():
    a = at(2025, 7, 1, 7)
    sample = bars(a+timedelta(minutes=2), 2)
    gaps = missing_intervals(sample, a, a+timedelta(minutes=8))
    assert gaps == (
        (a, a+timedelta(minutes=2)),
        (a+timedelta(minutes=4), a+timedelta(minutes=8)),
    )


def test_ny_weekend_label_is_only_topology_not_broker_closed():
    a, z = at(2025, 7, 4, 20), at(2025, 7, 7, 14)
    p = span_label(a, z)
    assert p["topology"] == "INTERSECTS_NY_WEEKEND"
    assert p["missing_m1_count"] == int((z-a)/timedelta(minutes=1))
    assert p["broker_closed_verified"] is False
    assert p["source_pool_available_verified"] is False


def test_2024_cash_holiday_flag_does_not_homologate_cfd():
    a, z = at(2024, 1, 12, 22), at(2024, 1, 16, 14)
    p = span_label(a, z)
    assert p["intersects_nasdaq_cash_holiday_reference_only"] is True
    assert p["broker_closed_verified"] is False
    assert p["topology"] == "INTERSECTS_NY_WEEKEND"


def test_cross_midnight_without_weekend_not_market_closed_proof():
    a, z = at(2025, 7, 2, 3), at(2025, 7, 2, 9)
    p = span_label(a, z)
    assert p["topology"] == "CROSSES_NY_DATE_NO_WEEKEND"
    assert p["broker_closed_verified"] is False


def test_intraday_gap_not_market_closed_proof():
    a, z = at(2025, 7, 1, 14), at(2025, 7, 1, 14, 5)
    p = span_label(a, z)
    assert p["topology"] == "WITHIN_ONE_NY_DATE"
    assert p["broker_closed_verified"] is False


def test_duplicate_and_unsorted_source_m1_fails_closed():
    a = at(2025, 7, 1, 7)
    orig = bars(a, 5)
    with pytest.raises(ValueError, match="DUPLICATE_OR_UNSORTED"):
        missing_intervals(orig + (orig[-1],), a, a+timedelta(minutes=5))
    with pytest.raises(ValueError, match="DUPLICATE_OR_UNSORTED"):
        missing_intervals((orig[1], orig[0]) + orig[2:], a, a+timedelta(minutes=5))


def test_bars_at_and_after_asof_do_not_enter_causal_interval():
    a = at(2025, 7, 1, 7)
    # The auditor is intentionally prefix-scoped even when the caller has
    # a larger immutable source array; no future bar can cure a past gap.
    series = bars(a, 5)
    assert missing_intervals(series, a, a+timedelta(minutes=4)) == ()
    removed = series[:2] + series[3:]
    assert missing_intervals(
        removed, a, a+timedelta(minutes=4)
    ) == ((a+timedelta(minutes=2), a+timedelta(minutes=3)),)


def test_unaligned_and_inverted_asof_rejected():
    a = at(2025, 7, 1, 7)
    with pytest.raises(ValueError, match="INVALID_SOURCE_OR_ASOF_MINUTE"):
        missing_intervals((), a+timedelta(seconds=5), a+timedelta(minutes=3))
    with pytest.raises(ValueError, match="INVALID_SOURCE_OR_ASOF_MINUTE"):
        missing_intervals((), a+timedelta(minutes=2), a)
