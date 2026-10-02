"""Pre-authority contract for the post-containment T11 market-impact cycle V3.

V1 was cancelled and left orphan DEMO exposure.  The technical replacement V2
was executed while that exposure existed and is therefore inadmissible.

A new provider experiment may be considered only after an independent read-only
post-cleanup audit proves zero target positions/orders.  This contract freezes
that scientific continuity before any V3 provider outcome exists.

It grants no broker execution authority by itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_arch2_t11_experiment_plan import (
    T11_MARKET_IMPACT_EXPERIMENT_PLAN,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    T11_NONLINEAR_INPUT_FREEZE,
)

CYCLE_ID = "CIBO_ARCH2_T11_MARKET_IMPACT_EXECUTION_CYCLE_V3"
V1_RUN_ID = 36945327912
V2_RUN_ID = 36946792349
V1_CONTAINMENT_AUDIT_RUN_ID = 36947334465
V1_DIRTY_CONTAINMENT_ARTIFACT_ID = 11202212072
V1_DIRTY_CONTAINMENT_DIGEST = (
    "sha256:15982828e8786065db2e08462f64dd61547d2ebec33772b0666255038fc47f78"
)
CLEANUP_RUN_ID = 36947697015
CLEANUP_ARTIFACT_ID = 11202798042
CLEANUP_ARTIFACT_DIGEST = (
    "sha256:9a5929eb455bef83b3f54a0f57b89e7006b10765182c9ce67b366c740b415280"
)
CLEAN_AUDIT_RUN_ID = 36947985223
CLEAN_AUDIT_HEAD_SHA = "af330950773aa89183839ef1810d2feaa9855d7e"
CLEAN_AUDIT_ARTIFACT_ID = 11202788608
CLEAN_AUDIT_ARTIFACT_DIGEST = (
    "sha256:06aaffd5e19f11bb4b9a3f5c6e6d6d0924c52effcce506617e1ccac7f98c0cc0"
)


@dataclass(frozen=True, slots=True)
class T11PostContainmentCycleV3:
    cycle_id: str
    protocol_sha256: str
    experiment_plan_sha256: str
    v1_run_id: int
    v2_run_id: int
    v1_dirty_containment_artifact_id: int
    v1_dirty_containment_digest: str
    cleanup_run_id: int
    cleanup_artifact_id: int
    cleanup_artifact_digest: str
    clean_audit_run_id: int
    clean_audit_head_sha: str
    clean_audit_artifact_id: int
    clean_audit_artifact_digest: str
    independent_clean_audit_required: bool
    independent_clean_audit_bound: bool
    v1_outcomes_consumable: bool
    v2_outcomes_consumable: bool
    changed_scientific_model: bool
    changed_thresholds: bool
    outcome_aware_repair: bool
    ready_for_versioned_execution: bool
    broker_execution_authorized: bool = False
    phase22_v2_consumed: bool = False
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.cycle_id != CYCLE_ID:
            raise ValueError("T11 V3 cycle identity drift")
        if self.protocol_sha256 != T11_NONLINEAR_INPUT_FREEZE.fingerprint():
            raise ValueError("T11 V3 scientific protocol drift")
        if (
            self.experiment_plan_sha256
            != T11_MARKET_IMPACT_EXPERIMENT_PLAN.fingerprint()
        ):
            raise ValueError("T11 V3 experiment plan drift")
        if self.v1_run_id != V1_RUN_ID or self.v2_run_id != V2_RUN_ID:
            raise ValueError("T11 V3 predecessor run lineage drift")
        if (
            self.v1_dirty_containment_artifact_id
            != V1_DIRTY_CONTAINMENT_ARTIFACT_ID
            or self.v1_dirty_containment_digest
            != V1_DIRTY_CONTAINMENT_DIGEST
        ):
            raise ValueError("T11 V3 dirty-containment lineage drift")
        if (
            self.cleanup_run_id != CLEANUP_RUN_ID
            or self.cleanup_artifact_id != CLEANUP_ARTIFACT_ID
            or self.cleanup_artifact_digest != CLEANUP_ARTIFACT_DIGEST
        ):
            raise ValueError("T11 V3 cleanup lineage drift")
        if (
            self.clean_audit_run_id != CLEAN_AUDIT_RUN_ID
            or self.clean_audit_head_sha != CLEAN_AUDIT_HEAD_SHA
            or self.clean_audit_artifact_id != CLEAN_AUDIT_ARTIFACT_ID
            or self.clean_audit_artifact_digest != CLEAN_AUDIT_ARTIFACT_DIGEST
        ):
            raise ValueError("T11 V3 clean-audit lineage drift")
        if not self.independent_clean_audit_required:
            raise ValueError("T11 V3 requires independent clean containment audit")
        expected_ready = self.independent_clean_audit_bound
        if self.ready_for_versioned_execution != expected_ready:
            raise ValueError("T11 V3 readiness/clean-audit binding drift")
        if (
            self.v1_outcomes_consumable
            or self.v2_outcomes_consumable
            or self.changed_scientific_model
            or self.changed_thresholds
            or self.outcome_aware_repair
            or self.broker_execution_authorized
            or self.phase22_v2_consumed
            or self.canonical_ledger_modified
            or self.productive_authority
        ):
            raise ValueError("T11 V3 governance contamination")


T11_POST_CONTAINMENT_CYCLE_V3 = T11PostContainmentCycleV3(
    cycle_id=CYCLE_ID,
    protocol_sha256=T11_NONLINEAR_INPUT_FREEZE.fingerprint(),
    experiment_plan_sha256=T11_MARKET_IMPACT_EXPERIMENT_PLAN.fingerprint(),
    v1_run_id=V1_RUN_ID,
    v2_run_id=V2_RUN_ID,
    v1_dirty_containment_artifact_id=V1_DIRTY_CONTAINMENT_ARTIFACT_ID,
    v1_dirty_containment_digest=V1_DIRTY_CONTAINMENT_DIGEST,
    cleanup_run_id=CLEANUP_RUN_ID,
    cleanup_artifact_id=CLEANUP_ARTIFACT_ID,
    cleanup_artifact_digest=CLEANUP_ARTIFACT_DIGEST,
    clean_audit_run_id=CLEAN_AUDIT_RUN_ID,
    clean_audit_head_sha=CLEAN_AUDIT_HEAD_SHA,
    clean_audit_artifact_id=CLEAN_AUDIT_ARTIFACT_ID,
    clean_audit_artifact_digest=CLEAN_AUDIT_ARTIFACT_DIGEST,
    independent_clean_audit_required=True,
    independent_clean_audit_bound=True,
    v1_outcomes_consumable=False,
    v2_outcomes_consumable=False,
    changed_scientific_model=False,
    changed_thresholds=False,
    outcome_aware_repair=False,
    ready_for_versioned_execution=True,
    broker_execution_authorized=False,
    phase22_v2_consumed=False,
    canonical_ledger_modified=False,
    productive_authority=False,
)
