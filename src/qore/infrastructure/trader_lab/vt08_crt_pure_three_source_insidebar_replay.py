"""Read-only VT08 comparison of a secondary-source inside-bar context.

QORE R2-C replay is the unchanged engineering control. SpeculatorFL and
TraderFlameseN explicitly propose inside bars as CRT selection context; this
experiment only annotates that one observable without modifying entry, stop,
target, lotage, trade volume, or execution. The two secondary accounts are
not independent methodological proofs. No source-certification or production
promotion can be inferred from these exploratory statistics.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
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
    _fold,
    _summary,
    aggregate_complete_m15,
    build_parent_crts,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    run_r2c,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_3SOURCE_INSIDE_BAR_REPLAY_EXPLORATORY_001"
SCHEMA = "qore.vt08.crt_pure.3source_inside_bar_context_replay.v1"
M15 = timedelta(minutes=15)


@dataclass(frozen=True, slots=True)
class C1InsideBarObservation:
    parent_c3_opened_at: str
    observed_at: str
    inside_bar_count: int
    eligible_m15_count: int
    complete_c1_m15: bool
    inside_bar_context: bool
    source_status: str = "LEVEL_B_ENGINEERING_OPERATIONALIZATION"


def count_inside_m15_bars(
    bars: tuple[M15Bar, ...],
    *,
    c1_opened_at: datetime,
    c1_closed_at: datetime,
) -> C1InsideBarObservation:
    """Count strict consecutive M15 inside bars wholly known by C1 close.

    This is ONE predeclared engineering interpretation of a Level-B protocol,
    NOT RomeoTPT's rule. Gaps prevent classification instead of manufacturing
    an 'absence of inside bars'. At least one strict containment is the binary
    context contrast; do not optimize a threshold based on results.
    """
    if c1_closed_at <= c1_opened_at:
        raise ValueError("C1 window must have positive duration")
    selected = tuple(
        bar for bar in bars if c1_opened_at <= bar.opened_at < c1_closed_at
    )
    expected_count = (c1_closed_at - c1_opened_at) / M15
    complete = (
        expected_count == len(selected)
        and all(
            bar.opened_at == c1_opened_at + index * M15
            for index, bar in enumerate(selected)
        )
    )
    inside_count = sum(
        right.high_price < left.high_price
        and right.low_price > left.low_price
        for left, right in zip(selected[:-1], selected[1:])
    ) if complete else 0
    return C1InsideBarObservation(
        parent_c3_opened_at="",
        observed_at=c1_closed_at.isoformat(),
        inside_bar_count=inside_count,
        eligible_m15_count=len(selected),
        complete_c1_m15=complete,
        inside_bar_context=complete and inside_count >= 1,
    )


def _trade_groups(
    trades: tuple[Model1LabTrade, ...],
    observed: dict[str, C1InsideBarObservation],
) -> dict[str, tuple[Model1LabTrade, ...]]:
    if any(trade.c3_opened_at not in observed for trade in trades):
        raise RuntimeError("Replay parent not found; cannot attribute inside-bar context")
    unknown = tuple(
        trade for trade in trades
        if not observed[trade.c3_opened_at].complete_c1_m15
    )
    has = tuple(
        trade for trade in trades
        if observed[trade.c3_opened_at].complete_c1_m15
        and observed[trade.c3_opened_at].inside_bar_context
    )
    no = tuple(
        trade for trade in trades
        if observed[trade.c3_opened_at].complete_c1_m15
        and not observed[trade.c3_opened_at].inside_bar_context
    )
    if len(unknown) + len(has) + len(no) != len(trades):
        raise RuntimeError("Partition is not exhaustive")
    if len({id(item) for item in (*unknown, *has, *no)}) != len(trades):
        raise RuntimeError("Overlapping trade partition")
    return {
        "R2C_UNCHANGED_CONTROL": trades,
        "LEVEL_B_INSIDE_BAR_PRESENT": has,
        "LEVEL_B_INSIDE_BAR_ABSENT": no,
        "UNKNOWN_C1_DATA": unknown,
    }


def _folded(groups: dict[str, tuple[Model1LabTrade, ...]]) -> dict[str, Any]:
    return {
        group: {
            "full": _summary(trades),
            "period_1": _summary(_fold(trades, START, FOLD_1_END)),
            "period_2": _summary(_fold(trades, FOLD_1_END, END_EXCLUSIVE)),
        }
        for group, trades in groups.items()
    }


def compare_three_sources_inside_bar_context(
    market: CrtPureMarket, bars: tuple[ReplayBar, ...]
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Run the predeclared control once, then annotate past-known C1 context.

    A group is a subset of unchanged trade outcomes, not a newly executed order.
    Does not infer source hierarchy, causally verify old CRTH, or use CSD/PD arrays.
    """
    if market is CrtPureMarket.BTCUSD:
        raise ValueError("BTCUSD freeze: this replay is limited to AUDUSD/USDJPY")
    trades, counters, parent_count = run_r2c(market, bars)
    parents = build_parent_crts(market, bars)
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    c1_observations: dict[str, C1InsideBarObservation] = {}

    for parent in parents:
        expected_bars = int((parent.c1.closed_at - parent.c1.opened_at) / M15)
        c1_m15 = tuple(
            m15_by_time[parent.c1.opened_at + index * M15]
            for index in range(expected_bars)
            if parent.c1.opened_at + index * M15 in m15_by_time
        )
        observation = count_inside_m15_bars(
            c1_m15,
            c1_opened_at=parent.c1.opened_at,
            c1_closed_at=parent.c1.closed_at,
        )
        key = parent.c3_opened_at.isoformat()
        if key in c1_observations:
            raise RuntimeError("duplicate parent C3 identity; cannot group causal source")
        c1_observations[key] = C1InsideBarObservation(
            parent_c3_opened_at=key,
            observed_at=observation.observed_at,
            inside_bar_count=observation.inside_bar_count,
            eligible_m15_count=observation.eligible_m15_count,
            complete_c1_m15=observation.complete_c1_m15,
            inside_bar_context=observation.inside_bar_context,
        )

    groups = _trade_groups(trades, c1_observations)
    diagnostics = tuple(
        {
            "market": trade.market,
            "c3_opened_at": trade.c3_opened_at,
            "source_opened_at": trade.source_opened_at,
            "entry_opened_at": trade.entry_opened_at,
            "reference_ids": list(trade.reference_ids),
            "inside_bar_context": c1_observations[trade.c3_opened_at].inside_bar_context,
            "inside_bar_count": c1_observations[trade.c3_opened_at].inside_bar_count,
            "complete_c1_m15": c1_observations[trade.c3_opened_at].complete_c1_m15,
            "r_multiple_original": trade.r_multiple,
            "original_exit_reason": trade.exit_reason,
        }
        for trade in trades
    )
    return (
        {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "market": market.value,
            "period_start_utc": START.isoformat(),
            "period_end_exclusive_utc": END_EXCLUSIVE.isoformat(),
            "period_split_utc": FOLD_1_END.isoformat(),
            "parent_crt_count": parent_count,
            "source_comparison": {
                "romeotpt": "PRIMARY_CRT_MODEL1_FAMILY_SOURCE_ONLY",
                "speculatorfl": "LEVEL_B_INSIDE_BAR_CONTEXT_HYPOTHESIS",
                "traderflamesn": "LEVEL_B_CORROBORATES_SPECULATORFL_NOT_INDEPENDENT",
            },
            "control_identity": "VT08_CRT_PURE_R2C_CLOSE_UNMITIGATED_MODEL1_001",
            "control_policy_authority": "QORE_ENGINEERING_NOT_ROMEO_CERTIFIED",
            "context_definition": (
                "One or more strictly inside consecutive M15 candles "
                "within fully closed C1 H4, available before C2 and C3"
            ),
            "context_known_at": "C1_H4_CLOSE",
            "inside_bar_threshold_tuned": False,
            "changed_trade_geometry": False,
            "source_priority_promoted": False,
            "read_only": True,
            "notional_sizing_used": False,
            "venue_orders_used": False,
            "costs_validated": False,
            "broker_bid_ask_executability_validated": False,
            "multiple_hypotheses_exploratory": True,
            "no_certification_from_filter_performance": True,
            "event_counters_control": counters,
            "summaries": _folded(groups),
        },
        diagnostics,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=["AUDUSD", "USDJPY"])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    market = CrtPureMarket(args.market)
    bars = load_two_year_m5(market)
    report, ledger = compare_three_sources_inside_bar_context(market, bars)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    with (args.output / "diagnostics.jsonl").open("w", encoding="utf-8") as writer:
        for item in ledger:
            writer.write(json.dumps(item, sort_keys=True) + "\n")
    print("VT08_THREE_SOURCE_INSIDE_BAR=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
