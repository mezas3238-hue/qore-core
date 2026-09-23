"""R2-AI long-window causal opportunity capacity census for VT08 CRT PURE.

This census asks how much opportunity density exists inside the already-built
CRT + Model #1 event stream before the engineering ceiling of one trade attempt
per parent and before the midpoint target geometry gate.

It creates NO trades and evaluates NO PnL.

For every parent it counts:
- aligned independent source events;
- body-confirmed + contiguous-next-bar entry slots;
- structurally valid risk slots (source extreme on correct side of entry);
- midpoint-valid slots (current R2-G/R1 geometry);
- hypothetical capacity at max 1 / 2 / 3 / all slots per parent.

The cap counts are capacity only, not an execution policy. Overlap, lifecycle,
risk budget and OCO must be solved before any multi-entry replay.

Research only. No capital/runtime authority.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    ParentCrt,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    _candidate_pairs,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    build_parent_crts_for_window,
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2AI_LONG_WINDOW_OPPORTUNITY_CAPACITY_001"
SCHEMA = "qore.vt08.crt_pure.r2ai_long_window_opportunity_capacity.v1"
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class MarketWindow:
    market: CrtPureMarket
    start: datetime


WINDOWS: dict[CrtPureMarket, MarketWindow] = {
    CrtPureMarket.AUDUSD: MarketWindow(
        market=CrtPureMarket.AUDUSD,
        start=datetime(2016, 9, 21, 0, 0, tzinfo=UTC),
    ),
    CrtPureMarket.USDJPY: MarketWindow(
        market=CrtPureMarket.USDJPY,
        start=datetime(2014, 9, 21, 0, 0, tzinfo=UTC),
    ),
}


def _structural_risk_valid(
    *,
    parent: ParentCrt,
    source_low: int,
    source_high: int,
    entry: int,
) -> bool:
    if parent.direction is CrtPureCandidateDirection.BULLISH:
        return source_low < entry
    return source_high > entry


def _midpoint_valid(
    *,
    parent: ParentCrt,
    source_low: int,
    source_high: int,
    entry: int,
) -> bool:
    if not _structural_risk_valid(
        parent=parent,
        source_low=source_low,
        source_high=source_high,
        entry=entry,
    ):
        return False
    midpoint = Decimal(parent.c1.high_price + parent.c1.low_price) / Decimal(2)
    if parent.direction is CrtPureCandidateDirection.BULLISH:
        return midpoint > Decimal(entry)
    return midpoint < Decimal(entry)


def _add_capacity(counter: Counter[str], prefix: str, slots: int) -> None:
    counter[f"{prefix}_slot_count"] += slots
    if slots > 0:
        counter[f"parent_with_{prefix}_slot"] += 1
    if slots >= 2:
        counter[f"parent_with_2plus_{prefix}_slots"] += 1
    if slots >= 3:
        counter[f"parent_with_3plus_{prefix}_slots"] += 1
    counter[f"{prefix}_capacity_cap1"] += min(slots, 1)
    counter[f"{prefix}_capacity_cap2"] += min(slots, 2)
    counter[f"{prefix}_capacity_cap3"] += min(slots, 3)
    counter[f"{prefix}_capacity_all"] += slots


def _rate(value: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(value / denominator, 8)


def run_capacity(market: CrtPureMarket) -> dict[str, Any]:
    window = WINDOWS[market]
    bars = load_m5_window(
        market,
        start=window.start,
        end_exclusive=END,
    )
    parents = build_parent_crts_for_window(
        market,
        bars,
        start=window.start,
        end_exclusive=END,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)
    counter: Counter[str] = Counter()

    generation_confirmed: Counter[int] = Counter()
    generation_structural: Counter[int] = Counter()
    generation_midpoint: Counter[int] = Counter()

    for parent in parents:
        counter["parent_count"] += 1
        c3_m15 = _c3_m15(parent, m15_by_time)
        observations = _aligned_sources(
            parent=parent,
            c3_m15=c3_m15,
            breaches=breaches,
        )
        counter["source_event_count"] += len(observations)
        if observations:
            counter["parent_with_source"] += 1
        if len(observations) >= 2:
            counter["parent_with_2plus_sources"] += 1
        if len(observations) >= 3:
            counter["parent_with_3plus_sources"] += 1

        pairs = _candidate_pairs(
            parent=parent,
            observations=observations,
            c3_m15=c3_m15,
        )

        structural_slots = 0
        midpoint_slots = 0
        for observation, _, entry_bar in pairs:
            generation = observations.index(observation) + 1
            generation_confirmed[generation] += 1
            source = observation.group.source_candle
            entry = entry_bar.open_price

            if _structural_risk_valid(
                parent=parent,
                source_low=source.low_price,
                source_high=source.high_price,
                entry=entry,
            ):
                structural_slots += 1
                generation_structural[generation] += 1

            if _midpoint_valid(
                parent=parent,
                source_low=source.low_price,
                source_high=source.high_price,
                entry=entry,
            ):
                midpoint_slots += 1
                generation_midpoint[generation] += 1

        _add_capacity(counter, "confirmed", len(pairs))
        _add_capacity(counter, "structural", structural_slots)
        _add_capacity(counter, "midpoint", midpoint_slots)

    years = END.year - window.start.year
    parent_count = counter["parent_count"]

    def capacity(prefix: str) -> dict[str, Any]:
        total = counter[f"{prefix}_slot_count"]
        return {
            "slots": total,
            "slots_per_year": round(total / years, 8),
            "parents_with_slot": counter[f"parent_with_{prefix}_slot"],
            "parents_with_2plus_slots": counter[
                f"parent_with_2plus_{prefix}_slots"
            ],
            "parents_with_3plus_slots": counter[
                f"parent_with_3plus_{prefix}_slots"
            ],
            "parent_coverage": _rate(
                counter[f"parent_with_{prefix}_slot"],
                parent_count,
            ),
            "cap1": counter[f"{prefix}_capacity_cap1"],
            "cap1_per_year": round(
                counter[f"{prefix}_capacity_cap1"] / years,
                8,
            ),
            "cap2": counter[f"{prefix}_capacity_cap2"],
            "cap2_per_year": round(
                counter[f"{prefix}_capacity_cap2"] / years,
                8,
            ),
            "cap3": counter[f"{prefix}_capacity_cap3"],
            "cap3_per_year": round(
                counter[f"{prefix}_capacity_cap3"] / years,
                8,
            ),
            "all": counter[f"{prefix}_capacity_all"],
            "all_per_year": round(
                counter[f"{prefix}_capacity_all"] / years,
                8,
            ),
        }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "window_start": window.start.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "years": years,
        "diagnostics": dict(counter),
        "source_events": {
            "count": counter["source_event_count"],
            "per_year": round(counter["source_event_count"] / years, 8),
            "parents_with_source": counter["parent_with_source"],
            "parents_with_2plus_sources": counter["parent_with_2plus_sources"],
            "parents_with_3plus_sources": counter["parent_with_3plus_sources"],
        },
        "confirmed_capacity": capacity("confirmed"),
        "structural_risk_capacity": capacity("structural"),
        "midpoint_capacity": capacity("midpoint"),
        "generation_confirmed": dict(sorted(generation_confirmed.items())),
        "generation_structural_valid": dict(
            sorted(generation_structural.items())
        ),
        "generation_midpoint_valid": dict(sorted(generation_midpoint.items())),
        "one_trade_per_parent_is_current_engineering_ceiling": True,
        "cap_counts_are_not_execution_policy": True,
        "multi_entry_lifecycle_not_yet_authorized": True,
        "pnl_evaluated": False,
        "trades_created": 0,
        "methodology_mutated": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=[item.value for item in WINDOWS])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    report = run_capacity(market)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print("CRT_R2AI_CAPACITY_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
