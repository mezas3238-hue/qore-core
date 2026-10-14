"""Independent VT08 density *root-cause* census on original QORE M5 data.

Does NOT generate any alternative trades. Distinguishes observed CRT scope
from R2-C's engineering restrictions, especially FIRST_SOURCE_ONLY.
Source role: RomeoTPT primary; SpeculatorFL and TraderFlameseN secondary.
The ability to identify later-source candidates is NOT permission to trade them.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    END_EXCLUSIVE,
    START,
    ReplayBar,
    _aggregate,
    _days,
    _midpoint,
    _segment,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_original_atlas_reader import (
    load_atlas_vt08_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    ParentCrt,
    ReferenceKind,
    _confirmation,
    _parent_direction,
    aggregate_complete_m15,
    build_parent_crts,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
    first_r2c_trade,
    run_r2c,
)
from qore.infrastructure.traders.crt_pure_identity import (
    CrtPureCandidateDirection,
    CrtPureMarket,
)
from qore.infrastructure.traders.crt_pure_timing_policy import (
    NY,
    utc_triplet_windows_for_local_date,
)

SCHEMA = "qore.vt08.crt_pure.r2c_density_root_cause_audit.v1"
M15 = timedelta(minutes=15)


def scheduled_parent_census(
    market: CrtPureMarket, bars: tuple[ReplayBar, ...]
) -> dict[str, int]:
    """Account for every scheduled C3, including M5 missing before parent gate."""
    by_time = {bar.opened_at: bar for bar in bars}
    if len(by_time) != len(bars):
        raise ValueError("duplicate M5 timestamps in replay input")
    seen: Counter[str] = Counter()
    first_day = (START - timedelta(days=1)).astimezone(NY).date()
    last_day = END_EXCLUSIVE.astimezone(NY).date()
    for day in _days(first_day, last_day):
        local_noon = datetime(day.year, day.month, day.day, 12, tzinfo=NY)
        for win in utc_triplet_windows_for_local_date(market, local_noon):
            if not START <= win.candle_3_open < END_EXCLUSIVE:
                continue
            seen["C3_SCHEDULED"] += 1
            c1 = _segment(by_time, win.candle_1_open, win.candle_2_open)
            c2 = _segment(by_time, win.candle_2_open, win.candle_3_open)
            c3 = _segment(by_time, win.candle_3_open, win.window_close)
            if c1 is None:
                seen["MISSING_COMPLETE_C1_M5"] += 1
            if c2 is None:
                seen["MISSING_COMPLETE_C2_M5"] += 1
            if c3 is None:
                seen["MISSING_COMPLETE_C3_M5"] += 1
            if c1 is None or c2 is None or c3 is None:
                seen["PARENT_REJECTED_INCOMPLETE_M5"] += 1
                continue
            seen["ALL_THREE_H4_CANDLES_COMPLETE"] += 1
            a = _aggregate(c1, win.candle_1_open, win.candle_2_open)
            b = _aggregate(c2, win.candle_2_open, win.candle_3_open)
            if _parent_direction(a, b) is None:
                seen["C2_NOT_CURRENT_ONE_SIDED_TURTLE_SOUP"] += 1
            else:
                seen["C2_MATCHES_CURRENT_TURTLE_SOUP"] += 1

    counts = dict(sorted(seen.items()))
    if counts.get("C3_SCHEDULED", 0) != (
        counts.get("PARENT_REJECTED_INCOMPLETE_M5", 0)
        + counts.get("ALL_THREE_H4_CANDLES_COMPLETE", 0)
    ):
        raise RuntimeError("scheduled window partition mismatch")
    if counts.get("ALL_THREE_H4_CANDLES_COMPLETE", 0) != (
        counts.get("C2_NOT_CURRENT_ONE_SIDED_TURTLE_SOUP", 0)
        + counts.get("C2_MATCHES_CURRENT_TURTLE_SOUP", 0)
    ):
        raise RuntimeError("H4 C2 category partition mismatch")
    return counts


def _geometry_valid(
    parent: ParentCrt,
    source: M15Bar,
    entry: M15Bar,
) -> bool:
    """Same R2-C structural inequalities; no economics and no order sizing."""
    target = _midpoint(parent.c1.high_price, parent.c1.low_price)
    if parent.direction is CrtPureCandidateDirection.BULLISH:
        return source.low_price < entry.open_price and target > Decimal(entry.open_price)
    return source.high_price > entry.open_price and target < Decimal(entry.open_price)


def density_root_cause_report(
    market: CrtPureMarket, bars: tuple[ReplayBar, ...]
) -> dict[str, Any]:
    if market is CrtPureMarket.BTCUSD:
        raise ValueError("BTCUSD frozen")
    scheduled = scheduled_parent_census(market, bars)
    trades, reasons, parent_count = run_r2c(market, bars)
    if scheduled["C2_MATCHES_CURRENT_TURTLE_SOUP"] != parent_count:
        raise RuntimeError("independent H4 census does not match original R2-C parents")

    parents = build_parent_crts(market, bars)
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)
    counts: Counter[str] = Counter()
    illustrative_later_cases: list[dict[str, Any]] = []

    for parent in parents:
        first_trade, first_reason = first_r2c_trade(
            parent=parent, m15_by_time=m15_by_time, breaches=breaches
        )
        expected_kind = (
            ReferenceKind.OLD_LOW
            if parent.direction is CrtPureCandidateDirection.BULLISH
            else ReferenceKind.OLD_HIGH
        )
        slots = int((parent.c3_closed_at - parent.c3_opened_at) / M15)
        c3_m15 = tuple(
            m15_by_time[parent.c3_opened_at + i * M15]
            for i in range(slots)
            if parent.c3_opened_at + i * M15 in m15_by_time
        )
        if len(c3_m15) != slots:
            raise RuntimeError("R2-C complete C3 M5 unexpectedly has missing M15")
        aligned_sources = [
            (index, group)
            for index, candle in enumerate(c3_m15)
            for group in breaches.get(candle.opened_at, ())
            if group.kind is expected_kind
        ]
        counts["TOTAL_PARENT_CR_TURTLE_SOUP"] += 1
        counts["DIRECTION_ALIGNED_M15_SOURCE_CANDLES"] += len(aligned_sources)
        if aligned_sources:
            counts["PARENTS_WITH_ANY_ALIGNED_M15_SOURCE"] += 1
        if len(aligned_sources) > 1:
            counts["PARENTS_WITH_MULTIPLE_ALIGNED_SOURCE_CANDLES"] += 1
            counts["SECOND_AND_LATER_SOURCE_EVENTS"] += len(aligned_sources) - 1

        confirmable = 0
        geometry_valid = 0
        later_valid = 0
        for i, (source_index, group) in enumerate(aligned_sources):
            source = c3_m15[source_index]
            if group.source_candle.opened_at != source.opened_at:
                raise RuntimeError("breach and source candle mismatched")
            confirmed = _confirmation(
                source, c3_m15[source_index + 1 :], parent.direction
            )
            if confirmed is None:
                continue
            confirmable += 1
            if not _geometry_valid(parent, source, confirmed[1]):
                continue
            geometry_valid += 1
            if i > 0:
                later_valid += 1

        if confirmable:
            counts["PARENTS_WITH_ANY_CONFIRMABLE_M15_SOURCE"] += 1
        if geometry_valid:
            counts["PARENTS_WITH_ANY_GEOMETRY_VALID_M15_SOURCE"] += 1
        if first_reason == "TRADE_CREATED":
            if first_trade is None:
                raise RuntimeError("R2-C trade count differs from reason")
            counts["PARENTS_WITH_FIRST_SOURCE_TRADE"] += 1
        else:
            if first_trade is not None:
                raise RuntimeError("R2-C returned inconsistent first-source rejection")
            if geometry_valid > 0:
                counts["PARENTS_REJECTED_BY_FIRST_SOURCE_WITH_LATER_VALID_CANDIDATE"] += 1
                if len(illustrative_later_cases) < 10:
                    illustrative_later_cases.append({
                        "parent_c3_opened_at": parent.c3_opened_at.isoformat(),
                        "parent_direction": parent.direction.value,
                        "original_rejection_reason": first_reason,
                        "total_aligned_source_candles": len(aligned_sources),
                        "later_valid_candidates": later_valid,
                        "research_label": "ALTERNATIVE_M15_SOURCE_NOT_AUTHORIZED_ENTRY",
                    })
        if first_reason in (
            "FIRST_CLOSE_UNMITIGATED_SOURCE_NOT_CONFIRMED",
            "CONFIRMED_SOURCE_INVALID_RISK_GEOMETRY",
        ) and aligned_sources:
            counts["FIRST_SOURCE_REJECTED_WITH_ANOTHER_ALIGNED_SOURCE"] += (
                len(aligned_sources) > 1
            )
    if counts["PARENTS_WITH_FIRST_SOURCE_TRADE"] != len(trades):
        raise RuntimeError("original R2-C count changed during density audit")
    if counts["TOTAL_PARENT_CR_TURTLE_SOUP"] != parent_count:
        raise RuntimeError("parent CRT reconciliation failed")
    if counts["PARENTS_WITH_ANY_GEOMETRY_VALID_M15_SOURCE"] < len(trades):
        raise RuntimeError("census somehow loses confirmed original R2-C trades")

    return {
        "schema": SCHEMA,
        "market": market.value,
        "source": "ORIGINAL_QORE_NATIVE_M5",
        "first_stage_h4": scheduled,
        "r2c_first_source_rejection_counts": reasons,
        "source_stage_m15": dict(sorted(counts.items())),
        "later_source_cases_for_visual_source_adjudication": illustrative_later_cases,
        "observed_r2c_trades": len(trades),
        "sample_start": START.isoformat(),
        "sample_planned_end_exclusive": END_EXCLUSIVE.isoformat(),
        "two_parent_triplets_per_day": True,
        "only_scheduled_H4_triples": True,
        "old_level_strength1_is_QORE_engineering": True,
        "one_trade_max_per_parent_is_QORE_engineering": True,
        "first_aligned_source_ONLY_is_QORE_engineering": True,
        "later_candidates_are_not_trades": True,
        "source_ownership_canonical_certified": False,
        "a_trader_can_run_multiple_sources": False,
        "no_trade_rewrites": True,
        "no_PnL_generated_from_alternative_candidates": True,
        "no_broker_orders": True,
        "no_trader_position_sizing": True,
        "no_certification": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=("AUDUSD", "USDJPY"))
    parser.add_argument("source_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    market = CrtPureMarket(args.market)
    bars, provenance = load_atlas_vt08_m5(market, args.source_root)
    report = density_root_cause_report(market, bars)
    report["source_provenance"] = provenance
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "density-root-cause.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("VT08_DENSITY_ROOT_CAUSE=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
