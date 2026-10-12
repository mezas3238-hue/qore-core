"""No-network forensic tests: bid=ask stale vs same-millisecond source chronology."""
from __future__ import annotations

from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_zero_spread_same_ms_forensics_v1 as q


def test_disjoint_age_bin_boundaries_frozen():
    samples = ((0, "same_millisecond"), (1, "lag_1_100ms"),
               (100, "lag_1_100ms"), (101, "lag_101_500ms"),
               (500, "lag_101_500ms"), (501, "lag_501_1000ms"),
               (1000, "lag_501_1000ms"), (1001, "lag_1001_5000ms"),
               (5000, "lag_1001_5000ms"))
    assert all(q.classify_zero_age(n) == label for n, label in samples)
    for age in (-1, 5001, True):
        with pytest.raises(ValueError, match="ZERO_AGE"):
            q.classify_zero_age(age)


def test_same_millisecond_zero_is_distinct_from_old_side_zero():
    bids = [(0, 100000), (200, 100005), (800, 100000)]
    asks = [(0, 100000), (300, 100005), (800, 100000)]
    report = q.analyze_market(bids, asks)
    assert report["zero_total"] == 3
    assert report["zero_age_bins"]["same_millisecond"] == 2
    assert report["zero_age_bins"]["lag_1_100ms"] == 1
    assert report["zero_age_threshold_cumulative"]["0"] == 2
    assert report["zero_age_threshold_cumulative"]["100"] == 3
    assert report["crossed"] == 1
    assert report["source_only_not_executable_spread"] is True


def test_absence_of_any_side_rejected():
    with pytest.raises(ValueError, match="BOTH_SIDES_REQUIRED"):
        q.analyze_market([], [(10, 300000)])


def test_stale_side_not_assigned_free_spread():
    report = q.analyze_market(
        [(0, 100000)],
        [(1000, 100000), (10000, 100000)],
    )
    assert report["missing"] == 1
    assert report["zero_total"] == 1
    assert report["stale"] == 1


def test_missing_raw_original_sha_register_blocks_any_forensic(tmp_path: Path):
    with pytest.raises(ValueError, match="SOURCE_SHA_REGISTER_MISSING"):
        q.inspect_source(tmp_path)


def test_no_confused_source_pnl_or_cibo_return():
    assert q.IDENTITY.endswith("V1")
    assert q.origin.ORIGINAL_RUN == 38283737706
    assert q.THRESHOLDS_MS == (0, 100, 500, 1000, 5000)
