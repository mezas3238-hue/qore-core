"""Causal/fail-closed synthetic tests; no real prices or PnL are inspected."""
from datetime import UTC, datetime
from math import cos, exp, sin

import pytest

from qore.research.alpha2_intermarket import (
    H4,
    M5,
    MARKETS,
    RESEARCH_CUTOFF,
    Bar,
    _correlation_beta,
    aggregate_complete_h4,
    signal_at,
)


def test_universe_is_33_unique_and_class_bounded() -> None:
    assert len(MARKETS) == 33
    assert len(set(MARKETS)) == 33
    assert MARKETS[:3] == ("NAS100", "SP500", "US30")
    assert MARKETS[3:5] == ("XAUUSD", "XAGUSD")


def test_full_m5_block_creates_one_h4_without_synthesis() -> None:
    t = datetime(2023, 1, 2, tzinfo=UTC)
    rows = [Bar(t + M5 * k, 100.0, 101.0, 99.0, 100.0 + k * 0.001)
            for k in range(48)]
    out = aggregate_complete_h4(rows)
    assert len(out) == 1
    assert out[t].close == rows[-1].close


def test_incomplete_h4_is_dropped_not_patched() -> None:
    t = datetime(2023, 1, 2, tzinfo=UTC)
    rows = [Bar(t + M5 * k, 100, 101, 99, 100) for k in range(48) if k != 8]
    assert aggregate_complete_h4(rows) == {}


def test_duplicate_timestamp_blocks_entire_input() -> None:
    t = datetime(2023, 1, 2, tzinfo=UTC)
    row = Bar(t, 100, 101, 99, 100)
    with pytest.raises(ValueError, match="duplicate"):
        aggregate_complete_h4([row, row])


def test_invalid_price_or_naive_timestamp_fails() -> None:
    with pytest.raises(ValueError, match="OHLC"):
        aggregate_complete_h4([Bar(datetime(2023, 1, 1, tzinfo=UTC),
                                   100, 98, 99, 100)])
    with pytest.raises(ValueError, match="UTC"):
        aggregate_complete_h4([Bar(datetime(2023, 1, 1), 100, 101, 99, 100)])


def test_fixed_correlation_is_past_only_and_requires_samples() -> None:
    assert _correlation_beta([1.0] * 95, [1.0] * 95) == (0.0, 0.0)
    a = [float(i) for i in range(120)]
    corr, beta = _correlation_beta(a, a)
    assert abs(corr - 1.0) < 1e-12
    assert abs(beta - 1.0) < 1e-12


def test_embargo_price_window_is_enforced() -> None:
    with pytest.raises(ValueError, match="reserved"):
        signal_at({}, RESEARCH_CUTOFF)


def test_no_price_future_can_change_frozen_decision() -> None:
    t0 = datetime(2022, 1, 1, tzinfo=UTC)
    at = t0 + 170 * H4
    symbols = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
               "NZDUSD", "USDCAD", "EURJPY", "GBPJPY")
    all_bars = {}
    for si, symbol in enumerate(symbols):
        px = 100.0 + si
        timeseries = {}
        for k in range(171):
            t = t0 + H4 * k
            open_px = px
            step = (0.0009 * sin(k * 0.2) + 0.0004 * cos(k * 0.07)
                    + 0.000002 * si * sin(k * 0.31))
            if k == 170:
                step = 0.00004 if si == 0 else 0.006
            px *= exp(step)
            timeseries[t] = Bar(t, open_px, max(open_px, px) * 1.0002,
                                min(open_px, px) * 0.9998, px)
        all_bars[symbol] = timeseries
    before = signal_at(all_bars, at)
    assert any(s.symbol == "EURUSD" and s.direction == 1 for s in before)
    for series in all_bars.values():
        previous = series[at]
        future = at + H4
        series[future] = Bar(future, previous.close, previous.close * 10,
                             previous.close * 0.1, previous.close * 2)
    after = signal_at(all_bars, at)
    assert before == after
    s = next(s for s in before if s.symbol == "EURUSD")
    assert s.decision_utc == (at + H4).isoformat()
    assert s.earliest_entry_utc == (at + H4 + M5).isoformat()
    assert "BLOCKED" in s.execution_status
