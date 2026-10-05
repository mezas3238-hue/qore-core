"""MC25 formal governance stress for the same-lineage candidate.

This stage is deliberately distinct from market performance stress. It proves
that the governed lifecycle fails closed when stage order, evidence lineage,
terminality, promotion authority, or productive authority are violated.
"""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from typing import Final

from qore.infrastructure.core_stack_v2.mc25_governed_lifecycle import (
    MC25LifecycleState,
    MC25Stage,
    advance_mc25_stage,
    initial_mc25_state,
)

FORMAL_STRESS_ID: Final = "QORE_SHARED_MC25_FORMAL_GOVERNANCE_STRESS_001"


def _fingerprint(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _must_reject(callable_obj) -> bool:
    try:
        callable_obj()
    except (ValueError, TypeError):
        return True
    return False


def run_formal_governance_stress() -> dict[str, object]:
    state = initial_mc25_state(
        candidate_id="WP04_V3B_REPRESENTATION",
        configuration_fingerprint=_fingerprint("WP04_V3B_REPRESENTATION"),
        evidence_refs=("freeze:sealed",),
    )
    state = advance_mc25_stage(
        state,
        target_stage=MC25Stage.LINEAGE_INTEGRITY,
        stage_passed=True,
        evidence_refs=("lineage-integrity:pass",),
    )
    state = advance_mc25_stage(
        state,
        target_stage=MC25Stage.PERFORMANCE_STRESS,
        stage_passed=True,
        evidence_refs=("performance-stress:pass",),
    )

    scenarios: dict[str, bool] = {}

    scenarios["SKIP_FORMAL_STRESS_TO_SHADOW"] = _must_reject(
        lambda: advance_mc25_stage(
            state,
            target_stage=MC25Stage.SHADOW,
            stage_passed=True,
            evidence_refs=("shadow:fake",),
        )
    )
    scenarios["SKIP_TO_CERTIFICATION"] = _must_reject(
        lambda: advance_mc25_stage(
            state,
            target_stage=MC25Stage.CERTIFICATION,
            stage_passed=True,
            evidence_refs=("certification:fake",),
        )
    )
    scenarios["SKIP_TO_PROMOTION"] = _must_reject(
        lambda: advance_mc25_stage(
            state,
            target_stage=MC25Stage.PROMOTION,
            stage_passed=True,
            evidence_refs=("promotion:fake",),
            owner_approval_ref="owner:fake",
        )
    )

    formal_state = advance_mc25_stage(
        state,
        target_stage=MC25Stage.FORMAL_STRESS,
        stage_passed=True,
        evidence_refs=("formal-stress:sealed",),
    )
    scenarios["PROMOTION_BEFORE_SHADOW_CERTIFICATION"] = _must_reject(
        lambda: advance_mc25_stage(
            formal_state,
            target_stage=MC25Stage.PROMOTION,
            stage_passed=True,
            evidence_refs=("promotion:fake",),
            owner_approval_ref="owner:fake",
        )
    )

    failed = advance_mc25_stage(
        state,
        target_stage=MC25Stage.FORMAL_STRESS,
        stage_passed=False,
        evidence_refs=("formal-stress:falsified",),
    )
    scenarios["FALSIFIED_CONFIGURATION_REOPEN"] = _must_reject(
        lambda: advance_mc25_stage(
            failed,
            target_stage=MC25Stage.SHADOW,
            stage_passed=True,
            evidence_refs=("shadow:fake",),
        )
    )

    scenarios["PRODUCTIVE_AUTHORITY_FORBIDDEN"] = _must_reject(
        lambda: MC25LifecycleState(
            candidate_id="WP04_V3B_REPRESENTATION",
            configuration_fingerprint=_fingerprint("WP04_V3B_REPRESENTATION"),
            stage=MC25Stage.FORMAL_STRESS,
            evidence_refs=("formal-stress:sealed",),
            productive_authority=True,
        )
    )

    certification_state = advance_mc25_stage(
        advance_mc25_stage(
            formal_state,
            target_stage=MC25Stage.SHADOW,
            stage_passed=True,
            evidence_refs=("shadow:sealed",),
        ),
        target_stage=MC25Stage.CERTIFICATION,
        stage_passed=True,
        evidence_refs=("certification:sealed",),
    )
    scenarios["PROMOTION_WITHOUT_OWNER_APPROVAL"] = _must_reject(
        lambda: advance_mc25_stage(
            certification_state,
            target_stage=MC25Stage.PROMOTION,
            stage_passed=True,
            evidence_refs=("promotion:sealed",),
        )
    )

    passed = all(scenarios.values())
    return {
        "identity": FORMAL_STRESS_ID,
        "status": (
            "MC25_FORMAL_GOVERNANCE_STRESS_PASS"
            if passed
            else "MC25_FORMAL_GOVERNANCE_STRESS_FAIL"
        ),
        "formal_stress_stage_completed": passed,
        "scenario_count": len(scenarios),
        "rejected_scenario_count": sum(scenarios.values()),
        "scenarios": scenarios,
        "highest_formal_stage": (
            MC25Stage.FORMAL_STRESS.value
            if passed
            else MC25Stage.PERFORMANCE_STRESS.value
        ),
        "shadow_stage_bound": False,
        "certification_stage_bound": False,
        "promotion_allowed": False,
        "productive_authority": False,
        "protected_certification_holdout_opened": False,
        "state_after_formal_stress": asdict(formal_state),
        "next_gate": (
            "MC25_SAME_LINEAGE_SHADOW"
            if passed
            else "FALSIFIED_AND_CLOSED_FOR_FORMAL_STRESS"
        ),
    }
