"""Adversarial null control: causal pivot timestamps and overlap partitions."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scripts import vt31_ob_breaker_negative_control_20261013 as subject
from scripts.vt31_ttrades_am_all_entry_sources_20261013 import FAMILIES
from scripts.vt31_ttrades_am_source_20261013 import Bar

T = datetime(2025, 7, 1, 14, tzinfo=UTC)


def candle(i: int, hi=30010., lo=29990.) -> Bar:
    return Bar(T+timedelta(minutes=i), 30000., hi, lo, 30000.)


def test_causal_generic_local_low_uses_confirmed_right_bar_only() -> None:
    candles = [candle(0), candle(1, lo=29985.), candle(2)]
    assert subject._confirmed_three_bar_pivot(candles, 1, "LONG") is False
    assert subject._confirmed_three_bar_pivot(candles, 2, "LONG") is True
    assert subject._confirmed_three_bar_pivot(candles, 2, "SHORT") is False


def test_causal_generic_local_high_for_short() -> None:
    c = [candle(0), candle(1, hi=30020.), candle(2)]
    assert subject._confirmed_three_bar_pivot(c, 2, "SHORT")
    assert not subject._confirmed_three_bar_pivot(c, 2, "LONG")


def test_no_ties_no_nonconsecutive_pivot() -> None:
    x = [candle(0), candle(1), candle(2)]
    assert not subject._confirmed_three_bar_pivot(x, 2, "LONG")
    x[1] = candle(4, lo=29980.)
    assert not subject._confirmed_three_bar_pivot(x, 2, "LONG")


def test_invalid_side_and_early_pivot_fail_closed() -> None:
    with pytest.raises(ValueError, match="invalid control"):
        subject._confirmed_three_bar_pivot(
            [candle(0), candle(1), candle(2)], 2, "UP"
        )
    assert not subject._confirmed_three_bar_pivot([candle(0)], 0, "LONG")


def test_generic_extreme_emitted_at_right_close_not_center(monkeypatch) -> None:
    def fake_context(nine, ten):
        del nine, ten
        return "CONTEXT_CONFIRMED", {"disp_i": 1, "side": "LONG"}

    monkeypatch.setattr(subject, "context", fake_context)
    ten = [candle(i) for i in range(60)]
    ten[3] = candle(3, lo=29980.)
    output = subject.generic_extreme(
        "2025-07-01", {9: [], 10: ten, 11: []}
    )
    assert output is not None
    assert output["confirmed_at"] == (T+timedelta(minutes=5)).isoformat()
    assert output["pivot_center_time_NOT_SIGNAL"] == (
        T+timedelta(minutes=3)
    ).isoformat()
    assert output["confirmed_at"] != output["pivot_center_time_NOT_SIGNAL"]


def test_no_context_or_no_pivot_is_missing_not_zero(monkeypatch) -> None:
    monkeypatch.setattr(subject, "context", lambda *_: ("NO_SWEEP", None))
    assert subject.generic_extreme("2025-07-01", {9: [], 10: []}) is None


def test_overlap_all_patterns_are_complete_and_not_trades() -> None:
    days = {"2025-07-01", "2025-07-02", "2025-07-03"}
    src = {
        FAMILIES[0]: {"2025-07-01": {}, "2025-07-02": {}},
        FAMILIES[1]: {"2025-07-02": {}},
        FAMILIES[2]: {"2025-07-02": {}},
        FAMILIES[3]: {"2025-07-01": {}},
    }
    z = subject.overlap_census(src, days)
    assert z["union_days"] == 2
    assert z["patterns_all_16"]["0000"] == 1
    assert z["patterns_all_16"]["1011"] == 0
    assert z["patterns_all_16"]["1100"] == 0
    assert z["patterns_all_16"]["1110"] == 1
    assert z["patterns_all_16"]["1001"] == 1
    assert z["pairwise_shared_days"][FAMILIES[2]][FAMILIES[1]] == 1
    assert z["ob_without_fvg_or_direct"] == 0
    assert z["breaker_without_any_other_family"] == 0
    assert sum(z["patterns_all_16"].values()) == 3


def test_overlap_wrong_family_or_unknown_day_refused() -> None:
    d = {"x"}
    with pytest.raises(ValueError, match="unknown source family"):
        subject.overlap_census({FAMILIES[0]: {}}, d)
    x = {key: {} for key in FAMILIES}
    x[FAMILIES[1]] = {"invalid-day": {}}
    with pytest.raises(ValueError, match="outside day universe"):
        subject.overlap_census(x, d)


def test_common_clock_lag_is_milliseconds_aware() -> None:
    assert subject.time_gap(
        "2025-07-01T14:10:00+00:00",
        "2025-07-01T14:02:00+00:00",
    ) == 8
    assert subject.describe_minutes([1, 2, 6])["median"] == 2


def test_empty_control_return_not_fabricated() -> None:
    assert subject.describe_minutes([])["mean"] is None
    assert subject.describe_minutes([])["n"] == 0
