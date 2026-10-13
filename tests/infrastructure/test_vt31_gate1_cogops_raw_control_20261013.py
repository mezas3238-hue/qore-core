"""Gate1 source-control adversarial tests; never economic fills."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scripts.vt31_gate1_cogops_vs_raw_first_fvg_20261013 import (
    blocks,
    gross,
    key_for,
    raw_first_for_complete_hour,
)


BASE = datetime(2025, 7, 1, 14, tzinfo=UTC)


def bar(i: int, *, high=30002., low=29998., o=30000., c=30000.):
    t = BASE + timedelta(minutes=i)
    return {
        "opened_at": t.isoformat(),
        "closed_at": (t + timedelta(minutes=1)).isoformat(),
        "open": str(o), "high": str(high), "low": str(low),
        "close": str(c),
    }


def test_raw_first_is_only_first_contiguous_fvg_same_hour() -> None:
    bars = [bar(i) for i in range(60)]
    bars[2] = bar(2, low=30003., high=30006., o=30004., c=30004.)
    bars[5] = bar(5, low=30007., high=30010., o=30008., c=30008.)
    key = ("2025-07-01", "VT31_NY_AM")
    e = raw_first_for_complete_hour(bars, key)
    assert e is not None
    assert e["formed"] == BASE + timedelta(minutes=3)
    assert e["side_sign"] == 1
    assert e["session"] == "VT31_NY_AM"


def test_raw_strict_gap_equality_is_not_FVG() -> None:
    bars = [bar(i) for i in range(60)]
    bars[2] = bar(2, low=30002., high=30005., o=30003., c=30003.)
    assert raw_first_for_complete_hour(
        bars, ("2025-07-01", "VT31_NY_AM")
    ) is None


def test_never_count_c3_closed_at_end_of_window_as_entry_source() -> None:
    bars = [bar(i) for i in range(60)]
    bars[59] = bar(59, low=30003., high=30007., o=30005., c=30005.)
    assert raw_first_for_complete_hour(
        bars, ("2025-07-01", "VT31_NY_AM")
    ) is None


def test_causality_gaps_in_hour_rejected() -> None:
    bars = [bar(i) for i in range(60)]
    bars[4] = bar(8)
    with pytest.raises(ValueError, match="contiguous"):
        raw_first_for_complete_hour(
            bars, ("2025-07-01", "VT31_NY_AM")
        )


def test_wrong_length_window_rejected() -> None:
    with pytest.raises(ValueError, match="fully observed"):
        raw_first_for_complete_hour(
            [bar(i) for i in range(59)],
            ("2025-07-01", "VT31_NY_AM"),
        )


def test_NY_DST_and_non_window_denominator() -> None:
    assert key_for(datetime(2025, 7, 1, 14, 5, tzinfo=UTC)) == (
        "2025-07-01", "VT31_NY_AM"
    )
    assert key_for(datetime(2025, 1, 2, 15, 5, tzinfo=UTC)) == (
        "2025-01-02", "VT31_NY_AM"
    )
    assert key_for(datetime(2025, 1, 2, 14, 5, tzinfo=UTC)) is None


def test_signed_open_to_open_requires_16_contiguous_M1() -> None:
    x = {"formed": BASE, "side_sign": -1}
    opens = {BASE+timedelta(minutes=i): 30000.+i for i in range(16)}
    assert gross(x, opens) == -15.
    del opens[BASE+timedelta(minutes=9)]
    assert gross(x, opens) is None


def test_2000_weekly_block_bootstrap_identical_observations() -> None:
    s = blocks([("2025-W10", 2.), ("2025-W11", 2.)])
    assert s["mean"] == 2.
    assert s["week_boot_ci95"] == [2., 2.]
    assert s["already_used_development_NOT_confirmation"] is True
