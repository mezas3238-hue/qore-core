"""N3 causal C2-close→M5-C3 clock census, QORE Native SHA M5 only.

Preregistered before results, no trade simulation, no R, no sizing.
The source B 'confirm C2 / examine C3' is temporal context only.
Swept-side detection and midpoint crossing are engineering observations,
NOT original RomeoTPT Model #1 entry conditions.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    FOLD_1_END,
    ReplayBar,
    _midpoint,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_nested_m15_census import (
    micro_crt_direction,
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
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

SCHEMA = "qore.vt08.crt_pure.n3_c2_closed_m5_c3_observation.v1"
M5 = timedelta(minutes=5)


def c2_purge_return(
    c1: M15Bar, c2: M15Bar
) -> CrtPureCandidateDirection | None:
    """Eligibility is decidable at the close of C2, never from C3 or M5 future."""
    if c2.opened_at != c1.closed_at or c1.low_price >= c1.high_price:
        return None
    low_sweep = c2.low_price < c1.low_price
    high_sweep = c2.high_price > c1.high_price
    if low_sweep == high_sweep:
        return None
    if not c1.low_price <= c2.close_price <= c1.high_price:
        return None
    return (
        CrtPureCandidateDirection.BULLISH
        if low_sweep else CrtPureCandidateDirection.BEARISH
    )


def first_m5_observation(
    *,
    micro_c1: M15Bar,
    micro_c3: M15Bar,
    direction: CrtPureCandidateDirection,
    m5_bars: tuple[ReplayBar, ...],
) -> dict[str, Any]:
    """Measure timestamps post-C2. Never use these flags as C2 admission filters."""
    if len(m5_bars) != 3:
        raise ValueError("must supply exactly three M5 candles in micro C3")
    if any(
        b.opened_at != micro_c3.opened_at + i * M5
        for i, b in enumerate(m5_bars)
    ):
        raise ValueError("M5 candles must be contiguous within micro C3")
    if (
        m5_bars[0].open_price != micro_c3.open_price
        or m5_bars[-1].close_price != micro_c3.close_price
        or max(b.high_price for b in m5_bars) != micro_c3.high_price
        or min(b.low_price for b in m5_bars) != micro_c3.low_price
    ):
        raise ValueError("M5 OHLC aggregation does not equal native M15")
    bullish = direction is CrtPureCandidateDirection.BULLISH
    midpoint_twice = micro_c1.high_price + micro_c1.low_price
    first_close_slot: int | None = None
    first_far_slot: int | None = None
    first_cross_close: str | None = None
    first_far_bar: str | None = None
    for i, bar in enumerate(m5_bars, start=1):
        above_mid = (
            2 * bar.close_price > midpoint_twice
            if bullish else 2 * bar.close_price < midpoint_twice
        )
        far_wick = (
            bar.high_price >= micro_c1.high_price
            if bullish else bar.low_price <= micro_c1.low_price
        )
        if above_mid and first_close_slot is None:
            first_close_slot = i
            first_cross_close = (bar.opened_at + M5).isoformat()
        if far_wick and first_far_slot is None:
            first_far_slot = i
            first_far_bar = bar.opened_at.isoformat()
    return {
        "first_m5_close_crossing_micro_c1_midpoint_slot": first_close_slot,
        "first_m5_close_crossing_midpoint_utc": first_cross_close,
        "first_m5_wick_touching_far_boundary_slot": first_far_slot,
        "first_m5_far_wick_bar_open_utc": first_far_bar,
        "midpoint_slot_precedes_far_slot": (
            first_close_slot < first_far_slot
            if first_close_slot is not None and first_far_slot is not None
            else None
        ),
        "far_slot_precedes_midpoint_slot": (
            first_far_slot < first_close_slot
            if first_close_slot is not None and first_far_slot is not None
            else None
        ),
        "same_M5_bar_order_if_both_occur": (
            "UNKNOWN_INTRABAR_SEQUENCE"
            if first_close_slot is not None and first_close_slot == first_far_slot
            else "NOT_SAME_M5_BAR_OR_ONE_MISSING"
        ),
        "measurement_only_not_M5_entry_signal": True,
    }


def census_c2_to_m5(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    if market is CrtPureMarket.BTCUSD:
        raise ValueError("BTCUSD frozen")
    parents = build_parent_crts(market, bars)
    m15_by_time = {b.opened_at: b for b in aggregate_complete_m15(bars)}
    m5_by_time = {b.opened_at: b for b in bars}
    if len(m5_by_time) != len(bars):
        raise ValueError("duplicate M5 timestamps")
    counts: Counter[str] = Counter()
    parent_ids: set[str] = set()
    aligned_parents: set[str] = set()
    n3b_strict_parents: set[str] = set()
    ledger: list[dict[str, Any]] = []
    for parent in parents:
        pk = parent.c3_opened_at.isoformat()
        parents_m15 = tuple(
            m15_by_time[parent.c3_opened_at + i * M15]
            for i in range(16)
        )
        counts["COMPLETE_PARENT_H4_C3"] += 1
        for i in range(len(parents_m15) - 2):
            c1, c2, c3 = parents_m15[i:i + 3]
            counts["C2_CANDIDATE_PAIRS_WITH_AVAILABLE_NEXT_M15"] += 1
            direction = c2_purge_return(c1, c2)
            if direction is None:
                continue
            # NO C3/M5 access occurs before this eligibility decision.
            counts["C2_ONE_SIDED_SWEEP_AND_RETURN"] += 1
            parent_ids.add(pk)
            aligned = direction is parent.direction
            if aligned:
                counts["ALIGNED_WITH_H4"] += 1
                aligned_parents.add(pk)
            else:
                counts["OPPOSITE_TO_H4"] += 1
            counts["PERIOD_1" if c2.opened_at < FOLD_1_END else "PERIOD_2"] += 1
            h4_target = _midpoint(
                parent.c1.high_price, parent.c1.low_price
            )
            before_c2_close = parents_m15[:i + 2]
            h4_old_target_touched = any(
                b.high_price >= h4_target
                if parent.direction is CrtPureCandidateDirection.BULLISH
                else b.low_price <= h4_target
                for b in before_c2_close
            )
            if h4_old_target_touched:
                counts["OLD_H4_TARGET_ALREADY_TOUCHED_AT_C2_CLOSE"] += 1
            midpoint_twice = c1.high_price + c1.low_price
            already_beyond_mid = (
                2 * c2.close_price > midpoint_twice
                if direction is CrtPureCandidateDirection.BULLISH
                else 2 * c2.close_price < midpoint_twice
            )
            if already_beyond_mid:
                counts["MICRO_MIDPOINT_ALREADY_CLOSED_THROUGH_C2"] += 1

            micro3_m5 = tuple(
                m5_by_time[c3.opened_at + j * M5]
                for j in range(3)
            )
            observed = first_m5_observation(
                micro_c1=c1, micro_c3=c3,
                direction=direction, m5_bars=micro3_m5,
            )
            mid_slot = observed["first_m5_close_crossing_micro_c1_midpoint_slot"]
            far_slot = observed["first_m5_wick_touching_far_boundary_slot"]
            counts[f"M5_FIRST_MIDPOINT_CLOSE_SLOT_{mid_slot or 'NEVER'}"] += 1
            counts[f"M5_FIRST_FAR_WICK_SLOT_{far_slot or 'NEVER'}"] += 1
            if mid_slot in (1, 2):
                counts["M5_MIDPOINT_CLOSE_BEFORE_FULL_M15_C3_CLOSE"] += 1
            if mid_slot == far_slot and mid_slot is not None:
                counts["MID_AND_FAR_ON_SAME_M5_BAR_ORDER_UNKNOWN"] += 1
            # N3B preregistered AFTER N3 aggregate read. A genuinely *new*
            # first M5 close beyond midpoint requires C2 NOT already beyond.
            # For structural far-side state use only the M5 prefix known at
            # that first early close; NEVER inspect later C3 M5 bars to gate.
            new_m5_early = (
                not already_beyond_mid and mid_slot in (1, 2)
            )
            far_untouched_at_early_m5_close = False
            if new_m5_early:
                assert isinstance(mid_slot, int)
                observed_prefix = micro3_m5[:mid_slot]
                far_untouched_at_early_m5_close = not any(
                    b.high_price >= c1.high_price
                    if direction is CrtPureCandidateDirection.BULLISH
                    else b.low_price <= c1.low_price
                    for b in observed_prefix
                )
                counts["N3B_NEW_FIRST_M5_MIDPOINT_CLOSE_BEFORE_C3_END"] += 1
                if far_untouched_at_early_m5_close:
                    counts["N3B_NEW_M5_EVIDENCE_FAR_UNTOUCHED_AT_CLOSE"] += 1
                else:
                    counts["N3B_NEW_M5_EVIDENCE_FAR_ALREADY_TOUCHED"] += 1
            n3b_strict = bool(
                new_m5_early
                and far_untouched_at_early_m5_close
                and aligned
                and not h4_old_target_touched
            )
            if n3b_strict:
                counts["N3B_STRICT_CONTEXT_EVENTS_NOT_TRADES"] += 1
                n3b_strict_parents.add(pk)
                counts[
                    "N3B_STRICT_PERIOD_1" if c2.opened_at < FOLD_1_END
                    else "N3B_STRICT_PERIOD_2"
                ] += 1
            n1_confirmed = micro_crt_direction(c1, c2, c3) is direction
            if n1_confirmed:
                counts["PREVIOUS_N1_M15_C3_CONFIRMATION"] += 1
            else:
                counts["NO_PREVIOUS_N1_M15_C3_CONFIRMATION"] += 1
            ledger.append({
                "market": market.value,
                "parent_c3_opened_at": pk,
                "parent_direction": parent.direction.value,
                "parent_c1_high_relative": parent.c1.high_price,
                "parent_c1_low_relative": parent.c1.low_price,
                "micro_id": (
                    market.value + ":" + c1.opened_at.isoformat()
                    + ":" + c2.opened_at.isoformat()
                ),
                "micro_c1_opened_at": c1.opened_at.isoformat(),
                "micro_c1_high_relative": c1.high_price,
                "micro_c1_low_relative": c1.low_price,
                "micro_c2_opened_at": c2.opened_at.isoformat(),
                "micro_c2_close_relative": c2.close_price,
                "micro_c2_confirm_known_at": c2.closed_at.isoformat(),
                "micro_direction": direction.value,
                "aligned_with_H4": aligned,
                "old_h4_midpoint_pre_touched_at_C2_close": h4_old_target_touched,
                "micro_midpoint_closed_through_at_C2_close": already_beyond_mid,
                "N3B_first_M5_new_evidence_before_C3_close": new_m5_early,
                "N3B_far_boundary_untouched_at_first_early_M5_close": (
                    far_untouched_at_early_m5_close if new_m5_early else None
                ),
                "N3B_aligned_H4_old_target_pristine_new_M5_event": n3b_strict,
                "N3B_prereg_registered_after_prior_N3_aggregate_counts": True,
                "micro_c3_opened_at": c3.opened_at.isoformat(),
                "micro_c3_full_close_relative": c3.close_price,
                "n1_conditional_C3_M15_confirmation": n1_confirmed,
                "M5_C3_ohlc_witness": [
                    {
                        "opened_at": b.opened_at.isoformat(),
                        "open_relative": b.open_price,
                        "high_relative": b.high_price,
                        "low_relative": b.low_price,
                        "close_relative": b.close_price,
                    }
                    for b in micro3_m5
                ],
                "subsequent_M5_observation_NOT_C2_ELIGIBILITY": observed,
                "eligible_at_C2_close_using_only_C1_C2": True,
                "author_original_crt_or_entry_certified": False,
                "is_trade": False,
            })
    total = counts["C2_ONE_SIDED_SWEEP_AND_RETURN"]
    if len(ledger) != total:
        raise RuntimeError("C2 source events mismatch ledger")
    if total != counts["ALIGNED_WITH_H4"] + counts["OPPOSITE_TO_H4"]:
        raise RuntimeError("H4 directional partition mismatch")
    if total != counts["PREVIOUS_N1_M15_C3_CONFIRMATION"] + counts[
        "NO_PREVIOUS_N1_M15_C3_CONFIRMATION"
    ]:
        raise RuntimeError("N1 and non-N1 partition mismatch")
    if total != sum(
        count for key, count in counts.items()
        if key.startswith("M5_FIRST_MIDPOINT_CLOSE_SLOT_")
    ):
        raise RuntimeError("M5 first midpoint slot partition mismatch")
    if total != sum(
        count for key, count in counts.items()
        if key.startswith("M5_FIRST_FAR_WICK_SLOT_")
    ):
        raise RuntimeError("M5 first far wick partition mismatch")
    if len({e["micro_id"] for e in ledger}) != len(ledger):
        raise RuntimeError("nonunique C2 source identity")
    # Previous N1 has 521+418 labels. Lockstep reconciliation protects the
    # experiment against accidental changes to N1's C3 confirmation contract.
    n1_expected = {CrtPureMarket.AUDUSD: 521, CrtPureMarket.USDJPY: 418}
    if counts["PREVIOUS_N1_M15_C3_CONFIRMATION"] != n1_expected[market]:
        raise RuntimeError("previous N1 frozen control count changed")
    return {
        "schema": SCHEMA,
        "market": market.value,
        "parent_H4_C3_n": len(parents),
        "c2_source_contexts_n_not_trades": total,
        "unique_H4_parents_with_C2_source": len(parent_ids),
        "unique_H4_parents_with_aligned_C2_source": len(aligned_parents),
        "previous_N1_confirmations_reconciled": counts[
            "PREVIOUS_N1_M15_C3_CONFIRMATION"
        ],
        "N3B_strict_unique_H4_contexts_NOT_TRADES": len(n3b_strict_parents),
        "N3B_extra_prereg_is_after_N3_aggregate_results": True,
        "clock_counters": dict(sorted(counts.items())),
        "C2_eligibility_does_not_inspect_C3_M5": True,
        "lower_timeframe_entry_rule_source_adjudicated": False,
        "original_romeo_model1_certified": False,
        "not_an_economic_backtest": True,
        "trades_created": 0,
        "trader_sizing": False,
        "no_merge_or_deployment": True,
    }, tuple(ledger)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=("AUDUSD", "USDJPY"))
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    market = CrtPureMarket(args.market)
    bars, provenance = load_atlas_vt08_m5(market, args.root)
    report, ledger = census_c2_to_m5(market, bars)
    report["source_provenance"] = provenance
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "n3-c2-m5-summary.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    with (args.output / "n3-c2-m5-ledger.jsonl").open(
        "w", encoding="utf-8"
    ) as writer:
        for case in ledger:
            writer.write(json.dumps(case, sort_keys=True) + "\n")
    print("VT08_N3_C2_M5_CLOCK=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
