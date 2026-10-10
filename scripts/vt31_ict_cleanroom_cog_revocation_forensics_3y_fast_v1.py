#!/usr/bin/env python3
"""Causal 3Y VT31 COG M1 thesis-revocation diagnostics on JOINED OPS cleanroom.

Observation-only research. Does not change source, decisions, order lifecycle,
frozen historical input or admitted candidate selection. A failed cognitive
proof may be a completed-M1 price-path fact, NOT a known historical fill.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
    _ny_day,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    MethodologyDecision,
    SessionId,
    Side,
    utc,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.trader import VT31Trader

from vt31_ict_cleanroom_cog_real_3y_fast_v1 import (
    BASE,
    FROZEN_SOURCE_SHA256,
    NY,
    WINDOW_HOURS,
    _bar,
    _completed_hour,
    _stream,
)

SCHEMA = "qore.vt31.cleanroom.one_trader.3y_cognitive_revocation_forensics.v1"
MAX_EXAMPLES = 18
COMPLETED = {
    MethodologyDecision.SOURCE_INVALIDATED,
    MethodologyDecision.RESEARCH_TOUCH_NOT_FILL,
    MethodologyDecision.AMBIGUOUS_PRICE_PATH,
    MethodologyDecision.WINDOW_EXPIRED,
}


class CausalForensicCognition(VT31CleanroomCognition):
    """Read before/after of the REAL M1 cognition, never override its output."""

    def __init__(self) -> None:
        super().__init__()
        self.probes: Counter[str] = Counter()
        self.probes_by_session: Counter[str] = Counter()
        self.last_causes: tuple[str, ...] = ()
        self.last_diagnosis: dict[str, object] = {}
        self.probe_examples: list[dict[str, str]] = []

    def assess(self, *, session: SessionId, as_of: datetime):
        at = utc(as_of)
        key = (_ny_day(at - timedelta(microseconds=1)), session)
        prior = self._active_m1_mss.get(key)
        result = super().assess(session=session, as_of=at)
        current = self._history[-1]
        pools = self._index.pools(at, session)
        current_shift = self._index.shift()
        reasons: list[str] = []
        if prior is not None:
            same_pool = any(
                p.family == prior.draw_family
                and p.level == prior.draw_target
                and p.confirmed_at == prior.draw_level_observed_at
                for p in pools
            )
            pivot_survived = (
                current.close > prior.structure_level
                if prior.side is Side.LONG
                else current.close < prior.structure_level
            )
            opposite = (
                current_shift is not None
                and current_shift.side is not prior.side
            )
            if not same_pool:
                touch_this_m1 = (
                    current.high >= prior.draw_target
                    if prior.side is Side.LONG
                    else current.low <= prior.draw_target
                )
                reasons.append(
                    "DOL_SWEPT_THIS_CLOSED_M1"
                    if touch_this_m1 else "DOL_NOT_AVAILABLE_AS_OF"
                )
            if not pivot_survived:
                reasons.append("M1_CLOSE_REVERSED_PREVIOUS_PIVOT")
            if opposite:
                reasons.append("OPPOSITE_M1_MSS_CONFIRMED")
            if not reasons and result.decision is None:
                # Existing old M1 MSS and DOL remain valid, yet a fresh
                # (usually supportive) MSS goes through separate DOL room
                # arbitration and can return no decision this exact minute.
                reasons.append("PRIOR_THESIS_VALID_BUT_CURRENT_MSS_NO_DECISION")
            if not reasons and result.decision is not None:
                reasons.append("PRIOR_THESIS_CONTINUED_OR_REPLACED")
            self.probes["ACTIVE_M1_THESIS_REEVALUATED"] += 1
            self.probes_by_session[session.value + "|ACTIVE_M1_THESIS_REEVALUATED"] += 1
            for reason in reasons:
                self.probes[reason] += 1
                self.probes_by_session[session.value + "|" + reason] += 1
            if result.decision is None and len(self.probe_examples) < MAX_EXAMPLES:
                self.probe_examples.append({
                    "as_of": at.isoformat(),
                    "session": session.value,
                    "prior_side": prior.side.value,
                    "prior_draw_family": prior.draw_family,
                    "prior_draw_target": str(prior.draw_target),
                    "prior_mss_time": utc(
                        prior.structure_break_confirmed_at
                    ).isoformat(),
                    "causes": "|".join(reasons),
                    "current_cog_missing": "|".join(result.missing),
                })
        else:
            self.probes["NO_PRIOR_M1_THESIS"] += 1
        self.last_causes = tuple(reasons)
        self.last_diagnosis = {
            "as_of": at.isoformat(),
            "session": session.value,
            "prior_thesis_present": prior is not None,
            "causes": tuple(reasons),
            "output_decision": result.decision is not None,
            "missing": result.missing,
            "current_shift_present": current_shift is not None,
        }
        return result


def scan(rows, *, max_examples: int = MAX_EXAMPLES) -> dict[str, Any]:
    cognition = CausalForensicCognition()
    trader = VT31Trader(cognition=cognition)
    full: Counter[str] = Counter()
    partial: Counter[str] = Counter()
    cognitive_events: Counter[str] = Counter()
    source_candidates: Counter[str] = Counter()
    final_candidate_states: Counter[str] = Counter()
    final_candidate_reasons: Counter[str] = Counter()
    reasons_at_new_invalidation: Counter[str] = Counter()
    none_at_invalidation: Counter[str] = Counter()
    invalidation_overlap: Counter[str] = Counter()
    candidate_examples: list[dict[str, str]] = []
    no_cog_pending = 0
    no_cog_pending_unique: set[tuple[str, str]] = set()
    rows_seen = 0
    prev_open: datetime | None = None
    pending_key: tuple[str, SessionId] | None = None
    pending: list[Any] = []

    def flush() -> None:
        nonlocal pending_key, pending, no_cog_pending
        if pending_key is None:
            return
        ses = pending_key[1]
        if _completed_hour(pending, ses):
            full[ses.value] += 1
            for bar in pending:
                ops = trader._windows.get(pending_key)
                old_decision = ops.decision if ops is not None else None
                old_candidate = ops.first_suitable if ops is not None else None
                result = trader.on_closed_m1(bar)
                cognition_result = result.cognition
                if cognition_result is None or result.operational_phase is None:
                    raise AssertionError("full source M1 must run COG and OPS")
                cognitive_events[ses.value] += 1
                if (
                    result.operational_phase
                    is MethodologyDecision.RESEARCH_PENDING_CE
                    and cognition_result.decision is None
                ):
                    no_cog_pending += 1
                    if old_candidate is not None:
                        no_cog_pending_unique.add((
                            ses.value,
                            old_candidate.formed_at.isoformat(),
                        ))
                ops = trader._windows[pending_key]
                new_candidate = ops.first_suitable
                if old_candidate is None and new_candidate is not None:
                    source_candidates[ses.value] += 1
                if (
                    old_candidate is not None
                    and old_decision is not MethodologyDecision.SOURCE_INVALIDATED
                    and result.operational_phase
                    is MethodologyDecision.SOURCE_INVALIDATED
                ):
                    reason = ops.source_invalidation_reason
                    if reason is None:
                        reason = "M1_FVG_SOURCE_OR_PRICE_BREAK"
                    final_candidate_reasons[ses.value + "|" + reason] += 1
                    if cognition_result.decision is None:
                        none_at_invalidation[ses.value] += 1
                    flags = cognition.last_causes
                    if len(flags) > 1:
                        invalidation_overlap[ses.value] += 1
                    if not flags:
                        reasons_at_new_invalidation[
                            ses.value + "|NO_ACTIVE_THESIS_CAUSE_AT_THIS_M1"
                        ] += 1
                    for flag in flags:
                        reasons_at_new_invalidation[ses.value + "|" + flag] += 1
                    if len(candidate_examples) < max_examples:
                        candidate_examples.append({
                            "session": ses.value,
                            "at": utc(bar.closed_at).isoformat(),
                            "selected_fvg_at": utc(
                                old_candidate.formed_at
                            ).isoformat(),
                            "ops_source_reason": reason,
                            "COG_current_decision_available": str(
                                cognition_result.decision is not None
                            ),
                            "COG_prior_M1_thesis_revalidation_causes": (
                                "|".join(flags) if flags else "NONE"
                            ),
                            "COG_m1_missing": "|".join(cognition_result.missing),
                        })
            source = trader._windows[pending_key]
            if source.first_suitable is not None:
                final_candidate_states[
                    ses.value + "|" + source.decision.value
                ] += 1
                if source.decision not in COMPLETED:
                    raise AssertionError("end-of-hour unresolved source hypothesis")
        else:
            partial[ses.value] += 1
            for bar in pending:
                trader.research_observe_incomplete_source_m1(bar)
        pending_key = None
        pending = []

    for row in rows:
        bar = _bar(row)
        if prev_open is not None and bar.opened_at <= prev_open:
            raise ValueError("input duplicate/out-of-order")
        prev_open = bar.opened_at
        rows_seen += 1
        local = utc(bar.opened_at).astimezone(NY)
        session = WINDOW_HOURS.get(local.hour)
        key = (local.date().isoformat(), session) if session else None
        if key != pending_key:
            flush()
        if key is None:
            trader.on_closed_m1(bar)
        else:
            pending_key = key
            pending.append(bar)
    flush()
    if trader.total_closed_m1 != rows_seen:
        raise AssertionError("source M1 records lost in forensic probe")
    if sum(source_candidates.values()) != sum(final_candidate_states.values()):
        raise AssertionError("source candidate -> terminal state provenance drift")
    if no_cog_pending or no_cog_pending_unique:
        raise AssertionError("P0 source still pending without present cognition")
    return {
        "schema": SCHEMA,
        "input_base": BASE,
        "trader_id": "VT31",
        "registered_trader_count": 1,
        "session_models": ["LONDON", "NEW_YORK"],
        "market_closed_m1": rows_seen,
        "full_m1_window_days": dict(sorted(full.items())),
        "partial_m1_window_days": dict(sorted(partial.items())),
        "cognitive_calls": sum(cognitive_events.values()),
        "cognitive_calls_by_window": dict(sorted(cognitive_events.items())),
        "source_candidate_by_window": dict(sorted(source_candidates.items())),
        "final_source_candidate_states": dict(sorted(final_candidate_states.items())),
        "final_source_invalidation_reasons": dict(sorted(final_candidate_reasons.items())),
        "cognitive_thesis_reevaluation_m1_causes": dict(sorted(cognition.probes.items())),
        "cognitive_thesis_m1_causes_by_window": dict(sorted(
            cognition.probes_by_session.items()
        )),
        "causal_reasons_at_selected_source_invalidation": dict(sorted(
            reasons_at_new_invalidation.items()
        )),
        "cognition_absent_at_source_invalidation": dict(sorted(none_at_invalidation.items())),
        "simultaneous_multi_cognitive_reason_at_invalidation": dict(
            sorted(invalidation_overlap.items())
        ),
        "unique_source_pending_without_cog": len(no_cog_pending_unique),
        "pending_m1_without_cog": no_cog_pending,
        "candidate_invalidation_examples": candidate_examples,
        "cognitive_reevaluation_examples": cognition.probe_examples,
        "interpretation_limits": {
            "all_causes_observed_as_of_closed_M1": True,
            "counterfactual_trade_PnL_or_alpha": False,
            "financial_execution_or_broker_fill_proven": False,
            "OHLC_cannot_resolve_same_M1_fill_cancel_order": True,
            "source_withdrawal_does_not_infer_realized_loss": True,
            "not_a_scientific_knockout_ablation": True,
            "uses_legacy_vt31_algorithms": False,
            "opens_holdout": False,
            "live_authorized": False,
            "certified": False,
        },
    }


def self_test() -> None:
    from datetime import UTC

    start = datetime(2025, 7, 7, 7, tzinfo=UTC)
    rows = [
        {
            "opened_at": (start + timedelta(minutes=i)).isoformat(),
            "closed_at": (start + timedelta(minutes=i+1)).isoformat(),
            "open": "100", "high": "101", "low": "99", "close": "100",
        }
        for i in range(60)
    ]
    result = scan(rows)
    assert result["market_closed_m1"] == 60
    assert result["cognitive_calls"] == 60
    assert result["source_candidate_by_window"] == {}
    assert result["pending_m1_without_cog"] == 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("ONE VT31 M1 causal COG revocation forensic self-test PASS")
        return
    if args.evidence is None or args.output is None:
        parser.error("--evidence and --output required")
    import os

    if os.environ.get("VT31_INPUT_SOURCE_SHA256") != FROZEN_SOURCE_SHA256:
        raise ValueError("wrong source hash — no possible 3Y evidence claims")
    result = scan(_stream(args.evidence))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
