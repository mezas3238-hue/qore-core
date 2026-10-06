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
from collections import Counter, defaultdict
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
    "COG_EXIT_STALE_MIXED",
    "COG_EXIT_CAUTION_OR_STALE_MIXED",
    "BASE_PLUS_FVG_NONSHALLOW",
    "BASE_PLUS_NONOB_NORMAL",
    "BASE_PLUS_FVG_NONSHALLOW_OR_NONOB_NORMAL",
    "COG_EXIT_NONSUPPORTIVE",
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _exit_allowed(
    diagnostic: dict[str, object],
    *,
    variant: str,
    entry_family: str,
    reference_volatility_state: str,
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
    reclaim_age_raw = diagnostic.get("reference_reclaim_age_minutes")
    reclaim_age = (
        None if reclaim_age_raw is None else int(reclaim_age_raw)
    )
    stale_sequence = (
        reclaim_age is not None
        and 8 <= reclaim_age < 15
    )

    if variant == "COG_EXIT_CAUTION":
        return context == "CAUTIOUS"
    if variant == "COG_EXIT_CAUTION_WEAK_PATH":
        return context == "CAUTIOUS" and weak_path
    if variant == "COG_EXIT_STALE_MIXED":
        return context == "MIXED" and stale_sequence
    base_safe = context == "CAUTIOUS" or (
        context == "MIXED" and stale_sequence
    )
    if variant == "COG_EXIT_CAUTION_OR_STALE_MIXED":
        return base_safe

    fvg_nonshallow = (
        entry_family == "fair-value-gap"
        and str(diagnostic["destination_state"]) != "SHALLOW"
    )
    nonob_normal = (
        reference_volatility_state == "normal"
        and entry_family != "order-block"
    )
    if variant == "BASE_PLUS_FVG_NONSHALLOW":
        return base_safe or fvg_nonshallow
    if variant == "BASE_PLUS_NONOB_NORMAL":
        return base_safe or nonob_normal
    if variant == "BASE_PLUS_FVG_NONSHALLOW_OR_NONOB_NORMAL":
        return base_safe or fvg_nonshallow or nonob_normal
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
        allowed = _exit_allowed(
            diagnostic,
            variant=variant,
            entry_family=str(executable.selected_family.value),
            reference_volatility_state=str(
                state["reference_volatility_state"]
            ),
        )
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


def _bucket_support_margin(value: object) -> str:
    margin = int(value)
    if margin <= -3:
        return "LE_-3"
    if margin <= -1:
        return "-2_-1"
    if margin <= 1:
        return "-0_1"
    if margin <= 3:
        return "2_3"
    return "GE_4"


def _bucket_open_r(value: object) -> str:
    open_r = _d(value)
    if open_r <= Decimal("-0.75"):
        return "LE_-0.75R"
    return "-0.75_TO_-0.50R"


def _bucket_reclaim_age(value: object) -> str:
    if value is None:
        return "NONE"
    age = int(value)
    if age < 8:
        return "LT8M"
    if age < 15:
        return "8_14M"
    return "GE15M"


def _bucket_efficiency(value: object) -> str:
    if value is None:
        return "NONE"
    efficiency = _d(value)
    if efficiency <= Decimal("0.30"):
        return "WEAK_LE_0.30"
    if efficiency >= Decimal("0.55"):
        return "HEALTHY_GE_0.55"
    return "MID"


def _bucket_overlap(value: object) -> str:
    if value is None:
        return "NONE"
    overlap = _d(value)
    if overlap >= Decimal("0.75"):
        return "HIGH_GE_0.75"
    if overlap <= Decimal("0.55"):
        return "LOW_LE_0.55"
    return "MID"


def _bucket_minutes(value: object) -> str:
    if value is None:
        return "NONE"
    minute = int(value)
    if minute <= 2:
        return "0_2M"
    if minute <= 5:
        return "3_5M"
    if minute <= 10:
        return "6_10M"
    return "GE11M"


def _state_transition(entry: object, current: object) -> str:
    return f"{entry}->{current}"


def _first_material_adverse_forensics(
    baseline: list[dict[str, object]],
    rows: list[dict[str, object]],
) -> dict[str, object]:
    baseline_map = {str(row["signal_at"]): row for row in baseline}
    samples: list[dict[str, object]] = []
    for row in rows:
        first = next(
            (
                cast(dict[str, object], event)
                for event in cast(
                    list[dict[str, object]],
                    row.get("cognitive_exit_evaluations", []),
                )
                if event.get("current_open_r") is not None
                and _d(event["current_open_r"]) <= MATERIAL_ADVERSE_R
            ),
            None,
        )
        if first is None:
            continue
        control = baseline_map[str(row["signal_at"])]
        control_net_r = _d(control["r_multiple"]) - specialist.FRICTION
        candidate_net_r = _d(row["r_multiple"]) - specialist.FRICTION
        entry_context = cast(
            dict[str, object],
            row.get("entry_context", {}),
        )
        samples.append(
            {
                "management_context": str(first["management_context"]),
                "entry_family": str(row["entry_family"]),
                "side": str(row["side"]),
                "prior_day_state": str(
                    entry_context.get("prior_day_state", "NA")
                ),
                "position_in_prior_day_range": str(
                    entry_context.get("position_in_prior_day_range", "NA")
                ),
                "reference_volatility_state": str(
                    entry_context.get("reference_volatility_state", "NA")
                ),
                "entry_h1_state": str(
                    entry_context.get("h1_state", "NA")
                ),
                "entry_m15_state": str(
                    entry_context.get("m15_state", "NA")
                ),
                "confirmation_latency_bucket": _bucket_minutes(
                    entry_context.get("confirmation_latency_minutes")
                ),
                "entry_evidence_age_bucket": _bucket_minutes(
                    entry_context.get("entry_evidence_age_minutes")
                ),
                "weak_path": bool(first.get("weak_path")),
                "current_reasoning_action": str(
                    first["current_reasoning_action"]
                ),
                "m15_state": str(first["m15_state"]),
                "h1_state": str(first["h1_state"]),
                "h4_state": str(first["h4_state"]),
                "h1_transition": _state_transition(
                    entry_context.get("h1_state", "NA"),
                    first["h1_state"],
                ),
                "m15_transition": _state_transition(
                    entry_context.get("m15_state", "NA"),
                    first["m15_state"],
                ),
                "destination_state": str(first["destination_state"]),
                "efficiency_bucket": _bucket_efficiency(
                    first.get("recent_path_efficiency")
                ),
                "overlap_bucket": _bucket_overlap(
                    first.get("recent_overlap_rate")
                ),
                "last_structure_event_family": str(
                    first["last_structure_event_family"]
                ),
                "last_structure_event_age_bucket": _bucket_minutes(
                    first.get("last_structure_event_age_minutes")
                ),
                "support_margin_bucket": _bucket_support_margin(
                    first["support_margin"]
                ),
                "open_r_bucket": _bucket_open_r(first["current_open_r"]),
                "reclaim_age_bucket": _bucket_reclaim_age(
                    first.get("reference_reclaim_age_minutes")
                ),
                "control_net_r": control_net_r,
                "candidate_net_r": candidate_net_r,
                "changed_vs_control": candidate_net_r != control_net_r,
            }
        )

    fields = (
        ("management_context",),
        ("entry_family",),
        ("side",),
        ("prior_day_state",),
        ("position_in_prior_day_range",),
        ("reference_volatility_state",),
        ("h1_transition",),
        ("m15_transition",),
        ("efficiency_bucket",),
        ("overlap_bucket",),
        ("last_structure_event_age_bucket",),
        ("confirmation_latency_bucket",),
        ("entry_evidence_age_bucket",),
        ("entry_family", "management_context"),
        ("entry_family", "side"),
        ("entry_family", "reclaim_age_bucket"),
        ("entry_family", "m15_state"),
        ("entry_family", "h1_state"),
        ("entry_family", "destination_state"),
        ("entry_family", "prior_day_state"),
        ("entry_family", "reference_volatility_state"),
        ("entry_family", "position_in_prior_day_range"),
        ("side", "m15_state"),
        ("side", "h1_state"),
        ("side", "reclaim_age_bucket"),
        ("management_context", "weak_path"),
        ("management_context", "m15_state"),
        ("management_context", "h1_state"),
        ("management_context", "h4_state"),
        ("management_context", "destination_state"),
        ("management_context", "current_reasoning_action"),
        ("management_context", "last_structure_event_family"),
        ("management_context", "support_margin_bucket"),
        ("management_context", "open_r_bucket"),
        ("management_context", "reclaim_age_bucket"),
        ("h1_state", "m15_state"),
        ("prior_day_state", "m15_state"),
        ("position_in_prior_day_range", "m15_state"),
        ("reference_volatility_state", "m15_state"),
        ("efficiency_bucket", "overlap_bucket"),
        ("last_structure_event_family", "last_structure_event_age_bucket"),
        ("entry_family", "m15_state", "reclaim_age_bucket"),
        ("side", "m15_state", "reclaim_age_bucket"),
        ("h1_state", "m15_state", "reclaim_age_bucket"),
        ("m15_state", "efficiency_bucket", "overlap_bucket"),
    )

    def summarize(
        selected: list[dict[str, object]],
    ) -> dict[str, dict[str, object]]:
        grouped: dict[str, dict[str, object]] = {}
        for field_tuple in fields:
            table: dict[str, list[dict[str, object]]] = defaultdict(list)
            for sample in selected:
                key = "|".join(str(sample[field]) for field in field_tuple)
                table[key].append(sample)
            grouped["+".join(field_tuple)] = {
                key: {
                    "sample": len(items),
                    "control_wins": sum(
                        cast(Decimal, item["control_net_r"]) > 0
                        for item in items
                    ),
                    "control_losses": sum(
                        cast(Decimal, item["control_net_r"]) < 0
                        for item in items
                    ),
                    "candidate_wins": sum(
                        cast(Decimal, item["candidate_net_r"]) > 0
                        for item in items
                    ),
                    "candidate_losses": sum(
                        cast(Decimal, item["candidate_net_r"]) < 0
                        for item in items
                    ),
                    "changed_count": sum(
                        bool(item["changed_vs_control"]) for item in items
                    ),
                    "mean_control_net_r": format(
                        sum(
                            (
                                cast(Decimal, item["control_net_r"])
                                for item in items
                            ),
                            Decimal(0),
                        )
                        / Decimal(len(items)),
                        "f",
                    ),
                    "mean_candidate_net_r": format(
                        sum(
                            (
                                cast(Decimal, item["candidate_net_r"])
                                for item in items
                            ),
                            Decimal(0),
                        )
                        / Decimal(len(items)),
                        "f",
                    ),
                }
                for key, items in sorted(table.items())
            }
        return grouped

    unchanged = [
        sample
        for sample in samples
        if not bool(sample["changed_vs_control"])
    ]
    return {
        "observation_only": True,
        "action_authority": False,
        "outcome_used_only_for_forensic_attribution": True,
        "first_material_adverse_trade_count": len(samples),
        "unchanged_first_material_adverse_trade_count": len(unchanged),
        "groups": summarize(samples),
        "unchanged_groups": summarize(unchanged),
    }

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
        "first_material_adverse_forensics": _first_material_adverse_forensics(
            baseline,
            rows,
        ),
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
            "stale_sequence_8_14_preexisting_reasoning_state": True,
            "stale_sequence_threshold_newly_outcome_tuned": False,
            "residual_context_hypotheses_consumed_discovery_only": True,
            "residual_context_new_numeric_threshold_added": False,
            "position_sizing_used": False,
            "dynamic_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "fold_identity_used_for_action": False,
            "future_outcome_used_for_action": False,
            "material_adverse_forensics_observation_only": True,
            "material_adverse_forensics_action_authority": False,
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
