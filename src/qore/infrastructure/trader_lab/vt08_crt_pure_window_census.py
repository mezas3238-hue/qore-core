"""Window-level census for VT08 CRT PURE 2Y replay diagnostics."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import timedelta
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    END_EXCLUSIVE,
    START,
    _aggregate,
    _days,
    _segment,
    _trade_from_window,
    load_two_year_m5,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    candidate_direction_from_turtle_soup,
    classify_range_outcome,
)
from qore.infrastructure.traders.crt_pure_timing_policy import (
    NY,
    utc_triplet_windows_for_local_date,
)


def build_window_census(market: CrtPureMarket) -> dict[str, object]:
    bars = load_two_year_m5(market)
    by_time = {bar.opened_at: bar for bar in bars}
    start_day = (START - timedelta(days=1)).astimezone(NY).date()
    end_day = END_EXCLUSIVE.astimezone(NY).date()
    counters: dict[str, Counter[str]] = {
        "1": Counter(),
        "2": Counter(),
    }

    for day in _days(start_day, end_day):
        local_noon = __import__("datetime").datetime(
            day.year, day.month, day.day, 12, tzinfo=NY
        )
        windows = utc_triplet_windows_for_local_date(market, local_noon)
        for timing_index, window in enumerate(windows):
            key = str(timing_index + 1)
            counter = counters[key]
            if not START <= window.candle_3_open < END_EXCLUSIVE:
                counter["outside_window"] += 1
                continue

            counter["eligible_window"] += 1
            c1_m5 = _segment(by_time, window.candle_1_open, window.candle_2_open)
            c2_m5 = _segment(by_time, window.candle_2_open, window.candle_3_open)
            c3_m5 = _segment(by_time, window.candle_3_open, window.window_close)
            if c1_m5 is None:
                counter["missing_c1"] += 1
                continue
            if c2_m5 is None:
                counter["missing_c2"] += 1
                continue
            if c3_m5 is None:
                counter["missing_c3"] += 1
                continue
            counter["complete_window"] += 1

            c1 = _aggregate(c1_m5, window.candle_1_open, window.candle_2_open)
            c2 = _aggregate(c2_m5, window.candle_2_open, window.candle_3_open)
            outcome = classify_range_outcome(
                reference_high=float(c1.high_price),
                reference_low=float(c1.low_price),
                observed_high=float(c2.high_price),
                observed_low=float(c2.low_price),
                observed_close=float(c2.close_price),
            )
            counter[f"outcome_{outcome.value}"] += 1
            direction = candidate_direction_from_turtle_soup(
                reference_high=float(c1.high_price),
                reference_low=float(c1.low_price),
                observed_high=float(c2.high_price),
                observed_low=float(c2.low_price),
                observed_close=float(c2.close_price),
            )
            if direction is None:
                counter["no_direction"] += 1
                continue
            counter[f"direction_{direction.value}"] += 1

            trade = _trade_from_window(
                market=market,
                timing_index=timing_index,
                c1=c1,
                c2=c2,
                c3_m5=c3_m5,
            )
            if trade is None:
                counter["geometry_rejected"] += 1
            else:
                counter["trade_created"] += 1

    return {
        "schema": "qore.vt08.crt_pure.2y_window_census.v1",
        "market": market.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END_EXCLUSIVE.isoformat(),
        "m5_bars_loaded": len(bars),
        "triplets": {key: dict(value) for key, value in counters.items()},
        "research_only": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=[market.value for market in CrtPureMarket])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_window_census(CrtPureMarket(args.market))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("CRT_WINDOW_CENSUS_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
