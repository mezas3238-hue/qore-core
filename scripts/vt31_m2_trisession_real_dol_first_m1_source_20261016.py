#!/usr/bin/env python3
"""Real NAS100 M1 source-provenance court for three Silver Bullet sessions.

Source QORE pools are NOT author-ICT DOL doctrine, MSS, signals or trades.
At exactly first closed M1 of each window, compare an independently built
source-pool witness against the original native G3 COG output, or record WAIT.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, deque
from collections.abc import Iterable
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    NEW_YORK,
    M1Bar,
    SessionId,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.trader import VT31Trader
from scripts.vt31_ict_cleanroom_cog_real_3y_fast_v1 import _bar, _stream
from scripts.vt31_ict_dol_source_v1_20261014 import attest_ict_dol_source
from scripts.vt31_trisession_online_real_g3_cog_20261015 import (
    sealed_ledger_index,
)
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    hash_file,
)

PREREG = "2e24b6ac2f08644441116d1df1f27ef8e011e161"
VERSION = "VT31_M2_REAL_FIRST_CLOSED_M1_DOL_QORE_PROVENANCE_3_SESSIONS_V1"
FIRST_HOURS = {3: SessionId.LONDON, 10: SessionId.NY_AM, 14: SessionId.NY_PM}
POOL_FAMILIES = {
    "PRIOR_NY_CASH_SESSION_HIGH", "PRIOR_NY_CASH_SESSION_LOW",
    "ASIA_NY_CLOCK_HIGH", "ASIA_NY_CLOCK_LOW",
    "LONDON_NY_CLOCK_HIGH", "LONDON_NY_CLOCK_LOW",
}


def first_m1_case(
    *,
    trader: VT31Trader,
    bar: M1Bar,
    history: tuple[M1Bar, ...],
    session: SessionId,
    observation: Any,
) -> dict[str, Any]:
    """Report independently sourced facts AFTER the original G3 response."""
    if not history or history[-1] is not bar:
        raise AssertionError("DOL_HISTORY_LAST_M1_SOURCE_NOT_THE_ASOF_CANDLE")
    if session is not FIRST_HOURS.get(bar.opened_at.astimezone(NEW_YORK).hour):
        raise AssertionError("DOL_WRONG_SESSION_CLOCK")
    if bar.opened_at.astimezone(NEW_YORK).minute != 0:
        raise AssertionError("DOL_NOT_FIRST_SESSION_M1")
    if any(x.closed_at > bar.closed_at for x in history):
        raise AssertionError("DOL_FUTURE_M1_IN_SOURCE_HISTORY")
    if trader.cognition.framework_policy != G3_MSS_FRAMEWORK_POLICY:
        raise AssertionError("DOL_NOT_G3_ORIGINAL_PRODUCER")
    assessment = observation.cognition
    dto = assessment.decision if assessment is not None else None
    attestation = attest_ict_dol_source(
        as_of=bar.closed_at,
        session=session,
        history=history,
        cognition=dto,
    )
    if len(attestation.pools) != 6:
        raise AssertionError("DOL_EXPECTED_ALL_SIX_INDEPENDENT_SOURCE_POOLS")
    if {pool.family for pool in attestation.pools} != POOL_FAMILIES:
        raise AssertionError("DOL_SOURCE_POOL_FAMILY_DRIFT")
    if session is SessionId.LONDON:
        for p in attestation.pools:
            if p.family.startswith("LONDON_NY_CLOCK_") and (
                p.state != "UNKNOWN" or p.level is not None
            ):
                raise AssertionError("LONDON_03H_MUST_NOT_READ_05H_FUTURE")
    if observation.source_wait_reason is not None and assessment is not None:
        raise AssertionError("DOL_COG_EXECUTED_AFTER_NATIVE_SOURCE_WAIT")
    if dto is None and attestation.state == "CONFIRMED":
        raise AssertionError("DOL_CONFIRMED_WITHOUT_ORIGINAL_COG_DECISION")
    if attestation.state not in ("CONFIRMED", "UNKNOWN", "REJECTED"):
        raise AssertionError("DOL_UNEXPECTED_SOURCE_VERDICT")
    matching_pool = next(
        (p for p in attestation.pools if dto and p.family == dto.draw_family),
        None,
    )
    temporal_source_end_lead_minutes = (
        int(
            (matching_pool.source_end - dto.draw_level_observed_at)
            .total_seconds() // 60
        ) if matching_pool is not None and dto is not None else None
    )
    ny = bar.opened_at.astimezone(NEW_YORK)
    return {
        "ny_day": ny.date().isoformat(),
        "session": session.value,
        "first_closed_M1_utc": bar.closed_at.isoformat(),
        "original_native_G3_invoked_at_first_m1": assessment is not None,
        "original_G3_QORE_DTO_present_not_trade": dto is not None,
        "original_G3_draw_family": dto.draw_family if dto is not None else None,
        "original_G3_draw_price": (
            str(dto.draw_target) if dto is not None else None
        ),
        "original_G3_draw_level_observed_at": (
            dto.draw_level_observed_at.isoformat()
            if dto is not None else None
        ),
        "matched_independent_source_end_utc": (
            matching_pool.source_end.isoformat()
            if matching_pool is not None else None
        ),
        "source_end_minus_cog_original_time_minutes": (
            temporal_source_end_lead_minutes
        ),
        "native_M0_source_wait": observation.source_wait_reason,
        "nyam_h1_09_completed_at_10_if_applicable": (
            observation.source_h1_09_complete
        ),
        "M2_QORE_independent_attestation_state": attestation.state,
        "M2_QORE_independent_attestation_reasons": list(attestation.reasons),
        "source_pool_six_independent_M1_witnesses": [
            p for p in attestation.record()["pools"]
        ],
        "ict_author_dol_certified": False,
        "mss_author_displacement_certified": False,
        "entry_author_certified": False,
        "broker_trades_or_fills": 0,
        "sizing": 0,
    }


def stream_m2_first_bar_witnesses(
    rows: Iterable[dict[str, Any]],
    *, expected_m1: int,
) -> tuple[dict[tuple[str, SessionId], dict[str, Any]], int]:
    """M1 streaming admits no ledger, full-hour futures, or backtest trades."""
    trader = VT31Trader(
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
        strict_source_admission=True,
    )
    # Source prior weekday 09:30-16:00 is <=3 NY calendar days earlier.
    # Eight calendar days is a strictly generous *past-only* history cap.
    history: deque[M1Bar] = deque()
    cases: dict[tuple[str, SessionId], dict[str, Any]] = {}
    previous_opened: datetime | None = None
    n = 0
    for row in rows:
        bar = _bar(row)
        if previous_opened is not None and bar.opened_at <= previous_opened:
            raise ValueError("M2_SOURCE_NON_MONOTONIC_REAL_M1")
        previous_opened = bar.opened_at
        history.append(bar)
        cutoff = bar.opened_at - timedelta(days=8)
        while history and history[0].opened_at < cutoff:
            history.popleft()
        n += 1
        native = trader.on_closed_m1(bar)
        ny = bar.opened_at.astimezone(NEW_YORK)
        session = FIRST_HOURS.get(ny.hour)
        if session is None or ny.minute != 0:
            continue
        key = (ny.date().isoformat(), session)
        if key in cases:
            raise ValueError("DUPLICATE_FIRST_CLOSED_M1_FOR_DAY_SESSION")
        cases[key] = first_m1_case(
            trader=trader,
            bar=bar,
            history=tuple(history),
            session=session,
            observation=native,
        )
    if n != expected_m1 or trader.total_closed_m1 != n:
        raise AssertionError("M2_CANONICAL_M1_BARS_NOT_FULLY_OBSERVED")
    return cases, n


def adjudicate_m2_posthoc(
    cases: dict[tuple[str, SessionId], dict[str, Any]],
    coverage: dict[str, Any],
    n: int,
) -> dict[str, Any]:
    if n != M1_TOTAL:
        raise AssertionError("M2_ORIGINAL_NAS100_M1_COUNT_WRONG")
    independent_index = sealed_ledger_index(coverage)
    if not set(cases).issubset(independent_index):
        raise AssertionError("M2_UNEXPECTED_CASE_OUTSIDE_SEALED_775_DAYS")
    expanded: list[dict[str, Any]] = []
    for (day, sess), source in sorted(
        independent_index.items(), key=lambda item: (item[0][0], item[0][1].value)
    ):
        raw = cases.get((day, sess))
        if raw is None:
            # This is NOT permission to infer CFD broker holiday/closure.
            raw = {
                "ny_day": day,
                "session": sess.value,
                "first_closed_M1_utc": None,
                "original_native_G3_invoked_at_first_m1": False,
                "original_G3_QORE_DTO_present_not_trade": False,
                "original_G3_draw_family": None,
                "original_G3_draw_price": None,
                "original_G3_draw_level_observed_at": None,
                "matched_independent_source_end_utc": None,
                "source_end_minus_cog_original_time_minutes": None,
                "native_M0_source_wait": "NO_FIRST_M1_SOURCE_UNKNOWN",
                "nyam_h1_09_completed_at_10_if_applicable": None,
                "M2_QORE_independent_attestation_state": "NO_FIRST_M1",
                "M2_QORE_independent_attestation_reasons": [
                    "NO_FIRST_CLOSED_SOURCE_M1_OR_WINDOW_MISSING",
                ],
                "source_pool_six_independent_M1_witnesses": [],
                "ict_author_dol_certified": False,
                "mss_author_displacement_certified": False,
                "entry_author_certified": False,
                "broker_trades_or_fills": 0,
                "sizing": 0,
            }
            if source["observed_window_m1"] == 60:
                raise AssertionError("M2_MISSING_FIRST_M1_BUT_SOURCE_COMPLETE")
        expanded.append({
            **raw,
            "posthoc_covered_window_m1_count": source["observed_window_m1"],
            "posthoc_complete_window_m1": source["window_m1_complete"],
            "posthoc_ttrades_nyam_09h_complete": (
                source["h1_09_ttrades_complete"]
            ),
            "method_certified": False,
            "cognition_certified": False,
        })
    if len(expanded) != 2325:
        raise AssertionError("M2_THREE_SESSION_DAY_SOURCE_CASEBOOK_DRIFT")
    stats: dict[str, Any] = {}
    for sess in SessionId:
        group = [x for x in expanded if x["session"] == sess.value]
        state = Counter(x["M2_QORE_independent_attestation_state"] for x in group)
        pools = Counter()
        reasons = Counter()
        for case in group:
            for item in case["source_pool_six_independent_M1_witnesses"]:
                pools[f"{item['family']}:{item['state']}"] += 1
            for reason in case["M2_QORE_independent_attestation_reasons"]:
                reasons[reason] += 1
        if sum(state.values()) != 775:
            raise AssertionError("M2_INCOMPLETE_SESSION_COHORT")
        if sess is SessionId.LONDON and any(
            case["source_pool_six_independent_M1_witnesses"] and any(
                p["state"] != "UNKNOWN"
                for p in case["source_pool_six_independent_M1_witnesses"]
                if p["family"].startswith("LONDON_NY_CLOCK_")
            ) for case in group
        ):
            raise AssertionError("M2_LONDON_FUTURE_RANGE_ADMITTED")
        stats[sess.value] = {
            "reference_anchor_days": len(group),
            "first_M1_witness_present": sum(
                x["first_closed_M1_utc"] is not None for x in group
            ),
            "native_COG_called": sum(
                x["original_native_G3_invoked_at_first_m1"] for x in group
            ),
            "native_QORE_G3_DTO_positive_not_trades": sum(
                x["original_G3_QORE_DTO_present_not_trade"] for x in group
            ),
            "research_QORE_DOL_attestation_states": dict(sorted(state.items())),
            "QORE_source_pool_M1_status_by_family": dict(sorted(pools.items())),
            "M2_source_reasons": dict(sorted(reasons.items())),
            "ict_author_dol_certified": False,
        }
    rejected = [
        {
            "day": case["ny_day"],
            "session": case["session"],
            "first_closed_M1_utc": case["first_closed_M1_utc"],
            "original_G3_draw_family": case["original_G3_draw_family"],
            "original_G3_draw_price": case["original_G3_draw_price"],
            "original_G3_draw_level_observed_at": (
                case["original_G3_draw_level_observed_at"]
            ),
            "source_interval_closed_at": (
                case["matched_independent_source_end_utc"]
            ),
            "source_end_minus_cog_time_minutes": (
                case["source_end_minus_cog_original_time_minutes"]
            ),
            "reason": case["M2_QORE_independent_attestation_reasons"],
            "author_certified": False,
        }
        for case in expanded
        if case["M2_QORE_independent_attestation_state"] == "REJECTED"
    ]
    # This independently observable count is not a target or tuning threshold.
    if any(
        c["source_end_minus_cog_time_minutes"] is None
        for c in rejected
        if "COG_DOL_ANNOUNCED_BEFORE_SOURCE_CLOSE" in c["reason"]
    ):
        raise AssertionError("M2_SOURCE_REJECTION_WITHOUT_DATED_TIME_WITNESS")
    canonical_bytes = json.dumps(
        expanded, sort_keys=True, separators=(",", ":")
    ).encode()
    return {
        "version": VERSION,
        "pre_registered_before_code": PREREG,
        "real_M1_source_sha256": MARKET_SHA,
        "real_M1_bars": n,
        "NY_days": 775,
        "day_session_casebook_size": len(expanded),
        "casebook_2325_json_sha256": sha256(canonical_bytes).hexdigest(),
        "session_M2_QORE_provenance_not_author_certification": stats,
        "full_2325_first_closed_M1_cases": expanded,
        "all_dated_rejected_G3_DOL_source_cases": rejected,
        "rejected_G3_DOL_source_count": len(rejected),
        "prior_independent_coverage_ledger_read_only_posthoc": True,
        "native_G3_COG_and_OPS_unmodified": True,
        "m2_qore_liquidity_source_context_tested": True,
        "ict_london_source_dol_certified": False,
        "ttrades_nyam_dol_certified": False,
        "ict_nypm_source_dol_certified": False,
        "m3_author_mss_certified": False,
        "m4_four_entry_families_certified": False,
        "m5_author_causative_swing_certified": False,
        "m6_two_independent_human_signatures": False,
        "m7_three_session_trader_certified": False,
        "broker_trades": 0,
        "broker_fills": 0,
        "sizing": 0,
        "PnL": None,
        "live_demo_vps_authorized": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--market", required=True, type=Path)
    p.add_argument("--coverage-ledger", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    if hash_file(args.market) != MARKET_SHA:
        raise ValueError("M2_ORIGINAL_NAS100_MARKET_SHA_MISMATCH")
    cases, n = stream_m2_first_bar_witnesses(
        _stream(args.market), expected_m1=M1_TOTAL,
    )
    # Entire market has been consumed BEFORE reading the earlier M1 ledger.
    ledger = json.loads(args.coverage_ledger.read_text(encoding="utf-8"))
    report = adjudicate_m2_posthoc(cases, ledger, n)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "M1": n,
        "casebook_sha": report["casebook_2325_json_sha256"],
        "stats": report["session_M2_QORE_provenance_not_author_certification"],
        "all_sessions_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
