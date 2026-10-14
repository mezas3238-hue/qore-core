#!/usr/bin/env python3
"""Development NAS100 3Y M1 first FVG source census; never calculate returns."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.vt31_m4_m5_ttrades_fvg_path_20261014 import (
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

MODEL = "VT31_TTRADES_M4_M5_FIRST_FVG_SOURCE_PATH_V1"


def census(
    groups: dict[str, dict[int, tuple[Any, ...]]],
) -> dict[str, Any]:
    base: Counter[str] = Counter()
    m4: Counter[str] = Counter()
    m5: Counter[str] = Counter()
    cases: list[dict[str, Any]] = []
    for day, hours in sorted(groups.items()):
        nine, ten = hours.get(9, ()), hours.get(10, ())
        if not complete_hour(day, 9, nine) or not complete_hour(day, 10, ten):
            base["INCOMPLETE_M1_HOURS"] += 1
            continue
        first = adjudicate_day(nine, ten)
        base[first["classification"]] += 1
        if not first["has_source_cognitive_proposal"]:
            continue
        mss_at = datetime.fromisoformat(first["as_of"])
        prefix = tuple(x for x in ten if x.closed_at <= mss_at)
        cog = propose_ttrades_am_cognition(
            as_of=mss_at, history=nine + prefix,
        )
        if cog.state != "CONTEXT_ATTESTED_NOT_CERTIFIED":
            raise ValueError("M2_M3_SOURCE_RECONSTRUCTION_INCONSISTENT")
        if cog.decision is None:
            raise ValueError("M2_M3_SOURCE_COG_DTO_ABSENT")
        path = first_fvg_and_source_path(
            nine=nine, ten=ten, cognition=cog.decision,
        )
        m4[path.state] += 1
        if path.first_fvg_confirmed_at is not None:
            m5[path.source_path_state] += 1
        cases.append({
            "ny_day": day,
            "first_return_mss_at": mss_at.isoformat(),
            "m4_m5_source_only": path.record(),
        })
    n = base["MSS_ATTESTED_CONTEXT_ONLY"]
    assert len(cases) == n
    assert sum(m4.values()) == n
    assert sum(m5.values()) == m4["FVG_GEOMETRY_ATTESTED_NOT_EXECUTABLE"]
    return {
        "model": MODEL,
        "original_3y_m1_sha256": MARKET_SHA,
        "baseline_M2_M3_state_counts": dict(sorted(base.items())),
        "baseline_days_total": sum(base.values()),
        "M2_M3_cognitive_contexts": n,
        "M4_source_state_counts": dict(sorted(m4.items())),
        "M5_hypothetical_source_path_counts": dict(sorted(m5.items())),
        "cognitive_case_evidence": cases,
        "explicit_profile": "TTRADES_NY_AM_2025_QORE_FVG_PROXY",
        "broker_tick_size_attested": False,
        "m1_CE_touch_is_fill": False,
        "broker_order_ACK_count": 0,
        "orders_submitted": 0,
        "entries_executed": 0,
        "trader_certified": False,
        "live_authorized": False,
        "PnL_PF_WR_DD_Sharpe": None,
        "is_fresh_holdout": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    options = parser.parse_args()
    if hash_file(options.market) != MARKET_SHA:
        raise ValueError("ORIGINAL_FROZEN_3Y_M1_HASH_MISMATCH")
    groups, size = collect_hours(market_rows(options.market))
    report = census(groups)
    report["original_M1_count"] = size
    if report["baseline_M2_M3_state_counts"] != {
        "FIRST_RETURN_NO_QORE_MSS": 483,
        "INCOMPLETE_M1_HOURS": 6,
        "MSS_ATTESTED_CONTEXT_ONLY": 128,
        "NO_SWEEP": 65,
        "REJECTED_SOURCE": 1,
        "SWEEP_NO_RETURN": 92,
    }:
        raise ValueError("BASELINE_PR934_SOURCE_CASE_SET_DRIFT")
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "original_M1_count": size,
        "M2_M3_cognitive_contexts": report["M2_M3_cognitive_contexts"],
        "M4_source_state_counts": report["M4_source_state_counts"],
        "M5_hypothetical_source_path_counts":
            report["M5_hypothetical_source_path_counts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
