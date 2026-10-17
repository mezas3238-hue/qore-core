#!/usr/bin/env python3
"""PIT research witness for M2 positive G3 hypotheses, independent of G3/OPS.

Audit historical M1 *coverage* between source-pool confirmation and M1 asof.
M1 gaps do NOT prove that price failed to touch liquidity; they force UNKNOWN.
"""
from __future__ import annotations

import argparse
import json
from array import array
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable

from scripts.vt31_ict_cleanroom_cog_real_3y_fast_v1 import _dt, _stream
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    hash_file,
)

PREREG = "2fdef8113e4ea591651933d72288e89287981288"
ORIGINAL_M2_CASEBOOK = "d74b24242c4b8c5656547727b88886ecd1a18243c362d9d366825880bddbfc21"
VERSION = "VT31_M2_298_UNKNOWN_M1_GAP_FORENSIC_INDEPENDENT_RESEARCH_V1"
POSITIVE_COUNT = 761
CONFIRMED_COUNT = 445
UNKNOWN_GAPPED_COUNT = 298
PREVIOUS_POLICY_REJECTED = 18
SESSION_SET = frozenset({"VT31_LONDON", "VT31_NY_AM", "VT31_NY_PM"})


def minute(value: str | datetime) -> int:
    d = _dt(value) if isinstance(value, str) else value
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError("M2_NAIVE_M1_OR_INTERVAL_TIMESTAMP")
    d = d.astimezone(UTC)
    if d.second or d.microsecond:
        raise ValueError("M2_NOT_ALIGNED_TO_CLOSED_M1_MINUTE")
    return int(d.timestamp() // 60)


def source_minutes(
    rows: Iterable[dict[str, Any]], *, expected_m1: int,
) -> array:
    """The source stream is one-time, strictly closed/ordered, never filled."""
    stamps = array("q")
    last: int | None = None
    for row in rows:
        opening = minute(row["opened_at"])
        closing = minute(row["closed_at"])
        if closing - opening != 1 or last is not None and opening <= last:
            raise ValueError("M2_SOURCE_DUPLICATE_OR_UNCLOSED_M1")
        stamps.append(opening)
        last = opening
    if len(stamps) != expected_m1:
        raise AssertionError("M2_CANONICAL_NAS100_M1_COUNT_DRIFT")
    return stamps


def gap_witness(stamps: array, *, start: int, end: int) -> dict[str, Any]:
    """Dense reference interval [source end, first M1 close): no lookahead."""
    if end <= start:
        raise ValueError("M2_SOURCE_POOL_END_MUST_PREDATE_DECISION_ASOF")
    lo, hi = bisect_left(stamps, start), bisect_left(stamps, end)
    cursor = start
    missing = 0
    gap_runs = 0
    longest = 0
    first_missing: int | None = None

    def add_gap(length: int) -> None:
        nonlocal missing, gap_runs, longest, first_missing
        if length <= 0:
            return
        if first_missing is None:
            first_missing = cursor
        gap_runs += 1
        missing += length
        longest = max(longest, length)

    for index in range(lo, hi):
        opened = stamps[index]
        if opened < cursor:
            raise AssertionError("M2_SOURCE_REPEATED_CLOSED_M1_IN_WITNESS")
        add_gap(opened - cursor)
        cursor = opened + 1
    add_gap(end - cursor)
    expected = end - start
    present = hi - lo
    if missing + present != expected:
        raise AssertionError("M2_COVERAGE_ACCOUNTING_DOES_NOT_RECONCILE")
    def time_of(t: int | None) -> str | None:
        return (
            datetime.fromtimestamp(t * 60, UTC).isoformat()
            if t is not None else None
        )
    return {
        "source_end_utc": time_of(start),
        "first_M1_closed_asof_utc": time_of(end),
        "expected_closed_M1_slots": expected,
        "observed_closed_M1_slots": present,
        "missing_M1_slots": missing,
        "gap_runs_count": gap_runs,
        "longest_consecutive_missing_M1": longest,
        "first_missing_opened_utc": time_of(first_missing),
        "complete_closed_M1_between_source_and_asof": missing == 0,
        "broker_market_closed_proven": False,
    }


def sealed_prior_casebook(report: dict[str, Any]) -> list[dict[str, Any]]:
    cases = report["full_2325_first_closed_M1_cases"]
    canonical = json.dumps(cases, sort_keys=True, separators=(",", ":")).encode()
    if sha256(canonical).hexdigest() != ORIGINAL_M2_CASEBOOK:
        raise ValueError("M2_PRIOR_CASEBOOK_NOT_THE_SEALED_2325_JSON")
    if len(cases) != 2325 or report["day_session_casebook_size"] != 2325:
        raise AssertionError("M2_PRIOR_775x3_COHORT_DRIFT")
    if {
        k: sum(c["session"] == k for c in cases)
        for k in SESSION_SET
    } != {k: 775 for k in SESSION_SET}:
        raise AssertionError("M2_PRIOR_SESSION_COUNTS_NOT_775")
    positives = sum(c["original_G3_QORE_DTO_present_not_trade"] for c in cases)
    if positives != POSITIVE_COUNT:
        raise AssertionError("M2_ORIGINAL_G3_DTO_POSITIVES_CHANGED")
    labels = Counter(c["M2_QORE_independent_attestation_state"] for c in cases)
    if labels != Counter({
        "CONFIRMED": CONFIRMED_COUNT, "UNKNOWN": 1827,
        "REJECTED": PREVIOUS_POLICY_REJECTED, "NO_FIRST_M1": 35,
    }):
        raise AssertionError("M2_PRIOR_SEALED_PROVENANCE_LABELS_CHANGED")
    return cases


def analyze_fixed_m2_positive_cases(
    stamps: array,
    report: dict[str, Any],
) -> dict[str, Any]:
    cases = sealed_prior_casebook(report)
    testimonies: list[dict[str, Any]] = []
    summary = defaultdict(Counter)
    by_family = defaultdict(Counter)
    examples = defaultdict(list)
    for case in cases:
        if not case["original_G3_QORE_DTO_present_not_trade"]:
            continue
        state = case["M2_QORE_independent_attestation_state"]
        if state == "REJECTED":
            # These 18 require alternative prior-cash policy, adjudicated in
            # sealed independent report #38976680827; do not conflate gaps.
            continue
        if state not in ("CONFIRMED", "UNKNOWN"):
            raise AssertionError("M2_ORIGINAL_POSITIVE_INVALID_PREVIOUS_STATE")
        family = case["original_G3_draw_family"]
        pools = [
            p for p in case["source_pool_six_independent_M1_witnesses"]
            if p["family"] == family
        ]
        if len(pools) != 1:
            raise AssertionError("M2_POSITIVE_NO_UNIQUE_INDEPENDENT_SOURCE_POOL")
        pool = pools[0]
        if pool["level"] is None:
            raise AssertionError("M2_GAPPED_POSITIVE_HAS_NO_RECONSTRUCTED_LEVEL")
        if state == "CONFIRMED" and pool["state"] != "UNCONSUMED":
            raise AssertionError("M2_CONFIRMED_NOT_IN_UNCONSUMED_POOL")
        if state == "UNKNOWN" and (
            pool["state"] != "UNKNOWN"
            or "POOL_AVAILABILITY_UNVERIFIABLE"
            not in case["M2_QORE_independent_attestation_reasons"]
            or pool["reason"] != "POST_SOURCE_M1_COVERAGE_GAPPED"
        ):
            raise AssertionError("M2_UNKNOWN_NOT_FROM_POSTSOURCE_M1_GAP")
        w = gap_witness(
            stamps,
            start=minute(pool["source_end"]),
            end=minute(case["first_closed_M1_utc"]),
        )
        if (state == "CONFIRMED") != w["complete_closed_M1_between_source_and_asof"]:
            raise AssertionError("M2_REPLAY_SOURCE_COMPLETENESS_CONTRADICTS_ORIGINAL")
        key = case["session"]
        bucket = "MISSING" if w["missing_M1_slots"] else "COMPLETE"
        summary[key][state] += 1
        summary[key][f"gap_{bucket}"] += 1
        summary[key]["missing_M1_sum"] += w["missing_M1_slots"]
        summary[key]["max_single_gap_minutes"] = max(
            summary[key]["max_single_gap_minutes"],
            w["longest_consecutive_missing_M1"],
        )
        by_family[key][f"{family}:{state}"] += 1
        if state == "UNKNOWN" and len(examples[key]) < 5:
            examples[key].append({
                "day": case["ny_day"],
                "source": family,
                "first_gap": w["first_missing_opened_utc"],
                "missing_M1": w["missing_M1_slots"],
                "largest_run": w["longest_consecutive_missing_M1"],
            })
        testimonies.append({
            "ny_day": case["ny_day"],
            "session": key,
            "G3_positive_hypothesis_NOT_TRADE": True,
            "source_family": family,
            "original_QORE_M2_state": state,
            "original_QORE_draw_price": case["original_G3_draw_price"],
            "independent_M1_gap_witness": w,
            "source_fact_author_method_certified": False,
            "broker_trade_authorized": False,
        })
    if len(testimonies) != CONFIRMED_COUNT + UNKNOWN_GAPPED_COUNT:
        raise AssertionError("M2_EXPECTED_445_PLUS_298_POSITIVE_SOURCE_CASES")
    if sum(v["CONFIRMED"] for v in summary.values()) != CONFIRMED_COUNT:
        raise AssertionError("M2_CONFIRMED_445_GAP_INTEGRITY_FAILED")
    if sum(v["UNKNOWN"] for v in summary.values()) != UNKNOWN_GAPPED_COUNT:
        raise AssertionError("M2_UNKNOWN_298_GAP_INTEGRITY_FAILED")
    if set(summary) != SESSION_SET:
        raise AssertionError("M2_MISSING_ONE_OR_MORE_SILVER_BULLET_SESSIONS")
    testimony_sha = sha256(json.dumps(
        testimonies, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    return {
        "version": VERSION,
        "preregistered_before_code": PREREG,
        "canonical_market_sha256": MARKET_SHA,
        "historical_original_closed_M1": len(stamps),
        "prior_source_first_M1_casebook_sha256": ORIGINAL_M2_CASEBOOK,
        "prior_775x3_cases_verified": len(cases),
        "original_G3_first_minute_positive_not_trades": POSITIVE_COUNT,
        "original_M2_QORE_CONFIRMED_source_only": CONFIRMED_COUNT,
        "original_M2_QORE_UNKNOWN_due_to_missing_M1": UNKNOWN_GAPPED_COUNT,
        "prior_nominal_calendar_disagreement_cases_kept_separate": (
            PREVIOUS_POLICY_REJECTED
        ),
        "independent_M1_gap_testimony_case_count": len(testimonies),
        "independent_M1_gap_testimony_SHA256": testimony_sha,
        "per_session_closed_M1_gap_counts": {
            k: dict(sorted(v.items())) for k, v in sorted(summary.items())
        },
        "per_session_G3_source_family": {
            k: dict(sorted(v.items())) for k, v in sorted(by_family.items())
        },
        "illustrative_first_five_UNKNOWN_gaps_per_session": dict(examples),
        "full_743_closed_M1_interval_testimonies": testimonies,
        "source_fact_certified_by_ICT_TTrades": False,
        "QORE_G3_COG_or_OPS_modified": False,
        "M2_author_certified": False,
        "M3_M4_M5_author_certified": False,
        "M6_two_independent_human_signatures": False,
        "M7_3_Silver_Bullet_sessions_certified": False,
        "orders": 0,
        "sizing": 0,
        "PnL": None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", type=Path, required=True)
    ap.add_argument("--original-m2-casebook", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if hash_file(args.market) != MARKET_SHA:
        raise ValueError("M2_M1_MARKET_SOURCE_SHA_DRIFT")
    report = json.loads(args.original_m2_casebook.read_text(encoding="utf-8"))
    source = source_minutes(_stream(args.market), expected_m1=M1_TOTAL)
    result = analyze_fixed_m2_positive_cases(source, report)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "M1": result["historical_original_closed_M1"],
        "confirmed": result["original_M2_QORE_CONFIRMED_source_only"],
        "unknown": result["original_M2_QORE_UNKNOWN_due_to_missing_M1"],
        "cases_sha": result["independent_M1_gap_testimony_SHA256"],
        "stats": result["per_session_closed_M1_gap_counts"],
        "method_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
