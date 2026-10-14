#!/usr/bin/env python3
"""VT31 M2: ORIGINAL native G3 COG versus external #930/#932 on real M1.

Never construct/alter a CognitiveDecision. Only call witnesses for a decision
actually emitted by VT31CleanroomCognition on causal closed M1 prefixes.
Market data is already-seen 3Y development; no order, sizing, PnL or OOS.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    M1Bar,
)
from scripts.vt31_ict_dol_source_v1_20261014 import attest_ict_dol_source
from scripts.vt31_m2_dol_reconciliation_20261014 import (
    DATES,
    MARKET_SHA,
    NY,
    SESSIONS,
    checksum,
    collect_frozen_days,
)
from scripts.vt31_mc_p3_ict_independent_dol_20261014 import verify_ict_dol_from_m1

MODEL = "VT31_M2_NATIVE_G3_COG_ACTUAL_EMITTER_REAL_M1_SOURCE_V1"
PREREG_SHA = "2949a80886965d79fdf8d8908f058facaa14eb38"
TOTAL_M1 = 1059784
SLOTS_PER_DAY = 180
SOURCE_SCOPE = "3Y_NAS100_ALREADY_STUDIED_DEVELOPMENT_NOT_OOS"
P3_VERIFIED = "VERIFIED_QORE_DOL_PRICE_LINEAGE"


def audit_one_day(
    day: str, source: tuple[M1Bar, ...],
) -> dict[str, Any]:
    """One fresh native COG instance, one chronological walk, NO future bars."""
    d = date.fromisoformat(day)
    engine = VT31CleanroomCognition(
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    seen_bars: list[M1Bar] = []
    prefix_counts: Counter[str] = Counter()
    decision_counts: Counter[str] = Counter()
    pair_counts: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    identities: set[tuple[Any, ...]] = set()
    unique_first_count = 0
    gaps_in_feed = 0
    previous_close: datetime | None = None

    for bar in source:
        if previous_close is not None:
            if bar.opened_at < previous_close:
                raise ValueError("NON_CAUSAL_OR_OVERLAPPING_NATIVE_M1")
            if bar.opened_at != previous_close:
                gaps_in_feed += 1
        previous_close = bar.closed_at
        engine.observe_closed_m1(bar)
        seen_bars.append(bar)
        ny = bar.opened_at.astimezone(NY)
        if ny.date() != d:
            continue
        session = next((session for session, h in SESSIONS if h == ny.hour), None)
        if session is None:
            continue
        # as_of is THE closing instant of the last fed bar, not a future clock.
        at = bar.closed_at
        session_key = session.value
        prefix_counts[session_key] += 1
        assessment = engine.assess(session=session, as_of=at)
        decision = assessment.decision
        if decision is None:
            continue

        if decision.framework_policy != G3_MSS_FRAMEWORK_POLICY:
            raise AssertionError("NATIVE_COG_NOT_G3")
        if decision.observed_at != at:
            raise AssertionError("NATIVE_COG_WITNESS_NOT_AT_CLOSED_M1")
        if decision.structure_break_confirmed_at > at:
            raise AssertionError("NATIVE_COG_MSS_FUTURE")
        if decision.draw_level_observed_at > at:
            raise AssertionError("NATIVE_COG_DOL_FUTURE")
        if decision.mss_anchor_close is None:
            raise AssertionError("NATIVE_G3_MSS_ANCHOR_MISSING")
        native_identity = (
            session.value, decision.structure_break_confirmed_at,
            decision.side.value, decision.draw_family,
            decision.draw_target, decision.mss_anchor_close,
        )
        is_first = native_identity not in identities
        if is_first:
            identities.add(native_identity)
            unique_first_count += 1
        decision_counts[session_key] += 1

        # Witnesses operate solely on the exact prefix fed to the NATIVE COG.
        prefix = tuple(seen_bars)
        p3 = verify_ict_dol_from_m1(
            as_of=at, session=session, cognition=decision, history=prefix,
        )
        v1 = attest_ict_dol_source(
            as_of=at, session=session, cognition=decision, history=prefix,
        )
        p3_state = "SUPPORTED" if p3.state == P3_VERIFIED else p3.state
        v1_state = "SUPPORTED" if v1.state == "CONFIRMED" else v1.state
        pair_counts[p3_state + "|" + v1_state] += 1
        for why in p3.reasons:
            reasons["P3:" + why] += 1
        for why in v1.reasons:
            reasons["V1:" + why] += 1
        if p3.method_certified or v1.method_certified:
            raise AssertionError("WITNESS_FALSE_METHOD_PROMOTION")
        rows.append({
            "ny_date": day,
            "session": session.value,
            "as_of": at.isoformat(),
            "native_cog_model": decision.cognitive_version,
            "native_g3_policy": decision.framework_policy,
            "real_native_decision": True,
            "first_native_thesis_not_trade": is_first,
            "mss_confirmed_at": decision.structure_break_confirmed_at.isoformat(),
            "dol_confirmed_at": decision.draw_level_observed_at.isoformat(),
            "dol_family": decision.draw_family,
            "side": decision.side.value,
            "p3_state": p3_state,
            "v1_state": v1_state,
            "p3_reasons": list(p3.reasons),
            "v1_reasons": list(v1.reasons),
            "source_agreement": p3_state == v1_state,
            "both_witnesses_support_only_qore_pool": (
                p3_state == "SUPPORTED" and v1_state == "SUPPORTED"
            ),
            "broker_ack_or_fills": 0,
            "method_certified": False,
            "cognition_certified": False,
            "execution_authorized": False,
        })

    if sum(prefix_counts.values()) > SLOTS_PER_DAY:
        raise AssertionError("MORE_THAN_180_M1_CLOSED_SESSION_SLOTS")
    return {
        "ny_date": day,
        "source_bars_in_five_day_warmup_and_target": len(source),
        "noncontiguous_feed_gaps": gaps_in_feed,
        "M1_closed_session_prefixes": sum(prefix_counts.values()),
        "missing_session_M1": SLOTS_PER_DAY - sum(prefix_counts.values()),
        "by_session_prefixes": dict(sorted(prefix_counts.items())),
        "native_decisions_emitted_prefixes_not_trades": len(rows),
        "native_unique_first_theses_not_trades": unique_first_count,
        "native_decisions_by_session": dict(sorted(decision_counts.items())),
        "witness_pair_counts": dict(sorted(pair_counts.items())),
        "witness_reason_counts": dict(sorted(reasons.items())),
        "emissions": rows,
    }


def audit_groups(
    groups: dict[str, tuple[M1Bar, ...]],
) -> dict[str, Any]:
    days = [audit_one_day(day, groups[day]) for day in DATES]
    expected_total = len(DATES) * SLOTS_PER_DAY
    observed_total = sum(d["M1_closed_session_prefixes"] for d in days)
    emitted = sum(d["native_decisions_emitted_prefixes_not_trades"] for d in days)
    unique = sum(d["native_unique_first_theses_not_trades"] for d in days)
    paired: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    for day in days:
        paired.update(day["witness_pair_counts"])
        reasons.update(day["witness_reason_counts"])
    if observed_total + sum(d["missing_session_M1"] for d in days) != expected_total:
        raise AssertionError("M1_SLOT_DENOMINATOR_DRIFT")
    if sum(paired.values()) != emitted:
        raise AssertionError("ONE_COG_DECISION_NOT_AUDITED_BY_BOTH_WITNESSES")
    if emitted == 0:
        verdict = "NATIVE_COG_EMISSION_NOT_EVALUABLE"
    elif paired.get("SUPPORTED|SUPPORTED", 0) == emitted:
        verdict = "QORE_DOL_SOURCE_PARITY_IN_SAMPLE_NOT_ICT_CERTIFIED"
    else:
        verdict = "NATIVE_COG_DOL_SOURCE_NONPARITY_M2_BLOCKED"
    return {
        "identity": MODEL,
        "prereg_commit": PREREG_SHA,
        "source": SOURCE_SCOPE,
        "market_sha256": MARKET_SHA,
        "fixed_dates": list(DATES),
        "expected_closed_M1_session_slots": expected_total,
        "observed_closed_M1_session_prefixes": observed_total,
        "missing_M1_session_slots": expected_total - observed_total,
        "native_emission_prefixes_not_trades": emitted,
        "native_unique_first_theses_not_trades": unique,
        "pair_matrix_actual_emitted_cog_only": dict(sorted(paired.items())),
        "witness_reason_counts": dict(sorted(reasons.items())),
        "native_cog_tested": True,
        "native_cog_g3_policy": G3_MSS_FRAMEWORK_POLICY,
        "all_results_in_situ_m1_no_future": True,
        "scope_verdict": verdict,
        "days": days,
        "method_certified": False,
        "cognition_certified": False,
        "trader_certified": False,
        "economic_pnl": None,
        "profit_factor": None,
        "broker_ack_or_fills": 0,
        "execution_authorized": False,
        "live_authorized": False,
        "no_sizing": True,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if checksum(args.market) != MARKET_SHA:
        raise ValueError("FROZEN_NAS100_M1_SHA_MISMATCH")
    groups, n = collect_frozen_days(args.market)
    if n != TOTAL_M1:
        raise AssertionError("SOURCE_1059784_M1_DRIFT")
    report = audit_groups(groups)
    report["source_total_m1"] = n
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    headline = {
        k: report[k] for k in (
            "source_total_m1", "expected_closed_M1_session_slots",
            "observed_closed_M1_session_prefixes", "missing_M1_session_slots",
            "native_emission_prefixes_not_trades",
            "native_unique_first_theses_not_trades",
            "pair_matrix_actual_emitted_cog_only", "scope_verdict",
        )
    }
    # Reasons are external *source* checks, not native trading outcomes.
    discrepancies = [
        emission for day in report["days"] for emission in day["emissions"]
        if emission["p3_state"] != emission["v1_state"]
    ]
    headline["nonparity_cases_by_date"] = dict(sorted(Counter(
        case["ny_date"] for case in discrepancies
    ).items()))
    headline["nonparity_reason_pairs"] = dict(sorted(Counter(
        (case["p3_state"] + ":" + ",".join(case["p3_reasons"])
         + " / " + case["v1_state"] + ":" + ",".join(case["v1_reasons"]))
        for case in discrepancies
    ).items()))
    headline["top_witness_reason_codes"] = dict(
        Counter(report["witness_reason_counts"]).most_common(15)
    )
    headline["native_emissions_by_date"] = {
        day["ny_date"]: day["native_decisions_emitted_prefixes_not_trades"]
        for day in report["days"]
    }
    print(json.dumps(headline, sort_keys=True))


if __name__ == "__main__":
    main()
