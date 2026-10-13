"""Trader Lab Alpha2 ultra-fast synthetic parity, no historical outcomes used."""
from datetime import UTC, datetime
from math import cos, exp, sin

import pytest

from qore.research.alpha2_intermarket import H4, MARKETS, Bar, signal_at
from qore.research.alpha2_ultrafast import optimized_signals


def fixtures(n_symbols=8, n_bars=210):
    first = datetime(2021, 1, 1, tzinfo=UTC)
    output = {}
    for sidx, symbol in enumerate(sorted(MARKETS)[:n_symbols]):
        price = 100.0 + sidx
        rows = {}
        for t in range(n_bars):
            at = first + t * H4
            previous = price
            movement = (0.0015 * sin(t * 0.25) +
                        0.0006 * cos(t * 0.13) +
                        0.000008 * sidx * cos(t * 0.31))
            if t in (170, 180, 190):
                movement = 0.00002 if sidx == 0 else 0.009
            price *= exp(movement)
            rows[at] = Bar(at, previous, max(previous, price) * 1.0003,
                           min(previous, price) * 0.9997, price)
        output[symbol] = rows
    return output, first


def as_identity(signal):
    return (signal.symbol, signal.bar_start_utc, signal.decision_utc,
            signal.earliest_entry_utc, signal.latest_exit_utc,
            signal.direction, signal.baseline_direction, signal.donors)


def test_fast_exact_direction_donors_timing_vs_reference_all_decisions():
    bars, first = fixtures()
    start, end = first + 160 * H4, first + 200 * H4
    reference = [r for step in range(160, 200)
                 for r in signal_at(bars, first + step * H4)]
    fast = optimized_signals(bars, start=start, end=end)
    assert fast  # non-vacuous proof
    assert [as_identity(x) for x in fast] == [as_identity(x) for x in reference]
    for q, r in zip(fast, reference, strict=True):
        assert q.own_return == pytest.approx(r.own_return, abs=1e-14)
        assert q.predicted_return == pytest.approx(r.predicted_return, abs=1e-10)
        assert q.own_past_sigma == pytest.approx(r.own_past_sigma, abs=1e-10)
        assert q.stop_distance_price == pytest.approx(r.stop_distance_price, rel=1e-12)


def test_future_mutation_cannot_change_previous_signal():
    bars, first = fixtures()
    start, end = first + 160 * H4, first + 191 * H4
    before = optimized_signals(bars, start=start, end=end)
    for series in bars.values():
        at = first + 209 * H4
        p = series[at]
        series[at] = Bar(at, p.open, p.high * 10, p.low / 10, p.close * 2)
    assert before == optimized_signals(bars, start=start, end=end)


def test_missing_market_does_not_invent_prices_or_a_trade():
    bars, first = fixtures()
    at = first + 170 * H4
    bars[next(iter(bars))].pop(at)
    fast = optimized_signals(bars, start=at, end=at + H4)
    assert all(x.symbol != sorted(bars)[0] for x in fast)


def test_future_periods_and_non_utc_rejected():
    bars, first = fixtures()
    with pytest.raises(ValueError, match="invalid research"):
        optimized_signals(bars, start=first, end=datetime(2025, 1, 1, tzinfo=UTC))
    with pytest.raises(ValueError, match="invalid research"):
        optimized_signals(bars, start=first, end=first)


def test_zero_sources_and_fewer_than_six_donors_abstain():
    assert optimized_signals({}, start=datetime(2022, 1, 1, tzinfo=UTC),
                             end=datetime(2022, 1, 2, tzinfo=UTC)) == []
    bars, first = fixtures(n_symbols=5)
    assert optimized_signals(bars, start=first, end=first + 200 * H4) == []
