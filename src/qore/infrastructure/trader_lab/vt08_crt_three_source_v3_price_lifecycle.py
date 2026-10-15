"""Read-only V3 lifecycle: frozen third-candle events, first later M5 barrier.

Registered in docs/research/VT08_CRT_THREE_SOURCE_V3_PRICE_LIFECYCLE_PREREG_2026-10-15.md.
All results are source-price observations, NOT trades, lots, PnL or certified edge.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_pure_original_atlas_reader import (
    load_atlas_vt08_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_v1_full_h4_census import (
    H4,
    M5,
    _aggregate,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_v2_full_h4_census import (
    M15,
    _m15_at,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_v2_price_lifecycle import (
    observe_price_only_path,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_v3_confirmed_h4_census import (
    POLICY_ID,
    full_utc_h4_v3_census,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

SCHEMA = "qore.vt08.crt_three_source.v3.price_only_lifecycle.dev.v1"


def evaluate_frozen_v3_price_lifecycle(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Only AFTER exact source case freeze observe first barrier before H4 C3 end."""
    census, all_rows = full_utc_h4_v3_census(market, bars)
    m5 = {bar.opened_at.astimezone(UTC): bar for bar in bars}
    if len(m5) != len(bars):
        raise ValueError("original M5 duplicated")
    cases = tuple(
        event for event in all_rows
        if event["conceptual_state"] == "CONCEPTUAL_CANDIDATE_V3"
    )
    if len(cases) != census["state_counts"].get("CONCEPTUAL_CANDIDATE_V3", 0):
        raise ValueError("V3 source count disagrees with freeze")
    ledger: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    years: dict[str, Counter[str]] = defaultdict(Counter)
    unique: set[str] = set()
    for event in cases:
        if event["policy_id"] != POLICY_ID:
            raise ValueError("source policy identity mutated")
        if event["not_a_trade"] is not True or not event["no_sizing_or_capital_authority"]:
            raise ValueError("price-only candidate claims capital/order authority")
        event_id = event["source_event_id"]
        if event_id in unique:
            raise ValueError("duplicate V3 candidate ID")
        unique.add(event_id)
        decision = datetime.fromisoformat(event["decision_clock_utc"])
        c3_open = datetime.fromisoformat(event["c3_H4_opened_at_utc"])
        parent_c1_started = c3_open - 2 * H4
        c1_rows = tuple(
            m5.get(parent_c1_started + i * M5) for i in range(48)
        )
        if any(bar is None for bar in c1_rows):
            raise ValueError("frozen H4 C1 context lacks real original M5")
        c1 = _aggregate(tuple(bar for bar in c1_rows if bar is not None))
        source = _m15_at(m5, decision - 2 * M15)
        if source is None:
            raise ValueError("missing V3 source M15 when reconciling frozen event")
        direction = event["parent_direction"]
        if direction not in ("BULLISH", "BEARISH"):
            raise ValueError("unknown source direction")
        invalidation = (
            source["low_relative"] if direction == "BULLISH"
            else source["high_relative"]
        )
        if event["structural_invalidation_price_if_candidate"] != str(invalidation):
            raise ValueError("V3 source wick invalidation changed")
        double_target = c1["high_relative"] + c1["low_relative"]
        outcome, first_hit, observed = observe_price_only_path(
            direction=direction,
            decision_at=decision,
            c3_open=c3_open,
            invalidation_relative=invalidation,
            target_double_relative=double_target,
            m5=m5,
        )
        row = {
            "schema": SCHEMA,
            "policy_id": POLICY_ID,
            "market": market.value,
            "source_event_id": event_id,
            "c3_H4_opened_at_utc": c3_open.isoformat(),
            "decision_clock_utc": decision.isoformat(),
            "year_utc": str(c3_open.year),
            "source_direction": direction,
            "source_m15_invalidating_extreme_relative": invalidation,
            "fixed_parent_h4_target_twice_relative": double_target,
            "price_path_outcome": outcome,
            "first_hit_opened_at_utc": first_hit,
            "observed_m5_after_decision": observed,
            "not_a_trade": True,
            "no_PnL_or_sizing": True,
            "not_fresh_OOS": True,
        }
        ledger.append(row)
        counts[outcome] += 1
        years[str(c3_open.year)][outcome] += 1
    if len(ledger) != len(cases) or len(unique) != len(cases):
        raise ValueError("frozen source event reconciliation lost candidates")
    summary = {
        "schema": SCHEMA,
        "policy_id": POLICY_ID,
        "market": market.value,
        "original_m5_count": len(bars),
        "parent_h4_contexts": census["complete_h4_c1_c2_contexts"],
        "v3_source_candidates": len(cases),
        "v3_price_path_reconciled": len(ledger),
        "outcomes": dict(sorted(counts.items())),
        "by_year": {k: dict(sorted(v.items())) for k, v in sorted(years.items())},
        "price_only_not_broker_fills": True,
        "no_PnL_or_sizing": True,
        "not_fresh_OOS": True,
        "source_GM1_pass": False,
        "cognitive_GM3_pass": False,
        "methodological_GM5_issued": False,
        "GLOBAL_CERTIFIED": False,
    }
    return summary, tuple(ledger)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("market", choices=("AUDUSD", "USDJPY"))
    ap.add_argument("atlas_root", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    market = CrtPureMarket(args.market)
    bars, provenance = load_atlas_vt08_m5(market, args.atlas_root)
    summary, ledger = evaluate_frozen_v3_price_lifecycle(market, bars)
    summary["original_source_provenance"] = provenance
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "v3-price-lifecycle-summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n"
    )
    with (args.output / "v3-price-lifecycle-ledger.jsonl").open("w") as fh:
        for item in ledger:
            fh.write(json.dumps(item, sort_keys=True) + "\n")
    print(json.dumps({
        k: v for k, v in summary.items() if k != "original_source_provenance"
    }, sort_keys=True))


if __name__ == "__main__":
    main()
