"""Tests for prespecified ALL 33 M5 sweep-reclaim gross-only causal panel."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from qore.infrastructure.trader_lab import qore_native_gross04_panel33_sweep_reclaim_v1 as m


def block(day: date, hour: int, bars: int, op: int, close: int, hi: int, lo: int) -> m.ClockBlock:
    start = datetime(day.year, day.month, day.day, hour, tzinfo=UTC)
    return m.ClockBlock(
        first_open=op, last_close=close, max_high=hi, min_low=lo,
        first_at=start, last_at=start + timedelta(minutes=5 * (bars-1)),
        count=bars, contiguous=True,
    )


def good(day=date(2020, 6, 16)) -> dict[str, m.ClockBlock]:
    return {
        "PRE": block(day, 8, 48, 100, 100, 105, 95),
        "PROBE": block(day, 12, 12, 102, 100, 107, 97),
        "TARGET": block(day, 13, 24, 100, 99, 103, 98),
    }


def test_future_return_cannot_change_signal_or_comparison() -> None:
    d = date(2020, 6, 16)
    b = good(d)
    e, reason = m.event_from_day(d, b)
    assert reason == "EVENT" and e is not None
    assert e["pattern"] == "SWEEP_UP_RECLAIM"
    assert e["signal"] == -1 and e["baseline_signal"] == 1
    assert e["strategy_gross_bps"] > 0 and e["baseline_gross_bps"] < 0
    assert abs(e["paired_delta_bps"] - 2 * e["strategy_gross_bps"]) < 1e-8
    b["TARGET"].last_close = 101
    e2, reason = m.event_from_day(d, b)
    assert reason == "EVENT" and e2 is not None
    assert e2["signal"] == e["signal"]
    assert e2["baseline_signal"] == e["baseline_signal"]
    assert e2["strategy_gross_bps"] < 0


def test_ambiguous_double_sweep_and_failed_reclaim_excluded() -> None:
    d = date(2020, 6, 16)
    b = good(d)
    b["PROBE"].min_low = 94
    assert m.event_from_day(d, b) == (None, "BOTH_OR_NO_BREACH")
    b = good(d)
    b["PROBE"].last_close = 106
    assert m.event_from_day(d, b) == (None, "FAILED_RECLAIM")


def test_source_M5_gaps_exclude_not_interpolate_or_shift_time() -> None:
    d = date(2020, 6, 16)
    b = good(d)
    assert m.event_from_day(d, b)[0] is not None
    b["PRE"].contiguous = False
    assert m.event_from_day(d, b) == (None, "INCOMPLETE_UTC_BLOCKS")
    b = good(d)
    b["TARGET"].count = 23
    assert m.event_from_day(d, b) == (None, "INCOMPLETE_UTC_BLOCKS")


def test_weekly_resamples_preserve_all_symbols_without_selection() -> None:
    symbols = m.final33.FROZEN_UNIVERSE_33
    one = {
        sym: [{"iso_week": "2020-W24", "paired_delta_bps": 2.0,
               "strategy_gross_bps": 1.0,
               "baseline_gross_bps": -1.0, "signal": 1}]
        for sym in symbols
    }
    ci = m.sample_panel_weeks(one, "paired_delta_bps")
    assert ci["whole_week_clusters"] == 1
    assert ci["null_resamples"] == 0
    assert ci["ci"] == {"low98_75": 2, "high98_75": 2}
    assert ci == m.sample_panel_weeks(one, "paired_delta_bps")
    out = m.summarize_all33(one, "TEMPORAL_DIAGNOSTIC")
    assert out["market_count"] == 33
    assert out["markets_passing_n_gate"] == 0
    assert out["verdict"] == "PANEL_UNDERPOWERED_NO_SYMBOL_EXCLUSION"
    assert out["equal_market_paired_delta_mean_bps"] == 2.0
    assert all(v["family_significance_test_performed"] is False
               for v in out["families_descriptive_no_selection"].values())


def test_32_market_observation_must_fail_even_if_pnl_positive() -> None:
    data = {sym: [] for sym in list(m.final33.FROZEN_UNIVERSE_33)[:32]}
    with pytest.raises(ValueError, match="not full frozen"):
        m.summarize_all33(data, "DEVELOPMENT")


def test_prices_after_embargo_skipped_before_fields_access(tmp_path: Path) -> None:
    raw = tmp_path / "RAW_M5_LEDGER"
    raw.mkdir()
    for year in range(2016, 2025):
        (raw / f"{year}.jsonl").write_text("", encoding="utf-8")
    (raw / "2024.jsonl").write_text(
        json.dumps({"opened_at": "2024-09-17T08:00:00+00:00",
                    "open_relative": "invalid_must_never_use"}) + "\n"
    )
    d, stats = m.collect_blocks(tmp_path, "NZDCAD", False)
    assert d == {}
    assert stats["source_m5_timestamps_before_embargo"] == 0


def test_prereg_original_source_sha_and_one_fixed_family_panel() -> None:
    assert m.PREREG_SHA == "9b147f0a385213dd4b0183b3205c6c9d467581ad"
    assert m.PANEL_SOURCE_33_SHA == "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"
    assert m.BLOCKS == {"PRE": (8, 48), "PROBE": (12, 12), "TARGET": (13, 24)}
    assert m.START == date(2016, 9, 17)
    assert m.EMBARGO_DATE == date(2024, 9, 17)
    assert m.BOOTSTRAP_COUNT == 2000
    assert m.COSTS_RT_HYPOTHETICAL_BPS == (0, 1, 3, 5, 10, 20)
    assert len(m.final33.FROZEN_UNIVERSE_33) == 33
    with pytest.raises(ValueError):
        m.source33_parent_manifest(Path("/not-mounted-src33-manifest"))


def test_no_live_order_or_historical_bidask_net_pnl_implementation() -> None:
    src = Path(m.__file__).read_text(encoding="utf-8")
    for forbidden in ("ProtoOANewOrderReq", "place_order(", "connect_live(",
                      "enable_vps_trading(", "broker_net_profit_factor("):
        assert forbidden not in src
