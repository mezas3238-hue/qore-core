"""E1 causal seven methods: exact M5, DST, embargo, no-lookahead, paired control."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_e1_33x7_seven_gross_per_market_v1 as m


def put(cal: m.BarMap, start: datetime, n: int, initial: int,
        last_close: int, high_bump: int = 5, low_bump: int = 5) -> None:
    for i in range(n):
        at = start + timedelta(minutes=i * 5)
        close = last_close if i == n - 1 else initial
        bar = (initial, close, max(initial, close) + high_bump,
               min(initial, close) - low_bump)
        cal.setdefault(at.date(), {})[at.hour * 60 + at.minute] = bar


def test_m5_blocks_fail_closed_missing_duplicate_clock_or_NAIVE() -> None:
    cal: m.BarMap = {}
    start = datetime(2020, 7, 1, 8, tzinfo=UTC)
    put(cal, start, 6, 10000, 10100)
    assert len(m.exact_bars(cal, start, 6)) == 6
    assert m.exact_bars(cal, start, 7) is None
    del cal[start.date()][8 * 60 + 10]
    assert m.exact_bars(cal, start, 6) is None
    with pytest.raises(ValueError, match="aware"):
        m.exact_bars(cal, datetime(2020, 7, 1, 8), 6)


def test_persistence_and_reversal_exact_opposites_and_causal_sign() -> None:
    day = date(2020, 7, 1)
    cal: m.BarMap = {}
    base = datetime(2020, 7, 1, tzinfo=UTC)
    put(cal, base + timedelta(hours=4), 96, 10000, 10000)
    put(cal, base + timedelta(hours=12), 48, 10000, 10200)
    put(cal, base + timedelta(hours=16), 48, 10200, 10100)
    p, label = m.synthetic_events_for_day("PERSISTENCE_12H", day, cal, [])
    r, label2 = m.synthetic_events_for_day("REVERSAL_12H", day, cal, [])
    assert label == label2 == "EVENT"
    assert p is not None and r is not None
    assert (p["strategy_signal"], r["strategy_signal"]) == (1, -1)
    assert (p["baseline_signal"], r["baseline_signal"]) == (1, -1)
    # Changing AFTER target begins alters returns, never signed decision.
    old_signal = p["strategy_signal"]
    put(cal, base + timedelta(hours=16), 48, 10200, 12000)
    changed, _ = m.synthetic_events_for_day("PERSISTENCE_12H", day, cal, [])
    assert changed and changed["strategy_signal"] == old_signal
    assert changed["strategy_gross_bps"] != p["strategy_gross_bps"]


def test_breakout_not_confused_with_sweep_recovery() -> None:
    day = date(2020, 7, 1)
    cal: m.BarMap = {}
    base = datetime(2020, 7, 1, tzinfo=UTC)
    put(cal, base + timedelta(hours=8), 48, 10000, 10100)
    put(cal, base + timedelta(hours=12), 12, 10100, 10400)
    put(cal, base + timedelta(hours=13), 24, 10400, 10300)
    x, reason = m.synthetic_events_for_day("RANGE_BREAK_CONT", day, cal, [])
    y, reason2 = m.synthetic_events_for_day("SWEEP_RECLAIM", day, cal, [])
    assert reason == "EVENT" and x and x["strategy_signal"] == 1
    assert reason2 == "NO_RECLAIM" and y is None


def test_cash_index_and_london_fx_local_dst_clocks() -> None:
    cal: m.BarMap = {}
    summer = date(2020, 7, 1)
    winter = date(2020, 1, 2)
    # NAS100 US cash proxy NY 09:30; London FX transition London 08:00.
    for day, nas_utc, fx_utc in (
        (summer, 13, 7),
        (winter, 14, 8),
    ):
        index_base = datetime(day.year, day.month, day.day, nas_utc, 30, tzinfo=UTC)
        for offset, n, op, cl in ((-30, 6, 10000, 10100), (0, 6, 10100, 10200),
                                  (30, 24, 10200, 10300)):
            put(cal, index_base + timedelta(minutes=offset), n, op, cl)
        fx_base = datetime(day.year, day.month, day.day, fx_utc, tzinfo=UTC)
        for offset, n, op, cl in ((-30, 6, 10000, 10100), (0, 6, 10100, 10200),
                                  (30, 24, 10200, 10300)):
            put(cal, fx_base + timedelta(minutes=offset), n, op, cl)
        index, label = m.session_events_for_day("POST_OPEN_CONT", "NAS100", day, cal)
        fx, label_fx = m.session_events_for_day("POST_OPEN_CONT", "EURUSD", day, cal)
        assert label == label_fx == "EVENT"
        assert index and fx
        assert index["reference_entry_utc"].startswith(f"{day}T{nas_utc+1:02d}:00")
        assert fx["reference_entry_utc"].startswith(f"{day}T{fx_utc:02d}:30")
        assert index["broker_executable_fill"] is False


def test_initial_reaction_differs_from_long_postopen() -> None:
    cal: m.BarMap = {}
    day = date(2020, 7, 1)
    ref = datetime(2020, 7, 1, 13, 30, tzinfo=UTC)
    put(cal, ref - timedelta(minutes=30), 6, 10000, 10050)
    put(cal, ref, 3, 10050, 10100)
    put(cal, ref + timedelta(minutes=15), 3, 10100, 10120)
    put(cal, ref + timedelta(minutes=30), 24, 10120, 10190)
    short, x = m.session_events_for_day("OPEN_INITIAL_REACTION", "NAS100", day, cal)
    long, y = m.session_events_for_day("POST_OPEN_CONT", "NAS100", day, cal)
    assert short and long and x == y == "EVENT"
    assert short["reference_entry_utc"] != long["reference_entry_utc"]
    assert short["strategy_signal"] == long["strategy_signal"] == 1


def test_trend_needs_three_past_full_sessions_no_current_or_future_data() -> None:
    cal: m.BarMap = {}
    chosen = date(2020, 7, 8)
    history = [date(2020, 7, 3), date(2020, 7, 6), date(2020, 7, 7), chosen]
    for date_ in history[:-1]:
        base = datetime(date_.year,date_.month,date_.day,16,tzinfo=UTC)
        put(cal, base, 48, 10000, 10050)
    base = datetime(2020, 7, 8, tzinfo=UTC)
    put(cal, base + timedelta(hours=12), 48, 10000, 10050)
    put(cal, base + timedelta(hours=16), 48, 10050, 10100)
    signal, reason = m.synthetic_events_for_day("TREND_MULTI_DAY", chosen, cal, history)
    assert signal is not None and reason == "EVENT"
    assert signal["strategy_signal"] == 1
    # Invalidate one previous session: three past FULL sessions no longer available.
    del cal[history[0]][16 * 60 + 5]
    no, why = m.synthetic_events_for_day("TREND_MULTI_DAY", chosen, cal, history)
    assert no is None and why == "NO_THREE_PAST_FULL_SESSIONS_WITHIN_7D"


def test_2024_embargo_even_if_price_fields_invalid(tmp_path: Path) -> None:
    raw = tmp_path / "RAW_M5_LEDGER"
    raw.mkdir()
    for year in range(2016, 2025):
        (raw / f"{year}.jsonl").write_text("", encoding="utf-8")
    (raw / "2024.jsonl").write_text(json.dumps({
        "opened_at": "2024-09-17T14:30:00+00:00",
        "open_relative": "must_not_access_future_prices",
    }) + "\n", encoding="utf-8")
    bars, count = m.read_original_preembargo(tmp_path, "NAS100")
    assert count["stored_session_bars"] == 0
    assert bars == {}


def test_prereg_and_no_net_live_provenance() -> None:
    assert m.PREREG_SHA == "67022daf7e2c3335eda991fd217df83fc1a34bc4"
    assert m.SOURCE_33_SHA == "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
    assert len(m.METHODS) == 7
    assert m.EMBARGO == datetime(2024, 9, 17, tzinfo=UTC)
    assert m.ROUNDTRIP_ASSUMPTIONS == (0, 1, 3, 5, 10, 20)
