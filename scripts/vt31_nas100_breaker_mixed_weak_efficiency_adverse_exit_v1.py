"""VT31 NAS100 Breaker mixed weak-efficiency adverse exit frontier V1.

Consumed-evidence development only.

Fixed base:
    VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR

Only new degree of freedom:
- preserve all Comparator-007 cognitive exits;
- for a still-pre-DOL1 Breaker, after a fully closed M1, additionally authorize
  next-M1-open EXIT when:
    * maximum cognition is verified;
    * current_open_r <= existing MATERIAL_ADVERSE_R (-0.50R);
    * management_context == MIXED;
    * recent_path_efficiency is available and <= existing weak-path 0.30.

No future bar, outcome, date/fold identity, sizing, leverage, compounding,
portfolio or capital state can influence action.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_adverse_journey_cognitive_exit_frontier_v1 as adverse
import vt31_nas100_breaker_rotation_recovery_exception_frontier_v1 as recovery
import vt31_nas100_comp007_residual_dd_forensics_v1 as comp007
import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_live_cognitive_breaker_protection_frontier_v1 as live_cognition
import vt31_nas100_rapid_breaker_conflict_admission_frontier_v1 as rapid
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.breaker_mixed_weak_efficiency_adverse_exit.v1"
COMPARATOR_ID = "VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR"
VARIANT = "COMP007_PLUS_BREAKER_MIXED_WEAK_EFFICIENCY_ADVERSE_EXIT"
WEAK_EFFICIENCY_THRESHOLD = Decimal("0.30")


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _extra_exit_allowed(
    diagnostic: dict[str, object],
    *,
    entry_family: str,
) -> bool:
    if entry_family != "breaker":
        return False
    if diagnostic.get("maximum_cognition_verified") is not True:
        return False
    if _d(diagnostic["current_open_r"]) > adverse.MATERIAL_ADVERSE_R:
        return False
    if str(diagnostic["management_context"]) != "MIXED":
        return False
    efficiency = diagnostic.get("recent_path_efficiency")
    if efficiency is None:
        return False
    return _d(efficiency) <= WEAK_EFFICIENCY_THRESHOLD


def _simulate_candidate(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
) -> dict[str, object]:
    evaluations: list[dict[str, object]] = []
    entry_family = str(executable.selected_family.value)
    reference_volatility_state = str(state["reference_volatility_state"])

    def exit_authorizer(
        bar: object,
        current_stop: Decimal,
    ) -> bool:
        observation_at = cast(datetime, bar.closed_at)
        _, diagnostic = live_cognition._live_cognitive_decision(
            day_bars=day_bars,
            executable=executable,
            state=state,
            observation_at=observation_at,
            current_stop=current_stop,
            candidate_stop=current_stop,
            confirmations=1,
            mode="WEAK_PATH",
        )
        base_allowed = adverse._exit_allowed(
            diagnostic,
            variant=rapid.POSITION_VARIANT,
            entry_family=entry_family,
            reference_volatility_state=reference_volatility_state,
        )
        extra_allowed = _extra_exit_allowed(
            diagnostic,
            entry_family=entry_family,
        )
        allowed = base_allowed or extra_allowed
        diagnostic["cognitive_exit_variant"] = VARIANT
        diagnostic["cognitive_exit_authorized"] = allowed
        diagnostic["comp007_base_exit_authorized"] = base_allowed
        diagnostic["breaker_mixed_weak_efficiency_exit_authorized"] = (
            extra_allowed
        )
        evaluations.append(diagnostic)
        return allowed

    outcome = composition._simulate_composite(
        day_bars,
        executable,
        state,
        window=adverse.WINDOW,
        pretarget_cognitive_exit_authorizer=exit_authorizer,
    )
    if outcome.get("status") == "terminal":
        outcome["target_plan"] = state["target_plan"]
        composition._attach_entry_context(outcome, state)
        outcome["cognitive_exit_variant"] = VARIANT
        outcome["cognitive_exit_evaluations"] = evaluations
    return outcome


def _apply_comp007_admission(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    admitted = [
        row
        for row in rows
        if not admission._is_abstained(row, rapid.ADMISSION_BASE)
    ]
    recovery_filtered = [
        row for row in admitted if not recovery._should_abstain(row)
    ]
    fvg_filtered = [
        row
        for row in recovery_filtered
        if not recovery._fvg_short_compressed_fresh_fast(row)
    ]
    comp006 = [
        row
        for row in fvg_filtered
        if not recovery._episode_breaker_bearish_compressed_bullish(row)
    ]
    return [
        row
        for row in comp006
        if not (rapid._conflict_a(row) or rapid._conflict_b(row))
    ]


def _build_candidate_rows(
    evidence_path: Path,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    original = specialist._simulate_selected_plan
    position_rows: list[dict[str, object]] = []

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

        outcome = _simulate_candidate(day_bars, executable, state)
        if outcome.get("status") != "terminal":
            raise AssertionError(
                "candidate changed sovereign terminal eligibility: "
                f"{outcome}"
            )
        position_rows.append(outcome)
        return structural

    try:
        specialist._simulate_selected_plan = simulator
        base_payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    structural_rows = cast(
        list[dict[str, object]],
        base_payload["trades"],
    )
    structural_ids = [str(row["signal_at"]) for row in structural_rows]
    if [str(row["signal_at"]) for row in position_rows] != structural_ids:
        raise AssertionError(
            "candidate changed sovereign terminal trade identity"
        )

    return structural_rows, _apply_comp007_admission(position_rows)


def _changed_trade_forensics(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> list[dict[str, object]]:
    baseline_map = {str(row["signal_at"]): row for row in baseline}
    candidate_map = {str(row["signal_at"]): row for row in candidate}
    if set(baseline_map) != set(candidate_map):
        raise AssertionError(
            "position-only frontier changed Comparator-007 trade identity"
        )

    changed = []
    for signal_at in sorted(baseline_map):
        left = baseline_map[signal_at]
        right = candidate_map[signal_at]
        left_r = _d(left["r_multiple"])
        right_r = _d(right["r_multiple"])
        if left_r == right_r and left.get("exit_reason") == right.get(
            "exit_reason"
        ):
            continue

        events = cast(
            list[dict[str, object]],
            right.get("cognitive_exit_evaluations", []),
        )
        extra_events = [
            event
            for event in events
            if event.get(
                "breaker_mixed_weak_efficiency_exit_authorized"
            )
            is True
        ]
        changed.append(
            {
                "signal_at": signal_at,
                "entry_family": right.get("entry_family"),
                "side": right.get("side"),
                "baseline_r": format(left_r, "f"),
                "candidate_r": format(right_r, "f"),
                "delta_r": format(right_r - left_r, "f"),
                "baseline_exit_reason": left.get("exit_reason"),
                "candidate_exit_reason": right.get("exit_reason"),
                "entry_context": right.get("entry_context", {}),
                "extra_authorization_events": extra_events,
            }
        )
    return changed


def _report(
    *,
    structural_count: int,
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> dict[str, object]:
    changed = _changed_trade_forensics(baseline, candidate)
    evaluations = [
        cast(dict[str, object], event)
        for row in candidate
        for event in cast(
            list[dict[str, object]],
            row.get("cognitive_exit_evaluations", []),
        )
    ]
    return {
        "trade_count": len(candidate),
        "same_trade_identity": (
            [str(row["signal_at"]) for row in baseline]
            == [str(row["signal_at"]) for row in candidate]
        ),
        "relative_density_vs_structural": (
            "0"
            if structural_count == 0
            else format(
                Decimal(len(candidate)) / Decimal(structural_count),
                "f",
            )
        ),
        "relative_density_vs_comp007": (
            "0"
            if not baseline
            else format(
                Decimal(len(candidate)) / Decimal(len(baseline)),
                "f",
            )
        ),
        "stress_0_05r": specialist._metrics(
            candidate,
            friction=specialist.FRICTION,
        ),
        "monte_carlo": specialist._monte_carlo(candidate),
        "halfyear_stress": specialist._block_metrics(
            candidate,
            halfyear=True,
        ),
        "winner_preservation_vs_comp007": admission._winner_preservation(
            baseline,
            candidate,
        ),
        "sequence_diagnostics": composition._sequence_diagnostics(candidate),
        "changed_trade_count": len(changed),
        "changed_trade_forensics": changed,
        "cognitive_evaluation_count": len(evaluations),
        "extra_authorization_count": sum(
            event.get(
                "breaker_mixed_weak_efficiency_exit_authorized"
            )
            is True
            for event in evaluations
        ),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    structural_base, comparator = comp007._build_union_rows(evidence_path)
    structural_candidate, candidate = _build_candidate_rows(evidence_path)

    base_ids = [str(row["signal_at"]) for row in structural_base]
    candidate_ids = [str(row["signal_at"]) for row in structural_candidate]
    if base_ids != candidate_ids:
        raise AssertionError("structural replay identity changed")

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "comparator_id": COMPARATOR_ID,
        "variant": VARIANT,
        "baseline": {
            "trade_count": len(comparator),
            "stress_0_05r": specialist._metrics(
                comparator,
                friction=specialist.FRICTION,
            ),
            "monte_carlo": specialist._monte_carlo(comparator),
            "halfyear_stress": specialist._block_metrics(
                comparator,
                halfyear=True,
            ),
        },
        "candidate": _report(
            structural_count=len(structural_candidate),
            baseline=comparator,
            candidate=candidate,
        ),
        "governance": {
            "consumed_evidence_only": True,
            "same_admission_as_comp007": True,
            "same_target_stack_until_new_cognitive_exit": True,
            "next_m1_open_execution": True,
            "material_adverse_threshold_preexisting": True,
            "weak_efficiency_threshold_preexisting": True,
            "new_numeric_threshold_added": False,
            "maximum_cognition_required": True,
            "outcome_used_for_action": False,
            "fold_identity_used_for_action": False,
            "date_identity_used_for_action": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
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
