"""Schedule-aware BTCUSD replay over the frozen CRT PURE R1 methodology.

Only data-completeness semantics change: missing M5 slots are admissible when the
broker-declared cTrader market calendar says the symbol is closed. Missing bars while
the symbol is open remain fail-closed. No bar is synthesized.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    END_EXCLUSIVE,
    FOLD_1_END,
    PERIOD_MINUTES,
    START,
    AggregatedCandle,
    ReplayBar,
    ReplayTrade,
    _aggregate,
    _days,
    _fold,
    _trade_from_window,
    load_two_year_m5,
    summarize,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_ctrader_market_calendar import (
    CTraderMarketCalendar,
    load_btcusd_ctrader_calendar,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_timing_policy import (
    NY,
    utc_triplet_windows_for_local_date,
)

IDENTITY = "VT08_CRT_PURE_BTCUSD_CTRADER_SCHEDULE_AWARE_R1_001"


def _session_segment(
    by_time: dict[datetime, ReplayBar],
    opened_at: datetime,
    closed_at: datetime,
    calendar: CTraderMarketCalendar,
) -> tuple[tuple[ReplayBar, ...] | None, int, int, int]:
    rows: list[ReplayBar] = []
    scheduled_closed_slots = 0
    missing_open_slots = 0
    closed_slots_with_bar = 0
    cursor = opened_at
    while cursor < closed_at:
        bar = by_time.get(cursor)
        if calendar.is_open_at(cursor):
            if bar is None:
                missing_open_slots += 1
            else:
                rows.append(bar)
        else:
            scheduled_closed_slots += 1
            if bar is not None:
                closed_slots_with_bar += 1
                rows.append(bar)
        cursor += timedelta(minutes=PERIOD_MINUTES)
    if missing_open_slots or not rows:
        return None, scheduled_closed_slots, missing_open_slots, closed_slots_with_bar
    return tuple(rows), scheduled_closed_slots, 0, closed_slots_with_bar


def run_schedule_aware_replay(
    bars: tuple[ReplayBar, ...],
    calendar: CTraderMarketCalendar,
) -> tuple[tuple[ReplayTrade, ...], dict[str, dict[str, int]]]:
    by_time = {bar.opened_at: bar for bar in bars}
    start_day = (START - timedelta(days=1)).astimezone(NY).date()
    end_day = END_EXCLUSIVE.astimezone(NY).date()
    trades: list[ReplayTrade] = []
    counters: dict[str, Counter[str]] = {
        "1": Counter(),
        "2": Counter(),
    }

    for day in _days(start_day, end_day):
        local_noon = datetime(day.year, day.month, day.day, 12, tzinfo=NY)
        windows = utc_triplet_windows_for_local_date(CrtPureMarket.BTCUSD, local_noon)
        for timing_index, window in enumerate(windows):
            key = str(timing_index + 1)
            counter = counters[key]
            if not START <= window.candle_3_open < END_EXCLUSIVE:
                counter["outside_window"] += 1
                continue
            counter["eligible_window"] += 1
            segments: list[tuple[ReplayBar, ...]] = []
            for stage, opened_at, closed_at in (
                ("c1", window.candle_1_open, window.candle_2_open),
                ("c2", window.candle_2_open, window.candle_3_open),
                ("c3", window.candle_3_open, window.window_close),
            ):
                segment, scheduled_closed, missing_open, closed_with_bar = _session_segment(
                    by_time,
                    opened_at,
                    closed_at,
                    calendar,
                )
                counter[f"{stage}_scheduled_closed_slots"] += scheduled_closed
                counter[f"{stage}_missing_open_slots"] += missing_open
                counter[f"{stage}_closed_slots_with_bar"] += closed_with_bar
                if segment is None:
                    counter[f"missing_{stage}"] += 1
                    break
                segments.append(segment)
            if len(segments) != 3:
                continue

            counter["complete_window"] += 1
            c1: AggregatedCandle = _aggregate(
                segments[0],
                window.candle_1_open,
                window.candle_2_open,
            )
            c2: AggregatedCandle = _aggregate(
                segments[1],
                window.candle_2_open,
                window.candle_3_open,
            )
            trade = _trade_from_window(
                market=CrtPureMarket.BTCUSD,
                timing_index=timing_index,
                c1=c1,
                c2=c2,
                c3_m5=segments[2],
            )
            if trade is None:
                counter["no_trade"] += 1
            else:
                counter["trade_created"] += 1
                trades.append(trade)

    return tuple(trades), {key: dict(value) for key, value in counters.items()}


def _triplet_summary(trades: tuple[ReplayTrade, ...], triplet: str) -> dict[str, Any]:
    return summarize(tuple(item for item in trades if item.timing_triplet == triplet))


def build_report(
    bars: tuple[ReplayBar, ...],
    calendar: CTraderMarketCalendar,
) -> tuple[dict[str, Any], tuple[ReplayTrade, ...]]:
    trades, coverage = run_schedule_aware_replay(bars, calendar)
    report = {
        "schema": "qore.vt08.crt_pure.btcusd_ctrader_schedule_aware_r1.v1",
        "identity": IDENTITY,
        "methodology_identity": "VT08_CRT_PURE_2Y_BASELINE_REPLAY_001",
        "data_semantics_change_only": True,
        "schedule_time_zone": calendar.schedule_time_zone,
        "schedule_intervals": [
            {
                "start_second": item.start_second,
                "end_second": item.end_second,
            }
            for item in calendar.intervals
        ],
        "window_coverage": coverage,
        "full_2y": summarize(trades),
        "year_1": summarize(_fold(trades, START, FOLD_1_END)),
        "year_2": summarize(_fold(trades, FOLD_1_END, END_EXCLUSIVE)),
        "triplet_1": {
            "full_2y": _triplet_summary(trades, "1"),
            "year_1": _triplet_summary(
                _fold(trades, START, FOLD_1_END),
                "1",
            ),
            "year_2": _triplet_summary(
                _fold(trades, FOLD_1_END, END_EXCLUSIVE),
                "1",
            ),
        },
        "triplet_2": {
            "full_2y": _triplet_summary(trades, "2"),
            "year_1": _triplet_summary(
                _fold(trades, START, FOLD_1_END),
                "2",
            ),
            "year_2": _triplet_summary(
                _fold(trades, FOLD_1_END, END_EXCLUSIVE),
                "2",
            ),
        },
        "synthetic_bars": False,
        "scheduled_closures_are_not_missing_data": True,
        "observed_bar_overrides_current_schedule_for_historical_evidence": True,
        "missing_during_open_is_fail_closed": True,
        "research_only": True,
        "candidate_certified": False,
    }
    return report, trades


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    bars = load_two_year_m5(CrtPureMarket.BTCUSD)
    calendar = load_btcusd_ctrader_calendar()
    report, trades = build_report(bars, calendar)
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("CRT_CTRADER_SCHEDULE_AWARE_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
