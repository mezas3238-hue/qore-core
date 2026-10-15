#!/usr/bin/env python3
"""VT31 M4 SOURCE-bound family audit; QORE 3-M1 FVG is NOT author trade proof.

Only observe cognitive/structural facts on original closed M1 streams.
OB, breaker, discretionary displacement and causative-swing stop remain
author-underdefined (not auto-certified, never fabricate entries).
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
    Side,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.m1_execution import (
    confirmed_m1_fvg,
)
from scripts.vt31_m3_ttrades_cog_wait_v2_20261015 import (
    TTradesAmWaitCognitionV2,
)
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    MARKET_SHA,
    M1_TOTAL,
    collect_hours,
    complete_hour,
    hash_file,
    market_rows,
    run_census,
)

PREREG = "67c35f7bf9284cb1feeee9bd54261abec21a6c9f"
FROZEN = {
    "MSS_ATTESTED_CONTEXT_ONLY": 128,
    "FIRST_RETURN_NO_QORE_MSS": 483,
    "SWEEP_NO_RETURN": 92,
    "NO_SWEEP": 65,
    "INCOMPLETE_M1_HOURS": 6,
    "REJECTED_SOURCE": 1,
}
COGNITIVE_ELIGIBILITY = frozenset({
    "WAIT_FOR_CONFIRMATION",
    "QORE_PROXY_OBSERVED_AUTHOR_DISPLACEMENT_UNVERIFIED",
})
M4_NOT_CERTIFIED = "AUTHOR_FOUR_FAMILIES_NOT_FULLY_FORMALIZED"
M5_NOT_CERTIFIED = "AUTHOR_CAUSATIVE_DISPLACEMENT_SWING_UNVERIFIED"


def audit_family_one_day(
    *, day: str, nine: tuple[M1Bar, ...],
    ten: tuple[M1Bar, ...], return_at: datetime,
) -> dict[str, Any]:
    """One day; never classify a future M1 as part of earlier cognitive state."""
    if not complete_hour(day, 9, nine) or not complete_hour(day, 10, ten):
        raise ValueError("INCOMPLETE_H1_CANNOT_VERIFY_M4")
    clock = return_at.astimezone(UTC)
    machine = TTradesAmWaitCognitionV2()
    for bar in nine:
        machine.observe_closed_m1(bar)
    seen: list[M1Bar] = []
    observed: list[dict[str, str]] = []
    source_target_consumed = False
    ambiguous_target_and_fvg_same_m1 = False
    for bar in ten:
        snap = machine.observe_closed_m1(bar)
        seen.append(bar)
        if snap.as_of is None or snap.as_of < clock:
            continue
        if snap.first_return_at is None or snap.bias not in ("LONG", "SHORT"):
            continue
        direction = Side(snap.bias)
        target = (
            max(b.high for b in nine)
            if direction is Side.LONG
            else min(b.low for b in nine)
        )
        target_this_bar = (
            bar.high >= target
            if direction is Side.LONG
            else bar.low <= target
        )
        if snap.as_of == clock:
            # No timestamp-tie speculation: return and target may
            # occur in either intrabar order.
            if target_this_bar:
                source_target_consumed = True
            continue
        if source_target_consumed:
            continue
        fvg = (
            confirmed_m1_fvg(
                session=SessionId.NY_AM,
                first=seen[-3], middle=seen[-2], third=seen[-1],
            )
            if len(seen) >= 3 and all(
                a.closed_at == b.opened_at
                for a, b in zip(seen[-3:-1], seen[-2:], strict=True)
            ) else None
        )
        # This close is at 11 NY, hence out of window for new intent.
        within_close = snap.as_of.astimezone(
            __import__("zoneinfo").ZoneInfo("America/New_York")
        ).hour == 10
        source_still_valid = snap.state in COGNITIVE_ELIGIBILITY
        fvg_matches = bool(
            fvg is not None and fvg.side is direction
        )
        if target_this_bar:
            if fvg_matches and source_still_valid and within_close:
                ambiguous_target_and_fvg_same_m1 = True
            source_target_consumed = True
            continue
        if (
            fvg_matches and source_still_valid and within_close
            and snap.first_return_at == clock
        ):
            observed.append({
                "third_m1_confirmed_at": snap.as_of.isoformat(),
                "side": snap.bias,
                "fvg_source": "QORE_THREE_CLOSED_M1_GEOMETRY_ONLY",
                "author_FVG_within_structure_certified": "NO",
                "broker_fill_evidence": "NO",
            })
    end_state = machine.snapshot().state
    if end_state in {"WAIT_FOR_SWEEP", "WAIT_FOR_RETURN"}:
        raise AssertionError("FROZEN_FIRST_RETURN_LOST_IN_COG_V2")
    return {
        "ny_day": day,
        "first_return_at": clock.isoformat(),
        "first_qore_fvg_asof": (
            observed[0]["third_m1_confirmed_at"] if observed else None
        ),
        "first_qore_fvg_observed_before_source_invalidation": bool(observed),
        "qore_fvg_observations_asof": observed,
        "target_consumed_at_some_observed_M1_after_return": source_target_consumed,
        "intrabar_target_and_fvg_same_m1_unknown": (
            ambiguous_target_and_fvg_same_m1
        ),
        "end_of_session_cognition": end_state,
        "four_source_families": {
            "DISPLACEMENT_RETURN": "AUTHOR_CONCEPT_UNDERDETERMINED_M1_TRIGGER",
            "FVG": (
                "QORE_3_M1_SHAPE_OBSERVED_NOT_AUTHOR_CERTIFIED"
                if observed else "QORE_3_M1_SHAPE_NOT_OBSERVED"
            ),
            "ORDER_BLOCK": "NOT_IMPLEMENTED_AUTHOR_RULE_UNDERDETERMINED",
            "BREAKER_BLOCK": "NOT_IMPLEMENTED_AUTHOR_RULE_UNDERDETERMINED",
        },
        "m4_certification": M4_NOT_CERTIFIED,
        "m5_causative_swing_stop_certification": M5_NOT_CERTIFIED,
        "cognitive_decision_emitted": False,
        "source_author_profile_certified": False,
        "trader_certified": False,
        "orders_fills_created": 0,
    }


def audit_483(groups: dict[str, dict[int, tuple[M1Bar, ...]]]) -> dict[str, Any]:
    census = run_census(groups)
    if census["observed_days_total"] != 775 or census["state_counts"] != FROZEN:
        raise AssertionError("ORIGINAL_TTRADES_COG_CASE_CENSUS_DRIFT")
    cases: list[dict[str, Any]] = []
    groups_out = Counter()
    first_examples: dict[str, dict[str, Any]] = {}
    for row in census["source_classifications"]:
        if row["classification"] != "FIRST_RETURN_NO_QORE_MSS":
            continue
        day = row["ny_day"]
        x = audit_family_one_day(
            day=day, nine=groups[day][9], ten=groups[day][10],
            return_at=datetime.fromisoformat(row["as_of"]),
        )
        cases.append(x)
        category = (
            "FVG_QORE_OBSERVED" if x[
                "first_qore_fvg_observed_before_source_invalidation"
            ] else "NO_QORE_FVG_BEFORE_INVALIDATION"
        )
        groups_out[category] += 1
        first_examples.setdefault(category, x)
        if x["end_of_session_cognition"] == "INVALIDATED_OPPOSITE_RAID":
            groups_out["SOURCE_INVALIDATED_BY_END_IN_SOME_CASES"] += 1
        if x["intrabar_target_and_fvg_same_m1_unknown"]:
            groups_out["FVG_AND_TARGET_SAME_CLOSED_M1_AMBIGUOUS"] += 1
    if len(cases) != 483:
        raise AssertionError("DID_NOT_REVIEW_ALL_FROZEN_483")
    if groups_out["FVG_QORE_OBSERVED"] + groups_out[
        "NO_QORE_FVG_BEFORE_INVALIDATION"
    ] != 483:
        raise AssertionError("M4_FAMILY_CASE_PARTITION_BROKEN")
    if any(x["cognitive_decision_emitted"] or x["trader_certified"] for x in cases):
        raise AssertionError("SOURCE_GEOMETRY_CANNOT_CERTIFY_OR_TRADE")
    return {
        "scope": "VT31_TTRADES_AM_M4_FOUR_FAMILIES_METHOD_COG_READ_ONLY",
        "preregistered_commit": PREREG,
        "source_m1_sha256": MARKET_SHA,
        "source_status": "DEVELOPMENT_ALREADY_SEEN_NOT_OOS",
        "frozen_M3_first_return_cases": len(cases),
        "cognitive_case_partitions_not_performance": dict(sorted(groups_out.items())),
        "lexicographic_first_example_by_class": first_examples,
        "all_real_m1_cognitive_cases": cases,
        "author_source": "https://ttrades.com/the-am-silver-bullet-strategy-on-nq/",
        "author_mentions_all_four_families": True,
        "author_specifies_deterministic_FVG_OB_BB_displacement_priority": False,
        "qore_m1_FVG_is_not_author_certification": True,
        "author_causative_swing_stop_identified": False,
        "m4_certified": False,
        "m5_certified": False,
        "m6_independent_review": "PENDING",
        "method_cognition_certified": False,
        "trader_certified": False,
        "economics_or_sizing_computed": False,
        "broker_orders_fills": 0,
        "live_authorized": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if hash_file(args.market) != MARKET_SHA:
        raise ValueError("ORIGINAL_SOURCE_SHA_MISMATCH")
    groups, observed = collect_hours(market_rows(args.market))
    if observed != M1_TOTAL:
        raise AssertionError("SOURCE_M1_BAR_COUNT_CHANGED")
    verdict = audit_483(groups)
    verdict["source_m1_total"] = observed
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(verdict, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({
        "frozen_cases": len(verdict["all_real_m1_cognitive_cases"]),
        "case_partitions": verdict["cognitive_case_partitions_not_performance"],
        "first_dates": {k: v["ny_day"] for k, v in
                        verdict["lexicographic_first_example_by_class"].items()},
        "m4_certified": False,
        "m5_certified": False,
        "trader_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
