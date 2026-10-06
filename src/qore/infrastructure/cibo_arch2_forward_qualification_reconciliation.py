"""Architect-2 reconciliation for FORWARD_QUALIFICATION and FRESH_OOS.

This proof consumes only the immutable Phase22 Dual Evidence Plan V2.  That
plan explicitly binds the superseded qualification-plan identity/digest and the
READY empirical provider execution receipt before any holdout outcomes.

Architect 2 deliberately avoids the currently broken Integrator import graph.
It does not consume V2 and cannot claim Fresh-OOS completion.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_phase22_dual_evidence_plan import (
    DUAL_EVIDENCE_PLAN_ID,
    PHASE22_DUAL_EVIDENCE_PLAN,
)

FORWARD_RECOMMENDATION = "SUPERSEDED_WITH_PROVEN_LINEAGE"
FRESH_OOS_LOCAL_STATE = "WAITING_ON_INTEGRATOR_RECEIPT"


@dataclass(frozen=True, slots=True)
class Architect2ForwardQualificationReconciliation:
    forward_qualification_recommendation: str
    old_qualification_plan_bound_as_superseded: bool
    old_qualification_plan_sha_bound: bool
    provider_execution_plane_ready: bool
    dual_evidence_activation_ready: bool
    frozen_before_holdout_outcomes: bool
    historical_fill_fabrication_forbidden: bool
    fresh_oos_local_state: str
    fresh_oos_remaining_requirement: str
    phase22_v2_consumed: bool
    terminal_disposition_assigned: bool
    productive_authority: bool


def build_arch2_forward_qualification_reconciliation(
) -> Architect2ForwardQualificationReconciliation:
    plan = PHASE22_DUAL_EVIDENCE_PLAN

    provider_ready = (
        plan.execution_population_ready
        and plan.empirical_provider_calibration_ready
        and plan.activation_ready
    )
    pre_outcome = (
        plan.protocol_frozen_before_holdout_outcomes
        and plan.forbid_holdout_mining
        and plan.require_both_planes_for_certification
        and plan.productive_authority is False
    )
    supersession_bound = (
        plan.plan_id == DUAL_EVIDENCE_PLAN_ID
        and bool(plan.superseded_plan_id)
        and plan.superseded_plan_id != plan.plan_id
    )
    supersession_sha_bound = (
        plan.superseded_plan_sha256.startswith("sha256:")
        and len(plan.superseded_plan_sha256) == 71
    )
    forbid_historical_fabrication = all(
        (
            plan.forbid_historical_provider_fill_claims,
            plan.forbid_historical_provider_order_refs,
            plan.forbid_historical_provider_deal_refs,
            plan.forbid_historical_provider_settlement_claims,
            plan.forbid_synthetic_fill_evidence,
        )
    )

    return Architect2ForwardQualificationReconciliation(
        forward_qualification_recommendation=FORWARD_RECOMMENDATION,
        old_qualification_plan_bound_as_superseded=supersession_bound,
        old_qualification_plan_sha_bound=supersession_sha_bound,
        provider_execution_plane_ready=provider_ready,
        dual_evidence_activation_ready=plan.activation_ready,
        frozen_before_holdout_outcomes=pre_outcome,
        historical_fill_fabrication_forbidden=forbid_historical_fabrication,
        fresh_oos_local_state=FRESH_OOS_LOCAL_STATE,
        fresh_oos_remaining_requirement=(
            "PHASE22_V2_FRESH_OUTCOME_RECEIPT_REQUIRED"
        ),
        phase22_v2_consumed=False,
        terminal_disposition_assigned=False,
        productive_authority=False,
    )
