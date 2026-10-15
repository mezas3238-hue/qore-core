#!/usr/bin/env python3
"""VT31 M5 author swing stop causation: fail closed, no numeric stop/sizing.

A QORE three-candle pivot is NEVER the author's causative displacement
swing until an independent source & cognition causal witness establishes it.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar, Side
from scripts.vt31_m4_source_family_cognitive_witness_20261015 import (
    audit_family_one_day,
)
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    collect_hours,
    hash_file,
    market_rows,
    run_census,
)

PREREG = "ba9b50abca2ede965975f6aacfcdab8a057a3735"
FROZEN = {
    "MSS_ATTESTED_CONTEXT_ONLY": 128,
    "FIRST_RETURN_NO_QORE_MSS": 483,
    "SWEEP_NO_RETURN": 92,
    "NO_SWEEP": 65,
    "INCOMPLETE_M1_HOURS": 6,
    "REJECTED_SOURCE": 1,
}
SWING_UNVERIFIED = "AUTHOR_CAUSATIVE_SWING_NOT_ESTABLISHED"


def confirmed_qore_pivots_before(
    ten: tuple[M1Bar, ...],
    side: Side,
    *,
    source_return_at: datetime,
    fvg_confirmed_at: datetime,
) -> tuple[datetime, ...]:
    """Strict three-M1 local pivots fully confirmed BEFORE FVG close.

    Only possible STRUCTURE CANDIDATES, not a stop and not author doctrine.
    """
    if source_return_at.tzinfo is None or fvg_confirmed_at.tzinfo is None:
        raise ValueError("AWARE_ASOF_REQUIRED")
    since = source_return_at.astimezone(UTC)
    until = fvg_confirmed_at.astimezone(UTC)
    if since >= until:
        raise ValueError("FVG_CANNOT_PRECEDE_RETURN_CAUSALLY")
    found: list[datetime] = []
    for left, pivot, right in zip(ten, ten[1:], ten[2:], strict=False):
        if left.closed_at != pivot.opened_at or pivot.closed_at != right.opened_at:
            # No invented local swing across a missing M1.
            continue
        if left.closed_at < since or right.closed_at >= until:
            continue
        if side is Side.LONG:
            valid = pivot.low < left.low and pivot.low < right.low
        else:
            valid = pivot.high > left.high and pivot.high > right.high
        if valid:
            found.append(right.closed_at)
    return tuple(found)


def examine_source_day(
    *, day: str, nine: tuple[M1Bar, ...],
    ten: tuple[M1Bar, ...], return_at: datetime,
) -> dict[str, Any]:
    base = audit_family_one_day(
        day=day, nine=nine, ten=ten, return_at=return_at,
    )
    fvg_stamp = base["first_qore_fvg_asof"]
    if fvg_stamp is None:
        state = "NO_QORE_FVG_EVIDENCE"
        pivots: tuple[datetime, ...] = ()
    else:
        side = Side(base["qore_fvg_observations_asof"][0]["side"])
        pivots = confirmed_qore_pivots_before(
            ten, side, source_return_at=return_at,
            fvg_confirmed_at=datetime.fromisoformat(fvg_stamp),
        )
        state = (
            "NO_QORE_PIVOT_CANDIDATE" if not pivots
            else "ONE_QORE_PIVOT_CAUSATION_NOT_PROVEN" if len(pivots) == 1
            else "MULTIPLE_QORE_PIVOTS_CAUSATION_UNDETERMINED"
        )
    return {
        "ny_day": day,
        "first_return_at": return_at.astimezone(UTC).isoformat(),
        "m4_first_qore_fvg_geometry_at": fvg_stamp,
        "m5_cognitive_evidence_class": state,
        "pivot_confirmed_at_only_qore_not_author": [
            p.isoformat() for p in pivots
        ],
        "m5_author_causative_swing_status": SWING_UNVERIFIED,
        "authorial_stop_price": None,
        "sweep_extreme_not_assumed_causative": True,
        "c2_full_wick_not_assumed_authorial": True,
        "method_certified": False,
        "cognition_certified": False,
        "stop_or_order_issued": False,
        "sizing_assigned": False,
        "trader_certified": False,
    }


def audit_483(groups: dict[str, dict[int, tuple[M1Bar, ...]]]) -> dict[str, Any]:
    census = run_census(groups)
    if census["observed_days_total"] != 775 or census["state_counts"] != FROZEN:
        raise AssertionError("FROZEN_SOURCE_CENSUS_CHANGED")
    result: list[dict[str, Any]] = []
    states: Counter[str] = Counter()
    samples: dict[str, dict[str, Any]] = {}
    for row in census["source_classifications"]:
        if row["classification"] != "FIRST_RETURN_NO_QORE_MSS":
            continue
        day = row["ny_day"]
        record = examine_source_day(
            day=day, nine=groups[day][9], ten=groups[day][10],
            return_at=datetime.fromisoformat(row["as_of"]),
        )
        result.append(record)
        states[record["m5_cognitive_evidence_class"]] += 1
        samples.setdefault(record["m5_cognitive_evidence_class"], record)
    if len(result) != 483 or sum(states.values()) != 483:
        raise AssertionError("FROZEN_483_SWING_REVIEW_CHANGED")
    if states["NO_QORE_FVG_EVIDENCE"] != 26:
        raise AssertionError("ORIGINAL_M4_FVG_GEOMETRY_DENOMINATOR_CHANGED")
    if any(
        x["authorial_stop_price"] is not None or x["method_certified"]
        or x["stop_or_order_issued"] for x in result
    ):
        raise AssertionError("QORE_PIVOT_FALSELY_CERTIFIED_AS_CAUSATIVE_SWING")
    return {
        "schema": "VT31_M5_AUTHOR_CAUSATIVE_SWING_SOURCE_WITNESS_V1",
        "prereg_commit": PREREG,
        "market_sha256": MARKET_SHA,
        "research_development_not_OOS": True,
        "cases_frozen": len(result),
        "m5_states": dict(sorted(states.items())),
        "lexicographic_first_real_case_per_state": samples,
        "all_source_cognitive_case_records": result,
        "primary_source": "https://ttrades.com/the-am-silver-bullet-strategy-on-nq/",
        "method_M5_certified": False,
        "cognition_M5_certified": False,
        "trader_certified": False,
        "M6_signers": "NOT_VERIFIED_TWO_DISTINCT_AUTHORIZED",
        "broker_orders_ack_fills": 0,
        "sizing_assigned": False,
        "live_authorized": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--market", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if hash_file(args.market) != MARKET_SHA:
        raise ValueError("NAS100_SOURCE_SHA_MISMATCH")
    groups, n = collect_hours(market_rows(args.market))
    if n != M1_TOTAL:
        raise AssertionError("ORIGINAL_NAS100_SOURCE_BAR_COUNT_CHANGED")
    report = audit_483(groups)
    report["source_m1_total"] = n
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({
        "cases_frozen": report["cases_frozen"],
        "m5_states": report["m5_states"],
        "first_real_dates": {
            k: v["ny_day"]
            for k, v in report["lexicographic_first_real_case_per_state"].items()
        },
        "method_M5_certified": False,
        "cognition_M5_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
