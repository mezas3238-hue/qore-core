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

SCHEMA = "qore.vt31.one_trader.source_AB_protected_pivot.v1"


def scan(rows):
    cognition = TracedCognition()
    trader = VT31Trader(cognition=cognition)
    full, partial, born = Counter(), Counter(), Counter()
    proven_pivot, arm_a, arm_b = Counter(), Counter(), Counter()
    a_ce, b_ce, mid = Counter(), Counter(), Counter()
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
        for bar in pending:
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
                overlaps
                and ops.decision is MethodologyDecision.SOURCE_INVALIDATED
                and ops.event_at == bar.closed_at
            ):
                a_ambiguous = True
            shadow.on_m1(bar, cognition, tuple(recent), session)
        if shadow:
            shadow.finish()
            ops = trader._windows[source_key]
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
