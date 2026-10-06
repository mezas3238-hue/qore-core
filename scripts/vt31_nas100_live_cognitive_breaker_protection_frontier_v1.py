"""VT31 NAS100 live-cognitive Breaker protection frontier V1.

Consumed-evidence development only.

At each confirmed improving pre-DOL1 Breaker swing, VT31 reconstructs the live
causal Situation, reruns reason_position() with the frozen entry thesis, runs
full position cognition, and uses the existing market-native HOLD/TRAIL
decision. No outcome, fold identity, sizing, leverage, compounding, capital
weighting, or future bar can authorize protection.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_full_cognition_attribution_v1 as cognition_lab
import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_post_1r_full_cognition_management_frontier_v2 as h3
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.traders.vt31_nas100_cognitive_telemetry import (
    capture_post_entry_cognitive_sensor,
)
from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    PositionAction,
    StructuralProtectionCandidate,
)
from qore.infrastructure.traders.vt31_nas100_post_entry_cognitive_runtime import (
    PostEntryCausalObservation,
    PostEntryCognitiveDecision,
    PostEntryMarketFacts,
    reassess_and_decide_post_entry,
)

SCHEMA = "qore.vt31.nas100.live_cognitive_breaker_protection_frontier.v1"
ADMISSION_VARIANT = "A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M"
B_COMPARATOR_ID = "VT31_BSIDE_H3_W5_DOL2_PS2_RESEARCH_COMPARATOR_001"
WINDOW = 5

VARIANTS: dict[str, tuple[str | None, int | None]] = {
    "CONTROL": (None, None),
    "COG_SWING_PS1": ("SWING", 1),
    "COG_SWING_PS2": ("SWING", 2),
    "COG_WEAK_PATH_PS1": ("WEAK_PATH", 1),
    "COG_WEAK_PATH_PS2": ("WEAK_PATH", 2),
}


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _target_touched_before(
    *,
    day_bars: tuple[object, ...],
    executable: object,
    observation_at: datetime,
) -> bool:
    side = str(executable.side.value)
    target = _d(executable.target_price)
    fill_index = h3.v2b._fill_index(day_bars, executable)
    if fill_index is None:
        return False
    for bar in day_bars[fill_index:]:
        if cast(datetime, bar.closed_at) > observation_at:
            break
        if composition.depth._target_hit(side, bar, target):
            return True
    return False


def _live_cognitive_position_decision(
    *,
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    observation_at: datetime,
    current_stop: Decimal,
    candidate_stop: Decimal,
    confirmations: int,
    mode: str,
) -> tuple[PostEntryCognitiveDecision | None, dict[str, object]]:
    if _target_touched_before(
        day_bars=day_bars,
        executable=executable,
        observation_at=observation_at,
    ):
        return None, {
            "observation_at": observation_at.astimezone(UTC).isoformat(),
            "authorized": False,
            "decision_action": "HOLD",
            "decision_reason": "SOFT_DOL1_ALREADY_TOUCHED_TARGET_LOGIC_OWNS_PATH",
            "mode": mode,
            "confirmations": confirmations,
        }

    source = executable.source_setup
    entry_situation = cognition_lab._reconstruct_situation(
        state=state,
        selected=executable,
        source=source,
        observation_at=executable.decision_at,
    )
    entry_reasoning = cognition_lab._reconstruct_reasoning(state)

    causal_today = tuple(
        bar
        for bar in day_bars
        if cast(datetime, bar.closed_at) <= observation_at
    )
    local = observation_at.astimezone(h3._NY)
    previous_range = h3._opt_d(state.get("previous_admitted_path_range"))
    current_path = tuple(
        bar
        for bar in causal_today
        if (0, 0, 0)
        <= specialist._wall(bar.opened_at)
        < (16, 0, 0)
    )
    current_range = specialist._interval_range(current_path)
    entry = _d(executable.entry_price)
    initial_stop = _d(executable.stop_price)
    initial_risk = abs(entry - initial_stop)
    if initial_risk <= 0 or not causal_today:
        raise ValueError("live cognition requires positive frozen initial risk")
    current_close = _d(causal_today[-1].close)
    current_open_r = h3._terminal_r(
        side=str(executable.side.value),
        entry=entry,
        price=current_close,
        risk=initial_risk,
    )
    current_ratio = (
        current_range / previous_range
        if current_range is not None
        and previous_range is not None
        and previous_range > 0
        else None
    )

    h1_state = h3.ctx._trend_state(
        h3.ctx._completed_hour_closes(causal_today, observation_at, 1)
    )
    h4_state = h3.ctx._trend_state(
        h3.ctx._completed_hour_closes(causal_today, observation_at, 4)
    )
    m15_state = h3.ctx._trend_state(
        h3.ctx._completed_minute_bucket_closes(
            causal_today,
            observation_at,
            15,
        )
    )
    premarket_state = h3.ctx._directional_state(
        h3.ctx._slice(
            causal_today,
            (8, 0, 0),
            (9, 0, 0),
            observation_at,
        )
    )
    cash_open_state = h3.ctx._directional_state(
        h3.ctx._slice(
            causal_today,
            (9, 30, 0),
            (10, 0, 0),
            observation_at,
        )
    )

    session_prefix = tuple(
        bar
        for bar in causal_today
        if (10, 0, 0)
        <= specialist._wall(bar.opened_at)
        < (11, 0, 0)
    )
    reclaim_at = specialist._first_reference_reclaim_at(session_prefix, source)
    reclaim_age = (
        None
        if reclaim_at is None
        else int((observation_at - reclaim_at).total_seconds() // 60)
    )
    last_family, last_age = specialist._last_structure_event_family(
        session_prefix,
        source,
        observation_at,
    )
    efficiency = h3.ctx._recent_efficiency(causal_today, observation_at)
    overlap = h3.ctx._recent_overlap(causal_today, observation_at)
    weak_path = bool(
        (efficiency is not None and efficiency <= Decimal("0.30"))
        or (overlap is not None and overlap >= Decimal("0.75"))
    )

    observation = PostEntryCausalObservation(
        as_of=observation_at.astimezone(UTC).isoformat(),
        decision_minute_ny=local.hour * 60 + local.minute,
        prior_day_state=entry_situation.prior_day_state,
        h4_state=h4_state,
        h1_state=h1_state,
        premarket_state=premarket_state,
        cash_open_state=cash_open_state,
        position_in_prior_day_range=(
            entry_situation.position_in_prior_day_range
        ),
        range_state=h3._range_state(current_ratio),
        volatility_state=entry_situation.volatility_state,
        current_path_vs_previous=current_ratio,
        reference_width_vs_prior5=entry_situation.reference_width_vs_prior5,
        raid_depth_ref=h3.ctx._raid_depth_ref(
            causal_today,
            decision_at=observation_at,
            side=str(executable.side.value),
            reference_high=source.reference.high,
            reference_low=source.reference.low,
        ),
        recent_path_efficiency=efficiency,
        recent_overlap_rate=overlap,
        reference_reclaimed=reclaim_at is not None,
        reference_reclaim_age_minutes=reclaim_age,
        last_structure_event_family=last_family,
        last_structure_event_age_minutes=last_age,
        recent_liquidity_event_count_10m=None,
        displacement_state=entry_situation.displacement_state,
        journey_stage="OPEN_PRE_DOL1_PROTECTION_EVALUATION",
        dol1_state="ACTIVE_PRE_DOL1",
        dol2_state="CALIBRATED_ECONOMIC_CAPACITY_COGNITION_REQUIRED",
        dol3_state="REJECTED_BY_EDGE_ECONOMICS",
        extension_capacity_state="CALIBRATED_PRE_DOL1_CURRENT_JOURNEY",
        exhaustion_state="NO_CONFIRMED_EXHAUSTION",
        cross_index_state=entry_situation.cross_index_state,
        m15_state=m15_state,
        current_open_r=current_open_r,
    )
    momentum_deteriorated = mode == "SWING" or (
        mode == "WEAK_PATH" and weak_path
    )
    market = PostEntryMarketFacts(
        side=str(executable.side.value),
        current_stop=current_stop,
        primary_structural_target=_d(executable.target_price),
        next_structural_target=None,
        protective_swing=StructuralProtectionCandidate(
            level=candidate_stop,
            confirmations=confirmations,
            source="confirmed-m1-protective-swing",
        ),
        primary_target_reached=False,
        primary_target_accepted=False,
        structure_invalidated=False,
        liquidity_failure_confirmed=False,
        momentum_deteriorated=momentum_deteriorated,
        regime_changed_against_thesis=False,
    )
    decision = reassess_and_decide_post_entry(
        entry_situation=entry_situation,
        entry_reasoning=entry_reasoning,
        observation=observation,
        market=market,
        entry_tier="CORE",
        dol1_acceptance_observed=False,
    )
    authorized = decision.position.action is PositionAction.TRAIL
    cognition = decision.cognition
    sensor = capture_post_entry_cognitive_sensor(
        observation=observation,
        market=market,
        decision=decision,
    )
    return decision, {
        "observation_at": observation_at.astimezone(UTC).isoformat(),
        "authorized": authorized,
        "mode": mode,
        "confirmations": confirmations,
        "decision_action": decision.position.action.value,
        "decision_reason": decision.position.reason,
        "current_reasoning_action": decision.current_reasoning_action,
        "management_context": cognition.management_context.value,
        "protection_urgency": cognition.protection_urgency.value,
        "destination_state": cognition.destination_state,
        "support_score": cognition.support_score,
        "caution_score": cognition.caution_score,
        "support_margin": cognition.support_score - cognition.caution_score,
        "weak_path": weak_path,
        "current_open_r": format(current_open_r, "f"),
        "recent_path_efficiency": (
            None if efficiency is None else format(efficiency, "f")
        ),
        "recent_overlap_rate": (
            None if overlap is None else format(overlap, "f")
        ),
        "m15_state": m15_state,
        "h1_state": h1_state,
        "h4_state": h4_state,
        "reference_reclaim_age_minutes": reclaim_age,
        "last_structure_event_family": last_family,
        "last_structure_event_age_minutes": last_age,
        "full_cognitive_accounting_verified": (
            cognition.full_cognitive_accounting_verified
        ),
        "maximum_cognition_verified": cognition.maximum_cognition_verified,
        "maximum_intelligence_blockers": list(
            cognition.reasoning_max_intelligence_blockers
        ),
        "cognitive_sensor": sensor.payload(),
        "cognitive_sensor_fingerprint": sensor.fingerprint(),
    }


def _live_cognitive_decision(
    *,
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    observation_at: datetime,
    current_stop: Decimal,
    candidate_stop: Decimal,
    confirmations: int,
    mode: str,
) -> tuple[bool, dict[str, object]]:
    """Backward-compatible trail-only view of the full position decision."""

    decision, diagnostic = _live_cognitive_position_decision(
        day_bars=day_bars,
        executable=executable,
        state=state,
        observation_at=observation_at,
        current_stop=current_stop,
        candidate_stop=candidate_stop,
        confirmations=confirmations,
        mode=mode,
    )
    authorized = (
        decision is not None
        and decision.position.action is PositionAction.TRAIL
    )
    if bool(diagnostic.get("authorized")) != authorized:
        raise AssertionError(
            "trail compatibility view drifted from full position decision"
        )
    return authorized, diagnostic


def _simulate(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    *,
    mode: str | None,
    confirmations: int | None,
) -> dict[str, object]:
    evaluations: list[dict[str, object]] = []

    def authorizer(
        bar: object,
        candidate_stop: Decimal,
        current_stop: Decimal,
    ) -> bool:
        if mode is None or confirmations is None:
            return False
        authorized, diagnostic = _live_cognitive_decision(
            day_bars=day_bars,
            executable=executable,
            state=state,
            observation_at=cast(datetime, bar.closed_at),
            current_stop=current_stop,
            candidate_stop=candidate_stop,
            confirmations=confirmations,
            mode=mode,
        )
        evaluations.append(diagnostic)
        return authorized

    applied = confirmations
    outcome = composition._simulate_composite(
        day_bars,
        executable,
        state,
        window=WINDOW,
        pretarget_breaker_ps_confirmations=applied,
        pretarget_breaker_ps_authorizer=(
            authorizer if confirmations is not None else None
        ),
    )
    if outcome.get("status") == "terminal":
        outcome["target_plan"] = state["target_plan"]
        composition._attach_entry_context(outcome, state)
        outcome["live_cognitive_protection_mode"] = mode
        outcome["live_cognitive_protection_evaluations"] = evaluations
    return outcome


def _report(
    full_control: list[dict[str, object]],
    baseline: list[dict[str, object]],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    evaluations = [
        cast(dict[str, object], event)
        for row in rows
        for event in cast(
            list[dict[str, object]],
            row.get("live_cognitive_protection_evaluations", []),
        )
    ]
    blocker_counts: Counter[str] = Counter()
    for event in evaluations:
        blocker_counts.update(
            cast(list[str], event.get("maximum_intelligence_blockers", []))
        )
    return {
        "trade_count": len(rows),
        "relative_density_vs_unfiltered_b": format(
            Decimal(len(rows)) / Decimal(len(full_control)),
            "f",
        )
        if full_control
        else "0",
        "stress_0_05r": specialist._metrics(
            rows,
            friction=specialist.FRICTION,
        ),
        "monte_carlo": specialist._monte_carlo(rows),
        "halfyear_stress": specialist._block_metrics(rows, halfyear=True),
        "winner_preservation_vs_control": admission._winner_preservation(
            baseline,
            rows,
        ),
        "sequence_diagnostics": composition._sequence_diagnostics(rows),
        "pretarget_breaker_ps_committed_count": sum(
            row.get("pretarget_breaker_ps_committed") is True for row in rows
        ),
        "pretarget_breaker_ps_exit_count": sum(
            row.get("exit_reason")
            == "composite-breaker-pretarget-protective-stop"
            for row in rows
        ),
        "cognitive_evaluation_count": len(evaluations),
        "cognitive_trail_authorized_count": sum(
            event.get("authorized") is True for event in evaluations
        ),
        "management_context_counts": dict(
            sorted(
                Counter(
                    str(event.get("management_context", "NA"))
                    for event in evaluations
                ).items()
            )
        ),
        "protection_urgency_counts": dict(
            sorted(
                Counter(
                    str(event.get("protection_urgency", "NA"))
                    for event in evaluations
                ).items()
            )
        ),
        "decision_reason_counts": dict(
            sorted(
                Counter(
                    str(event.get("decision_reason", "NA"))
                    for event in evaluations
                ).items()
            )
        ),
        "maximum_cognition_verified_count": sum(
            event.get("maximum_cognition_verified") is True
            for event in evaluations
        ),
        "maximum_intelligence_blocker_counts": dict(
            sorted(blocker_counts.items())
        ),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    full_rows: dict[str, list[dict[str, object]]] = {
        name: [] for name in VARIANTS
    }

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

        for name, (mode, confirmations) in VARIANTS.items():
            outcome = _simulate(
                day_bars,
                executable,
                state,
                mode=mode,
                confirmations=confirmations,
            )
            if outcome.get("status") != "terminal":
                raise AssertionError(
                    f"{name} changed terminal eligibility: {outcome}"
                )
            full_rows[name].append(outcome)
        return structural

    try:
        specialist._simulate_selected_plan = simulator
        base_payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    structural_rows = cast(list[dict[str, object]], base_payload["trades"])
    structural_ids = [str(row["signal_at"]) for row in structural_rows]
    for name, rows in full_rows.items():
        if [str(row["signal_at"]) for row in rows] != structural_ids:
            raise AssertionError(
                f"{name} changed sovereign terminal trade identity"
            )

    filtered = {
        name: [
            row
            for row in rows
            if not admission._is_abstained(row, ADMISSION_VARIANT)
        ]
        for name, rows in full_rows.items()
    }
    baseline = filtered["CONTROL"]
    baseline_ids = [str(row["signal_at"]) for row in baseline]
    for name, rows in filtered.items():
        if [str(row["signal_at"]) for row in rows] != baseline_ids:
            raise AssertionError(
                f"{name} changed fixed admission population"
            )

    reports = {
        name: _report(full_rows["CONTROL"], baseline, rows)
        for name, rows in filtered.items()
    }
    control_map = {str(row["signal_at"]): row for row in baseline}
    for name, rows in filtered.items():
        candidate_map = {str(row["signal_at"]): row for row in rows}
        reports[name]["changed_trade_count_vs_control"] = sum(
            _d(candidate_map[key]["r_multiple"])
            != _d(control_map[key]["r_multiple"])
            for key in control_map
        )

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "admission_variant": ADMISSION_VARIANT,
        "b_comparator_id": B_COMPARATOR_ID,
        "variants": reports,
        "governance": {
            "consumed_evidence_only": True,
            "same_admission_population_all_variants": True,
            "entry_price_changed": False,
            "initial_stop_changed": False,
            "live_post_fill_cognition_reassessed": True,
            "frozen_entry_reasoning_preserved": True,
            "full_cognitive_accounting_required": True,
            "existing_market_native_position_decision_used": True,
            "winner_preservation_veto_active": True,
            "weak_path_thresholds_preexisting_not_newly_tuned": True,
            "protection_can_only_improve_stop": True,
            "protection_effective_next_m1": True,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "fold_identity_used_for_action": False,
            "future_outcome_used_for_action": False,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
