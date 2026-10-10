#!/usr/bin/env python3
"""3Y original one-VT31 first-FVG A vs opposing-pivot B, source-only."""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    MethodologyDecision, utc,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.trader import VT31Trader
from vt31_ict_cleanroom_cog_real_3y_fast_v1 import (
    BASE, FROZEN_SOURCE_SHA256, NY, WINDOW_HOURS, _bar,
    _completed_hour, _stream,
)
from vt31_shadow_opposite_pivot_ab_v1 import Shadow, TracedCognition

SCHEMA = "qore.vt31.one_trader.source_AB_protected_pivot.v2"
THRESHOLD_PRIMARY_SOURCE_PP = 5.0
MAX_B_INDETERMINATE_PERCENT = 10.0


def classify_a(phase, *, ce, ambiguous, target_before_ce):
    if ce:
        return "VALID_CE"
    if ambiguous or phase is MethodologyDecision.AMBIGUOUS_PRICE_PATH:
        return "INDETERMINATE"
    if target_before_ce:
        return "TARGET_BEFORE_CE"
    if phase is MethodologyDecision.SOURCE_INVALIDATED:
        return "INVALIDATED"
    if phase is MethodologyDecision.WINDOW_EXPIRED:
        return "EXPIRED"
    return "OTHER"


def classify_b(outcome):
    if outcome == "CE_OVERLAP_NOT_BROKER_FILL":
        return "VALID_CE"
    if outcome in (
        "UNPROVEN_PROTECTED_SWING",
        "UNPROVEN_PROTECTED_STOP_GEOMETRY",
        "CE_AND_CANCELLATION_SAME_M1_UNKNOWN",
    ):
        return "INDETERMINATE"
    if outcome == "TARGET_BEFORE_CE":
        return "TARGET_BEFORE_CE"
    if outcome == "WINDOW_EXPIRED_BEFORE_CE":
        return "EXPIRED"
    if outcome in (
        "PROTECTED_SWING_CLOSE_BROKEN",
        "OPPOSING_MSS_DISPLACEMENT_AND_FVG",
        "FVG_FULL_CLOSE",
    ):
        return "INVALIDATED"
    return "OTHER"


def scan(rows):
    cognition = TracedCognition()
    trader = VT31Trader(cognition=cognition)
    full, partial, born = Counter(), Counter(), Counter()
    proven_pivot, arm_a, arm_b = Counter(), Counter(), Counter()
    a_ce, b_ce, mid = Counter(), Counter(), Counter()
    contingency, a_labels, b_labels = Counter(), Counter(), Counter()
    paired_records = []
    samples = []
    total, calls, p0 = 0, 0, 0
    last = None
    source_key = None
    pending = []

    def flush():
        nonlocal source_key, pending, calls, p0
        if source_key is None:
            return
        session = source_key[1]
        if not _completed_hour(pending, session):
            partial[session.value] += 1
            for bar in pending:
                trader.research_observe_incomplete_source_m1(bar)
            source_key, pending = None, []
            return
        full[session.value] += 1
        shadow = None
        recent = []
        a_touched, a_ambiguous = False, False
        a_target_before_ce = False
        for bar in pending:
            prior_ops = trader._windows.get(source_key)
            prior_phase = prior_ops.decision if prior_ops else None
            obs = trader.on_closed_m1(bar)
            calls += 1
            ops = trader._windows[source_key]
            recent.append(bar)
            if len(recent) > 3:
                recent.pop(0)
            if shadow is None and ops.first_suitable is not None:
                f = ops.first_suitable
                d = obs.cognition.decision if obs.cognition else None
                if d is None:
                    raise AssertionError("first FVG without live COG")
                pivot = cognition.protected.get((
                    utc(d.structure_break_confirmed_at), d.side
                ))
                shadow = Shadow(
                    f.side, f.consequent_encroachment, f.lower,
                    f.upper, f.target_price, pivot, f.formed_at,
                )
                born[session.value] += 1
                proven_pivot[
                    session.value + ("|CAUSAL" if pivot else "|UNKNOWN")
                ] += 1
                if pivot and pivot.confirmed_at >= d.structure_break_confirmed_at:
                    raise AssertionError("protected swing lookahead")
                continue
            if shadow is None:
                continue
            ce = shadow.source_ce
            overlaps = bar.low <= ce <= bar.high
            if (
                ops.decision is MethodologyDecision.RESEARCH_PENDING_CE
                and obs.cognition and obs.cognition.decision is None
            ):
                p0 += 1
            if (
                overlaps and obs.cognition and obs.cognition.decision
                and ops.decision in (
                    MethodologyDecision.RESEARCH_PENDING_CE,
                    MethodologyDecision.RESEARCH_TOUCH_NOT_FILL,
                )
            ):
                a_touched = True
            if (
                prior_phase is MethodologyDecision.RESEARCH_PENDING_CE
                and not a_touched and not overlaps
                and (
                    bar.high >= shadow.target
                    if shadow.side.value == "LONG"
                    else bar.low <= shadow.target
                )
            ):
                a_target_before_ce = True
            if (
                overlaps
                and ops.decision is MethodologyDecision.SOURCE_INVALIDATED
                and ops.event_at == bar.closed_at
            ):
                a_ambiguous = True
            shadow.on_m1(bar, cognition, tuple(recent), session)
        if shadow:
            shadow.finish()
            ops = trader._windows[source_key]
            lab_a = classify_a(
                ops.decision, ce=a_touched, ambiguous=a_ambiguous,
                target_before_ce=a_target_before_ce,
            )
            lab_b = classify_b(shadow.outcome)
            contingency[session.value + "|" + lab_a + "|" + lab_b] += 1
            a_labels[session.value + "|" + lab_a] += 1
            b_labels[session.value + "|" + lab_b] += 1
            paired_records.append({
                "ny_day": source_key[0],
                "session_window": session.value,
                "source_fvg_confirmed_at": shadow.formed_at.isoformat(),
                "A_class": lab_a,
                "B_class": lab_b,
                "A_original_terminal": ops.decision.value,
                "B_research_terminal": shadow.outcome,
                "B_protected_pivot": (
                    str(shadow.protected.price) if shadow.protected else None
                ),
                "B_opposite_mss_at": (
                    shadow.first_opposing_mss_at.isoformat()
                    if shadow.first_opposing_mss_at else None
                ),
                "B_first_opposing_fvg_at": (
                    shadow.first_opposing_fvg_at.isoformat()
                    if shadow.first_opposing_fvg_at else None
                ),
                "B_mid_only_post_ce": shadow.exit_after_ce,
                "real_broker_fill_proven": False,
            })
            arm_a[session.value + "|" + ops.decision.value] += 1
            arm_b[session.value + "|" + shadow.outcome] += 1
            mid[session.value + "|" + shadow.exit_after_ce] += 1
            if a_touched:
                a_ce[session.value + "|CE_WHILE_A_VALID_NO_FILL"] += 1
            if a_ambiguous:
                a_ce[session.value + "|CE_AND_CANCEL_SAME_M1_UNKNOWN"] += 1
            if shadow.initial_ce_at:
                b_ce[session.value + "|CE_WHILE_B_VALID_NO_FILL"] += 1
                if not a_touched:
                    b_ce[session.value + "|ADDITIONAL_VS_A"] += 1
            if len(samples) < 24:
                samples.append({
                    "session": session.value,
                    "ny_day": source_key[0],
                    "source_formed_at": shadow.formed_at.isoformat(),
                    "opposing_swing": str(
                        shadow.protected.price if shadow.protected
                        else "NOT_CONFIRMED"
                    ),
                    "A_terminal": ops.decision.value,
                    "B_terminal": shadow.outcome,
                    "post_CE_mid_only": shadow.exit_after_ce,
                    "broker_fill": False,
                })
        source_key, pending = None, []

    for item in rows:
        bar = _bar(item)
        if last is not None and utc(bar.opened_at) <= last:
            raise ValueError("frozen market duplicated/out of order")
        last = utc(bar.opened_at)
        total += 1
        local = last.astimezone(NY)
        session = WINDOW_HOURS.get(local.hour)
        new_key = (local.date().isoformat(), session) if session else None
        if new_key != source_key:
            flush()
        if new_key is None:
            trader.on_closed_m1(bar)
        else:
            source_key = new_key
            pending.append(bar)
    flush()
    if total != trader.total_closed_m1:
        raise AssertionError("source market not fully ingested")
    if sum(born.values()) != sum(arm_a.values()):
        raise AssertionError("missing original A candidate")
    if sum(born.values()) != sum(arm_b.values()):
        raise AssertionError("B invented or dropped FVG")
    if p0:
        raise AssertionError("original OPS pending without COG regression")
    if sum(contingency.values()) != sum(born.values()):
        raise AssertionError("paired contingency and original FVG count drift")
    if len({
        (r["ny_day"], r["session_window"], r["source_fvg_confirmed_at"])
        for r in paired_records
    }) != len(paired_records):
        raise AssertionError("duplicate first-FVG paired candidate IDs")
    n = len(paired_records)
    a_only = sum(r["A_class"] == "VALID_CE" and r["B_class"] != "VALID_CE"
                 for r in paired_records)
    b_only = sum(r["B_class"] == "VALID_CE" and r["A_class"] != "VALID_CE"
                 for r in paired_records)
    unknown_b = sum(r["B_class"] == "INDETERMINATE" for r in paired_records)
    delta_pct = (100.0 * (b_only - a_only) / n) if n else 0.0
    unknown_pct = (100.0 * unknown_b / n) if n else 0.0
    primary_met = (
        n > 0
        and delta_pct >= THRESHOLD_PRIMARY_SOURCE_PP
        and unknown_pct <= MAX_B_INDETERMINATE_PERCENT
    )
    return {
        "schema": SCHEMA, "base": BASE, "trader_id": "VT31",
        "registered_trader_count": 1, "models": ["LONDON", "NEW_YORK"],
        "market_M1": total, "cog_and_OPS_M1_calls": calls,
        "full_source_hours": dict(sorted(full.items())),
        "partial_source_hours": dict(sorted(partial.items())),
        "first_FVG_same_in_both": dict(sorted(born.items())),
        "opposing_pivot_confirmed_before_MSS": dict(sorted(proven_pivot.items())),
        "A_original_OPS_source_terminal": dict(sorted(arm_a.items())),
        "A_CE_overlap_M1_not_fill": dict(sorted(a_ce.items())),
        "B_protected_swing_shadow_source_terminal": dict(sorted(arm_b.items())),
        "B_CE_overlap_M1_not_fill": dict(sorted(b_ce.items())),
        "B_after_CE_mid_price_only": dict(sorted(mid.items())),
        "original_P0_pending_without_COG": p0,
        "paired_contingency_by_window": dict(sorted(contingency.items())),
        "A_mutually_exclusive_labels": dict(sorted(a_labels.items())),
        "B_mutually_exclusive_labels": dict(sorted(b_labels.items())),
        "paired_candidate_records": paired_records,
        "preregistered_primary_endpoint": {
            "population_original_first_FVGs": n,
            "A_only_unambiguous_CE_OHLC": a_only,
            "B_only_unambiguous_CE_OHLC": b_only,
            "paired_difference_percentage_points": round(delta_pct, 6),
            "B_indeterminate_count": unknown_b,
            "B_indeterminate_percentage": round(unknown_pct, 6),
            "min_net_B_advantage_percentage_points": THRESHOLD_PRIMARY_SOURCE_PP,
            "max_B_indeterminate_percentage": MAX_B_INDETERMINATE_PERCENT,
            "source_only_two_part_gate_met": primary_met,
            "authorized_for_real_money_or_production": False,
        },
        "multiple_comparisons": {
            "primary": "ONE pooled all-window paired source contrast",
            "three_windows_secondary_exploratory": True,
            "bonferroni_alpha_if_window_hypotheses_tested": 0.05 / 3,
            "valid_independent_pvalue_calculated": False,
        },
        "examples": samples,
        "guards": {
            "source_only_no_legacy": True,
            "opposite_3bar_pivot_is_research_not_canonical_claim": True,
            "NO_BID_ASK_TICK_HISTORY": True,
            "same_minute_chronology_unknown": True,
            "mid_price_labels_not_executed_trades": True,
            "unchanged_original_COG_OPS": True,
            "no_lookahead_pivot": True,
            "broker_fills_confirmed": 0,
            "profit_factor_drawdown_sharpe": None,
            "holdout_sealed": True,
            "live_authorized": False,
            "certified": False,
        },
    }


def self_test():
    start = datetime.fromisoformat("2025-07-07T07:00:00+00:00")
    data = [{
        "opened_at": (start + timedelta(minutes=i)).isoformat(),
        "closed_at": (start + timedelta(minutes=i + 1)).isoformat(),
        "open": "100", "high": "101", "low": "99", "close": "100",
    } for i in range(60)]
    result = scan(data)
    assert result["market_M1"] == 60
    assert result["cog_and_OPS_M1_calls"] == 60
    assert result["first_FVG_same_in_both"] == {}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--evidence", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    if a.self_test:
        self_test()
        print("AB first-FVG source-only paired self-test PASS")
        return
    if a.evidence is None or a.output is None:
        p.error("require --evidence and --output")
    if os.environ.get("VT31_INPUT_SOURCE_SHA256") != FROZEN_SOURCE_SHA256:
        raise ValueError("unverified exact 3Y source digest")
    result = scan(_stream(a.evidence))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
