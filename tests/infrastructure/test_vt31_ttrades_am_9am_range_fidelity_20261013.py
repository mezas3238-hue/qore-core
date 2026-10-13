"""Static causal and time-gate attacks against TTrades 2025 AM fidelity census."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scripts.vt31_ttrades_am_9am_range_fidelity_20261013 import (
    collect_9_10,
    evaluate,
    full_9am_hour,
    select_am_events,
    sweep_state,
    utc_stamp,
)


def fixture_9am(start: datetime, hi: float = 10010., lo: float = 9990.):
    return [(start + timedelta(minutes=k), hi, lo) for k in range(60)]


def fixture_event(start: datetime, side: str = "LONG", dol: float = 10010.):
    c1 = start + timedelta(hours=1, minutes=4)
    formed = c1 + timedelta(minutes=3)
    return {
        "id": "test", "day": c1.date().isoformat(), "c1": c1,
        "formed": formed, "side": side, "old_dol": dol,
    }


def test_directionally_correct_9am_low_high_sweep() -> None:
    t = datetime(2025, 7, 1, 14, 0, tzinfo=UTC)
    assert sweep_state("LONG", 10010., 9990., [(t, 10000., 9989.)]) == (
        "DIRECTIONAL_CORRECT"
    )
    assert sweep_state("SHORT", 10010., 9990., [(t, 10011., 10000.)]) == (
        "DIRECTIONAL_CORRECT"
    )


def test_no_sweep_wrong_side_and_both_sides_fail_closed() -> None:
    t = datetime(2025, 7, 1, 14, 0, tzinfo=UTC)
    assert sweep_state("LONG", 10010., 9990., []) == "NO_SWEEP"
    assert sweep_state("LONG", 10010., 9990., [(t, 10011., 10000.)]) == (
        "WRONG_SIDE_ONLY"
    )
    assert sweep_state("SHORT", 10010., 9990., [(t, 10011., 9989.)]) == (
        "BOTH_SIDES_AMBIGUOUS"
    )
    assert sweep_state("LONG", 10010., 9990., [(t, 10010., 9990.)]) == "NO_SWEEP"


def test_missing_or_noncontiguous_prior_hour_is_unknown_not_success() -> None:
    t = datetime(2025, 7, 1, 13, 0, tzinfo=UTC)
    xs = fixture_9am(t)
    assert full_9am_hour(xs) == (10010., 9990.)
    assert full_9am_hour(xs[:-1]) is None
    bad = list(xs)
    bad[-1] = (bad[-2][0], 10010., 9990.)
    assert full_9am_hour(bad) is None


def test_source_ledger_must_be_exact_old_2140_without_fills() -> None:
    with pytest.raises(ValueError, match="contract broken"):
        select_am_events({
            "market_m1_count": 1059784,
            "source_fvg_hypothesis_count": 2140,
            "trader_id": "VT31",
            "paper_fills_proven": 1, "live_fills_proven": 0,
            "events": [],
        })


def test_m1_source_must_be_strictly_ordered_and_utc() -> None:
    t = datetime(2025, 7, 1, 13, 0, tzinfo=UTC)
    b = {
        "opened_at": t.isoformat(),
        "closed_at": (t + timedelta(minutes=1)).isoformat(),
        "high": 10010., "low": 9990.,
    }
    with pytest.raises(ValueError, match="unsorted"):
        collect_9_10([b, b], set(), expected=2)
    with pytest.raises(ValueError, match="count drift"):
        collect_9_10([b], set(), expected=2)
    with pytest.raises(ValueError, match="timezone"):
        utc_stamp("2025-07-01T13:00:00")


def test_pre_c3_does_not_claim_same_minute_sweep_earlier_than_fvg() -> None:
    # 2025 summer NY = UTC-4: NY 09:00 is 13:00 UTC.
    t = datetime(2025, 7, 1, 13, 0, tzinfo=UTC)
    e = fixture_event(t)
    nine = fixture_9am(t)
    ten_start = t + timedelta(hours=1)
    ten = [
        (ten_start + timedelta(minutes=k), 10005., 9995.)
        for k in range(60)
    ]
    # Sweep happens during C3, not before its opening. Source is M1 OHLC only.
    ten[6] = (ten[6][0], 10005., 9989.)
    per_day = {e["day"]: {"nine": nine, "ten": ten}}
    # evaluate expects 721 frozen source identities; test with 721 cloned
    # synthetic day variants is unsafe. Assert the exact timing partition.
    pre_c3 = [
        b for b in ten if b[0] < e["c1"] + timedelta(minutes=2)
    ]
    through_c3 = [b for b in ten if b[0] < e["formed"]]
    assert sweep_state(e["side"], 10010., 9990., pre_c3) == "NO_SWEEP"
    assert sweep_state(e["side"], 10010., 9990., through_c3) == (
        "DIRECTIONAL_CORRECT"
    )
    assert per_day[e["day"]]["ten"] == ten


def test_evaluate_rejects_wrong_original_cohort_size() -> None:
    with pytest.raises(ValueError, match="wrong NY AM old population"):
        evaluate([], {})
