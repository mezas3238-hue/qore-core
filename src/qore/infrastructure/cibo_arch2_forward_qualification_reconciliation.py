"""Architect-2 reconciliation for FORWARD_QUALIFICATION and FRESH_OOS.

The legacy Phase20D/Phase21 forward-population blockers predate the Phase22 V2
dual-evidence qualification route.  This module consumes only pre-outcome,
read-only governance evidence.  It does not import the Integrator execution
manifest, consume V2, or claim Fresh-OOS completion.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_phase22_dual_evidence_plan import (
    PHASE22_DUAL_EVIDENCE_PLAN,
)
from qore.infrastructure.cibo_phase22_external_dependency_evidence import (
    build_phase22_external_dependency_evidence,
)

FORWARD_RECOMMENDATION = "SUPERSEDED_WITH_PROVEN_LINEAGE"
FRESH_OOS_LOCAL_STATE = "WAITING_ON_INTEGRATOR_RECEIPT"


@dataclass(frozen=True, slots=True)
class Architect2ForwardQualificationReconciliation:
    forward_qualification_recommendation: str
    old_phase20d_requirement_superseded: bool
    provider_execution_plane_ready: bool
    dual_evidence_activation_ready: bool
    one_shot_guard_prerequisites_resolved: bool
    frozen_dual_evidence_pre_outcome: bool
    fresh_oos_local_state: str
    fresh_oos_remaining_requirement: str
    phase22_v2_consumed: bool
    terminal_disposition_assigned: bool
    productive_authority: bool


def build_arch2_forward_qualification_reconciliation(
) -> Architect2ForwardQualificationReconciliation:
    dependency = build_phase22_external_dependency_evidence()
    plan = PHASE22_DUAL_EVIDENCE_PLAN

    resolved = (
        dependency.disposition == "DEPENDENCY_RESOLVED_PRE_HOLDOUT"
        and dependency.blockers == ()
        and dependency.authorized_to_emit_first_fresh_outcome
        and dependency.fresh_holdout_consumed is False
        and dependency.productive_authority is False
    )
    provider_ready = (
        plan.execution_population_ready
        and plan.empirical_provider_calibration_ready
        and plan.activation_ready
    )
    pre_outcome = (
        plan.protocol_frozen_before_holdout_outcomes
        and plan.forbid_holdout_mining
        and plan.forbid_historical_provider_fill_claims
        and plan.require_both_planes_for_certification
        and plan.productive_authority is False
    )

    return Architect2ForwardQualificationReconciliation(
        forward_qualification_recommendation=FORWARD_RECOMMENDATION,
        old_phase20d_requirement_superseded=(
            resolved and provider_ready and pre_outcome
        ),
        provider_execution_plane_ready=provider_ready,
        dual_evidence_activation_ready=plan.activation_ready,
        one_shot_guard_prerequisites_resolved=resolved,
        frozen_dual_evidence_pre_outcome=pre_outcome,
        fresh_oos_local_state=FRESH_OOS_LOCAL_STATE,
        fresh_oos_remaining_requirement=(
            "PHASE22_V2_FRESH_OUTCOME_RECEIPT_REQUIRED"
        ),
        phase22_v2_consumed=False,
        terminal_disposition_assigned=False,
        productive_authority=False,
    )
