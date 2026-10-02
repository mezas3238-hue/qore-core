"""Fail-closed containment state for the cancelled T11 V1 provider experiment.

Read-only containment run 36947334465 proved that the cancelled V1 experiment
left two open cTrader DEMO positions.  Therefore every later T11 market-impact
run executed before a clean containment receipt is scientifically contaminated
and cannot be consumed as certification evidence.

This module performs no broker mutation and grants no execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass

AUDIT_RUN_ID = 36947334465
AUDIT_HEAD_SHA = "1770295a178f15d69c330d3b9c6c2d8bdecbc6cb"
AUDIT_ARTIFACT_ID = 11202212072
AUDIT_ARTIFACT_DIGEST = (
    "sha256:15982828e8786065db2e08462f64dd61547d2ebec33772b0666255038fc47f78"
)
CANCELLED_RUN_ID = 36945327912
CONTAMINATED_REPLACEMENT_RUN_ID = 36946792349
OPEN_CANCELLED_RUN_POSITION_COUNT = 2
OPEN_CANCELLED_RUN_ORDER_COUNT = 0
OPEN_CANCELLED_RUN_LABELS = (
    "CIBOA2T11:GBPJPY:7912-1:C05:L2:C1",
    "CIBOA2T11:GBPJPY:7912-1:C05:L2:C2",
)
BLOCK_REASON = (
    "PREEXISTING_CANCELLED_RUN_ORPHAN_EXPOSURE_INVALIDATES_REPLACEMENT_EXPERIMENT"
)


@dataclass(frozen=True, slots=True)
class T11ProviderContainmentState:
    audit_run_id: int
    audit_head_sha: str
    audit_artifact_id: int
    audit_artifact_digest: str
    cancelled_run_id: int
    contaminated_replacement_run_id: int
    open_position_count: int
    open_order_count: int
    open_labels: tuple[str, ...]
    containment_clean: bool
    replacement_evidence_admissible: bool
    further_provider_experiment_allowed: bool
    block_reason: str
    broker_mutation_performed_by_receipt: bool = False
    phase22_v2_consumed: bool = False
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.audit_run_id != AUDIT_RUN_ID:
            raise ValueError("T11 containment audit run drift")
        if self.audit_head_sha != AUDIT_HEAD_SHA:
            raise ValueError("T11 containment audit HEAD drift")
        if self.audit_artifact_id != AUDIT_ARTIFACT_ID:
            raise ValueError("T11 containment artifact id drift")
        if self.audit_artifact_digest != AUDIT_ARTIFACT_DIGEST:
            raise ValueError("T11 containment artifact digest drift")
        if self.cancelled_run_id != CANCELLED_RUN_ID:
            raise ValueError("T11 cancelled run identity drift")
        if self.contaminated_replacement_run_id != CONTAMINATED_REPLACEMENT_RUN_ID:
            raise ValueError("T11 contaminated replacement identity drift")
        if self.open_position_count != OPEN_CANCELLED_RUN_POSITION_COUNT:
            raise ValueError("T11 containment position count drift")
        if self.open_order_count != OPEN_CANCELLED_RUN_ORDER_COUNT:
            raise ValueError("T11 containment order count drift")
        if self.open_labels != OPEN_CANCELLED_RUN_LABELS:
            raise ValueError("T11 containment label surface drift")
        if (
            self.containment_clean
            or self.replacement_evidence_admissible
            or self.further_provider_experiment_allowed
        ):
            raise ValueError("T11 contaminated provider state must fail closed")
        if self.block_reason != BLOCK_REASON:
            raise ValueError("T11 containment block reason drift")
        if (
            self.broker_mutation_performed_by_receipt
            or self.phase22_v2_consumed
            or self.canonical_ledger_modified
            or self.productive_authority
        ):
            raise ValueError("T11 containment receipt exceeded authority")


T11_PROVIDER_CONTAINMENT_STATE = T11ProviderContainmentState(
    audit_run_id=AUDIT_RUN_ID,
    audit_head_sha=AUDIT_HEAD_SHA,
    audit_artifact_id=AUDIT_ARTIFACT_ID,
    audit_artifact_digest=AUDIT_ARTIFACT_DIGEST,
    cancelled_run_id=CANCELLED_RUN_ID,
    contaminated_replacement_run_id=CONTAMINATED_REPLACEMENT_RUN_ID,
    open_position_count=OPEN_CANCELLED_RUN_POSITION_COUNT,
    open_order_count=OPEN_CANCELLED_RUN_ORDER_COUNT,
    open_labels=OPEN_CANCELLED_RUN_LABELS,
    containment_clean=False,
    replacement_evidence_admissible=False,
    further_provider_experiment_allowed=False,
    block_reason=BLOCK_REASON,
)
