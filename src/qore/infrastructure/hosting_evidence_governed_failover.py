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
)
from qore.infrastructure.hosting_execution_lease import (
    HostingExecutionLeaseError,
    HostingExecutionLeaseId,
    HostingExecutionLeaseSnapshot,
    HostingFencingGeneration,
    HostingLeaseEvidenceReference,
    acquire_hosting_execution_lease,
)
from qore.infrastructure.hosting_failover_reconciliation import (
    HostingExternalAccountReconciliation,
    HostingFailoverAssessment,
    HostingFailoverAssessmentId,
    HostingFailoverEvidenceReference,
    HostingFailoverReadiness,
    HostingFailoverReconciliationError,
    evaluate_hosting_failover_readiness,
)
from qore.infrastructure.hosting_health_heartbeat import (
    HostingRuntimeHealthAssessment,
)
from qore.infrastructure.hosting_io_certification import (
    HostingIOCertificateStatus,
    HostingIOPeriodicReliabilityReport,
)
from qore.infrastructure.hosting_reliability_incident import (
    HostingReliabilityIncidentFinalState,
    HostingReliabilityIncidentReport,
)
from qore.infrastructure.hosting_reliability_lab import (
    HostingReliabilityEvidenceReference,
    HostingReliabilityInfrastructureAction,
)
from qore.infrastructure.hosting_runtime_registry import (
    HostingRuntimeRegistrySnapshot,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class HostingEvidenceGovernedFailoverError(InfrastructureError):
    """Base error for evidence-governed Hosting failover composition."""

    __slots__ = ()


class HostingEvidenceGovernedFailoverValidationError(
    HostingEvidenceGovernedFailoverError
):
    """Violation of evidence-governed failover invariants."""

    __slots__ = ()


class HostingEvidenceGovernedFailoverExecutionError(
    HostingEvidenceGovernedFailoverError
):
    """Canonical MISSION-08 lease boundary rejected the requested handoff."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HostingEvidenceGovernedFailoverValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostingEvidenceGovernedFailoverValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise HostingEvidenceGovernedFailoverValidationError(
            f"{field_name} must be UUID"
        )


@dataclass(frozen=True, slots=True)
class HostingEvidenceGovernedFailoverAssessmentId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="evidence-governed failover assessment id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingAvailabilityFailoverCertificateId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="availability/failover certificate id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class HostingEvidenceGovernedFailoverReadiness(StrEnum):
    READY_FOR_CANONICAL_LEASE_ACQUISITION = "ready_for_canonical_lease_acquisition"
    BLOCKED = "blocked"


class HostingEvidenceGovernedFailoverReason(StrEnum):
    CURRENT_RUNTIME_NOT_PROVEN_UNSAFE = "current_runtime_not_proven_unsafe"
    FAILOVER_EVALUATION_NOT_AUTHORIZED = "failover_evaluation_not_authorized"
    CANDIDATE_IO_NOT_CERTIFIED = "candidate_io_not_certified"
    CANDIDATE_IO_SCOPE_MISMATCH = "candidate_io_scope_mismatch"
    MISSION08_READINESS_BLOCKED = "mission08_readiness_blocked"
    EVIDENCE_AND_MISSION08_READY = "evidence_and_mission08_ready"


class HostingAvailabilityFailoverCertificateStatus(StrEnum):
    CERTIFIED = "certified"
    NOT_CERTIFIED = "not_certified"


@dataclass(frozen=True, slots=True)
class HostingEvidenceGovernedFailoverAssessment:
    """Evidence + MISSION-08 readiness; this object never creates writer authority."""

    assessment_id: HostingEvidenceGovernedFailoverAssessmentId
    account_id: TradingAccountId
    previous_runtime_ref: ExecutionRuntimeReference
    candidate_runtime_ref: ExecutionRuntimeReference
    incident_report_id: object
    candidate_io_report_id: object
    readiness: HostingEvidenceGovernedFailoverReadiness
    reason: HostingEvidenceGovernedFailoverReason
    mission08_assessment: HostingFailoverAssessment | None
    next_generation: HostingFencingGeneration | None
    evaluated_at: datetime
    evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(
            self.assessment_id,
            HostingEvidenceGovernedFailoverAssessmentId,
        ):
            raise HostingEvidenceGovernedFailoverValidationError(
                "assessment_id must be HostingEvidenceGovernedFailoverAssessmentId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise HostingEvidenceGovernedFailoverValidationError(
                "account_id must be TradingAccountId"
            )
        if not isinstance(self.previous_runtime_ref, ExecutionRuntimeReference):
            raise HostingEvidenceGovernedFailoverValidationError(
                "previous_runtime_ref must be ExecutionRuntimeReference"
            )
        if not isinstance(self.candidate_runtime_ref, ExecutionRuntimeReference):
            raise HostingEvidenceGovernedFailoverValidationError(
                "candidate_runtime_ref must be ExecutionRuntimeReference"
            )
        if self.previous_runtime_ref == self.candidate_runtime_ref:
            raise HostingEvidenceGovernedFailoverValidationError(
                "candidate runtime must differ from previous runtime"
            )
        if not isinstance(self.readiness, HostingEvidenceGovernedFailoverReadiness):
            raise HostingEvidenceGovernedFailoverValidationError(
                "readiness must be HostingEvidenceGovernedFailoverReadiness"
            )
        if not isinstance(self.reason, HostingEvidenceGovernedFailoverReason):
            raise HostingEvidenceGovernedFailoverValidationError(
                "reason must be HostingEvidenceGovernedFailoverReason"
            )
        _validate_timestamp(self.evaluated_at, field_name="failover evaluated_at")
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise HostingEvidenceGovernedFailoverValidationError(
                "evidence_ref must be HostingReliabilityEvidenceReference"
            )
        ready = (
            self.readiness
            is HostingEvidenceGovernedFailoverReadiness.READY_FOR_CANONICAL_LEASE_ACQUISITION
        )
        if ready:
            if self.reason is not (
                HostingEvidenceGovernedFailoverReason.EVIDENCE_AND_MISSION08_READY
            ):
                raise HostingEvidenceGovernedFailoverValidationError(
                    "READY evidence-governed failover requires ready reason"
                )
            if not isinstance(self.mission08_assessment, HostingFailoverAssessment):
                raise HostingEvidenceGovernedFailoverValidationError(
                    "READY failover requires MISSION-08 readiness assessment"
                )
            if self.mission08_assessment.readiness is not (
                HostingFailoverReadiness.READY_FOR_LEASE_ACQUISITION
            ):
                raise HostingEvidenceGovernedFailoverValidationError(
                    "READY failover requires READY MISSION-08 assessment"
                )
            if not isinstance(self.next_generation, HostingFencingGeneration):
                raise HostingEvidenceGovernedFailoverValidationError(
                    "READY failover requires next fencing generation"
                )
            if self.next_generation != self.mission08_assessment.next_generation:
                raise HostingEvidenceGovernedFailoverValidationError(
                    "next generation must equal canonical MISSION-08 generation"
                )
        elif self.next_generation is not None:
            raise HostingEvidenceGovernedFailoverValidationError(
                "BLOCKED failover cannot carry next fencing generation"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.assessment_id.logical_values(),
            self.account_id.logical_values(),
            self.previous_runtime_ref.logical_values(),
            self.candidate_runtime_ref.logical_values(),
            str(self.incident_report_id),
            str(self.candidate_io_report_id),
            self.readiness.value,
            self.reason.value,
            (
                self.mission08_assessment.logical_values()
                if self.mission08_assessment
                else None
            ),
            self.next_generation.logical_values() if self.next_generation else None,
            self.evaluated_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class HostingAvailabilityFailoverCertificate:
    """Post-handoff evidence that the candidate owns exact N+1 authority and safe I/O."""

    certificate_id: HostingAvailabilityFailoverCertificateId
    status: HostingAvailabilityFailoverCertificateStatus
    assessment: HostingEvidenceGovernedFailoverAssessment
    candidate_io_report: HostingIOPeriodicReliabilityReport
    lease_snapshot: HostingExecutionLeaseSnapshot
    certified_at: datetime
    evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(
            self.certificate_id,
            HostingAvailabilityFailoverCertificateId,
        ):
            raise HostingEvidenceGovernedFailoverValidationError(
                "certificate_id must be HostingAvailabilityFailoverCertificateId"
            )
        if not isinstance(self.status, HostingAvailabilityFailoverCertificateStatus):
            raise HostingEvidenceGovernedFailoverValidationError(
                "certificate status must be HostingAvailabilityFailoverCertificateStatus"
            )
        if not isinstance(
            self.assessment,
            HostingEvidenceGovernedFailoverAssessment,
        ):
            raise HostingEvidenceGovernedFailoverValidationError(
                "certificate assessment must be evidence-governed assessment"
            )
        if not isinstance(
            self.candidate_io_report,
            HostingIOPeriodicReliabilityReport,
        ):
            raise HostingEvidenceGovernedFailoverValidationError(
                "candidate_io_report must be HostingIOPeriodicReliabilityReport"
            )
        if not isinstance(self.lease_snapshot, HostingExecutionLeaseSnapshot):
            raise HostingEvidenceGovernedFailoverValidationError(
                "lease_snapshot must be HostingExecutionLeaseSnapshot"
            )
        _validate_timestamp(self.certified_at, field_name="failover certified_at")
        if self.certified_at < self.assessment.evaluated_at:
            raise HostingEvidenceGovernedFailoverValidationError(
                "failover certification cannot predate readiness assessment"
            )
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise HostingEvidenceGovernedFailoverValidationError(
                "certificate evidence_ref must be HostingReliabilityEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.certificate_id.logical_values(),
            self.status.value,
            self.assessment.logical_values(),
            self.candidate_io_report.logical_values(),
            self.lease_snapshot.logical_values(),
            self.certified_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


def _blocked(
    *,
    assessment_id: HostingEvidenceGovernedFailoverAssessmentId,
    account_id: TradingAccountId,
    previous_runtime_ref: ExecutionRuntimeReference,
    candidate_runtime_ref: ExecutionRuntimeReference,
    incident_report: HostingReliabilityIncidentReport,
    candidate_io_report: HostingIOPeriodicReliabilityReport,
    reason: HostingEvidenceGovernedFailoverReason,
    evaluated_at: datetime,
    evidence_ref: HostingReliabilityEvidenceReference,
    mission08_assessment: HostingFailoverAssessment | None = None,
) -> HostingEvidenceGovernedFailoverAssessment:
    return HostingEvidenceGovernedFailoverAssessment(
        assessment_id=assessment_id,
        account_id=account_id,
        previous_runtime_ref=previous_runtime_ref,
        candidate_runtime_ref=candidate_runtime_ref,
        incident_report_id=incident_report.report_id,
        candidate_io_report_id=candidate_io_report.report_id,
        readiness=HostingEvidenceGovernedFailoverReadiness.BLOCKED,
        reason=reason,
        mission08_assessment=mission08_assessment,
        next_generation=None,
        evaluated_at=evaluated_at,
        evidence_ref=evidence_ref,
    )


def evaluate_evidence_governed_failover(
    incident_report: HostingReliabilityIncidentReport,
    candidate_io_report: HostingIOPeriodicReliabilityReport,
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
    assessment_id: HostingEvidenceGovernedFailoverAssessmentId,
    mission08_assessment_id: HostingFailoverAssessmentId,
    mission08_evidence_ref: HostingFailoverEvidenceReference,
    evidence_ref: HostingReliabilityEvidenceReference,
    evaluated_at: datetime,
) -> Result[
    HostingEvidenceGovernedFailoverAssessment,
    HostingEvidenceGovernedFailoverError,
]:
    """Compose Lab evidence with MISSION-08 readiness without creating a new lease."""

    try:
        _validate_timestamp(evaluated_at, field_name="failover evaluated_at")
    except HostingEvidenceGovernedFailoverValidationError as error:
        return Failure(error)
    if not isinstance(incident_report, HostingReliabilityIncidentReport):
        return Failure(
            HostingEvidenceGovernedFailoverValidationError(
                "incident_report must be HostingReliabilityIncidentReport"
            )
        )
    if not isinstance(candidate_io_report, HostingIOPeriodicReliabilityReport):
        return Failure(
            HostingEvidenceGovernedFailoverValidationError(
                "candidate_io_report must be HostingIOPeriodicReliabilityReport"
            )
        )
    incident_assessment = incident_report.incident.anomaly_report.assessment
    if (
        incident_assessment.account_id != account_id
        or incident_assessment.runtime_ref != previous_runtime_ref
    ):
        return Failure(
            HostingEvidenceGovernedFailoverValidationError(
                "incident report must bind previous runtime/account"
            )
        )
    if incident_report.final_state is not HostingReliabilityIncidentFinalState.UNRESOLVED:
        return Success(
            _blocked(
                assessment_id=assessment_id,
                account_id=account_id,
                previous_runtime_ref=previous_runtime_ref,
                candidate_runtime_ref=candidate_runtime_ref,
                incident_report=incident_report,
                candidate_io_report=candidate_io_report,
                reason=(
                    HostingEvidenceGovernedFailoverReason.CURRENT_RUNTIME_NOT_PROVEN_UNSAFE
                ),
                evaluated_at=evaluated_at,
                evidence_ref=evidence_ref,
            )
        )
    if incident_assessment.authorized_action is not (
        HostingReliabilityInfrastructureAction.INITIATE_FAILOVER_EVALUATION
    ):
        return Success(
            _blocked(
                assessment_id=assessment_id,
                account_id=account_id,
                previous_runtime_ref=previous_runtime_ref,
                candidate_runtime_ref=candidate_runtime_ref,
                incident_report=incident_report,
                candidate_io_report=candidate_io_report,
                reason=(
                    HostingEvidenceGovernedFailoverReason.FAILOVER_EVALUATION_NOT_AUTHORIZED
                ),
                evaluated_at=evaluated_at,
                evidence_ref=evidence_ref,
            )
        )
    if (
        candidate_io_report.account_id != account_id
        or candidate_io_report.runtime_ref != candidate_runtime_ref
    ):
        return Success(
            _blocked(
                assessment_id=assessment_id,
                account_id=account_id,
                previous_runtime_ref=previous_runtime_ref,
                candidate_runtime_ref=candidate_runtime_ref,
                incident_report=incident_report,
                candidate_io_report=candidate_io_report,
                reason=HostingEvidenceGovernedFailoverReason.CANDIDATE_IO_SCOPE_MISMATCH,
                evaluated_at=evaluated_at,
                evidence_ref=evidence_ref,
            )
        )
    if candidate_io_report.overall_status is not HostingIOCertificateStatus.CERTIFIED:
        return Success(
            _blocked(
                assessment_id=assessment_id,
                account_id=account_id,
                previous_runtime_ref=previous_runtime_ref,
                candidate_runtime_ref=candidate_runtime_ref,
                incident_report=incident_report,
                candidate_io_report=candidate_io_report,
                reason=HostingEvidenceGovernedFailoverReason.CANDIDATE_IO_NOT_CERTIFIED,
                evaluated_at=evaluated_at,
                evidence_ref=evidence_ref,
            )
        )
    try:
        mission08 = evaluate_hosting_failover_readiness(
            registry,
            leases,
            previous_health,
            candidate_health,
            account_reconciliation,
            execution_reconciliations,
            account_id=account_id,
            previous_runtime_ref=previous_runtime_ref,
            candidate_runtime_ref=candidate_runtime_ref,
            assessment_id=mission08_assessment_id,
            evidence_ref=mission08_evidence_ref,
            evaluated_at=evaluated_at,
        )
    except HostingFailoverReconciliationError as error:
        return Failure(
            HostingEvidenceGovernedFailoverValidationError(str(error))
        )
    if mission08.readiness is not HostingFailoverReadiness.READY_FOR_LEASE_ACQUISITION:
        return Success(
            _blocked(
                assessment_id=assessment_id,
                account_id=account_id,
                previous_runtime_ref=previous_runtime_ref,
                candidate_runtime_ref=candidate_runtime_ref,
                incident_report=incident_report,
                candidate_io_report=candidate_io_report,
                reason=HostingEvidenceGovernedFailoverReason.MISSION08_READINESS_BLOCKED,
                evaluated_at=evaluated_at,
                evidence_ref=evidence_ref,
                mission08_assessment=mission08,
            )
        )
    return Success(
        HostingEvidenceGovernedFailoverAssessment(
            assessment_id=assessment_id,
            account_id=account_id,
            previous_runtime_ref=previous_runtime_ref,
            candidate_runtime_ref=candidate_runtime_ref,
            incident_report_id=incident_report.report_id,
            candidate_io_report_id=candidate_io_report.report_id,
            readiness=(
                HostingEvidenceGovernedFailoverReadiness.READY_FOR_CANONICAL_LEASE_ACQUISITION
            ),
            reason=HostingEvidenceGovernedFailoverReason.EVIDENCE_AND_MISSION08_READY,
            mission08_assessment=mission08,
            next_generation=mission08.next_generation,
            evaluated_at=evaluated_at,
            evidence_ref=evidence_ref,
        )
    )


def acquire_evidence_governed_failover_lease(
    assessment: HostingEvidenceGovernedFailoverAssessment,
    registry: HostingRuntimeRegistrySnapshot,
    leases: HostingExecutionLeaseSnapshot,
    *,
    lease_id: HostingExecutionLeaseId,
    acquired_at: datetime,
    expires_at: datetime,
    evidence_ref: HostingLeaseEvidenceReference,
) -> Result[HostingExecutionLeaseSnapshot, HostingEvidenceGovernedFailoverError]:
    """Delegate the exact ready N+1 handoff to the canonical MISSION-08 lease function."""

    if not isinstance(assessment, HostingEvidenceGovernedFailoverAssessment):
        return Failure(
            HostingEvidenceGovernedFailoverValidationError(
                "assessment must be HostingEvidenceGovernedFailoverAssessment"
            )
        )
    if assessment.readiness is not (
        HostingEvidenceGovernedFailoverReadiness.READY_FOR_CANONICAL_LEASE_ACQUISITION
    ):
        return Failure(
            HostingEvidenceGovernedFailoverExecutionError(
                "blocked evidence-governed failover cannot acquire lease"
            )
        )
    if assessment.next_generation is None:
        return Failure(
            HostingEvidenceGovernedFailoverValidationError(
                "ready failover missing canonical next generation"
            )
        )
    try:
        _validate_timestamp(acquired_at, field_name="failover lease acquired_at")
        _validate_timestamp(expires_at, field_name="failover lease expires_at")
    except HostingEvidenceGovernedFailoverValidationError as error:
        return Failure(error)
    if acquired_at < assessment.evaluated_at:
        return Failure(
            HostingEvidenceGovernedFailoverValidationError(
                "lease acquisition cannot predate failover readiness"
            )
        )
    acquired = acquire_hosting_execution_lease(
        registry,
        leases,
        account_id=assessment.account_id,
        runtime_ref=assessment.candidate_runtime_ref,
        lease_id=lease_id,
        generation=assessment.next_generation,
        acquired_at=acquired_at,
        expires_at=expires_at,
        evidence_ref=evidence_ref,
    )
    if isinstance(acquired, Failure):
        error: HostingExecutionLeaseError = acquired.error
        return Failure(HostingEvidenceGovernedFailoverExecutionError(str(error)))
    return Success(acquired.value)


def certify_availability_failover_handoff(
    assessment: HostingEvidenceGovernedFailoverAssessment,
    candidate_io_report: HostingIOPeriodicReliabilityReport,
    leases: HostingExecutionLeaseSnapshot,
    *,
    certificate_id: HostingAvailabilityFailoverCertificateId,
    certified_at: datetime,
    evidence_ref: HostingReliabilityEvidenceReference,
) -> Result[HostingAvailabilityFailoverCertificate, HostingEvidenceGovernedFailoverError]:
    """Certify exact candidate N+1 authority plus certified Hosting I/O after handoff."""

    try:
        _validate_timestamp(certified_at, field_name="failover certified_at")
    except HostingEvidenceGovernedFailoverValidationError as error:
        return Failure(error)
    current = leases.current_authority(
        assessment.account_id,
        evaluated_at=certified_at,
    )
    authority_matches = False
    if isinstance(current, Success) and assessment.next_generation is not None:
        authority_matches = (
            current.value.runtime_ref == assessment.candidate_runtime_ref
            and current.value.generation == assessment.next_generation
        )
    io_matches = (
        candidate_io_report.account_id == assessment.account_id
        and candidate_io_report.runtime_ref == assessment.candidate_runtime_ref
        and candidate_io_report.overall_status is HostingIOCertificateStatus.CERTIFIED
    )
    status = (
        HostingAvailabilityFailoverCertificateStatus.CERTIFIED
        if authority_matches and io_matches
        else HostingAvailabilityFailoverCertificateStatus.NOT_CERTIFIED
    )
    try:
        certificate = HostingAvailabilityFailoverCertificate(
            certificate_id=certificate_id,
            status=status,
            assessment=assessment,
            candidate_io_report=candidate_io_report,
            lease_snapshot=leases,
            certified_at=certified_at,
            evidence_ref=evidence_ref,
        )
    except HostingEvidenceGovernedFailoverValidationError as error:
        return Failure(error)
    return Success(certificate)
