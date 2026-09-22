"""R2-A minimal-reference Model #1 characterization for VT08 CRT PURE.

R2-A is not canonical CRT and is not a certification candidate.  It is the least-
assumptive deterministic characterization available while RomeoTPT's exact old-level
ownership rule remains source-ambiguous.

Frozen R2-A engineering policies:
- old high/low = confirmed untouched M15 local turning point, swing strength 1;
- a reference is consumed on its first strict breach;
- only the FIRST direction-aligned Model #1 source event inside a parent C3 is eligible;
- if that first source event never body-confirms inside C3, the parent produces no trade;
- no second source event, fallback, re-entry, Journey or KOD entry is allowed;
- confirmation fill = next contiguous M15 open;
- stop = Model #1 source-candle extreme;
- target = frozen R1 C1 50% midpoint;
- expiry = frozen R1 C3 close;
- same-M15 ambiguity = STOP_FIRST.

The one-event rule intentionally prevents unclosed re-entry semantics from leaking into R2-A.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    END_EXCLUSIVE,
    FOLD_1_END,
    START,
    ReplayBar,
    load_two_year_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    Model1LabTrade,
    ParentCrt,
    ReferenceKind,
    ReferencePolicy,
    _confirmation,
    _fold,
    _resolve_trade,
    _summary,
    aggregate_complete_m15,
    build_first_breach_groups,
    build_parent_crts,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2A_MODEL1_MINIMAL_REFERENCE_001"
SCHEMA = "qore.vt08.crt_pure.r2a_model1_minimal_reference.v1"
REFERENCE_POLICY = ReferencePolicy.UNTOUCHED_SWING_STRENGTH_1


def first_eligible_model1_trade(
    *,
    parent: ParentCrt,
    m15_by_time: dict[object, M15Bar],
    breaches: dict[object, tuple[object, ...]],
) -> tuple[Model1LabTrade | None, str]:
    """Use only the first aligned source event; never fall through to a later one."""

    c3_m15 = tuple(
        m15_by_time[opened_at]
        for opened_at in sorted(m15_by_time)
        if parent.c3_opened_at <= opened_at < parent.c3_closed_at
    )
    if not c3_m15:
        return None, "NO_COMPLETE_M15_IN_C3"

    expected_kind = (
        ReferenceKind.OLD_LOW
        if parent.direction is CrtPureCandidateDirection.BULLISH
        else ReferenceKind.OLD_HIGH
    )

    first_group = None
    source_index = -1
    for index, source in enumerate(c3_m15):
        for group in breaches.get(source.opened_at, ()):
            if getattr(group, "kind", None) is expected_kind:
                first_group = group
                source_index = index
                break
        if first_group is not None:
            break

    if first_group is None:
        return None, "NO_DIRECTION_ALIGNED_MODEL1_SOURCE"

    source = c3_m15[source_index]
    confirmed = _confirmation(
        source,
        c3_m15[source_index + 1 :],
        parent.direction,
    )
    if confirmed is None:
        return None, "FIRST_MODEL1_SOURCE_NOT_CONFIRMED"

    confirmation_bar, entry_bar = confirmed
    trade = _resolve_trade(
        parent=parent,
        group=first_group,
        confirmation=confirmation_bar,
        entry_bar=entry_bar,
        c3_m15=c3_m15,
    )
    if trade is None:
        return None, "CONFIRMED_MODEL1_INVALID_RISK_GEOMETRY"

    return (
        replace(
            trade,
            schema=SCHEMA,
            identity=IDENTITY,
        ),
        "TRADE_CREATED",
    )


def run_r2a(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[tuple[Model1LabTrade, ...], dict[str, int], int]:
    parents = build_parent_crts(market, bars)
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_first_breach_groups(m15, REFERENCE_POLICY)

    counters: dict[str, int] = {}
    trades: list[Model1LabTrade] = []
    for parent in parents:
        trade, reason = first_eligible_model1_trade(
            parent=parent,
            m15_by_time=m15_by_time,
            breaches=breaches,
        )
        counters[reason] = counters.get(reason, 0) + 1
        if trade is not None:
            trades.append(trade)

    if len({item.c3_opened_at for item in trades}) != len(trades):
        raise RuntimeError("R2-A invariant violation: more than one trade per parent CRT")

    return tuple(trades), counters, len(parents)


def build_report(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[Model1LabTrade, ...]]:
    trades, counters, parent_count = run_r2a(market, bars)
    report = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "parent_crt_count": parent_count,
        "reference_policy": REFERENCE_POLICY.name,
        "reference_policy_authority": "ENGINEERING_POLICY_MINIMAL_SEMANTIC_TRANSLATION",
        "source_ambiguity_still_open": True,
        "single_source_event_per_parent": True,
        "later_source_fallback_allowed": False,
        "journey_reentry_allowed": False,
        "event_counters": counters,
        "full_2y": _summary(trades),
        "year_1": _summary(_fold(trades, START, FOLD_1_END)),
        "year_2": _summary(_fold(trades, FOLD_1_END, END_EXCLUSIVE)),
        "target_policy": "R1_C1_50_PERCENT_CONTROL",
        "expiry_policy": "R1_C3_CLOSE_CONTROL",
        "same_m15_ambiguity": "STOP_FIRST",
        "research_only": True,
        "candidate_certified": False,
        "source_canonical": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return report, trades


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=[item.value for item in CrtPureMarket])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    bars = load_two_year_m5(market)
    report, trades = build_report(market, bars)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for item in trades:
            handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")
    print("CRT_R2A_MODEL1_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
