"""VT31 NAS100 maximum-cognition + R management frontier V1.

Research objective:
- use VT31's complete causal pre-entry cognition to decide whether a trade
  should remain structural-only or arm a 3R/4R breakeven rule;
- preserve the exact sovereign admission population;
- test contextual R rather than a universal R threshold.

This is consumed-evidence development. It cannot promote a runtime policy,
freeze a candidate, or open a fresh holdout.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_full_cognition_attribution_v1 as cognition_lab
import vt31_nas100_sovereign_r_management_frontier_v1 as r_frontier
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.traders.vt31_nas100_position_intelligence import (
    FullCognitivePositionState,
    ManagementContext,
    ProtectionUrgency,
    assess_full_cognitive_position,
    validate_full_cognitive_accounting_for_research,
)

SCHEMA = "qore.vt31.nas100.max_cognition_r_management_frontier.v1"
VARIANTS = (
    "STRUCTURAL_ONLY",
    "URGENCY_HIGH_BE3",
    "URGENCY_NONLOW_BE4",
    "URGENCY_HYBRID_HIGH3_MIXED4",
    "DESTINATION_SHALLOW3_NEUTRAL4_DEEP_HOLD",
    "FULL_COGNITION_HYBRID",
)


def _cognition(
    executable: object,
    state: dict[str, object],
) -> FullCognitivePositionState:
    observation_at = getattr(executable, "decision_at")
    source = getattr(executable, "source_setup")
    situation = cognition_lab._reconstruct_situation(
        state=state,
        selected=executable,
        source=source,
        observation_at=observation_at,
    )
    reasoning = cognition_lab._reconstruct_reasoning(state)
    cognition = assess_full_cognitive_position(
        situation=situation,
        reasoning=reasoning,
        entry_tier="CORE",
        dol1_acceptance_observed=None,
    )
    validate_full_cognitive_accounting_for_research(cognition)
    return cognition


def _threshold(
    variant: str,
    cognition: FullCognitivePositionState,
) -> Decimal | None:
    if variant == "STRUCTURAL_ONLY":
        return None

    if variant == "URGENCY_HIGH_BE3":
        return (
            Decimal("3")
            if cognition.protection_urgency is ProtectionUrgency.HIGH
            else None
        )

    if variant == "URGENCY_NONLOW_BE4":
        return (
            None
            if cognition.protection_urgency is ProtectionUrgency.LOW
            else Decimal("4")
        )

    if variant == "URGENCY_HYBRID_HIGH3_MIXED4":
        if cognition.protection_urgency is ProtectionUrgency.HIGH:
            return Decimal("3")
        if cognition.protection_urgency is ProtectionUrgency.MODERATE:
            return Decimal("4")
        return None

    if variant == "DESTINATION_SHALLOW3_NEUTRAL4_DEEP_HOLD":
        if cognition.destination_state == "SHALLOW":
            return Decimal("3")
        if cognition.destination_state == "NEUTRAL":
            return Decimal("4")
        return None

    if variant == "FULL_COGNITION_HYBRID":
        # Preserve the strongest-looking runner state. Protect only when the
        # integrated cognition contains material caution. The R milestone is
        # selected by urgency; R never changes volume.
        if (
            cognition.management_context is ManagementContext.CAUTIOUS
            or cognition.protection_urgency is ProtectionUrgency.HIGH
            or cognition.destination_state == "SHALLOW"
        ):
            return Decimal("3")
        if (
            cognition.management_context is ManagementContext.MIXED
            or cognition.protection_urgency is ProtectionUrgency.MODERATE
            or cognition.destination_state == "NEUTRAL"
        ):
            return Decimal("4")
        return None

    raise ValueError(f"unknown variant: {variant}")


def _winner_preservation(
    baseline: list[dict[str, object]],
    candidate: list[dict[str, object]],
) -> dict[str, object]:
    return r_frontier._winner_preservation(baseline, candidate)


def replay(evidence_path: Path) -> dict[str, object]:
    original = specialist._simulate_selected_plan
    payloads: dict[str, dict[str, object]] = {}
    cognitive_counts: dict[str, Counter[str]] = {
        variant: Counter() for variant in VARIANTS
    }

    try:
        for variant in VARIANTS:

            def simulator(
                day_bars: tuple[object, ...],
                executable: object,
                state: dict[str, object],
                *,
                _variant: str = variant,
            ) -> dict[str, object]:
                cognition = _cognition(executable, state)
                threshold = _threshold(_variant, cognition)
                cognitive_counts[_variant][
                    f"context={cognition.management_context.value}"
                ] += 1
                cognitive_counts[_variant][
                    f"urgency={cognition.protection_urgency.value}"
                ] += 1
                cognitive_counts[_variant][
                    f"destination={cognition.destination_state}"
                ] += 1
                cognitive_counts[_variant][
                    "threshold="
                    + ("HOLD" if threshold is None else f"{threshold}R")
                ] += 1

                outcome = r_frontier._simulate(
                    day_bars,
                    executable,
                    threshold_r=threshold,
                )
                if outcome.get("status") == "terminal":
                    outcome["target_plan"] = state["target_plan"]
                    outcome["cognition_context"] = (
                        cognition.management_context.value
                    )
                    outcome["cognition_urgency"] = (
                        cognition.protection_urgency.value
                    )
                    outcome["cognition_destination"] = (
                        cognition.destination_state
                    )
                    outcome["cognition_support_score"] = (
                        cognition.support_score
                    )
                    outcome["cognition_caution_score"] = (
                        cognition.caution_score
                    )
                    outcome["full_cognitive_accounting_verified"] = (
                        cognition.full_cognitive_accounting_verified
                    )
                    outcome["maximum_cognition_verified"] = (
                        cognition.maximum_cognition_verified
                    )
                    outcome["reasoning_max_intelligence_ready"] = (
                        cognition.reasoning_max_intelligence_ready
                    )
                    outcome["reasoning_max_intelligence_blockers"] = list(
                        cognition.reasoning_max_intelligence_blockers
                    )
                    outcome["selected_be_threshold_r"] = (
                        None if threshold is None else format(threshold, "f")
                    )
                return outcome

            specialist._simulate_selected_plan = simulator
            payloads[variant] = specialist.replay(evidence_path)
    finally:
        specialist._simulate_selected_plan = original

    baseline = cast(
        list[dict[str, object]],
        payloads["STRUCTURAL_ONLY"]["trades"],
    )
    baseline_ids = [str(row["signal_at"]) for row in baseline]

    variants: dict[str, object] = {}
    for variant, payload in payloads.items():
        rows = cast(list[dict[str, object]], payload["trades"])
        ids = [str(row["signal_at"]) for row in rows]
        if ids != baseline_ids:
            raise AssertionError(
                f"{variant} changed sovereign admission population"
            )
        if any(
            row.get("full_cognitive_accounting_verified") is not True
            for row in rows
        ):
            raise AssertionError(
                f"{variant} contains an incompletely-accounted cognition trade"
            )

        variants[variant] = {
            "trade_count": len(rows),
            "stress_0_05r": payload["stress_0_05r"],
            "monte_carlo": payload["monte_carlo"],
            "halfyear_stress": payload["halfyear_stress"],
            "quarter_stress": payload["quarter_stress"],
            "target_plan_counts": payload["target_plan_counts"],
            "breakeven_armed_count": sum(
                row.get("breakeven_armed") is True for row in rows
            ),
            "selected_threshold_counts": dict(
                sorted(
                    Counter(
                        str(row.get("selected_be_threshold_r"))
                        for row in rows
                    ).items()
                )
            ),
            "cognitive_counts": dict(
                sorted(cognitive_counts[variant].items())
            ),
            "winner_preservation_vs_structural": (
                None
                if variant == "STRUCTURAL_ONLY"
                else _winner_preservation(baseline, rows)
            ),
        }

    return {
        "schema": SCHEMA,
        "market": "NAS100",
        "variants": variants,
        "governance": {
            "full_cognitive_accounting_required_for_every_trade": True,
            "maximum_intelligence_required_for_candidate_freeze": True,
            "same_admission_population": True,
            "entry_changed": False,
            "initial_structural_invalidation_changed": False,
            "structural_target_changed": False,
            "lifecycle_changed": False,
            "r_runtime_strategy_allowed": True,
            "r_used_for_volume": False,
            "position_sizing_used": False,
            "leverage_used": False,
            "compounding_used": False,
            "capital_weighting_used": False,
            "absolute_volume_used": False,
            "future_outcome_used_for_threshold_selection": False,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "live_authorized": False,
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
    print(
        json.dumps(
            {
                "variants": payload["variants"],
                "governance": payload["governance"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
