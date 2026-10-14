#!/usr/bin/env python3
"""Full-consumed 3Y M1 causal-prefix falsification for frozen first FVG/C2.

Research-only read, no orders/fills/returns, no strategy changes. Runs the
exact prior M2/M3 day adjudicator and M4/M5 module once per closed M1
prefix. All results are engineering evidence about QORE source formalization.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar
from scripts.vt31_m4_m5_ttrades_census_20261014 import (
    census,
)
from scripts.vt31_m4_m5_ttrades_fvg_path_20261014 import (
    M4M5SourcePath,
    first_fvg_and_source_path,
)
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    MARKET_SHA,
    adjudicate_day,
    collect_hours,
    complete_hour,
    hash_file,
    market_rows,
)
from scripts.vt31_ttrades_am_native_cog_v1_20261014 import (
    propose_ttrades_am_cognition,
)

IDENTITY = "VT31_M4_P1_FIRST_FVG_3Y_FULL_M1_PREFIX_PARITY_NO_PNL"
PREREG = "8a4a3a83c954cf5a148c0a42324cd91d8205d829"
GEOMETRY = (
    "first_fvg_confirmed_at", "side", "fvg_lower", "fvg_upper",
    "ce_research_only", "c2_full_wick_reference", "target_dol",
    "mss_anchor", "potential_points_at_mss",
)
TERMINAL_PATH = {
    "TOUCH_NOT_FILL", "AMBIGUOUS_M1_SEQUENCE_NO_FILL",
    "INVALIDATED_AT_M1_CLOSE_NO_ORDER", "EXPIRED_NO_ORDER_OR_ACK",
}


def prefix_parity(
    *, nine: tuple[M1Bar, ...], ten: tuple[M1Bar, ...],
    cognition: Any,
) -> dict[str, Any]:
    """Falsifiable test: no future bars can change selected first geometry."""
    full = first_fvg_and_source_path(
        nine=nine, ten=ten, cognition=cognition,
    )
    mss_at = cognition.structure_break_confirmed_at
    mss_indices = [i for i, x in enumerate(ten) if x.closed_at == mss_at]
    if len(mss_indices) != 1:
        raise AssertionError("MSS_NOT_UNIQUE_IN_10AM_HOUR")
    start = mss_indices[0]+1
    prefix_count = 0
    first_visible = None
    first_terminal: tuple[str, datetime | None] | None = None
    prior_terminal: tuple[str, datetime | None] | None = None
    for end in range(start, len(ten)+1):
        subset = ten[:end]
        visible_at = subset[-1].closed_at
        current = first_fvg_and_source_path(
            nine=nine, ten=subset, cognition=cognition,
        )
        prefix_count += 1
        if current.first_fvg_confirmed_at is not None:
            if current.first_fvg_confirmed_at > visible_at:
                raise AssertionError("FVG_FORMED_USING_FUTURE_M1")
            if full.first_fvg_confirmed_at is None:
                raise AssertionError("FINAL_FVG_DISAPPEARED_USING_FUTURE")
            if current.first_fvg_confirmed_at != full.first_fvg_confirmed_at:
                raise AssertionError("FVG_FIRST_C3_MOVES_WHEN_FUTURE_M1_ADDED")
            if any(getattr(current, k) != getattr(full, k) for k in GEOMETRY):
                raise AssertionError("M4_FIRST_FVG_OR_C2_MUTATED_BY_FUTURE_M1")
            if first_visible is None:
                first_visible = visible_at
            path = (current.source_path_state, current.path_observation_at)
            if current.source_path_state in TERMINAL_PATH:
                if first_terminal is None:
                    first_terminal = path
                elif first_terminal != path:
                    raise AssertionError("M5_TERMINAL_PATH_REWRITTEN_WITH_FUTURE_M1")
                if prior_terminal is not None and prior_terminal != path:
                    raise AssertionError("M5_TERMINAL_PATH_EVENT_DIVERGED")
                prior_terminal = path
            elif prior_terminal is not None:
                raise AssertionError("M5_TERMINAL_PATH_RESURRECTED")
        elif full.first_fvg_confirmed_at is not None and visible_at >= full.first_fvg_confirmed_at:
            raise AssertionError("FVG_HIDDEN_AT_OR_AFTER_ITS_C3_CLOSE")
    if full.first_fvg_confirmed_at != first_visible:
        raise AssertionError("FIRST_FVG_NOT_VISIBLE_AT_ORIGINAL_C3")
    if full.first_fvg_confirmed_at is not None:
        if full.source_path_state in TERMINAL_PATH and first_terminal != (
            full.source_path_state, full.path_observation_at
        ):
            raise AssertionError("M5_FIRST_TERMINAL_EVENT_NOT_REPRODUCED")
    return {
        "prefixes_checked": prefix_count,
        "first_fvg_at": first_visible.isoformat() if first_visible else None,
        "final_m4_state": full.state,
        "final_m5_source_path": full.source_path_state,
        "earliest_terminal_path": (
            {"state": first_terminal[0],
             "time": first_terminal[1].isoformat() if first_terminal[1] else None}
            if first_terminal else None
        ),
        "causal_first_fvg_and_C2_immutable": True,
        "source_ohlc_touch_not_broker_fill": True,
    }


def audit_groups(groups: dict[str, dict[int, tuple[M1Bar, ...]]]) -> dict[str, Any]:
    baseline = census(groups)
    if baseline["baseline_days_total"] != 775 or baseline["M2_M3_cognitive_contexts"] != 128:
        raise AssertionError("SOURCE_M2_M3_BASELINE_DRIFT")
    if baseline["M4_source_state_counts"] != {
        "FVG_GEOMETRY_ATTESTED_NOT_EXECUTABLE": 119,
        "NO_ELIGIBLE_FVG": 8,
        "WINDOW_CLOSED_FOR_NEW_LIMIT": 1,
    }:
        raise AssertionError("FROZEN_M4_POPULATION_DRIFT")
    if baseline["M5_hypothetical_source_path_counts"] != {
        "TOUCH_NOT_FILL": 61,
        "AMBIGUOUS_M1_SEQUENCE_NO_FILL": 31,
        "EXPIRED_NO_ORDER_OR_ACK": 27,
    }:
        raise AssertionError("FROZEN_M5_PATH_POPULATION_DRIFT")

    cases = []
    prefixes_total = 0
    class_counts: Counter[str] = Counter()
    for day, hours in sorted(groups.items()):
        nine, ten = hours.get(9, ()), hours.get(10, ())
        if not complete_hour(day, 9, nine) or not complete_hour(day, 10, ten):
            continue
        classified = adjudicate_day(nine, ten)
        if not classified["has_source_cognitive_proposal"]:
            continue
        mss_at = datetime.fromisoformat(classified["as_of"])
        prefix = tuple(x for x in ten if x.closed_at <= mss_at)
        source_cog = propose_ttrades_am_cognition(
            as_of=mss_at, history=nine + prefix,
        )
        if source_cog.state != "CONTEXT_ATTESTED_NOT_CERTIFIED" or source_cog.decision is None:
            raise AssertionError("COG_128_CANDIDATE_SET_DRIFT")
        comparison = prefix_parity(
            nine=nine, ten=ten, cognition=source_cog.decision,
        )
        class_counts[comparison["final_m4_state"]] += 1
        prefixes_total += comparison["prefixes_checked"]
        cases.append({"ny_day": day, "mss_at": mss_at.isoformat(), **comparison})
    if len(cases) != 128:
        raise AssertionError("CAUSAL_CONTEXT_SET_NOT_128")
    if dict(class_counts) != baseline["M4_source_state_counts"]:
        raise AssertionError("PREFIX_AUDIT_FINAL_M4_RECLASSIFIED")
    return {
        "identity": IDENTITY,
        "source_m1_sha256": MARKET_SHA,
        "pre_registered_commit": PREREG,
        "m2m3_candidate_days": len(cases),
        "days_source": baseline["baseline_days_total"],
        "m4_counts": baseline["M4_source_state_counts"],
        "m5_counts": baseline["M5_hypothetical_source_path_counts"],
        "total_closed_m1_prefixes_replayed": prefixes_total,
        "causal_first_fvg_geometry_parity": True,
        "cases": cases,
        "economic_pnl": None,
        "profit_factor": None,
        "fills_or_ack": 0,
        "method_certified": False,
        "cognition_certified": False,
        "trading_authorized": False,
        "live_authorized": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if hash_file(args.market) != MARKET_SHA:
        raise ValueError("FROZEN_MARKET_M1_SOURCE_SHA_DRIFT")
    groups, total = collect_hours(market_rows(args.market))
    if total != 1059784:
        raise ValueError("FROZEN_MARKET_CANDLE_COUNT_DRIFT")
    result = audit_groups(groups)
    result["source_total_m1"] = total
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8",
    )
    print(json.dumps({
        "identity": IDENTITY,
        "tested_days": result["m2m3_candidate_days"],
        "prefixes": result["total_closed_m1_prefixes_replayed"],
        "m4": result["m4_counts"],
        "m5": result["m5_counts"],
        "parity": result["causal_first_fvg_geometry_parity"],
        "broker_fills": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
