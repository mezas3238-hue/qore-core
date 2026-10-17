"""N2: 57-case forensic book for nested M15 CRT, no orders or economics.

Preregistered in docs/research/VT08_CRT_PURE_N2_57_CASEBOOK_PRE_REGISTRATION_2026-10-14.md.
Preserves all N1 candidates, makes no posthoc strategy selection, and checks
all prospective structural flags no later than M15 confirmation / next-bar open.
Full C3 OHLC is casebook ONLY, not used to derive candidate eligibility.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    FOLD_1_END,
    ReplayBar,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_nested_m15_census import (
    census_micro_crt,
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
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

SCHEMA = "qore.vt08.crt_pure.n2_57_nested_micro_casebook.v1"


def interval_overlap(
    a_start: datetime,
    a_end: datetime,
    b_start: datetime,
    b_end: datetime,
) -> bool:
    """Half-open M15 event intervals; adjacent events do NOT overlap."""
    if a_start >= a_end or b_start >= b_end:
        raise ValueError("invalid micro-event interval")
    return a_start < b_end and b_start < a_end


def micro_target_context(
    *,
    bullish: bool,
    own_high: int,
    own_low: int,
    micro_c2: M15Bar,
    micro_c3: M15Bar,
    next_open: int,
    parent_high: int,
    parent_low: int,
    micro_c1: M15Bar,
) -> dict[str, bool]:
    """Own micro-C1 target status at confirmation and next OPEN, not later prices.

    Far-boundary remaining is observational, NOT a profit target decision.
    """
    if own_high <= own_low:
        raise ValueError("micro reference range nonpositive")
    midpoint_twice = own_high + own_low
    confirmed_midpoint = (
        2 * micro_c3.close_price > midpoint_twice
        if bullish else 2 * micro_c3.close_price < midpoint_twice
    )
    if not confirmed_midpoint:
        raise ValueError("unconfirmed micro supplied as N1 event")
    return {
        "micro_c1_range_inside_parent_h4_c1": (
            micro_c1.high_price <= parent_high
            and micro_c1.low_price >= parent_low
        ),
        "micro_c1_same_range_as_parent_h4_c1": (
            micro_c1.high_price == parent_high
            and micro_c1.low_price == parent_low
        ),
        "micro_c2_swept_original_h4_c1_side": (
            micro_c2.low_price < parent_low
            if bullish else micro_c2.high_price > parent_high
        ),
        "micro_c3_close_against_h4_original_thesis": (
            micro_c3.close_price < parent_low
            if bullish else micro_c3.close_price > parent_high
        ),
        "own_micro_midpoint_already_closed_through": confirmed_midpoint,
        "own_far_boundary_touched_by_micro_c3_wick": (
            micro_c3.high_price >= own_high
            if bullish else micro_c3.low_price <= own_low
        ),
        "own_far_boundary_already_closed_through": (
            micro_c3.close_price >= own_high
            if bullish else micro_c3.close_price <= own_low
        ),
        "own_far_boundary_not_ahead_at_next_open": (
            next_open >= own_high
            if bullish else next_open <= own_low
        ),
        "own_far_boundary_ahead_at_next_open": (
            next_open < own_high
            if bullish else next_open > own_low
        ),
    }


def _bar_record(bar: M15Bar, index: int) -> dict[str, Any]:
    return {
        "h4_m15_slot": index,
        "opened_at_utc": bar.opened_at.isoformat(),
        "closed_at_utc": bar.closed_at.isoformat(),
        "open_price_relative": bar.open_price,
        "high_price_relative": bar.high_price,
        "low_price_relative": bar.low_price,
        "close_price_relative": bar.close_price,
    }


def forensic_casebook_57(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    if market is CrtPureMarket.BTCUSD:
        raise ValueError("BTCUSD frozen")
    previous, n1 = census_micro_crt(market, bars)
    selected = tuple(
        e for e in n1
        if e["micro_parent_alignment"] == "SAME_H4_DIRECTION"
        and e["prospective_next_m15_opened_at"] is not None
        and e["old_h4_midpoint_pre_touched"] is False
        and e["parent_first_r2c_trade_exists"] is False
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_by_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in n1:
        all_by_parent[e["parent_c3_opened_at"]].append(e)
    for e in selected:
        grouped[e["parent_c3_opened_at"]].append(e)
    if len(grouped) != previous[
        "unique_parent_h4_aligned_next_untouched_no_old_r2c_trade"
    ]:
        raise RuntimeError("57-case scope cannot reconcile to frozen N1 census")
    if len(selected) != previous["counts"][
        "ALIGNED_NEXT_UNTOUCHED_OLD_R2C_PARENT_REJECTED"
    ]:
        raise RuntimeError("64 selected N1 case identities do not reconcile")

    parents = {p.c3_opened_at.isoformat(): p for p in build_parent_crts(market, bars)}
    m15 = {b.opened_at: b for b in aggregate_complete_m15(bars)}
    counts: Counter[str] = Counter()
    flags: Counter[str] = Counter()
    book: list[dict[str, Any]] = []
    for key, options in sorted(grouped.items()):
        parent = parents.get(key)
        if parent is None:
            raise RuntimeError("H4 parent absent for casebook")
        options.sort(key=lambda e: (e["micro_c1_opened_at"], e["micro_id"]))
        all_events = sorted(
            all_by_parent[key],
            key=lambda e: (e["micro_c1_opened_at"], e["micro_id"]),
        )
        h4_m15 = tuple(
            m15[parent.c3_opened_at + i * M15]
            for i in range(16)
        )
        if len(h4_m15) != 16:
            raise RuntimeError("incomplete H4 M15 witness")

        overlaps: list[tuple[str, str]] = []
        for ia, a in enumerate(options):
            for b in options[ia + 1:]:
                if interval_overlap(
                    datetime.fromisoformat(a["micro_c1_opened_at"]),
                    datetime.fromisoformat(a["micro_decision_known_at"]),
                    datetime.fromisoformat(b["micro_c1_opened_at"]),
                    datetime.fromisoformat(b["micro_decision_known_at"]),
                ):
                    overlaps.append((a["micro_id"], b["micro_id"]))
        status = (
            "SINGLE_MICRO" if len(options) == 1 else
            "MULTIPLE_OVERLAPPING" if overlaps else
            "MULTIPLE_DISJOINT"
        )
        counts[status] += 1
        counts["H4_CASES"] += 1
        counts["N1_EVENTS_IN_H4_ALL_DIRECTIONS"] += len(all_events)
        counts["QUALIFYING_N1_EVENTS"] += len(options)
        if key in {e["parent_c3_opened_at"] for e in all_events
                   if e["parent_belongs_to_previous_88"]}:
            counts["CASE_H4_BELONGS_TO_PREVIOUS_88"] += 1
        has_opposite = any(
            e["micro_parent_alignment"] == "OPPOSITE_H4_DIRECTION"
            for e in all_events
        )
        if has_opposite:
            counts["CASE_H4_ALSO_CONTAINS_OPPOSITE_N1"] += 1
        details: list[dict[str, Any]] = []
        for candidate in options:
            c1_at = datetime.fromisoformat(candidate["micro_c1_opened_at"])
            c2_at = datetime.fromisoformat(candidate["micro_c2_opened_at"])
            c3_at = datetime.fromisoformat(candidate["micro_c3_opened_at"])
            entry_at = datetime.fromisoformat(
                candidate["prospective_next_m15_opened_at"]
            )
            if c2_at != c1_at + M15 or c3_at != c2_at + M15:
                raise RuntimeError("micro source candles not contiguous")
            if entry_at != c3_at + M15:
                raise RuntimeError("micro decision uses lookahead entry time")
            c1, c2, c3, next_bar = (
                m15[c1_at], m15[c2_at], m15[c3_at], m15[entry_at]
            )
            if not parent.c3_opened_at <= c1_at < entry_at < parent.c3_closed_at:
                raise RuntimeError("independent nested parent timeframe violation")
            bullish = candidate["micro_direction"] == "BULLISH"
            context = micro_target_context(
                bullish=bullish,
                own_high=c1.high_price,
                own_low=c1.low_price,
                micro_c1=c1,
                micro_c2=c2,
                micro_c3=c3,
                next_open=next_bar.open_price,
                parent_high=parent.c1.high_price,
                parent_low=parent.c1.low_price,
            )
            for flag, yes in context.items():
                if yes:
                    flags[flag] += 1
            earlier_n1 = [
                e for e in all_events
                if e["micro_decision_known_at"] < candidate["micro_decision_known_at"]
            ]
            earlier_opposite = any(
                e["micro_parent_alignment"] == "OPPOSITE_H4_DIRECTION"
                for e in earlier_n1
            )
            if earlier_n1:
                flags["candidate_has_earlier_N1_in_same_H4"] += 1
            if earlier_opposite:
                flags["candidate_has_earlier_opposite_N1"] += 1
            details.append({
                "micro_id": candidate["micro_id"],
                "micro_source_c1_utc": c1_at.isoformat(),
                "micro_sweep_c2_utc": c2_at.isoformat(),
                "micro_confirm_c3_utc": c3_at.isoformat(),
                "decision_known_after": c3.closed_at.isoformat(),
                "potential_next_bar_open_utc": entry_at.isoformat(),
                "micro_direction": candidate["micro_direction"],
                "own_reference_range_high_relative": c1.high_price,
                "own_reference_range_low_relative": c1.low_price,
                "c3_confirm_close_relative": c3.close_price,
                "next_open_relative": next_bar.open_price,
                "structural_observations": context,
                "earlier_N1_in_this_H4_count": len(earlier_n1),
                "earlier_opposite_N1": earlier_opposite,
                "review_priority": (
                    "FIRST_OF_QUALIFYING_CONTEXT" if candidate is options[0]
                    else "SECOND_OR_LATER_RESEARCH_CANDIDATE"
                ),
                "methodological_source_authority": "UNADJUDICATED",
                "trade_admitted": False,
            })
        counts[
            "CASE_WITH_EARLIER_OPPOSITE_SIGNAL"
            if any(d["earlier_opposite_N1"] for d in details)
            else "CASE_WITHOUT_EARLIER_OPPOSITE_SIGNAL"
        ] += 1
        book.append({
            "market": market.value,
            "parent_C3_start_utc": key,
            "parent_C3_end_utc": parent.c3_closed_at.isoformat(),
            "parent_H4_C1_high_relative": parent.c1.high_price,
            "parent_H4_C1_low_relative": parent.c1.low_price,
            "parent_H4_C2_high_relative": parent.c2.high_price,
            "parent_H4_C2_low_relative": parent.c2.low_price,
            "parent_H4_direction": parent.direction.value,
            "parent_R2C_trade_exists": False,
            "parent_previously_rejected_88": options[0][
                "parent_belongs_to_previous_88"
            ],
            "h4_context_period": (
                "PERIOD_1" if parent.c3_opened_at < FOLD_1_END else "PERIOD_2"
            ),
            "all_N1_in_parent": [
                {"micro_id": e["micro_id"],
                 "micro_c1_opened_at": e["micro_c1_opened_at"],
                 "micro_direction": e["micro_direction"],
                 "alignment": e["micro_parent_alignment"],
                 "decision_at": e["micro_decision_known_at"]}
                for e in all_events
            ],
            "qualified_micro_candidates": details,
            "qualified_micro_count": len(details),
            "overlap_pairs": overlaps,
            "context_overlap_class": status,
            "earliest_research_candidate_micro_id": details[0]["micro_id"],
            "full_h4_C3_m15_chart_witness_ONLY_NOT_SELECTION_INPUT": [
                _bar_record(bar, i) for i, bar in enumerate(h4_m15)
            ],
            "source_verdict": "REQUIRES_ROMEO_SPECULATORFL_FLAMESEN_ADJUDICATION",
            "certified_independent_trader_opportunity": False,
        })
    if len(book) != len(grouped):
        raise RuntimeError("57-case book is incomplete")
    if sum(x["qualified_micro_count"] for x in book) != len(selected):
        raise RuntimeError("qualified event census drift")
    if len({x["parent_C3_start_utc"] for x in book}) != len(book):
        raise RuntimeError("duplicate H4 parent case")

    return {
        "schema": SCHEMA,
        "market": market.value,
        "source": "QORE_NATIVE_ORIGINAL_M5_SHA_VERIFIED",
        "N1_parent_count_control": previous["original_parent_h4"],
        "N1_original_R2C_trades_unchanged": previous[
            "original_r2c_trades_unchanged"
        ],
        "N1_raw_micro_observations": previous["candidate_micro_n1_events_NOT_TRADES"],
        "strict_context_H4_cases": len(book),
        "strict_context_N1_events": len(selected),
        "case_counts": dict(sorted(counts.items())),
        "observation_flag_counts_overlapping": dict(sorted(flags.items())),
        "methodology_primary_source_authorized": False,
        "first_candidate_is_only_chart_review_order_NOT_ENTRY": True,
        "no_trade_PnL_R_stop_sizing_produced": True,
        "full_H4_chart_witness_is_posthoc_reconstruction_not_entry_feature": True,
        "requires_source_adjudication": True,
        "certified": False,
    }, tuple(book)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=("AUDUSD", "USDJPY"))
    parser.add_argument("original_data_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    market = CrtPureMarket(args.market)
    bars, provenance = load_atlas_vt08_m5(market, args.original_data_root)
    report, cases = forensic_casebook_57(market, bars)
    report["source_provenance"] = provenance
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "n2-57-casebook-summary.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    with (args.output / "n2-57-casebook-full.jsonl").open(
        "w", encoding="utf-8"
    ) as writer:
        for case in cases:
            writer.write(json.dumps(case, sort_keys=True) + "\n")
    print("VT08_N2_CASEBOOK=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
