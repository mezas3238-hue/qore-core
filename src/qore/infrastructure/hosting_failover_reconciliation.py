from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.client_accounts import (
    ExecutionRuntimeReference,
    TradingAccountId,
)
from qore.infrastructure.execution_reconciliation import (
    ExecutionReconciliationSnapshot,
    ExecutionReconciliationStatus,
)
from qore.infrastructure.hosting_execution_lease import (
    HostingExecutionLease,
    HostingExecutionLeaseSnapshot,
    HostingFencingGeneration,
)
from qore.infrastructure.hosting_health_heartbeat import (
    HostingHeartbeatFreshness,
    HostingNewWorkContainment,
    HostingRuntimeHealth,
    HostingRuntimeHealthAssessment,
)
from qore.infrastructure.hosting_runtime_registry import (
    HostingRuntimeRegistrySnapshot,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Success


class HostingFailoverReconciliationError(InfrastructureError):
    """Base error for Managed Hosting failover readiness contracts."""

    __slots__ = ()


class HostingFailoverReconciliationValidationError(
    HostingFailoverReconciliationError
):
    """Violation of failover/fencing/reconciliation invariants."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HostingFailoverReconciliationValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostingFailoverReconciliationValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class HostingFailoverAssessmentId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise HostingFailoverReconciliationValidationError(
                "hosting failover assessment id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingFailoverEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise HostingFailoverReconciliationValidationError(
                "hosting failover evidence reference must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class HostingExternalAccountReconciliationStatus(StrEnum):
    MATCHED = "matched"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class HostingExternalAccountReconciliation:
    """Provider-neutral account/order/position reconciliation attestation."""

    account_id: TradingAccountId
    status: HostingExternalAccountReconciliationStatus
    reconciled_at: datetime
    evidence_ref: HostingFailoverEvidenceReference | None

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, TradingAccountId):
            raise HostingFailoverReconciliationValidationError(
                "account reconciliation requires TradingAccountId"
            )
        if not isinstance(self.status, HostingExternalAccountReconciliationStatus):
            raise HostingFailoverReconciliationValidationError(
                "invalid external account reconciliation status"
            )
        _validate_timestamp(
            self.reconciled_at,
            field_name="account reconciliation reconciled_at",
        )
        if self.status is HostingExternalAccountReconciliationStatus.MATCHED:
            if not isinstance(self.evidence_ref, HostingFailoverEvidenceReference):
                raise HostingFailoverReconciliationValidationError(
                    "MATCHED account reconciliation requires evidence"
                )
        elif self.evidence_ref is not None:
            raise HostingFailoverReconciliationValidationError(
                "ambiguous/unknown reconciliation must not claim matched evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account_id.logical_values(),
            self.status.value,
            self.reconciled_at.isoformat(),
            self.evidence_ref.logical_values() if self.evidence_ref else None,
        )


class HostingFailoverReadiness(StrEnum):
    READY_FOR_LEASE_ACQUISITION = "ready_for_lease_acquisition"
    BLOCKED = "blocked"


class HostingFailoverReason(StrEnum):
    RECONCILED_AND_FENCED = "reconciled_and_fenced"
    PREVIOUS_RUNTIME_NOT_CONTAINED = "previous_runtime_not_contained"
    PREVIOUS_AUTHORITY_STILL_ACTIVE = "previous_authority_still_active"
    CANDIDATE_NOT_HEALTHY = "candidate_not_healthy"
    EXTERNAL_ACCOUNT_AMBIGUOUS = "external_account_ambiguous"
    EXECUTION_RECONCILIATION_AMBIGUOUS = "execution_reconciliation_ambiguous"


@dataclass(frozen=True, slots=True)
class HostingFailoverAssessment:
    """Failover readiness only; it never acquires the replacement lease."""

    assessment_id: HostingFailoverAssessmentId
    account_id: TradingAccountId
    previous_runtime_ref: ExecutionRuntimeReference
    candidate_runtime_ref: ExecutionRuntimeReference
    readiness: HostingFailoverReadiness
    reason: HostingFailoverReason
    next_generation: HostingFencingGeneration | None
    evaluated_at: datetime
    evidence_ref: HostingFailoverEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.assessment_id, HostingFailoverAssessmentId):
            raise HostingFailoverReconciliationValidationError(
                "assessment_id must be HostingFailoverAssessmentId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise HostingFailoverReconciliationValidationError(
                "account_id must be TradingAccountId"
            )
        if not isinstance(self.previous_runtime_ref, ExecutionRuntimeReference):
            raise HostingFailoverReconciliationValidationError(
                "previous_runtime_ref must be ExecutionRuntimeReference"
            )
        if not isinstance(self.candidate_runtime_ref, ExecutionRuntimeReference):
            raise HostingFailoverReconciliationValidationError(
                "candidate_runtime_ref must be ExecutionRuntimeReference"
            )
        if self.previous_runtime_ref == self.candidate_runtime_ref:
            raise HostingFailoverReconciliationValidationError(
                "failover candidate must differ from previous runtime"
            )
        if not isinstance(self.readiness, HostingFailoverReadiness):
            raise HostingFailoverReconciliationValidationError(
                "readiness must be HostingFailoverReadiness"
            )
        if not isinstance(self.reason, HostingFailoverReason):
            raise HostingFailoverReconciliationValidationError(
                "reason must be HostingFailoverReason"
            )
        _validate_timestamp(self.evaluated_at, field_name="failover evaluated_at")
        if not isinstance(self.evidence_ref, HostingFailoverEvidenceReference):
            raise HostingFailoverReconciliationValidationError(
                "evidence_ref must be HostingFailoverEvidenceReference"
            )
        ready = self.readiness is HostingFailoverReadiness.READY_FOR_LEASE_ACQUISITION
        if ready != isinstance(self.next_generation, HostingFencingGeneration):
            raise HostingFailoverReconciliationValidationError(
                "only READY failover may carry next fencing generation"
            )
        if ready and self.reason is not HostingFailoverReason.RECONCILED_AND_FENCED:
            raise HostingFailoverReconciliationValidationError(
                "READY failover requires reconciled-and-fenced reason"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.assessment_id.logical_values(),
            self.account_id.logical_values(),
            self.previous_runtime_ref.logical_values(),
            self.candidate_runtime_ref.logical_values(),
            self.readiness.value,
            self.reason.value,
            self.next_generation.logical_values() if self.next_generation else None,
            self.evaluated_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


def _latest_account_lease(
    leases: HostingExecutionLeaseSnapshot,
    account_id: TradingAccountId,
) -> HostingExecutionLease:
    candidates = leases.leases_for_account(account_id)
    if not candidates:
        raise HostingFailoverReconciliationValidationError(
            "failover requires previous account lease history"
        )
    return max(candidates, key=lambda item: item.generation.value)


def _validate_health_binding(
    assessment: HostingRuntimeHealthAssessment,
    *,
    account_id: TradingAccountId,
    runtime_ref: ExecutionRuntimeReference,
    evaluated_at: datetime,
) -> None:
    if assessment.account_id != account_id or assessment.runtime_ref != runtime_ref:
        raise HostingFailoverReconciliationValidationError(
            "health assessment account/runtime binding mismatch"
        )
    if assessment.evaluated_at != evaluated_at:
        raise HostingFailoverReconciliationValidationError(
            "health assessment must bind exact failover evaluation time"
        )


def evaluate_hosting_failover_readiness(
    registry: HostingRuntimeRegistrySnapshot,
    leases: HostingExecutionLeaseSnapshot,
    previous_health: HostingRuntimeHealthAssessment,
    candidate_health: HostingRuntimeHealthAssessment,
    account_reconciliation: HostingExternalAccountReconciliation,
    execution_reconciliations: tuple[ExecutionReconciliationSnapshot, ...],
    *,
    account_id: TradingAccountId,
    previous_runtime_ref: ExecutionRuntimeReference,
    candidate_runtime_ref: ExecutionRuntimeReference,
    assessment_id: HostingFailoverAssessmentId,
    evidence_ref: HostingFailoverEvidenceReference,
    evaluated_at: datetime,
) -> HostingFailoverAssessment:
    """Prove readiness to request a new fenced lease; never acquire it here."""

    _validate_timestamp(evaluated_at, field_name="failover evaluated_at")
    previous = registry.resolve_runtime(previous_runtime_ref)
    candidate = registry.resolve_runtime(candidate_runtime_ref)
    if isinstance(previous, Failure) or isinstance(candidate, Failure):
        raise HostingFailoverReconciliationValidationError(
            "both failover runtimes must exist in Runtime Registry"
        )
    if previous.value.account_id != account_id or candidate.value.account_id != account_id:
        raise HostingFailoverReconciliationValidationError(
            "failover runtimes must bind the exact account"
        )
    if previous_runtime_ref == candidate_runtime_ref:
        raise HostingFailoverReconciliationValidationError(
            "candidate runtime must differ from previous runtime"
        )
    if evaluated_at > registry.captured_at or evaluated_at > leases.captured_at:
        raise HostingFailoverReconciliationValidationError(
            "registry/lease snapshots must cover failover evaluation time"
        )
    _validate_health_binding(
        previous_health,
        account_id=account_id,
        runtime_ref=previous_runtime_ref,
        evaluated_at=evaluated_at,
    )
    _validate_health_binding(
        candidate_health,
        account_id=account_id,
        runtime_ref=candidate_runtime_ref,
        evaluated_at=evaluated_at,
    )
    if account_reconciliation.account_id != account_id:
        raise HostingFailoverReconciliationValidationError(
            "external account reconciliation binding mismatch"
        )
    if account_reconciliation.reconciled_at > evaluated_at:
        raise HostingFailoverReconciliationValidationError(
            "external account reconciliation cannot be from the future"
        )
    if not isinstance(execution_reconciliations, tuple):
        raise HostingFailoverReconciliationValidationError(
            "execution reconciliations must be an immutable tuple"
        )
    if any(
        not isinstance(item, ExecutionReconciliationSnapshot)
        for item in execution_reconciliations
    ):
        raise HostingFailoverReconciliationValidationError(
            "execution reconciliations contain invalid value"
        )
    if any(item.reconciled_at > evaluated_at for item in execution_reconciliations):
        raise HostingFailoverReconciliationValidationError(
            "execution reconciliation cannot be from the future"
        )

    current = leases.current_authority(account_id, evaluated_at=evaluated_at)
    latest = _latest_account_lease(leases, account_id)

    if previous_health.containment is HostingNewWorkContainment.NONE:
        return HostingFailoverAssessment(
            assessment_id=assessment_id,
            account_id=account_id,
            previous_runtime_ref=previous_runtime_ref,
            candidate_runtime_ref=candidate_runtime_ref,
            readiness=HostingFailoverReadiness.BLOCKED,
            reason=HostingFailoverReason.PREVIOUS_RUNTIME_NOT_CONTAINED,
            next_generation=None,
            evaluated_at=evaluated_at,
            evidence_ref=evidence_ref,
        )
    if isinstance(current, Success):
        return HostingFailoverAssessment(
            assessment_id=assessment_id,
            account_id=account_id,
            previous_runtime_ref=previous_runtime_ref,
            candidate_runtime_ref=candidate_runtime_ref,
            readiness=HostingFailoverReadiness.BLOCKED,
            reason=HostingFailoverReason.PREVIOUS_AUTHORITY_STILL_ACTIVE,
            next_generation=None,
            evaluated_at=evaluated_at,
            evidence_ref=evidence_ref,
        )
    candidate_ready = (
        candidate_health.health is HostingRuntimeHealth.HEALTHY
        and candidate_health.freshness is HostingHeartbeatFreshness.CURRENT
        and candidate_health.containment is HostingNewWorkContainment.NONE
    )
    if not candidate_ready:
        return HostingFailoverAssessment(
            assessment_id=assessment_id,
            account_id=account_id,
            previous_runtime_ref=previous_runtime_ref,
            candidate_runtime_ref=candidate_runtime_ref,
            readiness=HostingFailoverReadiness.BLOCKED,
            reason=HostingFailoverReason.CANDIDATE_NOT_HEALTHY,
            next_generation=None,
            evaluated_at=evaluated_at,
            evidence_ref=evidence_ref,
        )
    if account_reconciliation.status is not (
        HostingExternalAccountReconciliationStatus.MATCHED
    ):
        return HostingFailoverAssessment(
            assessment_id=assessment_id,
            account_id=account_id,
            previous_runtime_ref=previous_runtime_ref,
            candidate_runtime_ref=candidate_runtime_ref,
            readiness=HostingFailoverReadiness.BLOCKED,
            reason=HostingFailoverReason.EXTERNAL_ACCOUNT_AMBIGUOUS,
            next_generation=None,
            evaluated_at=evaluated_at,
            evidence_ref=evidence_ref,
        )
    if any(
        item.status is not ExecutionReconciliationStatus.MATCHED
        for item in execution_reconciliations
    ):
        return HostingFailoverAssessment(
            assessment_id=assessment_id,
            account_id=account_id,
            previous_runtime_ref=previous_runtime_ref,
            candidate_runtime_ref=candidate_runtime_ref,
            readiness=HostingFailoverReadiness.BLOCKED,
            reason=HostingFailoverReason.EXECUTION_RECONCILIATION_AMBIGUOUS,
            next_generation=None,
            evaluated_at=evaluated_at,
            evidence_ref=evidence_ref,
        )

    return HostingFailoverAssessment(
        assessment_id=assessment_id,
        account_id=account_id,
        previous_runtime_ref=previous_runtime_ref,
        candidate_runtime_ref=candidate_runtime_ref,
        readiness=HostingFailoverReadiness.READY_FOR_LEASE_ACQUISITION,
        reason=HostingFailoverReason.RECONCILED_AND_FENCED,
        next_generation=HostingFencingGeneration(latest.generation.value + 1),
        evaluated_at=evaluated_at,
        evidence_ref=evidence_ref,
    )
