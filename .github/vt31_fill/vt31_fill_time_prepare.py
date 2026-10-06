#!/usr/bin/env python3
"""Prepare causal VT31 pending-fill revalidation ledger.

The prospective fill is identified from the historical path only to locate the
counterfactual decision timestamp. Revalidation itself uses bars closed no
later than the fill bar OPEN, never the fill bar high/low/close.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import vt31_nas100_comp010_live_context_adverse_exit_v1 as comp010
import vt31_nas100_full_cognition_attribution_v1 as cognition_lab
import vt31_nas100_live_cognitive_breaker_protection_frontier_v1 as live
import vt31_nas100_post_1r_full_cognition_management_frontier_v2 as h3
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.traders.vt31_nas100_cognitive_plumbing import (
    recent_liquidity_event_count_10m,
)
from qore.infrastructure.traders.vt31_nas100_reasoning_engine import reason

SCHEMA = "qore.github-trader-lab.vt31-fill-time-ledger.v1"
ENTRY_BLOCKERS = frozenset(
    {
        "M15_CONTEXT_UNWIRED",
        "H4_CONTEXT_UNAVAILABLE",
        "H1_CONTEXT_UNAVAILABLE",
        "STRUCTURE_CONTEXT_UNAVAILABLE",
        "VOLATILITY_CONTEXT_UNAVAILABLE",
        "ENTRY_INTELLIGENCE_UNAVAILABLE",
    }
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _pending_fill_revalidation(
    *,
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
) -> dict[str, object] | None:
    fill_index = h3.v2b._fill_index(day_bars, executable)
    if fill_index is None:
        return None

    fill_bar = day_bars[fill_index]
    fill_open_at = cast(datetime, getattr(fill_bar, "opened_at"))
    source = executable.source_setup
    entry_situation = cognition_lab._reconstruct_situation(
        state=state,
        selected=executable,
        source=source,
        observation_at=executable.decision_at,
    )

    causal_today = tuple(
        bar
        for bar in day_bars
        if cast(datetime, getattr(bar, "closed_at")) <= fill_open_at
    )
    local = fill_open_at.astimezone(h3._NY)
    previous_range = h3._opt_d(state.get("previous_admitted_path_range"))
    current_path = tuple(
        bar
        for bar in causal_today
        if (0, 0, 0)
        <= specialist._wall(getattr(bar, "opened_at"))
        < (16, 0, 0)
    )
    current_range = specialist._interval_range(current_path)
    current_ratio = (
        current_range / previous_range
        if current_range is not None
        and previous_range is not None
        and previous_range > 0
        else None
    )

    h1_state = h3.ctx._trend_state(
        h3.ctx._completed_hour_closes(causal_today, fill_open_at, 1)
    )
    h4_state = live._carry_forward_h4_state(
        h3.ctx._trend_state(
            h3.ctx._completed_hour_closes(causal_today, fill_open_at, 4)
        ),
        entry_situation.h4_state,
    )
    m15_state = h3.ctx._trend_state(
        h3.ctx._completed_minute_bucket_closes(
            causal_today,
            fill_open_at,
            15,
        )
    )
    premarket_state = h3.ctx._directional_state(
        h3.ctx._slice(causal_today, (8, 0, 0), (9, 0, 0), fill_open_at)
    )
    cash_open_state = h3.ctx._directional_state(
        h3.ctx._slice(causal_today, (9, 30, 0), (10, 0, 0), fill_open_at)
    )
    session_prefix = tuple(
        bar
        for bar in causal_today
        if (10, 0, 0)
        <= specialist._wall(getattr(bar, "opened_at"))
        < (11, 0, 0)
    )
    reclaim_at = specialist._first_reference_reclaim_at(session_prefix, source)
    reclaim_age = (
        None
        if reclaim_at is None
        else int((fill_open_at - reclaim_at).total_seconds() // 60)
    )
    last_family, last_age = specialist._last_structure_event_family(
        session_prefix,
        source,
        fill_open_at,
    )
    elapsed = max(
        0,
        int(
            (
                fill_open_at - cast(datetime, executable.decision_at)
            ).total_seconds()
            // 60
        ),
    )
    entry_age = int(cast(int, state["entry_evidence_age_minutes"])) + elapsed

    current = replace(
        entry_situation,
        as_of=fill_open_at.astimezone(UTC).isoformat(),
        weekday=local.strftime("%A"),
        decision_minute_ny=local.hour * 60 + local.minute,
        h4_state=h4_state,
        h1_state=h1_state,
        m15_state=m15_state,
        premarket_state=premarket_state,
        cash_open_state=cash_open_state,
        range_state=h3._range_state(current_ratio),
        current_path_vs_previous=current_ratio,
        raid_depth_ref=h3.ctx._raid_depth_ref(
            causal_today,
            decision_at=fill_open_at,
            side=str(executable.side.value),
            reference_high=source.reference.high,
            reference_low=source.reference.low,
        ),
        recent_path_efficiency=h3.ctx._recent_efficiency(
            causal_today,
            fill_open_at,
        ),
        recent_overlap_rate=h3.ctx._recent_overlap(
            causal_today,
            fill_open_at,
        ),
        reference_reclaimed=reclaim_at is not None,
        reference_reclaim_age_minutes=reclaim_age,
        last_structure_event_family=last_family,
        last_structure_event_age_minutes=last_age,
        recent_liquidity_event_count_10m=recent_liquidity_event_count_10m(
            session_prefix,
            source,
            fill_open_at,
        ),
        entry_evidence_freshness=(
            "fresh-0-5m" if entry_age <= 5 else "older-than-5m"
        ),
    )
    current_reasoning = reason(current)
    entry_blockers = sorted(
        set(current_reasoning.max_intelligence_blockers) & ENTRY_BLOCKERS
    )
    accepted = current_reasoning.action == "EXECUTE" and not entry_blockers
    return {
        "fill_open_at": fill_open_at.astimezone(UTC).isoformat(),
        "fill_bar_closed_at": cast(
            datetime,
            getattr(fill_bar, "closed_at"),
        ).astimezone(UTC).isoformat(),
        "signal_to_fill_open_minutes": elapsed,
        "current_reasoning_action": current_reasoning.action,
        "current_reasoning_thesis": current_reasoning.thesis,
        "current_reasoning_contradictions": list(
            current_reasoning.contradictions
        ),
        "current_reasoning_uncertainty": list(current_reasoning.uncertainty),
        "max_intelligence_blockers": list(
            current_reasoning.max_intelligence_blockers
        ),
        "fill_stage_blockers": entry_blockers,
        "fill_revalidation_accepts": accepted,
        "h4_state": current.h4_state,
        "h1_state": current.h1_state,
        "m15_state": current.m15_state,
        "premarket_state": current.premarket_state,
        "cash_open_state": current.cash_open_state,
        "reference_reclaim_age_minutes": current.reference_reclaim_age_minutes,
        "recent_liquidity_event_count_10m": (
            current.recent_liquidity_event_count_10m
        ),
        "entry_evidence_freshness": current.entry_evidence_freshness,
        "decision_authority_uses_fill_bar_ohlc": False,
    }


def prepare(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    full_rows: list[dict[str, object]] = []

    def simulator(
        day_bars: tuple[object, ...],
        executable: object,
        state: dict[str, object],
    ) -> dict[str, object]:
        structural = specialist._simulate_structural_boundary_only(
            day_bars,
            executable,
        )
        if structural.get("status") != "terminal":
            return structural
        revalidation = _pending_fill_revalidation(
            day_bars=day_bars,
            executable=executable,
            state=state,
        )
        outcome = comp010._simulate_variant(
            day_bars,
            executable,
            state,
            variant=comp010.LAB_CONTROL_ALIAS,
        )
        if outcome.get("status") != "terminal":
            raise AssertionError("truthful control changed terminal eligibility")
        outcome["fill_revalidation"] = revalidation
        full_rows.append(outcome)
        return structural

    try:
        specialist._simulate_selected_plan = simulator
        base = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    structural = cast(list[dict[str, object]], base["trades"])
    if [str(row["signal_at"]) for row in structural] != [
        str(row["signal_at"]) for row in full_rows
    ]:
        raise AssertionError("fill ledger changed structural identity")

    admitted = comp010._apply_comp009_admission(full_rows)
    eligible_dates = comp010._eligible_dates(evidence_path)
    return {
        "schema": SCHEMA,
        "rows": admitted,
        "eligible_dates": eligible_dates,
        "governance": {
            "consumed_evidence_only": True,
            "fill_bar_ohlc_used_for_decision": False,
            "fill_open_event_time_only": True,
            "new_delay_threshold_added": False,
            "outcome_used_for_decision": False,
            "fold_identity_used_for_decision": False,
            "date_identity_used_for_decision": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "fresh_holdout_opened": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = prepare(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "VT31_FILL_LEDGER "
        + json.dumps(
            {
                "trade_count": len(payload["rows"]),
                "eligible_session_count": len(payload["eligible_dates"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
