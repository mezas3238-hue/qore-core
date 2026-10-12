"""Gold H4-GROSS-02: causal reversal, gross-only and multiplicity tests."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab import qore_native_h4_gross02_xauusd_v1 as m


def make_block(d: date, h: int, op: int, cl: int) -> m.Block:
    start = datetime(d.year, d.month, d.day, h, tzinfo=UTC)
    b = m.Block(start, op, op, start)
    for i in range(1, 48):
        b.push(start + timedelta(minutes=5 * i), op, cl if i == 47 else op)
    return b


def sample():
    d = date(2020, 6, 16)
    return d, {
        4: make_block(d, 4, 100000, 100200),
        8: make_block(d, 8, 100200, 100000),
        12: make_block(d, 12, 100500, 100100),
        16: make_block(d, 16, 100200, 100300),
    }


def test_gold_reversal_is_opposite_prior_trend_both_horizons() -> None:
    day, blocks = sample()
    o = m.evaluate_day(day, blocks)
    assert o is not None
    assert o["signal_12h"] == -1
    assert o["control_4h"] == 1
    assert o["paired_delta_bps"] < 0
    assert o["signed_gross_bps"] < 0


def test_future_candle_never_changes_past_signals() -> None:
    day, blocks = sample()
    before = m.evaluate_day(day, blocks)
    assert before
    blocks[16].last_close = 99900
    after = m.evaluate_day(day, blocks)
    assert after
    assert before["signal_12h"] == after["signal_12h"]
    assert before["control_4h"] == after["control_4h"]
    assert before["signed_gross_bps"] < 0 < after["signed_gross_bps"]


def test_noncontiguous_gold_calendar_day_excluded() -> None:
    day, blocks = sample()
    assert m.evaluate_day(day, blocks)
    blocks[12].contiguous = False
    assert m.evaluate_day(day, blocks) is None


def test_new_ci_is_97_5_and_weekly_clustered() -> None:
    rows = [
        {"iso_week": "2020-W24", "paired_delta_bps": 2.0},
        {"iso_week": "2020-W24", "paired_delta_bps": -1.0},
        {"iso_week": "2020-W25", "paired_delta_bps": 3.0},
    ]
    ci = m.bootstrap_week_mean(rows, "paired_delta_bps")
    assert ci is not None
    assert ci["cluster_units"] == 2
    assert ci["bootstrap_count"] == 2000
    assert "low975" in ci and "high975" in ci
    assert "low95" not in ci
    assert ci == m.bootstrap_week_mean(rows, "paired_delta_bps")


def test_small_sample_cannot_support_and_costs_not_broker() -> None:
    rows = [{
        "iso_week": "2020-W24", "signed_gross_bps": 3.5,
        "control_gross_bps": -1.0, "paired_delta_bps": 4.5,
        "signal_12h": 1,
    }]
    o = m.summarize(rows, "TEST")
    assert o["verdict"] == "INCONCLUSIVE_UNDERPOWERED_BY_PRESET_GATE"
    assert o["break_even_total_rt_cost_bps"] == 3.5
    assert o["hypothetical_cost_grid_not_broker_spread"][-1]["mean_after_assumed_rt_cost_bps"] == -16.5
    assert o["economic_net_certified"] is False


def test_price_quarantine_after_2024_09_17_not_even_parsed(tmp_path: Path) -> None:
    folder = tmp_path / "RAW_M5_LEDGER"
    folder.mkdir()
    for year in range(2016, 2025):
        (folder / f"{year}.jsonl").write_text("")
    earlier = {"opened_at": "2024-09-16T00:00:00+00:00"}
    later = {"opened_at": "2024-09-17T16:00:00+00:00",
             "open_relative": "invalid hidden future value"}
    (folder / "2024.jsonl").write_text(json.dumps(earlier) + "\n" + json.dumps(later) + "\n")
    rows, stats = m.read_clock_blocks(tmp_path)
    assert rows == {}
    assert stats["source_m5_rows_in_research_span"] == 1


def test_source_pre_registration_and_no_live() -> None:
    assert m.SOURCE_SYMBOL == "XAUUSD"
    assert m.PREREG_COMMIT == "94bc58e89b5b2112e1c65df77a077bff2758b63c"
    assert m.DEV_END == date(2022, 9, 17)
    assert m.DIAGNOSTIC_END == date(2024, 9, 17)
    assert m.STATUS == "GROSS_PHENOMENON_ONLY_NEWS_UNFILTERED"
