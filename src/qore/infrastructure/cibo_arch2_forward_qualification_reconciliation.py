"""Architect-2 reconciliation for FORWARD_QUALIFICATION and FRESH_OOS.

The legacy Phase20D/Phase21 forward-population blockers were written before the
Phase22 V2 dual-evidence architecture became the active frozen qualification
contract.  This module proves only the pre-outcome lineage transition.  It does
not consume V2 and cannot claim Fresh-OOS completion.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_phase22_dual_evidence_plan import (
    PHASE22_DUAL_EVIDENCE_PLAN,
)
from qore.infrastructure.cibo_phase22_execution_manifest import (
    build_phase22_execution_manifest,
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
    phase21_policy_freeze_bound: bool
    provider_execution_plane_ready: bool
    dual_evidence_activation_ready: bool
    external_dependency_resolved_pre_holdout: bool
    execution_manifest_frozen_pre_outcome: bool
    fresh_oos_local_state: str
    fresh_oos_remaining_requirement: str
    phase22_v2_consumed: bool
    terminal_disposition_assigned: bool
    productive_authority: bool


def build_arch2_forward_qualification_reconciliation(
) -> Architect2ForwardQualificationReconciliation:
    dependency = build_phase22_external_dependency_evidence()
    plan = PHASE22_DUAL_EVIDENCE_PLAN
    manifest = build_phase22_execution_manifest()

    resolved = (
        dependency.disposition == "DEPENDENCY_RESOLVED_PRE_HOLDOUT"
        and dependency.blockers == ()
        and dependency.authorized_to_emit_first_fresh_outcome
    )
    manifest_ready = (
        manifest.fresh_outcomes_executed is False
        and manifest.productive_authority is False
        and bool(manifest.phase21_policy_freeze_sha256)
        and bool(manifest.provider_execution_calibration_receipt_sha256)
        and bool(manifest.dual_evidence_plan_sha256)
        and len(manifest.trader_bindings) == 7
    )
    provider_ready = (
        plan.execution_population_ready
        and plan.empirical_provider_calibration_ready
        and plan.activation_ready
    )

    return Architect2ForwardQualificationReconciliation(
        forward_qualification_recommendation=FORWARD_RECOMMENDATION,
        old_phase20d_requirement_superseded=resolved and manifest_ready,
        phase21_policy_freeze_bound=bool(manifest.phase21_policy_freeze_sha256),
        provider_execution_plane_ready=provider_ready,
        dual_evidence_activation_ready=plan.activation_ready,
        external_dependency_resolved_pre_holdout=resolved,
        execution_manifest_frozen_pre_outcome=manifest_ready,
        fresh_oos_local_state=FRESH_OOS_LOCAL_STATE,
        fresh_oos_remaining_requirement=(
            "PHASE22_V2_FRESH_OUTCOME_RECEIPT_REQUIRED"
        ),
        phase22_v2_consumed=False,
        terminal_disposition_assigned=False,
        productive_authority=False,
    )
