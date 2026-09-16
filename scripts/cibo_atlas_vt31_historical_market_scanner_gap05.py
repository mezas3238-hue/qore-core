"""CIBO Atlas historical scanner using consumed gap05 reference semantics.

This is the compatibility layer for the frozen VT-31 consumed ledger. It keeps
all independent-market analysis from the strict scanner, but admits 09:00-10:00
reference hours when the longest missing M1 run is <=5 minutes. The 10:00-11:00
session still requires all 60 M1 bars. This matches the consumed sparse-reference
evidence semantics and exists solely so Atlas can compare all 780 ledger roots.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, cast

import cibo_atlas_vt31_historical_market_scanner as strict
import vt31_r8_sparse_reference_forensics as sparse

from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.cibo_atlas.vt31.historical_market_scanner.gap05.v1"


def analyze_day_gap05(
    partition: str,
    market: str,
    provider: str,
    local_day: date,
    day_bars: tuple[OhlcSnapshot, ...],
) -> strict.MarketDay | None:
    reference = cast(tuple[OhlcSnapshot, ...], sparse._reference_bars(cast(tuple[object, ...], day_bars)))
    session = strict.bars_between(day_bars, (10, 0, 0), (11, 0, 0))
    lifecycle = strict.bars_between(day_bars, (10, 0, 0), (16, 0, 0))
    if len(session) != 60 or not strict.contiguous(session):
        return None
    if not sparse._policy_accepts(cast(tuple[object, ...], reference), "gap05"):
        return None
    ref_high = max(strict.D(bar.high) for bar in reference)
    ref_low = min(strict.D(bar.low) for bar in reference)
    ref_width = ref_high - ref_low
    if ref_width <= 0:
        return None
    side, breach_index, breach_bar, both_sides = strict.first_breach(session, ref_high, ref_low)
    life_complete = len(lifecycle) == 360 and strict.contiguous(lifecycle)
    life_range = (
        (max(strict.D(bar.high) for bar in lifecycle) - min(strict.D(bar.low) for bar in lifecycle))
        / ref_width
        if lifecycle
        else None
    )
    depth = None
    breach_body = None
    close_reentry = None
    opposite_11 = None
    opposite_16 = None
    continuation = None
    reversal_11 = None
    reversal_16 = None
    if side in {"high", "low"} and breach_index is not None and breach_bar is not None:
        depth = (
            (strict.D(breach_bar.high) - ref_high) / ref_width
            if side == "high"
            else (ref_low - strict.D(breach_bar.low)) / ref_width
        )
        breach_body = strict.body_fraction(breach_bar)
        path_11 = session[breach_index:]
        continuation, reversal_11, opposite_11 = strict.directional_path(
            side, path_11, ref_high, ref_low, ref_width
        )
        path_16 = lifecycle[breach_index:] if len(lifecycle) > breach_index else path_11
        _, reversal_16, opposite_16 = strict.directional_path(
            side, path_16, ref_high, ref_low, ref_width
        )
        for relative_index, bar in enumerate(path_11):
            close = strict.D(bar.close)
            reentered = close < ref_high if side == "high" else close > ref_low
            if reentered:
                close_reentry = relative_index
                break
    session_high = max(strict.D(bar.high) for bar in session)
    session_low = min(strict.D(bar.low) for bar in session)
    return strict.MarketDay(
        partition=partition,
        market=market,
        ny_date=local_day.isoformat(),
        provider=provider,
        reference_width=ref_width,
        session_range_to_reference=(session_high - session_low) / ref_width,
        lifecycle_range_to_reference=life_range,
        lifecycle_complete=life_complete,
        first_breach=side,
        first_breach_minute=strict.minute_from_1000(breach_bar) if breach_bar is not None else None,
        first_breach_depth_ref=depth,
        first_breach_body_fraction=breach_body,
        both_sides_by_11=both_sides,
        close_reentry_latency_m1=close_reentry,
        opposite_boundary_hit_by_11=opposite_11,
        opposite_boundary_hit_by_16=opposite_16,
        max_continuation_depth_ref=continuation,
        max_reversal_excursion_ref_by_11=reversal_11,
        max_reversal_excursion_ref_by_16=reversal_16,
        session_close_location_ref=(strict.D(session[-1].close) - ref_low) / ref_width,
        lifecycle_close_location_ref=(strict.D(lifecycle[-1].close) - ref_low) / ref_width
        if lifecycle
        else None,
    )


def load_partition_gap05(partition: str, market: str, path: Path) -> list[strict.MarketDay]:
    series, _, _, _, _, provider = load_market_evidence(path)
    by_day: dict[date, list[OhlcSnapshot]] = defaultdict(list)
    for bar in series:
        by_day[_day(bar.opened_at)].append(bar)
    rows: list[strict.MarketDay] = []
    for local_day, bars in sorted(by_day.items()):
        row = analyze_day_gap05(partition, market, provider, local_day, tuple(bars))
        if row is not None:
            rows.append(row)
    return rows


def build(args: argparse.Namespace) -> dict[str, Any]:
    ledger = strict.load_ledger(cast(Path, args.ledger))
    raw_rows: list[strict.MarketDay] = []
    for partition in strict.PARTITIONS:
        for market in strict.MARKETS:
            raw_rows.extend(
                load_partition_gap05(
                    partition,
                    market,
                    cast(Path, getattr(args, f"{partition}_{market.lower()}")),
                )
            )
    unique: dict[tuple[str, str], strict.MarketDay] = {}
    for row in raw_rows:
        key = (row.market, row.ny_date)
        if key in unique:
            raise ValueError(f"overlapping consumed market day {key}")
        unique[key] = row
    rows = strict.overlay_trader(
        sorted(unique.values(), key=lambda row: (row.ny_date, row.market)), ledger
    )
    overlay_roots = sum(row.trader_root_count for row in rows)
    if overlay_roots != 780:
        raise ValueError(f"gap05 Atlas must cover all 780 ledger roots, got {overlay_roots}")
    by_market = {
        market: [row for row in rows if row.market == market] for market in strict.MARKETS
    }
    reference_histogram: dict[str, dict[str, int]] = {}
    for market in strict.MARKETS:
        histogram: Counter[str] = Counter()
        for partition in strict.PARTITIONS:
            path = cast(Path, getattr(args, f"{partition}_{market.lower()}"))
            series, _, _, _, _, _ = load_market_evidence(path)
            by_day: dict[date, list[OhlcSnapshot]] = defaultdict(list)
            for bar in series:
                by_day[_day(bar.opened_at)].append(bar)
            for bars in by_day.values():
                reference = sparse._reference_bars(cast(tuple[object, ...], tuple(bars)))
                session = strict.bars_between(tuple(bars), (10, 0, 0), (11, 0, 0))
                if len(session) != 60 or not reference:
                    continue
                if sparse._policy_accepts(reference, "gap05"):
                    histogram[f"bars-{len(reference):02d}"] += 1
        reference_histogram[market] = dict(sorted(histogram.items()))
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "research_only": True,
        "selection_prohibited": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "live_authorized": False,
        "production_authorized": False,
        "methodology_family": "ttrades-am-silver-bullet",
        "reference_admission": "gap05-max-consecutive-missing-reference-minutes",
        "session_admission": "strict60-10:00-11:00",
        "market_universe": list(strict.MARKETS),
        "source_partitions": list(strict.PARTITIONS),
        "independent_market_day_count": len(rows),
        "ledger_root_overlay_count": overlay_roots,
        "reference_bar_histogram": reference_histogram,
        "market_summary": {
            market: strict.summarize(by_market[market]) for market in strict.MARKETS
        },
        "trader_outcome_market_contrasts": {
            market: strict.outcome_contrasts(by_market[market]) for market in strict.MARKETS
        },
        "cross_index": strict.cross_index(rows),
        "timing_contract": {
            "market_day_features": "independent-market-observation",
            "trader_outcomes": "post-outcome-research-label-only",
        },
        "interpretation_constraints": [
            "gap05 is an already-consumed data-admission semantic, not a new trading filter",
            "market-day rows are independent of trader acceptance",
            "trader outcomes are post-outcome labels only",
            "no positive contrast is a candidate rule",
            "no fresh holdout was opened",
        ],
    }
    output_dir = cast(Path, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cibo-atlas-vt31-historical-market-scanner-gap05.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    strict.write_csv(output_dir / "cibo-atlas-vt31-market-day-matrix-gap05.csv", rows)
    return payload


def self_test() -> None:
    assert sparse.POLICIES["gap05"] == 5
    strict.self_test()
    print("CIBO Atlas gap05 scanner self-test PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--output-dir", type=Path)
    for partition in strict.PARTITIONS:
        for market in strict.MARKETS:
            parser.add_argument(f"--{partition.replace('_', '-')}-{market.lower()}", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    required = [args.ledger, args.output_dir]
    required.extend(
        getattr(args, f"{partition}_{market.lower()}")
        for partition in strict.PARTITIONS
        for market in strict.MARKETS
    )
    if any(value is None for value in required):
        parser.error("ledger, output-dir and all nine consumed market files are required")
    payload = build(args)
    print(
        json.dumps(
            {
                "days": payload["independent_market_day_count"],
                "roots": payload["ledger_root_overlay_count"],
                "markets": payload["market_summary"],
                "cross_index_complete_days": payload["cross_index"]["complete_three_market_day_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
