"""VT31 P0: partial identification of CE-price contacts from frozen paired ledger.

This tool NEVER assigns fills or PnL. Unknown source chronology remains unknown.
All lower/upper limits refer solely to the already tested HYPOTHETICAL
NAS100 MID +/- 0.80 fixed spread; do not describe as historical Bid/Ask.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "qore.vt31.partial_identification.fixed_spread_source.v1"
SOURCE_SHA = "0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa"
ORIGINAL_RUN_SHA = "90deb73a47cbc09b88580595800607f2516323b7"
N = 2140
SOURCE_WINDOWS = {
    "VT31_LONDON": 766, "VT31_NY_AM": 721, "VT31_NY_PM": 653,
}
ARMS = ("A", "B")
KNOWN_LABELS = {"VALID_CE", "INVALIDATED", "INDETERMINATE",
                "TARGET_BEFORE_CE", "EXPIRED"}
B_UNKNOWN_TERMINALS = {
    "CE_AND_CANCELLATION_SAME_M1_UNKNOWN",
    "UNPROVEN_PROTECTED_STOP_GEOMETRY",
}


def _state(record: dict[str, Any], arm: str) -> tuple[int, int, int]:
    label = record.get(arm + "_class")
    if label not in KNOWN_LABELS:
        raise ValueError("unrecognized or missing " + arm + " class")
    key = arm + "_original_clean_CE_quote_side_reachable_1p60"
    hit = record.get(key)
    if type(hit) is not bool:
        raise ValueError("missing/nonboolean spread-side observation")
    if hit and label != "VALID_CE":
        raise ValueError("price-side CE declared on non-clean candidate")
    lower = int(hit)
    unknown = int(label == "INDETERMINATE")
    return lower, int(hit or unknown), unknown


def _summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    for row in records:
        a_lo, a_hi, a_u = _state(row, "A")
        b_lo, b_hi, b_u = _state(row, "B")
        counts["n"] += 1
        counts["A_known"] += a_lo
        counts["B_known"] += b_lo
        counts["A_unknown"] += a_u
        counts["B_unknown"] += b_u
        counts["A_max"] += a_hi
        counts["B_max"] += b_hi
        counts["paired_lower_diff"] += b_lo - a_hi
        counts["paired_upper_diff"] += b_hi - a_lo
        counts["known_diff"] += b_lo - a_lo
        if a_lo and b_lo:
            counts["both_known"] += 1
        elif a_lo:
            counts["A_only_known"] += 1
        elif b_lo:
            counts["B_only_known"] += 1
        if a_u and b_u:
            counts["both_unknown"] += 1
        elif a_u:
            counts["A_only_unknown"] += 1
        elif b_u:
            counts["B_only_unknown"] += 1
    n = counts["n"]
    if n <= 0:
        raise ValueError("missing source candidate records")
    if counts["paired_lower_diff"] > counts["paired_upper_diff"]:
        raise AssertionError("impossible partial identification ordering")
    if counts["known_diff"] != counts["B_known"] - counts["A_known"]:
        raise AssertionError("known totals drift")
    return {
        **dict(sorted(counts.items())),
        "lower_diff_percentage_points": round(
            100 * counts["paired_lower_diff"] / n, 6),
        "upper_diff_percentage_points": round(
            100 * counts["paired_upper_diff"] / n, 6),
        "observed_known_diff_percentage_points": round(
            100 * counts["known_diff"] / n, 6),
        "B_unknown_pct": round(100 * counts["B_unknown"] / n, 6),
        "preregistered_5pp_guaranteed_over_missingness": (
            100 * counts["paired_lower_diff"] / n >= 5),
    }


def analyze(data: dict[str, Any]) -> dict[str, Any]:
    """Strict artifact lineage + fully paired, per-window identification bounds."""
    if data.get("market_M1") != 1059784 or data.get("base") != (
        "VT31_NAS100_OWNER_3Y_BASE_001"
    ):
        raise ValueError("not the original development 3Y source ledger")
    if (data.get("registered_trader_count") != 1
            or data.get("trader_id") != "VT31"
            or data.get("models") != ["LONDON", "NEW_YORK"]):
        raise ValueError("split or altered VT31 trader identity")
    if data.get("cog_and_OPS_M1_calls") != 137160:
        raise ValueError("source COG/OPS call drift")
    if data.get("first_FVG_same_in_both") != SOURCE_WINDOWS:
        raise ValueError("missing or altered same-source candidate windows")
    if data.get("original_P0_pending_without_COG") != 0:
        raise ValueError("P0 original fail-closed regression")
    q = data.get("fixed_spread_1p60_scenario")
    if not isinstance(q, dict):
        raise ValueError("scenario missing")
    if (q.get("spread_price_points_applied_to_all_historical_M1") != "1.60"
            or q.get("hypothesis_historical_M1_price_basis") !=
            "MID_ASSUMED_NOT_VERIFIED"
            or q.get("source_symbol") != "NAS100"
            or q.get("screenshot_symbol") != "NDX100"
            or q.get("source_symbol_equivalence_broker_verified") is not False
            or q.get("historical_actual_bid_ask_available") is not False
            or q.get("broker_confirmed_fill_count") != 0
            or q.get("not_full_historical_quote_series") is not True):
        raise ValueError("unsafe quote scenario or unsupported broker provenance")
    g = data.get("guards", {})
    if (g.get("broker_fills_confirmed") != 0
            or g.get("profit_factor_drawdown_sharpe") is not None
            or g.get("holdout_sealed") is not True
            or g.get("live_authorized") is not False):
        raise ValueError("unexpected economic, live or holdout claim")
    p = data.get("preregistered_primary_endpoint")
    if (not isinstance(p, dict)
            or p.get("population_original_first_FVGs") != N
            or p.get("min_net_B_advantage_percentage_points") != 5.0
            or p.get("max_B_indeterminate_percentage") != 10.0
            or p.get("source_only_two_part_gate_met") is not False):
        raise ValueError("changed preregistered guard")
    rows = data.get("paired_candidate_records")
    if not isinstance(rows, list) or len(rows) != N:
        raise ValueError("not 2140 paired candidate rows")
    seen = set()
    groups: dict[str, list[dict[str, Any]]] = {
        session: [] for session in SOURCE_WINDOWS
    }
    b_unknown_reasons: Counter[str] = Counter()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid paired record")
        session = row.get("session_window")
        if session not in groups:
            raise ValueError("unexpected session")
        identity = (row.get("ny_day"), session,
                    row.get("source_fvg_confirmed_at"))
        if any(not isinstance(item, str) or not item for item in identity):
            raise ValueError("missing matched source identity")
        if identity in seen:
            raise ValueError("duplicate first FVG source identity")
        seen.add(identity)
        if row.get("real_broker_fill_proven") is not False:
            raise ValueError("false broker execution evidence in source ledger")
        if row.get("B_class") == "INDETERMINATE":
            cause = row.get("B_research_terminal")
            if cause not in B_UNKNOWN_TERMINALS:
                raise ValueError("unclassified B unknown cause")
            b_unknown_reasons[cause] += 1
        groups[session].append(row)
    if {key: len(value) for key, value in groups.items()} != SOURCE_WINDOWS:
        raise ValueError("unbalanced original session-source identities")
    total = _summary(rows)
    sessions = {key: _summary(value) for key, value in groups.items()}
    if (total["A_known"] != 232 or total["B_known"] != 577
            or total["A_unknown"] != 637 or total["B_unknown"] != 670):
        raise ValueError("frozen source counts differ: do NOT silently rewrite")
    if b_unknown_reasons != {
        "CE_AND_CANCELLATION_SAME_M1_UNKNOWN": 619,
        "UNPROVEN_PROTECTED_STOP_GEOMETRY": 51,
    }:
        raise ValueError("B unknown cause decomposition changed")
    for field in ("n", "A_known", "B_known", "A_unknown", "B_unknown",
                  "paired_lower_diff", "paired_upper_diff", "known_diff"):
        if sum(w[field] for w in sessions.values()) != total[field]:
            raise AssertionError("session reconciliation failed: " + field)
    observed = q.get("price_only_original_clean_CE_quote_side_stress_by_window", {})
    for key, row in sessions.items():
        if (observed.get(key + "|A_QUOTE_SIDE_REACHABLE") != row["A_known"]
                or observed.get(key + "|B_QUOTE_SIDE_REACHABLE") != row["B_known"]):
            raise ValueError("summary incompatible with all 2140 paired rows")
    return {
        "schema": SCHEMA,
        "source_market_sha256_reported_not_rehashed_in_this_step": SOURCE_SHA,
        "parent_scenario_source_commit": ORIGINAL_RUN_SHA,
        "data_type": "HYPOTHETICAL_MID_1P60_PRICE_ONLY",
        "analysis": "logical_partial_identification_not_confidence_interval",
        "description": (
            "Every known price-side contact is 1; every known no-contact is 0; "
            "each INDETERMINATE is [0,1]. The sharp algebraic envelope is "
            "computed candidate-by-candidate without outcomes imputation. "
            "Physical joint feasibility can only tighten these bounds."
        ),
        "all": total,
        "by_window": sessions,
        "B_unknown_causes": dict(sorted(b_unknown_reasons.items())),
        "precommitted_B_unknown_max_pct": 10.0,
        "precommitted_B_unknown_gate_passed": False,
        "actual_bid_ask_ticks_used": False,
        "broker_fills_count": 0,
        "net_profit_factor": None,
        "net_expectancy": None,
        "net_drawdown": None,
        "holdout_opened": False,
        "production_authorized": False,
        "decision": "INSUFFICIENT_ECONOMIC_EXECUTION_EVIDENCE",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyze(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "N": result["all"]["n"],
        "A_known": result["all"]["A_known"],
        "B_known": result["all"]["B_known"],
        "A_unknown": result["all"]["A_unknown"],
        "B_unknown": result["all"]["B_unknown"],
        "lower_pp": result["all"]["lower_diff_percentage_points"],
        "upper_pp": result["all"]["upper_diff_percentage_points"],
        "economic_edge_demonstrated": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
