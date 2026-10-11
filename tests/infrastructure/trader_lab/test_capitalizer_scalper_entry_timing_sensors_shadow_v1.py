"""As-of multi-sensor instrumentation; never a forward-return entry optimizer."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_entry_timing_sensors_shadow_v1 import (
    IDENTITY,
    EntrySensorFrame,
    EntrySensorInput,
    SensorStatus,
    observe_entry_timing_sensors,
)

START = datetime(2026, 1, 2, 12, tzinfo=UTC)


def _bar(i: int, o: str, h: str, low: str, c: str) -> CapitalizerM1Bar:
    at = START + timedelta(minutes=i)
    return CapitalizerM1Bar(
        symbol="EURUSD", opened_at=at,
        closed_at=at + timedelta(minutes=1),
        open=Decimal(o), high=Decimal(h), low=Decimal(low),
        close=Decimal(c), volume=100, digits=5,
    )


SWEEP = (
    _bar(0, "1.1000", "1.1010", "1.0995", "1.1005"),
    _bar(1, "1.1005", "1.1008", "1.0990", "1.0995"),
    _bar(2, "1.0995", "1.1002", "1.0993", "1.1000"),
    _bar(3, "1.1000", "1.1001", "1.0985", "1.0990"),
    _bar(4, "1.0990", "1.0994", "1.0988", "1.0991"),
    _bar(5, "1.0991", "1.1006", "1.0990", "1.1004"),
)

FVG = (
    _bar(0, "10.00", "10.10", "9.90", "10.05"),
    _bar(1, "10.05", "10.30", "10.00", "10.25"),
    _bar(2, "10.25", "10.50", "10.20", "10.45"),
    _bar(3, "10.45", "10.48", "10.05", "10.15"),
    _bar(4, "10.15", "10.25", "10.00", "10.08"),
    _bar(5, "10.08", "10.20", "9.95", "10.02"),
    _bar(6, "10.02", "10.20", "10.00", "10.12"),
    _bar(7, "10.12", "10.60", "10.10", "10.55"),
)


def _context(bars: tuple[CapitalizerM1Bar, ...] = SWEEP) -> EntrySensorInput:
    return EntrySensorInput(
        symbol="EURUSD", session="LONDON",
        decision_at=bars[-1].closed_at,
        h1_direction="BULLISH",
        h1_basis="CANDLE2_REVERSAL:SWING_LOW",
        h1_confirmed_at=START - timedelta(minutes=30),
        m15_confirmed_at=START,
        m15_protected_stop=Decimal("1.0950")
        if bars[0].close < Decimal("5") else Decimal("9.80"),
        m1_bars=bars,
    )


def _sensor(frame: EntrySensorFrame, name: str) -> tuple[SensorStatus, str | None]:
    rows = [r for r in frame.sensors if r.sensor == name]
    assert len(rows) == 1
    return rows[0].status, rows[0].value


def test_sweep_cisd_sensor_emits_only_at_actual_closed_confirmation() -> None:
    pre = observe_entry_timing_sensors(_context(SWEEP[:5]))
    assert pre.source_event_observed is False
    assert _sensor(pre, "SOURCE_SIGNAL_OBSERVED")[0] is SensorStatus.DEVELOPING
    assert _sensor(pre, "M1_SWEEP_CISD_CLOSED")[0] is SensorStatus.DEVELOPING

    confirmed = observe_entry_timing_sensors(_context())
    assert confirmed.identity == IDENTITY
    assert confirmed.source_event_observed
    assert confirmed.first_source_cisd_family == "LIQUIDITY_SWEEP_CISD"
    assert confirmed.first_source_cisd_confirmed_at == SWEEP[-1].closed_at.isoformat()
    assert _sensor(confirmed, "M1_SWEEP_CISD_CLOSED")[0] is SensorStatus.OBSERVED
    assert _sensor(confirmed, "H1_THESIS_AGE_MINUTES")[1] == "36.0"
    assert _sensor(confirmed, "M15_TO_M1_ELAPSED_MINUTES")[1] == "6.0"
    assert _sensor(confirmed, "M1_PROTECTED_SWING_ATTESTATION")[0] is (
        SensorStatus.NOT_AVAILABLE
    )
    assert not confirmed.execution_authorized
    assert not confirmed.hard_entry_gate_added
    assert not confirmed.cognitive_master_frame_attested
    assert not confirmed.trader_certified
    assert not confirmed.live_authorized


def test_fvg_sensor_checks_retrace_then_source_valid_cisd() -> None:
    result = observe_entry_timing_sensors(_context(FVG))
    assert result.first_source_cisd_family == "FVG_RETRACE_CISD"
    assert _sensor(result, "M1_FVG_FORMED")[0] is SensorStatus.OBSERVED
    assert _sensor(result, "M1_FVG_RETRACE")[0] is SensorStatus.OBSERVED
    assert _sensor(result, "M1_FVG_CISD_CLOSED")[0] is SensorStatus.OBSERVED
    assert _sensor(result, "FULL_COGNITIVE_MASTER_FRAME")[0] is (
        SensorStatus.NOT_AVAILABLE
    )


def test_future_ohlc_or_candle_open_at_decision_cannot_leak_into_sensors() -> None:
    original = _context()
    future = _bar(6, "1.1004", "1.1500", "1.0700", "1.1200")
    with pytest.raises(ValueError, match="future/inflight"):
        EntrySensorInput(**{
            **{key: getattr(original, key)
               for key in original.__dataclass_fields__},
            "m1_bars": SWEEP + (future,),
        })
    inflight = replace(
        future, opened_at=SWEEP[-1].closed_at,
        closed_at=SWEEP[-1].closed_at + timedelta(minutes=1),
    )
    with pytest.raises(ValueError, match="future/inflight"):
        replace(original, m1_bars=SWEEP + (inflight,))


def test_spread_costs_and_target_require_independent_asof_witness() -> None:
    ctx = _context()
    reading = observe_entry_timing_sensors(ctx)
    for name in ("H1_TARGET_ROOM_R", "BROKER_BID_ASK_SPREAD",
                 "BROKER_COMMISSION_PER_LOT"):
        assert _sensor(reading, name)[0] is SensorStatus.NOT_AVAILABLE
    with pytest.raises(ValueError, match="as-of witness"):
        replace(
            ctx, witnessed_h1_target=Decimal("1.1100"),
            h1_target_confirmed_at=START + timedelta(minutes=60),
        )
    quotes = observe_entry_timing_sensors(replace(
        ctx, witnessed_h1_target=Decimal("1.1100"),
        h1_target_confirmed_at=START - timedelta(minutes=60),
        bid=Decimal("1.1003"), ask=Decimal("1.1005"),
        commission_round_trip_per_lot=Decimal("14"),
    ))
    assert _sensor(quotes, "H1_TARGET_ROOM_R")[0] is SensorStatus.OBSERVED
    assert _sensor(quotes, "BROKER_BID_ASK_SPREAD")[1] == "0.0002"
    assert _sensor(quotes, "BROKER_COMMISSION_PER_LOT")[1] == "14"
    assert not quotes.trade_size_authorized


def test_no_future_h1_state_expiry_is_ever_accepted_as_an_input() -> None:
    fields = EntrySensorInput.__dataclass_fields__
    assert "h1_state_until" not in fields
    assert "outcome_r" not in fields
    assert "mfe" not in fields
    assert "future_candle" not in fields


def test_source_chronology_and_original_stop_fail_closed() -> None:
    x = _context()
    with pytest.raises(ValueError, match="upstream H1/M15"):
        replace(x, h1_confirmed_at=x.decision_at)
    with pytest.raises(ValueError, match="upstream H1/M15"):
        replace(x, m15_confirmed_at=x.decision_at)
    with pytest.raises(ValueError, match="risk side"):
        observe_entry_timing_sensors(
            replace(x, m15_protected_stop=Decimal("1.1200"))
        )
    with pytest.raises(ValueError, match="chronological"):
        replace(x, m1_bars=tuple(reversed(SWEEP)))
    with pytest.raises(ValueError, match="incomplete broker bid/ask"):
        replace(x, bid=Decimal("1.1"))


def test_source_signal_is_not_an_entry_and_no_scores_are_invented() -> None:
    f = observe_entry_timing_sensors(_context())
    names = {s.sensor for s in f.sensors}
    assert len(names) == len(f.sensors)
    assert len(names) >= 18
    assert "H1_ASOF_PARTIAL_PRICE_RANK" in names
    assert "SESSION_REMAINING_MINUTES" in names
    assert "M1_LOCAL_MEDIAN_BAR_RANGE" in names
    assert "M1_OPPOSING_SERIES" in names
    assert "SOURCE_SIGNAL_OBSERVED" in names
    assert not hasattr(f, "win_probability")
    assert not hasattr(f, "optimized_entry_score")
