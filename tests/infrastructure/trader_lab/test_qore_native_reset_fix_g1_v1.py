"""RESET G1 causal fixtures: no lookahead, DST, missing, cohorts and zero support."""
from __future__ import annotations

from collections import deque
from datetime import UTC, date, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab import qore_native_reset_fix_g1_v1 as g


def bar(d: date, minute: int, op: float, cl: float) -> g.Bar:
    opened = datetime(d.year, d.month, d.day, minute // 60, minute % 60,
                      tzinfo=g.LONDON).astimezone(UTC)
    return g.Bar(opened, op, cl)


def test_frozen_hypothesis_exact() -> None:
    assert g.SOURCE_RUN_ID == 35166210458
    assert g.SOURCE_ARTIFACT_ID == 10475354631
    assert g.SYMBOL == "EURUSD"
    assert g.LOOKBACK == 120 and g.HIGH_QUANTILE == 0.75
    assert g.MIN_PER_CELL == 50 and g.MIN_DAYS == 300
    assert g.SEED == 941102 and g.N_BOOTSTRAP == 2000
    assert g.CLOCK["FIX"] == (930, 965, 990, 970)
    assert g.CLOCK["PLACEBO"] == (810, 845, 870, 850)


def test_london_dst_open_conversion() -> None:
    winter = bar(date(2022, 1, 11), 930, 1.1, 1.2)
    summer = bar(date(2022, 7, 11), 930, 1.1, 1.2)
    assert winter.opened_utc.hour == 15
    assert summer.opened_utc.hour == 14


def test_formation_requires_five_completed_m5() -> None:
    day = date(2022, 7, 11)
    sample = {930 + i * 5: bar(day, 930 + i * 5, 1.1, 1.1 + i * 0.0001)
              for i in range(5)}
    p = g.formation(day, sample, "FIX")
    assert p == pytest.approx(10000 * __import__("math").log((1.1 + 0.0004) / 1.1))
    del sample[950]
    assert g.formation(day, sample, "FIX") is None


def test_reversal_is_opposite_pressure_and_uses_open() -> None:
    day = date(2022, 7, 11)
    sample = {m: bar(day, m, p, p + .1)
              for m, p in [(965, 1.2000), (970, 1.2005), (990, 1.1990)]}
    actual = g.reversal(day, sample, "FIX", +4.0)
    assert actual is not None and actual > 0
    delayed = g.reversal(day, sample, "FIX", +4.0, delayed=True)
    assert delayed is not None and delayed > actual
    assert g.reversal(day, sample, "FIX", 0) is None


def test_p75_linear_interpolation_and_120_causal_history() -> None:
    previous = deque([float(i) for i in range(120)], maxlen=120)
    assert g.quantile75(previous) == pytest.approx(89.25)
    previous.pop()
    with pytest.raises(ValueError, match="exactly 120"):
        g.quantile75(previous)


def test_common_cohort_formations_update_only_after_classification() -> None:
    start = date(2017, 1, 2)
    series = {}
    for i in range(125):
        day = start + timedelta(days=i)
        if day.weekday() >= 5:
            continue
        data = {}
        for arm, (forming, entry, exit_, late) in g.CLOCK.items():
            for j in range(5):
                minute = forming + 5 * j
                data[minute] = bar(day, minute, 1.1, 1.1001)
            data[entry] = bar(day, entry, 1.1000, 1.0999)
            data[late] = bar(day, late, 1.0999, 1.0998)
            data[exit_] = bar(day, exit_, 1.0998, 1.0999)
        series[day] = data
    events, info = g.build_events(series)
    assert info["nominal_weekdays"] > 125
    assert info["reasons"]["INSUFFICIENT_HISTORY"] >= 80
    assert all(event.fixing_class in ("HIGH", "LOW") for event in events)


def test_did_stratification_does_not_pick_best_market() -> None:
    def event(cls1: str, cls2: str, rev1: float, rev2: float) -> g.Event:
        return g.Event("2022-04-01", "2022-W13", 2022, cls1, cls2,
                       5.0, 3.0, rev1, rev2, rev1, rev2, False)
    items = [
        event("HIGH", "HIGH", 4.0, 2.0),
        event("LOW", "HIGH", 1.0, 2.0),
        event("HIGH", "LOW", 4.0, 0.0),
        event("LOW", "LOW", 1.0, 0.0),
    ]
    cells, d = g.stratified_means(items)
    assert all(cells[k]["n"] == 2 for k in cells)
    assert d == pytest.approx((4 - 1) - (2 - 0))


def test_no_events_fail_sample_gate() -> None:
    cells, d = g.stratified_means([])
    assert d is None and all(v["n"] == 0 for v in cells.values())
    assert g.bootstrap_weekly([])["ci95_d_bps"] is None


def test_monthend_flag_is_proxy_last_local_weekday() -> None:
    assert g.month_end_flag(date(2021, 7, 30))
    assert not g.month_end_flag(date(2021, 7, 29))
