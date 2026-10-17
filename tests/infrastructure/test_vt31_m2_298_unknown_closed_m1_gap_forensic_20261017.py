"""Adversarial independent M2 observed-M1 interval-gap tribunal, no G3 mutation."""
from __future__ import annotations

from array import array
from datetime import UTC, datetime, timedelta

import pytest

from scripts.vt31_m2_298_unknown_closed_m1_gap_forensic_20261017 import (
    gap_witness,
    minute,
    source_minutes,
)


def rows(minutes: list[int], *, base: datetime) -> list[dict[str, str]]:
    return [
        {
            "opened_at": (base + timedelta(minutes=n)).isoformat(),
            "closed_at": (base + timedelta(minutes=n + 1)).isoformat(),
        }
        for n in minutes
    ]


@pytest.mark.parametrize("month,offset", [(1, -5), (7, -4)])
def test_utc_m1_dst_source_same_absolute_causal_clock(month, offset):
    ny = __import__("zoneinfo").ZoneInfo("America/New_York")
    source_local = datetime(2025, month, 15, 3, tzinfo=ny)
    assert int(source_local.utcoffset().total_seconds() // 3600) == offset
    start = source_local.astimezone(UTC)
    stamps = source_minutes(rows(list(range(60)), base=start), expected_m1=60)
    assert len(stamps) == 60
    witness = gap_witness(
        stamps, start=minute(start), end=minute(start + timedelta(minutes=60)),
    )
    assert witness["complete_closed_M1_between_source_and_asof"]
    assert witness["observed_closed_M1_slots"] == 60
    assert witness["missing_M1_slots"] == 0


def test_one_missing_middle_closed_m1_forces_unknown_no_interpolation():
    base = datetime(2025, 7, 15, 7, tzinfo=UTC)
    stamps = source_minutes(
        rows([n for n in range(60) if n != 33], base=base),
        expected_m1=59,
    )
    w = gap_witness(
        stamps, start=minute(base), end=minute(base + timedelta(minutes=60)),
    )
    assert w["observed_closed_M1_slots"] == 59
    assert w["missing_M1_slots"] == 1
    assert w["gap_runs_count"] == 1
    assert w["longest_consecutive_missing_M1"] == 1
    assert w["first_missing_opened_utc"] == (
        base + timedelta(minutes=33)
    ).isoformat()
    assert not w["broker_market_closed_proven"]


def test_source_gap_at_first_last_and_multiple_disjoint_runs():
    base = datetime(2025, 1, 15, 8, tzinfo=UTC)
    stamps = source_minutes(
        rows([2, 3, 7], base=base), expected_m1=3,
    )
    w = gap_witness(
        stamps, start=minute(base), end=minute(base + timedelta(minutes=10)),
    )
    assert w["expected_closed_M1_slots"] == 10
    assert w["observed_closed_M1_slots"] == 3
    assert w["missing_M1_slots"] == 7
    assert w["gap_runs_count"] == 3
    assert w["longest_consecutive_missing_M1"] == 3
    assert w["first_missing_opened_utc"] == base.isoformat()


@pytest.mark.parametrize("bad_minutes", [[0, 0], [1, 0]])
def test_duplicate_or_unsorted_source_aborts(bad_minutes):
    base = datetime(2025, 7, 15, 7, tzinfo=UTC)
    with pytest.raises(ValueError, match="DUPLICATE_OR_UNCLOSED"):
        source_minutes(rows(bad_minutes, base=base), expected_m1=2)


def test_broken_bar_duration_and_original_count_failclosed():
    base = datetime(2025, 7, 15, 7, tzinfo=UTC)
    r = rows([0], base=base)
    r[0]["closed_at"] = (base + timedelta(minutes=2)).isoformat()
    with pytest.raises(ValueError, match="DUPLICATE_OR_UNCLOSED"):
        source_minutes(r, expected_m1=1)
    with pytest.raises(AssertionError, match="COUNT_DRIFT"):
        source_minutes(rows([0], base=base), expected_m1=2)


def test_no_future_or_zero_elapsed_source_pool_accepted():
    points = array("q", [10, 11, 12])
    with pytest.raises(ValueError, match="MUST_PREDATE"):
        gap_witness(points, start=12, end=12)
    with pytest.raises(ValueError, match="MUST_PREDATE"):
        gap_witness(points, start=15, end=12)


def test_overnight_source_gap_does_not_assume_broker_closed():
    points = array("q", [0, 1, 10, 11])
    w = gap_witness(points, start=0, end=12)
    assert w["missing_M1_slots"] == 8
    assert w["longest_consecutive_missing_M1"] == 8
    assert w["gap_runs_count"] == 1
    assert not w["broker_market_closed_proven"]


def test_naive_and_second_offset_source_are_invalid():
    with pytest.raises(ValueError, match="NAIVE"):
        minute(datetime(2025, 7, 15, 7))
    with pytest.raises(ValueError, match="NOT_ALIGNED"):
        minute(datetime(2025, 7, 15, 7, 0, 1, tzinfo=UTC))


def test_minute_timezone_aware_iso_and_numeric_utc_same():
    at = datetime(2025, 7, 15, 7, tzinfo=UTC)
    assert minute(at.isoformat()) == minute(at)
    assert minute(at) == int(at.timestamp() // 60)


def test_history_data_from_after_asof_not_read_by_bisect_witness():
    points = array("q", [100, 101, 102, 200, 201])
    w = gap_witness(points, start=100, end=103)
    assert w["observed_closed_M1_slots"] == 3
    assert w["missing_M1_slots"] == 0


def test_sparse_history_outside_source_interval_not_counted():
    points = array("q", [50, 51, 100, 102, 104, 200])
    w = gap_witness(points, start=100, end=105)
    assert w["observed_closed_M1_slots"] == 3
    assert w["missing_M1_slots"] == 2
    assert w["gap_runs_count"] == 2
