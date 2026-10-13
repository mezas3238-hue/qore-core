"""PIT as-of controls against trend/vol regime leakage and p-hacking."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from scripts.vt31_gate2_pit_regimes_20261013 import (
    CELLS,
    classify_at_start,
    summarize,
)

START = datetime(2025, 7, 1, 14, tzinfo=UTC)


def hour(values: list[float]):
    return [
        (START - timedelta(minutes=60-i), value)
        for i, value in enumerate(values)
    ]


def test_four_regimes_can_be_chosen_only_before_source_start() -> None:
    assert len(CELLS) == 4
    assert set(CELLS) == {
        "HIGH_VOL_TREND", "HIGH_VOL_CHOP",
        "LOW_VOL_TREND", "LOW_VOL_CHOP",
    }
    smooth = hour([30000.+i for i in range(60)])
    high, vol, eff = classify_at_start(START, smooth, [15.]*20)
    low, _, _ = classify_at_start(START, smooth, [90.]*20)
    assert high == "HIGH_VOL_TREND"
    assert low == "LOW_VOL_TREND"
    assert vol == 59
    assert eff == 1


def test_chop_and_borderline_vol_without_lookahead() -> None:
    values = [30000. if i % 2 == 0 else 30010. for i in range(60)]
    z, vol, eff = classify_at_start(START, hour(values), [vol0 := 590.]*20)
    assert z == "LOW_VOL_CHOP"
    assert vol == vol0
    assert eff < .35


def test_prior_reference_20_is_required_fail_closed() -> None:
    x, vol, eff = classify_at_start(
        START, hour([30000.+i for i in range(60)]), [1.]*19
    )
    assert x == "UNKNOWN_WARMUP"
    assert vol == 59 and eff == 1


def test_missing_one_m1_or_future_m1_refused() -> None:
    original = hour([30000.+i for i in range(60)])
    assert classify_at_start(START, original[:-1], [30.]*20)[0] == (
        "UNKNOWN_PREWINDOW"
    )
    bad = list(original)
    bad[-1] = (START, bad[-1][1])
    assert classify_at_start(START, bad, [30.]*20)[0] == (
        "UNKNOWN_PREWINDOW"
    )


def test_flat_hour_unknown_without_unearned_trend() -> None:
    x, realized, eff = classify_at_start(
        START, hour([30000.]*60), [2.]*20
    )
    assert x == "UNKNOWN_FLAT"
    assert realized == 0
    assert eff is None


def test_bootstrap_98p75_and_95_are_deterministic_no_zero_imputation() -> None:
    a = summarize([("2025-W10", 3.), ("2025-W11", 3.)])
    b = summarize([("2025-W10", 3.), ("2025-W11", 3.)])
    assert a == b
    assert a["week_CI98p75_bonferroni"] == [3., 3.]
    assert a["week_CI95"] == [3., 3.]
    assert summarize([])["week_CI95"] is None
