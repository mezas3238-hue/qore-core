from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.hosting_reliability_lab import (
    HostingReliabilityActionRecord,
    HostingReliabilityAssessment,
    HostingReliabilityCondition,
    HostingReliabilityEvidenceReference,
    HostingReliabilityInfrastructureAction,
    HostingReliabilityObservation,
    HostingReliabilityRationaleCode,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class HostingReliabilityIncidentError(InfrastructureError):
    """Base error for reliability incident genealogy contracts."""

    __slots__ = ()


class HostingReliabilityIncidentValidationError(HostingReliabilityIncidentError):
    """Violation of an incident/anomaly genealogy invariant."""

    __slots__ = ()


class HostingReliabilityIncidentAuthorizationError(HostingReliabilityIncidentError):
    """Requested incident transition is not justified by the Lab assessment."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HostingReliabilityIncidentValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostingReliabilityIncidentValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise HostingReliabilityIncidentValidationError(
            f"{field_name} must be UUID"
        )


def _validate_text(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise HostingReliabilityIncidentValidationError(
            f"{field_name} must be a non-empty string"
        )


@dataclass(frozen=True, slots=True)
class HostingReliabilityAnomalyReportId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="anomaly report id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingReliabilityIncidentId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="reliability incident id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingReliabilityRecoveryAttemptId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="recovery attempt id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingReliabilityPostCertificationId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="post-action certification id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingReliabilityIncidentReportId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="incident report id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingReliabilityMetricName:
    value: str

    def __post_init__(self) -> None:
        _validate_text(self.value, field_name="reliability metric name")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class HostingReliabilityProcedureReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="reliability procedure reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingReliabilityRecoveryReasonCode:
    value: str

    def __post_init__(self) -> None:
        _validate_text(self.value, field_name="recovery reason code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class HostingReliabilityRecoveryOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class HostingReliabilityPostCertificationState(StrEnum):
    CERTIFIED = "certified"
    NOT_CERTIFIED = "not_certified"
    UNKNOWN = "unknown"


class HostingReliabilityIncidentFinalState(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class HostingReliabilityAnomalyReport:
    """Evidence report for anomaly/unknown observations, including justified NO_ACTION."""

    report_id: HostingReliabilityAnomalyReportId
    observation: HostingReliabilityObservation
    assessment: HostingReliabilityAssessment
    metric_name: HostingReliabilityMetricName
    threshold_evidence_ref: HostingReliabilityEvidenceReference
    generated_at: datetime
    evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.report_id, HostingReliabilityAnomalyReportId):
            raise HostingReliabilityIncidentValidationError(
                "anomaly report_id must be HostingReliabilityAnomalyReportId"
            )
        if not isinstance(self.observation, HostingReliabilityObservation):
            raise HostingReliabilityIncidentValidationError(
                "anomaly observation must be HostingReliabilityObservation"
            )
        if self.observation.condition not in {
            HostingReliabilityCondition.ANOMALOUS,
            HostingReliabilityCondition.UNKNOWN,
        }:
            raise HostingReliabilityIncidentValidationError(
                "anomaly report requires ANOMALOUS or UNKNOWN observation"
            )
        if not isinstance(self.assessment, HostingReliabilityAssessment):
            raise HostingReliabilityIncidentValidationError(
                "anomaly assessment must be HostingReliabilityAssessment"
            )
        if self.assessment.observation_id != self.observation.observation_id:
            raise HostingReliabilityIncidentValidationError(
                "anomaly assessment must bind the exact observation"
            )
        if (
            self.assessment.account_id != self.observation.account_id
            or self.assessment.runtime_ref != self.observation.runtime_ref
        ):
            raise HostingReliabilityIncidentValidationError(
                "anomaly assessment scope must match observation scope"
            )
        if not isinstance(self.metric_name, HostingReliabilityMetricName):
            raise HostingReliabilityIncidentValidationError(
                "metric_name must be HostingReliabilityMetricName"
            )
        if not isinstance(
            self.threshold_evidence_ref,
            HostingReliabilityEvidenceReference,
        ):
            raise HostingReliabilityIncidentValidationError(
                "threshold_evidence_ref must be HostingReliabilityEvidenceReference"
            )
        _validate_timestamp(self.generated_at, field_name="anomaly generated_at")
        if self.generated_at < self.assessment.assessed_at:
            raise HostingReliabilityIncidentValidationError(
                "anomaly report cannot predate assessment"
            )
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise HostingReliabilityIncidentValidationError(
                "anomaly evidence_ref must be HostingReliabilityEvidenceReference"
            )

    @property
    def is_justified_no_action(self) -> bool:
        return (
            self.assessment.authorized_action
            is HostingReliabilityInfrastructureAction.NO_ACTION
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.report_id.logical_values(),
            self.observation.logical_values(),
            self.assessment.logical_values(),
            self.metric_name.logical_values(),
            self.threshold_evidence_ref.logical_values(),
            self.generated_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class HostingReliabilityIncident:
    """Opened intervention incident derived from one anomaly report."""

    incident_id: HostingReliabilityIncidentId
    anomaly_report: HostingReliabilityAnomalyReport
    opened_at: datetime
    evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.incident_id, HostingReliabilityIncidentId):
            raise HostingReliabilityIncidentValidationError(
                "incident_id must be HostingReliabilityIncidentId"
            )
        if not isinstance(self.anomaly_report, HostingReliabilityAnomalyReport):
            raise HostingReliabilityIncidentValidationError(
                "incident anomaly_report must be HostingReliabilityAnomalyReport"
            )
        if self.anomaly_report.is_justified_no_action:
            raise HostingReliabilityIncidentAuthorizationError(
                "NO_ACTION anomaly must not manufacture an intervention incident"
            )
        _validate_timestamp(self.opened_at, field_name="incident opened_at")
        if self.opened_at < self.anomaly_report.generated_at:
            raise HostingReliabilityIncidentValidationError(
                "incident cannot predate anomaly report"
            )
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise HostingReliabilityIncidentValidationError(
                "incident evidence_ref must be HostingReliabilityEvidenceReference"
            )

    @property
    def authorized_action(self) -> HostingReliabilityInfrastructureAction:
        return self.anomaly_report.assessment.authorized_action

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.incident_id.logical_values(),
            self.anomaly_report.logical_values(),
            self.opened_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class HostingReliabilityRecoveryAttempt:
    """Evidence for one policy-authorized stabilization/recovery attempt."""

    attempt_id: HostingReliabilityRecoveryAttemptId
    incident_id: HostingReliabilityIncidentId
    ordinal: int
    procedure_ref: HostingReliabilityProcedureReference
    rationale_code: HostingReliabilityRationaleCode
    started_at: datetime
    completed_at: datetime
    outcome: HostingReliabilityRecoveryOutcome
    failure_reason: HostingReliabilityRecoveryReasonCode | None
    evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.attempt_id, HostingReliabilityRecoveryAttemptId):
            raise HostingReliabilityIncidentValidationError(
                "attempt_id must be HostingReliabilityRecoveryAttemptId"
            )
        if not isinstance(self.incident_id, HostingReliabilityIncidentId):
            raise HostingReliabilityIncidentValidationError(
                "recovery incident_id must be HostingReliabilityIncidentId"
            )
        if type(self.ordinal) is not int or self.ordinal <= 0:
            raise HostingReliabilityIncidentValidationError(
                "recovery ordinal must be a positive integer"
            )
        if not isinstance(self.procedure_ref, HostingReliabilityProcedureReference):
            raise HostingReliabilityIncidentValidationError(
                "procedure_ref must be HostingReliabilityProcedureReference"
            )
        if not isinstance(self.rationale_code, HostingReliabilityRationaleCode):
            raise HostingReliabilityIncidentValidationError(
                "recovery rationale_code must be HostingReliabilityRationaleCode"
            )
        _validate_timestamp(self.started_at, field_name="recovery started_at")
        _validate_timestamp(self.completed_at, field_name="recovery completed_at")
        if self.completed_at < self.started_at:
            raise HostingReliabilityIncidentValidationError(
                "recovery completed_at cannot predate started_at"
            )
        if not isinstance(self.outcome, HostingReliabilityRecoveryOutcome):
            raise HostingReliabilityIncidentValidationError(
                "recovery outcome must be HostingReliabilityRecoveryOutcome"
            )
        if self.outcome is HostingReliabilityRecoveryOutcome.SUCCEEDED:
            if self.failure_reason is not None:
                raise HostingReliabilityIncidentValidationError(
                    "successful recovery cannot carry failure_reason"
                )
        elif not isinstance(self.failure_reason, HostingReliabilityRecoveryReasonCode):
            raise HostingReliabilityIncidentValidationError(
                "failed/unknown recovery requires explicit failure_reason"
            )
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise HostingReliabilityIncidentValidationError(
                "recovery evidence_ref must be HostingReliabilityEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.attempt_id.logical_values(),
            self.incident_id.logical_values(),
            self.ordinal,
            self.procedure_ref.logical_values(),
            self.rationale_code.logical_values(),
            self.started_at.isoformat(),
            self.completed_at.isoformat(),
            self.outcome.value,
            self.failure_reason.logical_values() if self.failure_reason else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class HostingReliabilityPostActionCertification:
    """Evidence-only certification of the state observed after intervention."""

    certification_id: HostingReliabilityPostCertificationId
    incident_id: HostingReliabilityIncidentId
    state: HostingReliabilityPostCertificationState
    certified_at: datetime
    evidence_refs: tuple[HostingReliabilityEvidenceReference, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.certification_id,
            HostingReliabilityPostCertificationId,
        ):
            raise HostingReliabilityIncidentValidationError(
                "certification_id must be HostingReliabilityPostCertificationId"
            )
        if not isinstance(self.incident_id, HostingReliabilityIncidentId):
            raise HostingReliabilityIncidentValidationError(
                "post certification incident_id must be HostingReliabilityIncidentId"
            )
        if not isinstance(self.state, HostingReliabilityPostCertificationState):
            raise HostingReliabilityIncidentValidationError(
                "post certification state must be HostingReliabilityPostCertificationState"
            )
        _validate_timestamp(self.certified_at, field_name="post certified_at")
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs or any(
            not isinstance(ref, HostingReliabilityEvidenceReference)
            for ref in self.evidence_refs
        ):
            raise HostingReliabilityIncidentValidationError(
                "post certification requires immutable non-empty evidence refs"
            )
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise HostingReliabilityIncidentValidationError(
                "post certification evidence refs must be unique"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.certification_id.logical_values(),
            self.incident_id.logical_values(),
            self.state.value,
            self.certified_at.isoformat(),
            tuple(ref.logical_values() for ref in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class HostingReliabilityIncidentReport:
    """Complete intervention genealogy from anomaly through post-action certification."""

    report_id: HostingReliabilityIncidentReportId
    incident: HostingReliabilityIncident
    action_record: HostingReliabilityActionRecord
    recovery_attempts: tuple[HostingReliabilityRecoveryAttempt, ...]
    post_certification: HostingReliabilityPostActionCertification
    generated_at: datetime
    evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.report_id, HostingReliabilityIncidentReportId):
            raise HostingReliabilityIncidentValidationError(
                "incident report_id must be HostingReliabilityIncidentReportId"
            )
        if not isinstance(self.incident, HostingReliabilityIncident):
            raise HostingReliabilityIncidentValidationError(
                "incident report incident must be HostingReliabilityIncident"
            )
        if not isinstance(self.action_record, HostingReliabilityActionRecord):
            raise HostingReliabilityIncidentValidationError(
                "incident report action_record must be HostingReliabilityActionRecord"
            )
        assessment = self.incident.anomaly_report.assessment
        if self.action_record.assessment_id != assessment.assessment_id:
            raise HostingReliabilityIncidentValidationError(
                "action record must bind incident assessment"
            )
        if self.action_record.action is not assessment.authorized_action:
            raise HostingReliabilityIncidentValidationError(
                "action record must match incident authorized action"
            )
        if (
            self.action_record.account_id != assessment.account_id
            or self.action_record.runtime_ref != assessment.runtime_ref
        ):
            raise HostingReliabilityIncidentValidationError(
                "action record scope must match incident assessment"
            )
        if not isinstance(self.recovery_attempts, tuple) or any(
            not isinstance(attempt, HostingReliabilityRecoveryAttempt)
            for attempt in self.recovery_attempts
        ):
            raise HostingReliabilityIncidentValidationError(
                "recovery_attempts must be immutable recovery attempt tuple"
            )
        if any(
            attempt.incident_id != self.incident.incident_id
            for attempt in self.recovery_attempts
        ):
            raise HostingReliabilityIncidentValidationError(
                "all recovery attempts must bind incident id"
            )
        ordinals = tuple(attempt.ordinal for attempt in self.recovery_attempts)
        if ordinals != tuple(range(1, len(ordinals) + 1)):
            raise HostingReliabilityIncidentValidationError(
                "recovery attempt ordinals must be contiguous from 1"
            )
        if not isinstance(
            self.post_certification,
            HostingReliabilityPostActionCertification,
        ):
            raise HostingReliabilityIncidentValidationError(
                "post_certification must be HostingReliabilityPostActionCertification"
            )
        if self.post_certification.incident_id != self.incident.incident_id:
            raise HostingReliabilityIncidentValidationError(
                "post certification must bind incident id"
            )
        latest_event = self.action_record.occurred_at
        if self.recovery_attempts:
            latest_event = max(
                latest_event,
                max(attempt.completed_at for attempt in self.recovery_attempts),
            )
        if self.post_certification.certified_at < latest_event:
            raise HostingReliabilityIncidentValidationError(
                "post certification cannot predate action/recovery evidence"
            )
        _validate_timestamp(self.generated_at, field_name="incident report generated_at")
        if self.generated_at < self.post_certification.certified_at:
            raise HostingReliabilityIncidentValidationError(
                "incident report cannot predate post certification"
            )
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise HostingReliabilityIncidentValidationError(
                "incident report evidence_ref must be HostingReliabilityEvidenceReference"
            )

    @property
    def final_state(self) -> HostingReliabilityIncidentFinalState:
        if (
            self.post_certification.state
            is HostingReliabilityPostCertificationState.CERTIFIED
        ):
            return HostingReliabilityIncidentFinalState.RESOLVED
        if (
            self.post_certification.state
            is HostingReliabilityPostCertificationState.NOT_CERTIFIED
        ):
            return HostingReliabilityIncidentFinalState.UNRESOLVED
        return HostingReliabilityIncidentFinalState.UNKNOWN

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.report_id.logical_values(),
            self.incident.logical_values(),
            self.action_record.logical_values(),
            tuple(attempt.logical_values() for attempt in self.recovery_attempts),
            self.post_certification.logical_values(),
            self.generated_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


def build_hosting_reliability_anomaly_report(
    observation: HostingReliabilityObservation,
    assessment: HostingReliabilityAssessment,
    *,
    report_id: HostingReliabilityAnomalyReportId,
    metric_name: HostingReliabilityMetricName,
    threshold_evidence_ref: HostingReliabilityEvidenceReference,
    generated_at: datetime,
    evidence_ref: HostingReliabilityEvidenceReference,
) -> Result[HostingReliabilityAnomalyReport, HostingReliabilityIncidentError]:
    """Build anomaly evidence, including explicit policy-backed NO_ACTION."""

    try:
        report = HostingReliabilityAnomalyReport(
            report_id=report_id,
            observation=observation,
            assessment=assessment,
            metric_name=metric_name,
            threshold_evidence_ref=threshold_evidence_ref,
            generated_at=generated_at,
            evidence_ref=evidence_ref,
        )
    except HostingReliabilityIncidentError as error:
        return Failure(error)
    return Success(report)


def open_hosting_reliability_incident(
    anomaly_report: HostingReliabilityAnomalyReport,
    *,
    incident_id: HostingReliabilityIncidentId,
    opened_at: datetime,
    evidence_ref: HostingReliabilityEvidenceReference,
) -> Result[HostingReliabilityIncident, HostingReliabilityIncidentError]:
    """Open an incident only when the Lab assessment authorized intervention."""

    try:
        incident = HostingReliabilityIncident(
            incident_id=incident_id,
            anomaly_report=anomaly_report,
            opened_at=opened_at,
            evidence_ref=evidence_ref,
        )
    except HostingReliabilityIncidentError as error:
        return Failure(error)
    return Success(incident)
