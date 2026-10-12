"""Pre-outcome tests for one NAS100 NY cash-open gross-only trial."""
from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab import qore_native_nas100_ny_open_drive03_gross_v1 as m


def make_block(day: date, hour: int, minute: int, count: int,
               open_: int, close: int) -> m.ClockBlock:
    start = datetime(day.year, day.month, day.day, hour, minute, tzinfo=m.NEW_YORK)
    b = m.ClockBlock(start, start, open_, open_)
    for i in range(1, count):
        b.add(start + timedelta(minutes=5 * i), close if i == count - 1 else open_)
    return b


def three_blocks(day: date) -> dict[str, m.ClockBlock]:
    return {
        "PRE": make_block(day, 9, 0, 6, 100000, 100020),
        "DRIVE": make_block(day, 9, 30, 6, 100020, 99950),
        "TARGET": make_block(day, 10, 0, 24, 99950, 99900),
    }


def test_fixed_09_30_ny_dst_maps_to_distinct_correct_utc_instants() -> None:
    assert m.required_slot(datetime(2020, 7, 1, 13, 30, tzinfo=UTC)) == "DRIVE"
    assert m.required_slot(datetime(2020, 1, 2, 14, 30, tzinfo=UTC)) == "DRIVE"
    assert m.required_slot(datetime(2020, 7, 1, 13, 0, tzinfo=UTC)) == "PRE"
    assert m.required_slot(datetime(2020, 1, 2, 15, 0, tzinfo=UTC)) == "TARGET"
    assert m.required_slot(datetime(2020, 7, 4, 13, 30, tzinfo=UTC)) is None


def test_open_drive_sign_distinct_from_preopen_control_without_future_prices() -> None:
    day = date(2020, 7, 1)
    x = three_blocks(day)
    y = m.evaluate_ny_day(day, x)
    assert y is not None
    assert y["open_drive_sign"] == -1
    assert y["pre_open_baseline_sign"] == 1
    assert y["strategy_gross_bps"] > 0
    assert y["baseline_gross_bps"] < 0
    assert y["paired_delta_bps"] == 2 * y["strategy_gross_bps"]
    x["TARGET"].last_close = 100100
    z = m.evaluate_ny_day(day, x)
    assert z is not None
    assert z["open_drive_sign"] == y["open_drive_sign"]
    assert z["pre_open_baseline_sign"] == y["pre_open_baseline_sign"]
    assert z["strategy_gross_bps"] < 0


def test_missing_one_m5_or_duplicated_clock_cannot_inflate_sample() -> None:
    day = date(2020, 1, 2)
    x = three_blocks(day)
    assert m.evaluate_ny_day(day, x) is not None
    x["DRIVE"].contiguous = False
    assert m.evaluate_ny_day(day, x) is None
    x = three_blocks(day)
    x["TARGET"].count = 23
    assert m.evaluate_ny_day(day, x) is None


def test_weekly_ci_exact_deterministic_and_costs_not_real() -> None:
    rows = [
        {"ny_iso_week": "2020-W01", "paired_delta_bps": 3.0},
        {"ny_iso_week": "2020-W01", "paired_delta_bps": 2.0},
        {"ny_iso_week": "2020-W02", "paired_delta_bps": -1.0},
    ]
    ci = m.weekly_bootstrap(rows, "paired_delta_bps")
    assert ci is not None
    assert ci["week_clusters"] == 2
    assert ci["bootstrap_draws"] == 2000
    assert "lower_98_333pct" in ci
    assert "upper_98_333pct" in ci
    assert ci == m.weekly_bootstrap(rows, "paired_delta_bps")
    sample = [{
        "ny_iso_week": "2020-W01", "strategy_gross_bps": 10.0,
        "baseline_gross_bps": 2.0, "paired_delta_bps": 8.0,
        "open_drive_sign": 1,
    }]
    d = m.summarize(sample, "unit-test")
    assert d["verdict"] == "INCONCLUSIVE_UNDERPOWERED_BY_PRESET_GATE"
    assert d["net_economics_certified"] is False
    assert d["mean_roundtrip_break_even_bps"] == 10
    assert [r["assumed_RT_cost_bps"] for r in d["hypothetical_total_RT_cost_not_actual_broker"]] == [0, 1, 3, 5, 10, 20]


def test_OHLC_2024_09_17_quarantined_even_when_malformed(tmp_path: Path) -> None:
    folder = tmp_path / "RAW_M5_LEDGER"
    folder.mkdir()
    for year in range(2016, 2025):
        (folder / f"{year}.jsonl").write_text("", encoding="utf-8")
    after = {
        "opened_at": "2024-09-17T14:30:00+00:00",
        "open_relative": "invalid_must_never_parse_as_price"
    }
    (folder / "2024.jsonl").write_text(json.dumps(after) + "\n")
    days, c = m.source_blocks(tmp_path)
    assert days == {}
    assert c["original_m5_timestamps_before_embargo"] == 0


def test_before_prices_commit_is_fixed_and_no_live() -> None:
    assert m.PREREG_COMMIT == "4b26a2da961da6f778028835efaa7ea899ebda9d"
    assert m.SYMBOL == "NAS100"
    assert m.PROVIDER_SYMBOL == "USTEC"
    assert m.DEV_END_UTC == datetime(2022, 9, 17, tzinfo=UTC)
    assert m.EMBARGO_UTC == datetime(2024, 9, 17, tzinfo=UTC)
    assert m.STATUS == "RESEARCH_GROSS_NEWS_UNFILTERED_NO_OPERATIONS"
    assert m.MIN_DAYS == 300 and m.MIN_ISO_WEEKS == 52
