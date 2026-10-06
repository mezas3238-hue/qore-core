"""VT31 NAS100 causal adverse-journey cognitive-exit frontier V1.

Consumed-evidence development only.

Fixed stack:
- admission: A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M;
- H3 full-cognition post-1R management;
- W5 soft-DOL1;
- full-cognition DOL2;
- post-acceptance PS2.

The only degree of freedom is whether full causal post-entry cognition may exit
a still-pre-DOL1 trade after a MATERIAL_ADVERSE current journey observation.

A decision is made only from a fully closed M1 and executes at the next M1
open. No same-bar close execution, outcome label, fold identity, sizing,
leverage, compounding or capital weighting is allowed.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_a_b_admission_integration_frontier_v1 as admission
import vt31_nas100_h3_dol2_composition_frontier_v1 as composition
import vt31_nas100_live_cognitive_breaker_protection_frontier_v1 as live_cognition
import vt31_nas100_specialist_r1_candidate as specialist

SCHEMA = "qore.vt31.nas100.adverse_journey_cognitive_exit_frontier.v1"
ADMISSION_VARIANT = "A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M"
B_COMPARATOR_ID = "VT31_BSIDE_H3_W5_DOL2_PS2_RESEARCH_COMPARATOR_001"
WINDOW = 5
MATERIAL_ADVERSE_R = Decimal("-0.50")

VARIANTS = (
    "CONTROL",
    "COG_EXIT_CAUTION",
    "COG_EXIT_CAUTION_WEAK_PATH",
    "COG_EXIT_NONSUPPORTIVE",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _exit_allowed(
    diagnostic: dict[str, object],
    *,
    variant: str,
) -> bool:
    if variant == "CONTROL":
        return False
    if diagnostic.get("maximum_cognition_verified") is not True:
        return False

    open_r = _d(diagnostic["current_open_r"])
    if open_r > MATERIAL_ADVERSE_R:
        return False

    context = str(diagnostic["management_context"])
    weak_path = diagnostic.get("weak_path") is True

    if variant == "COG_EXIT_CAUTION":
        return context == "CAUTIOUS"
    if variant == "COG_EXIT_CAUTION_WEAK_PATH":
        return context == "CAUTIOUS" and weak_path
    if variant == "COG_EXIT_NONSUPPORTIVE":
        return context in {"MIXED", "CAUTIOUS"}
    raise ValueError(f"unsupported variant: {variant}")


def _simulate(
    day_bars: tuple[object, ...],
    executable: object,
    state: dict[str, object],
    *,
    variant: str,
) -> dict[str, object]:
    evaluations: list[dict[str, object]] = []

    def exit_authorizer(
        bar: object,
        current_stop: Decimal,
    ) -> bool:
        observation_at = cast(datetime, getattr(bar, "closed_at"))
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
        allowed = _exit_allowed(diagnostic, variant=variant)
        diagnostic["cognitive_exit_variant"] = variant
        diagnostic["cognitive_exit_authorized"] = allowed
        evaluations.append(diagnostic)
        return allowed

    outcome = composition._simulate_composite(
        day_bars,
        executable,
        state,
        window=WINDOW,
        pretarget_cognitive_exit_authorizer=(
            None if variant == "CONTROL" else exit_authorizer
        ),
    )
    if outcome.get("status") == "terminal":
        outcome["target_plan"] = state["target_plan"]
        composition._attach_entry_context(outcome, state)
        outcome["cognitive_exit_variant"] = variant
        outcome["cognitive_exit_evaluations"] = evaluations
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
            row.get("cognitive_exit_evaluations", []),
        )
    ]
    return {
        "trade_count": len(rows),
        "relative_density_vs_unfiltered_b": (
            "0"
            if not full_control
            else format(
                Decimal(len(rows)) / Decimal(len(full_control)),
                "f",
            )
        ),
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
        "cognitive_exit_count": sum(
            row.get("exit_reason")
            == "composite-pretarget-cognitive-exit"
            for row in rows
        ),
        "cognitive_evaluation_count": len(evaluations),
        "cognitive_exit_authorized_count": sum(
            event.get("cognitive_exit_authorized") is True
            for event in evaluations
        ),
        "material_adverse_observation_count": sum(
            _d(event["current_open_r"]) <= MATERIAL_ADVERSE_R
            for event in evaluations
            if event.get("current_open_r") is not None
        ),
        "management_context_counts": dict(
            sorted(
                Counter(
                    str(event.get("management_context", "NA"))
                    for event in evaluations
                ).items()
            )
        ),
        "authorized_context_counts": dict(
            sorted(
                Counter(
                    str(event.get("management_context", "NA"))
                    for event in evaluations
                    if event.get("cognitive_exit_authorized") is True
                ).items()
            )
        ),
        "authorized_open_r": [
            str(event["current_open_r"])
            for event in evaluations
            if event.get("cognitive_exit_authorized") is True
        ],
        "maximum_cognition_verified_count": sum(
            event.get("maximum_cognition_verified") is True
            for event in evaluations
        ),
        "maximum_intelligence_blocker_counts": dict(
            sorted(
                Counter(
                    blocker
                    for event in evaluations
                    for blocker in cast(
                        list[str],
                        event.get("maximum_intelligence_blockers", []),
                    )
                ).items()
            )
        ),
    }


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    full_rows: dict[str, list[dict[str, object]]] = {
        variant: [] for variant in VARIANTS
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

        for variant in VARIANTS:
            outcome = _simulate(
                day_bars,
                executable,
                state,
                variant=variant,
            )
            if outcome.get("status") != "terminal":
                raise AssertionError(
                    f"{variant} changed terminal eligibility: {outcome}"
                )
            full_rows[variant].append(outcome)
        return structural

    try:
        specialist._simulate_selected_plan = simulator
        base_payload = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    structural_rows = cast(list[dict[str, object]], base_payload["trades"])
    structural_ids = [str(row["signal_at"]) for row in structural_rows]
    for variant, rows in full_rows.items():
        if [str(row["signal_at"]) for row in rows] != structural_ids:
            raise AssertionError(
                f"{variant} changed sovereign terminal trade identity"
            )

    filtered = {
        variant: [
            row
            for row in rows
            if not admission._is_abstained(row, ADMISSION_VARIANT)
        ]
        for variant, rows in full_rows.items()
    }
    baseline = filtered["CONTROL"]
    baseline_ids = [str(row["signal_at"]) for row in baseline]
    for variant, rows in filtered.items():
        if [str(row["signal_at"]) for row in rows] != baseline_ids:
            raise AssertionError(
                f"{variant} changed fixed admission population"
            )

    reports = {
        variant: _report(full_rows["CONTROL"], baseline, rows)
        for variant, rows in filtered.items()
    }
    control_map = {str(row["signal_at"]): row for row in baseline}
    for variant, rows in filtered.items():
        candidate_map = {str(row["signal_at"]): row for row in rows}
        reports[variant]["changed_trade_count_vs_control"] = sum(
            _d(candidate_map[key]["r_multiple"])
            != _d(control_map[key]["r_multiple"])
            for key in control_map
        )

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "admission_variant": ADMISSION_VARIANT,
        "b_comparator_id": B_COMPARATOR_ID,
        "material_adverse_r": format(MATERIAL_ADVERSE_R, "f"),
        "variants": reports,
        "governance": {
            "consumed_evidence_only": True,
            "same_admission_population_all_variants": True,
            "same_entry_all_variants": True,
            "same_initial_stop_all_variants": True,
            "same_target_stack_until_cognitive_exit": True,
            "live_full_cognition_reassessed": True,
            "current_open_r_causal": True,
            "current_open_r_uses_frozen_initial_risk": True,
            "exit_decision_on_closed_m1": True,
            "exit_execution_next_m1_open": True,
            "same_bar_hindsight_used": False,
            "material_adverse_threshold_predeclared": True,
            "material_adverse_threshold_newly_outcome_tuned": False,
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
