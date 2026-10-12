"""No real historical OHLC; synthetic causal TSMOM and statistical gate checks."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from qore.research.alpha2_intermarket import Bar
from qore.research.alpha2_tsmom_daily_weekly import (
    Day,
    daily_from_native,
    directions_before_entry,
    replay_days,
)


def sample_days(start=date(2020, 1, 1), n=310, *, rising=True):
    d = start
    result = []
    for k in range(n):
        while d.weekday() >= 5:
            d += timedelta(days=1)
        base = 10000 + k if rising else 10000 - k
        result.append(Day(d, base + 0.2, base + 0.8, 36))
        d += timedelta(days=1)
    return result


def test_positive_future_trend_generates_nonoverlapping_weekly_long_gross():
    d = sample_days()
    x = replay_days("EURUSD", d)
    assert x["original_events"] > 4
    assert all(e["direction_252_prior_sessions"] == 1 for e in x["events"])
    assert all(e["control_direction_5_prior_sessions"] == 1 for e in x["events"])
    assert all(e["strategy_gross_reference_bps"] > 0 for e in x["events"])
    a = x["events"]
    assert all(a[i]["exit_last_native_M5_close_on_utc_day"] <
               a[i+1]["entry_first_native_M5_open_on_utc_day"]
               for i in range(len(a)-1))


def test_prior_lookback_only_current_day_outcome_poisoning_cannot_flip_signal():
    d = sample_days()
    a = directions_before_entry(d, 260)
    d[260] = Day(d[260].utc_day, 1, 999999, 36)
    assert directions_before_entry(d, 260) == a
    assert a == (1, 1)


def test_adverse_entry_gap_is_included_in_gross_reference_not_prev_close_fill():
    d = sample_days()
    x = replay_days("EURUSD", d)["events"]
    first = next(e for e in x)
    idx = next(i for i, v in enumerate(d)
               if v.utc_day.isoformat() == first["entry_first_native_M5_open_on_utc_day"])
    d[idx] = Day(d[idx].utc_day, 50000, d[idx].close, 36)
    y = replay_days("EURUSD", d)["events"][0]
    assert y["direction_252_prior_sessions"] == first["direction_252_prior_sessions"]
    assert y["strategy_gross_reference_bps"] < first["strategy_gross_reference_bps"]


def test_negative_momentum_has_short_direction_and_gross_gain_downtrend():
    d = sample_days(rising=False)
    x = replay_days("EURUSD", d)
    assert x["original_events"] > 0
    assert all(e["direction_252_prior_sessions"] == -1 for e in x["events"])
    assert all(e["strategy_gross_reference_bps"] > 0 for e in x["events"])


def test_control_can_differ_caused_by_last_five_reversal():
    d = sample_days()
    for i in range(255, 262):
        d[i] = Day(d[i].utc_day, 10200 + 262 - i, 10000 + 262 - i, 36)
    primary, control = directions_before_entry(d, 262)
    assert primary == 1
    assert control == -1


def test_zero_long_lookback_abstains_for_that_week():
    d = sample_days()
    at = 255
    d[at-1] = Day(d[at-1].utc_day, d[at-1].open,
                   d[at-253].close, 36)
    assert directions_before_entry(d, at)[0] == 0
    d = [Day(x.utc_day, 100, 100, 36) for x in d]
    x = replay_days("EURUSD", d)
    assert x["not_entered_week_counts"]["ZERO_PRIOR_MOMENTUM_OR_BASELINE_CENSORED"] >= 1


def test_era_boundary_and_embargo_never_appear_in_events():
    days = sample_days(date(2021, 7, 1), 450)
    events = replay_days("EURUSD", days)["events"]
    assert events
    for e in events:
        entry = date.fromisoformat(e["entry_first_native_M5_open_on_utc_day"])
        exit_ = date.fromisoformat(e["exit_last_native_M5_close_on_utc_day"])
        assert not (entry < date(2022, 9, 17) <= exit_)
        assert exit_ < date(2024, 9, 17)


def test_no_future_five_sessions_censors_instead_of_early_exit():
    d = sample_days(n=255)
    x = replay_days("EURUSD", d)
    assert x["original_events"] == 0
    assert x["not_entered_week_counts"]["INSUFFICIENT_FIVE_FUTURE_SESSIONS_CENSORED"] >= 1


def test_missing_monday_uses_first_existing_tuesday_nonoverlap():
    d = sample_days(n=300)
    d = [x for x in d if not (x.utc_day.weekday() == 0 and x.utc_day.year == 2021)]
    rows = replay_days("GBPUSD", d)["events"]
    assert rows
    assert any(date.fromisoformat(
        e["entry_first_native_M5_open_on_utc_day"]
    ).weekday() == 1 for e in rows)


def test_daily_native_uses_first_open_last_close_no_resampled_missing_quotes():
    morning = datetime(2021, 6, 1, tzinfo=UTC)
    bars = [Bar(morning + i*timedelta(minutes=5),
                float(100+i), float(101+i), float(99+i), float(100.5+i))
            for i in range(12)]
    d, quality = daily_from_native(bars)
    assert len(d) == 1 and d[0].native_m5_bars == 12
    assert d[0].open == bars[0].open and d[0].close == bars[-1].close
    assert quality["native_M5_rows_read_pre_embargo"] == 12


def test_sparse_days_and_weekend_are_not_synthesized():
    a = datetime(2020, 1, 4, tzinfo=UTC)
    b = datetime(2020, 1, 6, tzinfo=UTC)
    rows = ([Bar(a+i*timedelta(minutes=5), 100, 101, 99, 100)
             for i in range(12)]
            + [Bar(b+i*timedelta(minutes=5), 100, 101, 99, 100)
               for i in range(11)])
    d, quality = daily_from_native(rows)
    assert d == []
    assert quality["ignored_weekend_UTC_days"] == 1
    assert quality["dropped_sparse_UTC_days"] == 1


def test_out_of_order_and_embargo_and_utc_future_source_rejected():
    a = datetime(2021, 6, 1, tzinfo=UTC)
    x = Bar(a, 100, 101, 99, 100)
    with pytest.raises(ValueError, match="NOT_STRICT_M5"):
        daily_from_native([x, x])
    with pytest.raises(ValueError, match="EMBARGO"):
        daily_from_native([Bar(datetime(2025,1,1,tzinfo=UTC), 100, 101, 99, 100)])


def test_date_source_contract_does_not_accept_weekend_or_bad_daily_open():
    with pytest.raises(ValueError, match="UNADMITTED_DAY"):
        Day(date(2022, 1, 1), 100, 99, 60)
    with pytest.raises(ValueError, match="QUOTE_OR_DENSITY"):
        Day(date(2022, 1, 3), 0, 99, 60)
