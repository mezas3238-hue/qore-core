"""QORE H4-GROSS-01 scientific causal and failure-mode tests, no market download."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab import qore_native_h4_gross01_eurusd_v1 as m


def block(d: date, h: int, start: int, end: int) -> m.Block:
    at = datetime(d.year, d.month, d.day, h, tzinfo=UTC)
    b = m.Block(at, start, start, at)
    for i in range(1, 48):
        tick = at + timedelta(minutes=5 * i)
        last = end if i == 47 else start
        b.push(tick, start, last)
    return b


def test_one_day_exact_causal_signs_and_equal_timestamp_control() -> None:
    day = date(2020, 6, 16)
    bs = {
        4: block(day, 4, 100000, 100200),
        8: block(day, 8, 100200, 100000),
        12: block(day, 12, 100500, 100100),
        16: block(day, 16, 100200, 100300),
    }
    d = m.evaluate_day(day, bs)
    assert d is not None
    assert d["signal_12h"] == 1  # 04:00 open 100000 < 15:55 close 100100
    assert d["control_4h"] == -1  # 12:00 open 100500 > 15:55 close 100100
    assert abs(d["signed_gross_bps"] - 10000 * 100 / 100200) < 1e-9
    assert abs(d["paired_delta_bps"] - 2 * d["signed_gross_bps"]) < 1e-9
    assert d["reference_entry_price_relative"] == 100200


def test_h4_incomplete_day_is_excluded_not_interpolated() -> None:
    day = date(2020, 6, 16)
    blocks = {
        h: block(day, h, 100100, 100400) for h in m.REQUIRED_STARTS_UTC
    }
    assert m.evaluate_day(day, blocks) is not None
    blocks[8].contiguous = False
    assert m.evaluate_day(day, blocks) is None


def test_future_outcome_change_does_not_change_signal() -> None:
    day = date(2020, 6, 16)
    base = {
        4: block(day, 4, 100000, 100010),
        8: block(day, 8, 100010, 100050),
        12: block(day, 12, 100050, 100080),
        16: block(day, 16, 100080, 100200),
    }
    original = m.evaluate_day(day, base)
    assert original is not None
    base[16].last_close = 99000
    changed = m.evaluate_day(day, base)
    assert changed is not None
    assert changed["signal_12h"] == original["signal_12h"]
    assert changed["control_4h"] == original["control_4h"]
    assert changed["signed_gross_bps"] < 0 < original["signed_gross_bps"]


def test_week_bootstrap_deterministic_and_single_cluster_not_event_n() -> None:
    day = date(2020, 6, 16)
    rows = [
        {"iso_week": "2020-W24", "paired_delta_bps": 1.0},
        {"iso_week": "2020-W24", "paired_delta_bps": 3.0},
        {"iso_week": "2020-W25", "paired_delta_bps": -1.0},
    ]
    ci = m.bootstrap_week_mean(rows, "paired_delta_bps")
    assert ci is not None
    assert ci["cluster_units"] == 2
    assert ci["bootstrap_count"] == 2000
    assert ci == m.bootstrap_week_mean(rows, "paired_delta_bps")
    assert day.year == 2020


def test_insufficient_sample_never_support_and_cost_is_hypothetical() -> None:
    rows = [
        {"iso_week": "2020-W24", "signed_gross_bps": 8.0,
         "control_gross_bps": 2.0, "paired_delta_bps": 6.0,
         "signal_12h": 1}
    ]
    o = m.summarize(rows, "TEST")
    assert o["verdict"] == "INCONCLUSIVE_UNDERPOWERED_BY_PRESET_GATE"
    assert o["economic_net_certified"] is False
    assert o["break_even_total_rt_cost_bps"] == 8.0
    grid = o["hypothetical_cost_grid_not_broker_spread"]
    assert [p["rt_cost_bps"] for p in grid] == [0, 1, 3, 5, 10, 20]
    assert grid[-1]["mean_after_assumed_rt_cost_bps"] == -12


def test_cutoff_does_not_even_parse_quarantined_ohlc(tmp_path: Path) -> None:
    folder = tmp_path / "RAW_M5_LEDGER"
    folder.mkdir()
    for y in range(2016, 2025):
        (folder / f"{y}.jsonl").write_text("", encoding="utf-8")
    before = {
        "opened_at": "2024-09-16T00:00:00+00:00",
        "schema": "not-required-outside-selected-hour"
    }
    after = {
        "opened_at": "2024-09-17T16:00:00+00:00",
        "open_relative": "forbidden future malformed price"
    }
    (folder / "2024.jsonl").write_text(
        json.dumps(before) + "\n" + json.dumps(after) + "\n", encoding="utf-8"
    )
    days, stats = m.read_clock_blocks(tmp_path)
    assert days == {}
    assert stats["source_m5_rows_in_research_span"] == 1


def test_preoutcome_gate_and_fixed_symbol_no_live() -> None:
    assert m.PREREG_COMMIT == "a4424ba3027018bab54f03aff668894f63f47da9"
    assert m.SOURCE_SYMBOL == "EURUSD"
    assert m.DEV_END == date(2022, 9, 17)
    assert m.DIAGNOSTIC_END == date(2024, 9, 17)
    assert m.REQUIRED_STARTS_UTC == (4, 8, 12, 16)
    assert m.STATUS == "GROSS_PHENOMENON_ONLY_NEWS_UNFILTERED"
