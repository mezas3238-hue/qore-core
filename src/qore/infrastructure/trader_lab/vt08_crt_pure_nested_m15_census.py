"""Preregistered N1 micro-CRT M15 census inside H4-C3, original QORE M5 only.

Counts hypotheses, not trades. SpeculatorFL/TraderFlameseN secondary nested
CRT concept; exact three-bar confirmation is QORE research operationalization,
not RomeoTPT certified Model #1. No PnL, risk, sizing or broker operations.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    FOLD_1_END,
    ReplayBar,
    _midpoint,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_later_source_forensics import (
    audit_88_original_cases,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_original_atlas_reader import (
    load_atlas_vt08_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15,
    M15Bar,
    aggregate_complete_m15,
    build_parent_crts,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    run_r2c,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

SCHEMA = "qore.vt08.crt_pure.n1_micro_crt_nested_m15_census.v1"


def micro_crt_direction(
    c1: M15Bar, c2: M15Bar, c3: M15Bar
) -> CrtPureCandidateDirection | None:
    """Only a CLOSED micro C1/C2/C3 can confirm the preregistered N1 pattern."""
    if c2.opened_at != c1.closed_at or c3.opened_at != c2.closed_at:
        return None
    if c1.low_price >= c1.high_price:
        return None
    swept_low = c2.low_price < c1.low_price
    swept_high = c2.high_price > c1.high_price
    if swept_low == swept_high:  # no sweep or two-sided sweep, avoid hindsight
        return None
    if not (c1.low_price <= c2.close_price <= c1.high_price):
        return None
    midpoint_twice = c1.low_price + c1.high_price
    if swept_low and 2 * c3.close_price > midpoint_twice:
        return CrtPureCandidateDirection.BULLISH
    if swept_high and 2 * c3.close_price < midpoint_twice:
        return CrtPureCandidateDirection.BEARISH
    return None


def census_micro_crt(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    if market is CrtPureMarket.BTCUSD:
        raise ValueError("BTCUSD is frozen")
    old_forensic, old_cases = audit_88_original_cases(market, bars)
    old_88 = {record["parent_c3_opened_at"] for record in old_cases}
    old_trades, _, old_parent_count = run_r2c(market, bars)
    old_traded = {trade.c3_opened_at for trade in old_trades}
    parents = build_parent_crts(market, bars)
    if len(parents) != old_parent_count:
        raise RuntimeError("original R2C parent count drifted")
    if len(old_88) != old_forensic["forensic_parent_cases"]:
        raise RuntimeError("rejected case identity duplicate")
    m15_by_time = {b.opened_at: b for b in aggregate_complete_m15(bars)}
    ledger: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    parent_hits: Counter[str] = Counter()
    rejected_88_hits: set[str] = set()
    for parent in parents:
        key = parent.c3_opened_at.isoformat()
        slots = int((parent.c3_closed_at - parent.c3_opened_at) / M15)
        sequence = tuple(m15_by_time.get(parent.c3_opened_at + i * M15)
                         for i in range(slots))
        if any(b is None for b in sequence):
            raise RuntimeError("complete parent H4-C3 has missing M15")
        observed = tuple(b for b in sequence if b is not None)
        counts["PARENT_H4_TURTLE_SOUP"] += 1
        for index in range(len(observed) - 2):
            c1, c2, c3 = observed[index:index + 3]
            direction = micro_crt_direction(c1, c2, c3)
            counts["THREE_M15_NESTED_WINDOWS_OBSERVED"] += 1
            if direction is None:
                continue
            parent_hits[key] += 1
            if key in old_88:
                rejected_88_hits.add(key)
                counts["MICRO_EVENTS_IN_88_REJECTED_PARENTS"] += 1
            alignment = (
                "SAME_H4_DIRECTION" if direction is parent.direction
                else "OPPOSITE_H4_DIRECTION"
            )
            counts[alignment] += 1
            phase = (
                "PERIOD_1" if c3.opened_at < FOLD_1_END else "PERIOD_2"
            )
            counts[phase] += 1
            next_bar = (
                observed[index + 3] if index + 3 < len(observed) else None
            )
            executable_clock = (
                next_bar is not None and next_bar.opened_at == c3.closed_at
            )
            counts["HAS_NEXT_M15_OPEN_WITHIN_H4_C3" if executable_clock
                   else "NO_NEXT_BAR_IN_PARENT"] += 1
            if key in old_traded:
                counts["MICRO_EVENT_WHERE_OLD_R2C_TRADED"] += 1
            else:
                counts["MICRO_EVENT_WHERE_OLD_R2C_REJECTED"] += 1
            original_target = _midpoint(
                parent.c1.high_price, parent.c1.low_price
            )
            before_close = observed[:index+3]
            old_target_touched = any(
                b.high_price >= original_target
                if parent.direction is CrtPureCandidateDirection.BULLISH
                else b.low_price <= original_target
                for b in before_close
            )
            if old_target_touched:
                counts["OLD_H4_C1_MIDPOINT_TOUCHED_BEFORE_MICRO_DECISION"] += 1
            ledger.append({
                "market": market.value,
                "parent_c3_opened_at": key,
                "parent_direction": parent.direction.value,
                "parent_first_r2c_trade_exists": key in old_traded,
                "parent_belongs_to_previous_88": key in old_88,
                "parent_original_c1_high_relative": parent.c1.high_price,
                "parent_original_c1_low_relative": parent.c1.low_price,
                "micro_id": (
                    market.value + ":" + c1.opened_at.isoformat() + ":"
                    + c2.opened_at.isoformat()
                ),
                "micro_direction": direction.value,
                "micro_parent_alignment": alignment,
                "micro_c1_opened_at": c1.opened_at.isoformat(),
                "micro_c1_high_relative": c1.high_price,
                "micro_c1_low_relative": c1.low_price,
                "micro_c2_opened_at": c2.opened_at.isoformat(),
                "micro_c2_high_relative": c2.high_price,
                "micro_c2_low_relative": c2.low_price,
                "micro_c2_close_relative": c2.close_price,
                "micro_c3_opened_at": c3.opened_at.isoformat(),
                "micro_c3_close_relative": c3.close_price,
                "micro_decision_known_at": c3.closed_at.isoformat(),
                "prospective_next_m15_opened_at": (
                    next_bar.opened_at.isoformat() if executable_clock and next_bar
                    else None
                ),
                "own_micro_c1_midpoint_relative": str(
                    _midpoint(c1.high_price, c1.low_price)
                ),
                "old_h4_midpoint_pre_touched": old_target_touched,
                "family_authority": "LEVEL_B_NESTED_CONCEPT_QORE_N1_DEFINITION",
                "original_romeo_model1_certified": False,
                "is_trade": False,
            })
    n = len(ledger)
    if n != counts["SAME_H4_DIRECTION"] + counts["OPPOSITE_H4_DIRECTION"]:
        raise RuntimeError("micro/parent direction partition incomplete")
    if n != counts["PERIOD_1"] + counts["PERIOD_2"]:
        raise RuntimeError("temporal partitions incomplete")
    if n != counts["HAS_NEXT_M15_OPEN_WITHIN_H4_C3"] + counts["NO_NEXT_BAR_IN_PARENT"]:
        raise RuntimeError("execution clock partitions incomplete")
    if any(v > old_parent_count for v in (len(parent_hits), len(rejected_88_hits))):
        raise RuntimeError("uniqueness of nested parent identities violated")
    if len({r["micro_id"] for r in ledger}) != len(ledger):
        raise RuntimeError("duplicate micro event identity")
    return {
        "schema": SCHEMA,
        "market": market.value,
        "replay_source": "QORE_NATIVE_ORIGINAL_M5",
        "prereg": "docs/research/VT08_CRT_PURE_NESTED_M15_SOURCE_PREREG_2026-10-14.md",
        "original_parent_h4": old_parent_count,
        "original_r2c_trades_unchanged": len(old_trades),
        "original_88_later_source_cases_unchanged": len(old_88),
        "candidate_micro_n1_events_NOT_TRADES": n,
        "unique_h4_parents_with_candidate": len(parent_hits),
        "unique_previously_rejected_88_parents_with_micro": len(rejected_88_hits),
        "multiple_micro_per_parent_count": sum(v > 1 for v in parent_hits.values()),
        "counts": dict(sorted(counts.items())),
        "posthoc_performance_selection": False,
        "return_or_R_computed": False,
        "trade_entry_created": False,
        "source_family_certified": False,
        "broker_execution_authorized": False,
        "sizing_or_volume_authorized": False,
    }, tuple(ledger)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("market", choices=("AUDUSD", "USDJPY"))
    p.add_argument("source_root", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    market = CrtPureMarket(a.market)
    bars, provenance = load_atlas_vt08_m5(market, a.source_root)
    report, ledger = census_micro_crt(market, bars)
    report["source_provenance"] = provenance
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / "nested-m15-census.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (a.output / "nested-m15-ledger.jsonl").open("w", encoding="utf-8") as f:
        for x in ledger:
            f.write(json.dumps(x, sort_keys=True) + "\n")
    print("VT08_NESTED_M15_CENSUS=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
