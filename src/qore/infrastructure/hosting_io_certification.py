from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.client_accounts import (
    ExecutionRuntimeReference,
    TradingAccountId,
)
from qore.infrastructure.hosting_latency_safety import (
    HostingLatencyBaseline,
    HostingLatencyDistribution,
    HostingLatencyDuration,
    HostingLatencyEnvelopeAssessment,
    HostingLatencyEnvelopePolicy,
    HostingLatencyEnvelopeState,
    HostingLatencySafetyError,
    evaluate_hosting_latency_envelope,
)
from qore.infrastructure.hosting_reliability_lab import (
    HostingReliabilityAssessmentId,
    HostingReliabilityBoundary,
    HostingReliabilityEvidenceReference,
    HostingReliabilityObservationId,
    HostingReliabilityPolicySnapshot,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class HostingIOCertificationError(InfrastructureError):
    """Base error for Hosting I/O timing and certification contracts."""

    __slots__ = ()


class HostingIOCertificationValidationError(HostingIOCertificationError):
    """Violation of a Hosting I/O timing/certificate invariant."""

    __slots__ = ()


class HostingIOCertificationEvaluationError(HostingIOCertificationError):
    """A latency/reliability dependency rejected I/O certification."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HostingIOCertificationValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostingIOCertificationValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise HostingIOCertificationValidationError(f"{field_name} must be UUID")


def _duration_microseconds(value: timedelta) -> int:
    return (
        value.days * 86_400_000_000
        + value.seconds * 1_000_000
        + value.microseconds
    )


@dataclass(frozen=True, slots=True)
class HostingIOTimingSampleId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="hosting I/O timing sample id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingIOCertificateId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="hosting I/O certificate id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingIOReportId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="hosting I/O report id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class HostingIOCheckpoint(StrEnum):
    PROVIDER_EVENT = "provider_event"
    HOSTING_INGRESS = "hosting_ingress"
    NORMALIZATION_START = "normalization_start"
    NORMALIZATION_END = "normalization_end"
    CORE_INGRESS = "core_ingress"
    CORE_DECISION = "core_decision"
    HOSTING_EGRESS = "hosting_egress"
    ADAPTER_RECEIVE = "adapter_receive"
    EXTERNAL_ACK = "external_ack"


_EXPECTED_CHECKPOINTS: dict[
    HostingReliabilityBoundary,
    tuple[HostingIOCheckpoint, HostingIOCheckpoint],
] = {
    HostingReliabilityBoundary.NETWORK_INGRESS: (
        HostingIOCheckpoint.PROVIDER_EVENT,
        HostingIOCheckpoint.HOSTING_INGRESS,
    ),
    HostingReliabilityBoundary.INTERNAL_PIPELINE: (
        HostingIOCheckpoint.HOSTING_INGRESS,
        HostingIOCheckpoint.CORE_INGRESS,
    ),
    HostingReliabilityBoundary.NETWORK_EGRESS: (
        HostingIOCheckpoint.CORE_DECISION,
        HostingIOCheckpoint.ADAPTER_RECEIVE,
    ),
    HostingReliabilityBoundary.ROUND_TRIP: (
        HostingIOCheckpoint.CORE_DECISION,
        HostingIOCheckpoint.EXTERNAL_ACK,
    ),
}

_REQUIRED_REPORT_BOUNDARIES = frozenset(
    {
        HostingReliabilityBoundary.NETWORK_INGRESS,
        HostingReliabilityBoundary.INTERNAL_PIPELINE,
        HostingReliabilityBoundary.NETWORK_EGRESS,
    }
)


@dataclass(frozen=True, slots=True)
class HostingIOTimingSample:
    """One immutable checkpoint-to-checkpoint I/O timing fact."""

    sample_id: HostingIOTimingSampleId
    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    boundary: HostingReliabilityBoundary
    started_checkpoint: HostingIOCheckpoint
    ended_checkpoint: HostingIOCheckpoint
    started_at: datetime
    ended_at: datetime
    evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.sample_id, HostingIOTimingSampleId):
            raise HostingIOCertificationValidationError(
                "sample_id must be HostingIOTimingSampleId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise HostingIOCertificationValidationError(
                "sample account_id must be TradingAccountId"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise HostingIOCertificationValidationError(
                "sample runtime_ref must be ExecutionRuntimeReference"
            )
        expected = _EXPECTED_CHECKPOINTS.get(self.boundary)
        if expected is None:
            raise HostingIOCertificationValidationError(
                "sample boundary must be an I/O latency boundary"
            )
        if (self.started_checkpoint, self.ended_checkpoint) != expected:
            raise HostingIOCertificationValidationError(
                "sample checkpoints do not match the canonical I/O boundary"
            )
        _validate_timestamp(self.started_at, field_name="sample started_at")
        _validate_timestamp(self.ended_at, field_name="sample ended_at")
        if self.ended_at < self.started_at:
            raise HostingIOCertificationValidationError(
                "sample ended_at must not predate started_at"
            )
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise HostingIOCertificationValidationError(
                "sample evidence_ref must be HostingReliabilityEvidenceReference"
            )

    @property
    def duration(self) -> HostingLatencyDuration:
        return HostingLatencyDuration(
            _duration_microseconds(self.ended_at - self.started_at)
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.sample_id.logical_values(),
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            self.boundary.value,
            self.started_checkpoint.value,
            self.ended_checkpoint.value,
            self.started_at.isoformat(),
            self.ended_at.isoformat(),
            self.duration.logical_values(),
            self.evidence_ref.logical_values(),
        )


class HostingIOCertificateStatus(StrEnum):
    CERTIFIED = "certified"
    NOT_CERTIFIED = "not_certified"


@dataclass(frozen=True, slots=True)
class HostingIOPathCertificate:
    """Independent certificate for one exact Hosting I/O path."""

    certificate_id: HostingIOCertificateId
    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    boundary: HostingReliabilityBoundary
    status: HostingIOCertificateStatus
    distribution: HostingLatencyDistribution
    latency_assessment: HostingLatencyEnvelopeAssessment
    issued_at: datetime
    evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.certificate_id, HostingIOCertificateId):
            raise HostingIOCertificationValidationError(
                "certificate_id must be HostingIOCertificateId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise HostingIOCertificationValidationError(
                "certificate account_id must be TradingAccountId"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise HostingIOCertificationValidationError(
                "certificate runtime_ref must be ExecutionRuntimeReference"
            )
        if self.boundary not in _EXPECTED_CHECKPOINTS:
            raise HostingIOCertificationValidationError(
                "certificate boundary must be an I/O latency boundary"
            )
        if not isinstance(self.status, HostingIOCertificateStatus):
            raise HostingIOCertificationValidationError(
                "certificate status must be HostingIOCertificateStatus"
            )
        if not isinstance(self.distribution, HostingLatencyDistribution):
            raise HostingIOCertificationValidationError(
                "certificate distribution must be HostingLatencyDistribution"
            )
        if not isinstance(self.latency_assessment, HostingLatencyEnvelopeAssessment):
            raise HostingIOCertificationValidationError(
                "certificate assessment must be HostingLatencyEnvelopeAssessment"
            )
        if (
            self.distribution.account_id != self.account_id
            or self.distribution.runtime_ref != self.runtime_ref
            or self.distribution.boundary is not self.boundary
        ):
            raise HostingIOCertificationValidationError(
                "certificate distribution scope must match certificate scope"
            )
        if self.latency_assessment.distribution != self.distribution:
            raise HostingIOCertificationValidationError(
                "certificate latency assessment must bind the exact distribution"
            )
        expected_status = (
            HostingIOCertificateStatus.CERTIFIED
            if self.latency_assessment.state is HostingLatencyEnvelopeState.CERTIFIED
            else HostingIOCertificateStatus.NOT_CERTIFIED
        )
        if self.status is not expected_status:
            raise HostingIOCertificationValidationError(
                "certificate status must reflect latency assessment state"
            )
        _validate_timestamp(self.issued_at, field_name="certificate issued_at")
        if self.issued_at < self.latency_assessment.evaluated_at:
            raise HostingIOCertificationValidationError(
                "certificate cannot predate latency assessment"
            )
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise HostingIOCertificationValidationError(
                "certificate evidence_ref must be HostingReliabilityEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.certificate_id.logical_values(),
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            self.boundary.value,
            self.status.value,
            self.distribution.logical_values(),
            self.latency_assessment.logical_values(),
            self.issued_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class HostingIOPeriodicReliabilityReport:
    """Periodic report that preserves every path certificate independently."""

    report_id: HostingIOReportId
    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    certificates: tuple[HostingIOPathCertificate, ...]
    window_started_at: datetime
    window_ended_at: datetime
    reported_at: datetime
    evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.report_id, HostingIOReportId):
            raise HostingIOCertificationValidationError(
                "report_id must be HostingIOReportId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise HostingIOCertificationValidationError(
                "report account_id must be TradingAccountId"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise HostingIOCertificationValidationError(
                "report runtime_ref must be ExecutionRuntimeReference"
            )
        if not isinstance(self.certificates, tuple) or any(
            not isinstance(certificate, HostingIOPathCertificate)
            for certificate in self.certificates
        ):
            raise HostingIOCertificationValidationError(
                "report certificates must be immutable HostingIOPathCertificate tuple"
            )
        boundaries = tuple(certificate.boundary for certificate in self.certificates)
        if len(boundaries) != len(set(boundaries)):
            raise HostingIOCertificationValidationError(
                "report may contain only one certificate per I/O boundary"
            )
        if not _REQUIRED_REPORT_BOUNDARIES.issubset(set(boundaries)):
            raise HostingIOCertificationValidationError(
                "report requires independent ingress, internal and egress certificates"
            )
        if any(
            certificate.account_id != self.account_id
            or certificate.runtime_ref != self.runtime_ref
            for certificate in self.certificates
        ):
            raise HostingIOCertificationValidationError(
                "report certificates must share exact account/runtime scope"
            )
        _validate_timestamp(
            self.window_started_at,
            field_name="report window_started_at",
        )
        _validate_timestamp(
            self.window_ended_at,
            field_name="report window_ended_at",
        )
        _validate_timestamp(self.reported_at, field_name="report reported_at")
        if self.window_ended_at <= self.window_started_at:
            raise HostingIOCertificationValidationError(
                "report window_ended_at must be after window_started_at"
            )
        if self.reported_at < self.window_ended_at:
            raise HostingIOCertificationValidationError(
                "report cannot predate reporting window end"
            )
        for certificate in self.certificates:
            distribution = certificate.distribution
            if (
                distribution.window_started_at < self.window_started_at
                or distribution.window_ended_at > self.window_ended_at
            ):
                raise HostingIOCertificationValidationError(
                    "certificate distribution must fit inside report window"
                )
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise HostingIOCertificationValidationError(
                "report evidence_ref must be HostingReliabilityEvidenceReference"
            )

    @property
    def overall_status(self) -> HostingIOCertificateStatus:
        if all(
            certificate.status is HostingIOCertificateStatus.CERTIFIED
            for certificate in self.certificates
        ):
            return HostingIOCertificateStatus.CERTIFIED
        return HostingIOCertificateStatus.NOT_CERTIFIED

    def certificate_for(
        self,
        boundary: HostingReliabilityBoundary,
    ) -> HostingIOPathCertificate | None:
        for certificate in self.certificates:
            if certificate.boundary is boundary:
                return certificate
        return None

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.report_id.logical_values(),
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            tuple(certificate.logical_values() for certificate in self.certificates),
            self.window_started_at.isoformat(),
            self.window_ended_at.isoformat(),
            self.reported_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


def _nearest_rank(
    ordered: tuple[HostingLatencyDuration, ...],
    percentile: int,
) -> HostingLatencyDuration:
    rank = (percentile * len(ordered) + 99) // 100
    return ordered[rank - 1]


def _maximum_adjacent_jitter(
    samples: tuple[HostingIOTimingSample, ...],
) -> HostingLatencyDuration:
    ordered = tuple(
        sorted(samples, key=lambda sample: (sample.ended_at, str(sample.sample_id.value)))
    )
    if len(ordered) < 2:
        return HostingLatencyDuration(0)
    differences = tuple(
        abs(current.duration.microseconds - previous.duration.microseconds)
        for previous, current in zip(ordered[:-1], ordered[1:], strict=True)
    )
    return HostingLatencyDuration(max(differences))


def build_hosting_io_distribution(
    samples: tuple[HostingIOTimingSample, ...],
    *,
    evidence_ref: HostingReliabilityEvidenceReference,
) -> Result[HostingLatencyDistribution, HostingIOCertificationError]:
    """Build a deterministic nearest-rank distribution from one exact I/O path batch."""

    if not isinstance(samples, tuple) or not samples or any(
        not isinstance(sample, HostingIOTimingSample) for sample in samples
    ):
        return Failure(
            HostingIOCertificationValidationError(
                "I/O distribution requires a non-empty immutable sample tuple"
            )
        )
    sample_ids = tuple(sample.sample_id for sample in samples)
    if len(sample_ids) != len(set(sample_ids)):
        return Failure(
            HostingIOCertificationValidationError("I/O sample ids must be unique")
        )
    first = samples[0]
    if any(
        sample.account_id != first.account_id
        or sample.runtime_ref != first.runtime_ref
        or sample.boundary is not first.boundary
        for sample in samples
    ):
        return Failure(
            HostingIOCertificationValidationError(
                "all I/O samples must share exact account/runtime/boundary scope"
            )
        )
    ordered_durations = tuple(sorted(sample.duration for sample in samples))
    try:
        distribution = HostingLatencyDistribution(
            account_id=first.account_id,
            runtime_ref=first.runtime_ref,
            boundary=first.boundary,
            sample_count=len(samples),
            minimum=ordered_durations[0],
            p50=_nearest_rank(ordered_durations, 50),
            p95=_nearest_rank(ordered_durations, 95),
            p99=_nearest_rank(ordered_durations, 99),
            maximum=ordered_durations[-1],
            jitter=_maximum_adjacent_jitter(samples),
            window_started_at=min(sample.started_at for sample in samples),
            window_ended_at=max(sample.ended_at for sample in samples),
            evidence_ref=evidence_ref,
        )
    except HostingLatencySafetyError as error:
        return Failure(HostingIOCertificationValidationError(str(error)))
    return Success(distribution)


def certify_hosting_io_path(
    samples: tuple[HostingIOTimingSample, ...],
    baseline: HostingLatencyBaseline,
    envelope_policy: HostingLatencyEnvelopePolicy,
    reliability_policy: HostingReliabilityPolicySnapshot,
    *,
    distribution_evidence_ref: HostingReliabilityEvidenceReference,
    observation_id: HostingReliabilityObservationId,
    assessment_id: HostingReliabilityAssessmentId,
    certificate_id: HostingIOCertificateId,
    certificate_evidence_ref: HostingReliabilityEvidenceReference,
    evaluated_at: datetime,
    issued_at: datetime,
) -> Result[HostingIOPathCertificate, HostingIOCertificationError]:
    """Measure and independently certify one path; performs no provider/runtime I/O."""

    built = build_hosting_io_distribution(
        samples,
        evidence_ref=distribution_evidence_ref,
    )
    if isinstance(built, Failure):
        return Failure(built.error)
    assessed = evaluate_hosting_latency_envelope(
        built.value,
        baseline,
        envelope_policy,
        reliability_policy,
        observation_id=observation_id,
        assessment_id=assessment_id,
        evaluated_at=evaluated_at,
    )
    if isinstance(assessed, Failure):
        return Failure(
            HostingIOCertificationEvaluationError(
                f"latency/reliability assessment rejected I/O certificate: {assessed.error}"
            )
        )
    status = (
        HostingIOCertificateStatus.CERTIFIED
        if assessed.value.state is HostingLatencyEnvelopeState.CERTIFIED
        else HostingIOCertificateStatus.NOT_CERTIFIED
    )
    distribution = built.value
    try:
        certificate = HostingIOPathCertificate(
            certificate_id=certificate_id,
            account_id=distribution.account_id,
            runtime_ref=distribution.runtime_ref,
            boundary=distribution.boundary,
            status=status,
            distribution=distribution,
            latency_assessment=assessed.value,
            issued_at=issued_at,
            evidence_ref=certificate_evidence_ref,
        )
    except HostingIOCertificationValidationError as error:
        return Failure(error)
    return Success(certificate)
