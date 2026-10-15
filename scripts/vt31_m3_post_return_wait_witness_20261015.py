#!/usr/bin/env python3
"""VT31 TTrades M3 post-first-return WAIT, independent read-only COG study.

All calls are actual frozen native producer #933 and independent source #929;
MSS is _mss_proxy QORE, NOT an author-certified TTrades requirement.
There are NO orders, sizing, fills, economic metrics or strategy changes.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar, Side
from scripts.vt31_mc_p2_ttrades_native_h1_evidence_20261014 import (
    native_ttrades_am_context,
)
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    collect_hours,
    complete_hour,
    hash_file,
    market_rows,
    run_census,
)
from scripts.vt31_ttrades_am_native_cog_v1_20261014 import (
    _mss_proxy,
    propose_ttrades_am_cognition,
)

MODEL = "VT31_TTRADES_AM_M3_POST_RETURN_COG_WAIT_V1"
PREREG = "eeb0aefff638e39805c6dff1e39128e76dbdcdb5"
SOURCE_SCOPE = "NAS100_ALREADY_EXAMINED_3Y_DEVELOPMENT_NOT_OOS"
PRESET = {
    "MSS_ATTESTED_CONTEXT_ONLY": 128,
    "FIRST_RETURN_NO_QORE_MSS": 483,
    "SWEEP_NO_RETURN": 92,
    "NO_SWEEP": 65,
    "INCOMPLETE_M1_HOURS": 6,
    "REJECTED_SOURCE": 1,
}
TERMINALS = frozenset({
    "LATE_QORE_PROXY_ONLY_NOT_AUTHOR_CERTIFIED",
    "SOURCE_REJECTED",
    "SOURCE_AMBIGUOUS",
    "SOURCE_CHANGED_NOT_ATTESTABLE",
    "TARGET_TOUCHED_BEFORE_CONFIRMATION",
    "AMBIGUOUS_TARGET_AND_PROXY_SAME_M1",
    "EXPIRED_WITHOUT_LATE_PROXY",
})
NO_CERT = {
    "methodology_certified": False,
    "cognition_certified": False,
    "trader_certified": False,
    "trade_or_order_created": False,
}


def target_contacted(bar: M1Bar, side: Side, target: object) -> bool:
    return (bar.high >= target) if side is Side.LONG else (bar.low <= target)


def examine_first_return_day(
    *, day: str, nine: tuple[M1Bar, ...],
    ten: tuple[M1Bar, ...], first_return_at: datetime,
) -> dict[str, Any]:
    """Walk chronological CLOSED 10AM M1 only, no reassignment after first raid."""
    if not complete_hour(day, 9, nine) or not complete_hour(day, 10, ten):
        raise ValueError("SOURCE_HOURS_INCOMPLETE_NO_COG_EVIDENCE")
    at = first_return_at.astimezone(UTC)
    index = next(
        (i for i, b in enumerate(ten) if b.closed_at == at), None
    )
    if index is None:
        raise ValueError("FROZEN_FIRST_RETURN_NOT_IN_SOURCE")
    original = propose_ttrades_am_cognition(
        as_of=at, history=nine+ten[:index+1],
    )
    independent = native_ttrades_am_context(
        as_of=at, nine=nine, ten=ten[:index+1],
    )
    if not (
        independent.state == "RETURN_INSIDE_OBSERVED"
        and independent.return_inside_at == at
        and independent.candidate_side in {"LONG", "SHORT"}
        and independent.opposite_h1_dol is not None
        and original.state == "UNKNOWN"
        and original.decision is None
        and "QORE_MSS_PROXY_NOT_CONFIRMED_ON_FIRST_RETURN" in original.reasons
    ):
        raise AssertionError("CASE_NOT_FIRST_RETURN_WITHOUT_QORE_MSS")
    side = Side(independent.candidate_side)
    target = independent.opposite_h1_dol
    baseline_raid = independent.first_sweep_at
    wait_steps = 0
    outcome: str | None = None
    reason = ""
    end_at = at
    late_proxy_structure_confirmed_at: datetime | None = None

    # If the same first-return minute spans an opposing target, sequence is
    # unknowable from OHLC. Do NOT preserve an apparently fresh objective.
    if target_contacted(ten[index], side, target):
        outcome = "TARGET_TOUCHED_BEFORE_CONFIRMATION"
        reason = "DOL_TOUCHED_IN_FIRST_RETURN_M1_NO_PROXY"
    else:
        for minute in range(index+1, len(ten)):
            observed = ten[minute]
            as_of = observed.closed_at
            prefix = ten[:minute+1]
            native = native_ttrades_am_context(
                as_of=as_of, nine=nine, ten=prefix,
            )
            # Same real COG, not synthetic CognitiveDecision.
            unchanged_cog = propose_ttrades_am_cognition(
                as_of=as_of, history=nine+prefix,
            )
            end_at = as_of
            if native.state == "REJECTED":
                outcome = "SOURCE_REJECTED"
                reason = "+".join(native.reasons)
                break
            if native.state == "UNKNOWN":
                outcome = "SOURCE_AMBIGUOUS"
                reason = "+".join(native.reasons)
                break
            if native.state != "RETURN_INSIDE_OBSERVED":
                outcome = "SOURCE_CHANGED_NOT_ATTESTABLE"
                reason = native.state
                break
            if not (
                native.return_inside_at == at
                and native.first_sweep_at == baseline_raid
                and native.candidate_side == side.value
                and native.opposite_h1_dol == target
            ):
                raise AssertionError("HISTORICAL_FIRST_RAID_OR_RETURN_REWRITTEN")
            if not (
                unchanged_cog.state == "UNKNOWN"
                and unchanged_cog.decision is None
                and "RETURN_M1_NOT_FRESH_AT_ASOF" in unchanged_cog.reasons
            ):
                raise AssertionError("FROZEN_REAL_COG_POST_RETURN_STATE_CHANGED")
            proxy = _mss_proxy(nine+prefix, side)
            target_this_m1 = target_contacted(observed, side, target)
            if target_this_m1 and proxy is not None:
                outcome = "AMBIGUOUS_TARGET_AND_PROXY_SAME_M1"
                reason = "INTRABAR_ORDER_UNKNOWN_TARGET_VS_QORE_PROXY"
                break
            if target_this_m1:
                outcome = "TARGET_TOUCHED_BEFORE_CONFIRMATION"
                reason = "H1_OPPOSITE_DOL_TOUCHED_NO_INTENT"
                break
            if proxy is not None:
                outcome = "LATE_QORE_PROXY_ONLY_NOT_AUTHOR_CERTIFIED"
                reason = "NATIVE_COG_UNKNOWN_AFTER_RETURN_BUT_QORE_PROXY_LATE"
                late_proxy_structure_confirmed_at = proxy[1]
                break
            # WAIT is a DIAGNOSTIC semantic interpretation; native COG says
            # UNKNOWN RETURN_M1_NOT_FRESH_AT_ASOF, not explicit WAIT.
            wait_steps += 1
        if outcome is None:
            outcome = "EXPIRED_WITHOUT_LATE_PROXY"
            reason = "NO_ELIGIBLE_PROXY_BEFORE_11AM_END"
            end_at = ten[-1].closed_at
    assert outcome in TERMINALS
    return {
        "ny_day": day,
        "first_return_at": at.isoformat(),
        "first_sweep_at": (
            baseline_raid.isoformat() if baseline_raid else None
        ),
        "last_observed_at": end_at.isoformat(),
        "candidate_side_from_first_raid": side.value,
        "terminal_state": outcome,
        "terminal_reason": reason,
        "wait_for_confirmation_m1_steps": wait_steps,
        "late_qore_pivot_confirmed_at": (
            late_proxy_structure_confirmed_at.isoformat()
            if late_proxy_structure_confirmed_at else None
        ),
        "authentic_cog_at_first_return": original.state,
        "authentic_cog_reason_at_first_return": list(original.reasons),
        "original_cog_kept_intent_absent": True,
        "post_return_wait_is_test_witness_not_native_API": True,
        "source_h1_raid_opposite_dol_locked": True,
        "m3_proxy_is_qore_not_ttrades_author_rule": True,
        **NO_CERT,
    }


def examine_all_days(
    groups: dict[str, dict[int, tuple[M1Bar, ...]]],
) -> dict[str, Any]:
    census = run_census(groups)
    if census["observed_days_total"] != 775 or census["state_counts"] != PRESET:
        raise AssertionError("FROZEN_SOURCE_DAY_CASES_DRIFTED")
    entries: list[dict[str, Any]] = []
    first_by_outcome: dict[str, dict[str, Any]] = {}
    for row in census["source_classifications"]:
        if row["classification"] != "FIRST_RETURN_NO_QORE_MSS":
            continue
        ny_day = row["ny_day"]
        source = groups[ny_day]
        result = examine_first_return_day(
            day=ny_day, nine=source[9], ten=source[10],
            first_return_at=datetime.fromisoformat(row["as_of"]),
        )
        entries.append(result)
        first_by_outcome.setdefault(result["terminal_state"], result)
    if len(entries) != 483:
        raise AssertionError("FROZEN_483_REAL_FIRST_RETURN_CASES_DRIFTED")
    by_outcome = Counter(r["terminal_state"] for r in entries)
    if sum(by_outcome.values()) != 483:
        raise AssertionError("ONE_FIRST_RETURN_MISSING_TERMINAL")
    if any(
        r["late_qore_pivot_confirmed_at"] is not None
        and r["terminal_state"] != "LATE_QORE_PROXY_ONLY_NOT_AUTHOR_CERTIFIED"
        for r in entries
    ):
        raise AssertionError("LATE_PROXY_ON_NONELIGIBLE_SOURCE_CASE")
    return {
        "model": MODEL,
        "prereg": PREREG,
        "market_sha256": MARKET_SHA,
        "scope": SOURCE_SCOPE,
        "profile": "TTRADES_NY_AM_2025",
        "input_483_first_return_no_qore_mss": len(entries),
        "cognitive_terminal_states": dict(sorted(by_outcome.items())),
        "first_chronological_example_per_terminal": first_by_outcome,
        "all_real_m1_asof_case_records": entries,
        "conclusions": {
            "author_source_requires_sweep_and_confirmation": True,
            "author_source_requires_qore_1p25_pivot3_on_first_return": False,
            "late_qore_proxy_is_not_author_certification": True,
            "frozen_cog_does_not_extend_first_return_for_late_mss": True,
            "no_new_cognitive_decision_dto_created": True,
        },
        "m3_method_certified": False,
        "m3_cognition_certified": False,
        "m4_setup_families_certified": False,
        "m5_invalidation_certified": False,
        "m6_independent_signatures": "PENDING",
        "trader_certified": False,
        "broker_orders_ack_fills": 0,
        "economic_performance_computed": False,
        "vt31_owns_sizing": False,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if hash_file(args.market) != MARKET_SHA:
        raise ValueError("NAS100_SOURCE_SHA_MISMATCH")
    data, observed = collect_hours(market_rows(args.market))
    if observed != M1_TOTAL:
        raise AssertionError("FROZEN_TOTAL_M1_DRIFT")
    result = examine_all_days(data)
    result["source_m1_total"] = observed
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2)+"\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "source_m1_total": observed,
        "first_returns_with_no_qore_mss": result[
            "input_483_first_return_no_qore_mss"
        ],
        "semantic_outcomes": result["cognitive_terminal_states"],
        "first_examples": result["first_chronological_example_per_terminal"],
        "m3_method_certified": False,
        "m3_cognition_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
