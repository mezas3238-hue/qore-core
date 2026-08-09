from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from qore.infrastructure import market_data
from qore.infrastructure.hosting_latency_safety import HostingLatencyDuration
from qore.infrastructure.hosting_reliability_lab import (
    HostingReliabilityEvidenceReference,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class MarketDataIntegrityError(InfrastructureError):
    """Base error for provider-neutral market-data integrity certification."""

    __slots__ = ()


class MarketDataIntegrityValidationError(MarketDataIntegrityError):
    """Violation of a market-data integrity contract invariant."""

    __slots__ = ()


class MarketDataIntegrityQuarantineError(MarketDataIntegrityError):
    """A quarantine record was requested for evidence that is not quarantineable."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise MarketDataIntegrityValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise MarketDataIntegrityValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise MarketDataIntegrityValidationError(f"{field_name} must be UUID")


def _duration_microseconds(value: timedelta) -> int:
    return (
        value.days * 86_400_000_000
        + value.seconds * 1_000_000
        + value.microseconds
    )


@dataclass(frozen=True, slots=True)
class MarketDataIntegrityAssessmentId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="market-data integrity assessment id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class MarketDataIntegrityCertificateId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="market-data integrity certificate id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class MarketDataQuarantineId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="market-data quarantine id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class MarketDataIntegrityRationaleCode:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise MarketDataIntegrityValidationError(
                "market-data integrity rationale code must be non-empty"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class MarketDataIntegrityState(StrEnum):
    VALID = "valid"
    DELAYED = "delayed"
    GAP_DETECTED = "gap_detected"
    DUPLICATE = "duplicate"
    OUT_OF_ORDER = "out_of_order"
    CORRUPTED = "corrupted"
    QUARANTINED = "quarantined"


class MarketDataIntegrityDisposition(StrEnum):
    ACCEPT = "accept"
    DEGRADE = "degrade"
    QUARANTINE = "quarantine"


class MarketDataIntegrityCertificateStatus(StrEnum):
    CERTIFIED = "certified"
    NOT_CERTIFIED = "not_certified"


@dataclass(frozen=True, slots=True)
class MarketDataIntegrityPolicy:
    """Provider-neutral freshness boundary for canonical closed OHLC bars."""

    max_delivery_delay: HostingLatencyDuration

    def __post_init__(self) -> None:
        if not isinstance(self.max_delivery_delay, HostingLatencyDuration):
            raise MarketDataIntegrityValidationError(
                "max_delivery_delay must be HostingLatencyDuration"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.max_delivery_delay.logical_values(),)


@dataclass(frozen=True, slots=True)
class MarketDataIngressRecord:
    """Canonical OHLC plus source-to-Core ingress timestamps and evidence."""

    snapshot: market_data.OhlcSnapshot
    hosting_received_at: datetime
    core_ingress_at: datetime
    normalization_evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, market_data.OhlcSnapshot):
            raise MarketDataIntegrityValidationError(
                "ingress snapshot must be canonical OhlcSnapshot"
            )
        _validate_timestamp(
            self.hosting_received_at,
            field_name="market-data hosting_received_at",
        )
        _validate_timestamp(
            self.core_ingress_at,
            field_name="market-data core_ingress_at",
        )
        if self.hosting_received_at < self.snapshot.closed_at:
            raise MarketDataIntegrityValidationError(
                "closed OHLC cannot arrive before its canonical close timestamp"
            )
        if self.core_ingress_at < self.hosting_received_at:
            raise MarketDataIntegrityValidationError(
                "core_ingress_at cannot predate hosting_received_at"
            )
        if not isinstance(
            self.normalization_evidence_ref,
            HostingReliabilityEvidenceReference,
        ):
            raise MarketDataIntegrityValidationError(
                "normalization_evidence_ref must be HostingReliabilityEvidenceReference"
            )

    @property
    def delivery_delay(self) -> HostingLatencyDuration:
        return HostingLatencyDuration(
            _duration_microseconds(self.hosting_received_at - self.snapshot.closed_at)
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.snapshot.logical_values(),
            self.hosting_received_at.isoformat(),
            self.core_ingress_at.isoformat(),
            self.delivery_delay.logical_values(),
            self.normalization_evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class MarketDataIntegrityAssessment:
    """Immutable classification of one canonical bar against accepted history."""

    assessment_id: MarketDataIntegrityAssessmentId
    state: MarketDataIntegrityState
    disposition: MarketDataIntegrityDisposition
    record: MarketDataIngressRecord
    previous_snapshot_id: market_data.MarketDataSnapshotId | None
    expected_opened_at: datetime | None
    rationale_code: MarketDataIntegrityRationaleCode
    evidence_refs: tuple[HostingReliabilityEvidenceReference, ...]
    assessed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.assessment_id, MarketDataIntegrityAssessmentId):
            raise MarketDataIntegrityValidationError(
                "assessment_id must be MarketDataIntegrityAssessmentId"
            )
        if not isinstance(self.state, MarketDataIntegrityState):
            raise MarketDataIntegrityValidationError(
                "assessment state must be MarketDataIntegrityState"
            )
        if self.state is MarketDataIntegrityState.QUARANTINED:
            raise MarketDataIntegrityValidationError(
                "initial integrity assessment cannot use QUARANTINED state"
            )
        if not isinstance(self.disposition, MarketDataIntegrityDisposition):
            raise MarketDataIntegrityValidationError(
                "assessment disposition must be MarketDataIntegrityDisposition"
            )
        expected_disposition = _disposition_for_state(self.state)
        if self.disposition is not expected_disposition:
            raise MarketDataIntegrityValidationError(
                "assessment disposition must match integrity state"
            )
        if not isinstance(self.record, MarketDataIngressRecord):
            raise MarketDataIntegrityValidationError(
                "assessment record must be MarketDataIngressRecord"
            )
        if self.previous_snapshot_id is not None and not isinstance(
            self.previous_snapshot_id,
            market_data.MarketDataSnapshotId,
        ):
            raise MarketDataIntegrityValidationError(
                "previous_snapshot_id must be MarketDataSnapshotId or None"
            )
        if self.expected_opened_at is not None:
            _validate_timestamp(
                self.expected_opened_at,
                field_name="assessment expected_opened_at",
            )
        if not isinstance(self.rationale_code, MarketDataIntegrityRationaleCode):
            raise MarketDataIntegrityValidationError(
                "assessment rationale_code must be MarketDataIntegrityRationaleCode"
            )
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs or any(
            not isinstance(ref, HostingReliabilityEvidenceReference)
            for ref in self.evidence_refs
        ):
            raise MarketDataIntegrityValidationError(
                "assessment requires immutable non-empty evidence refs"
            )
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise MarketDataIntegrityValidationError(
                "assessment evidence refs must be unique"
            )
        _validate_timestamp(self.assessed_at, field_name="assessment assessed_at")
        if self.assessed_at < self.record.core_ingress_at:
            raise MarketDataIntegrityValidationError(
                "integrity assessment cannot predate core ingress observation"
            )

    @property
    def allows_core_ingress(self) -> bool:
        return self.disposition is MarketDataIntegrityDisposition.ACCEPT

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.assessment_id.logical_values(),
            self.state.value,
            self.disposition.value,
            self.record.logical_values(),
            (
                str(self.previous_snapshot_id.value)
                if self.previous_snapshot_id is not None
                else None
            ),
            self.expected_opened_at.isoformat() if self.expected_opened_at else None,
            self.rationale_code.logical_values(),
            tuple(ref.logical_values() for ref in self.evidence_refs),
            self.assessed_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class MarketDataIntegrityCertificate:
    """Certification result that binds the exact assessed canonical snapshot."""

    certificate_id: MarketDataIntegrityCertificateId
    status: MarketDataIntegrityCertificateStatus
    assessment: MarketDataIntegrityAssessment
    issued_at: datetime
    evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.certificate_id, MarketDataIntegrityCertificateId):
            raise MarketDataIntegrityValidationError(
                "certificate_id must be MarketDataIntegrityCertificateId"
            )
        if not isinstance(self.status, MarketDataIntegrityCertificateStatus):
            raise MarketDataIntegrityValidationError(
                "certificate status must be MarketDataIntegrityCertificateStatus"
            )
        if not isinstance(self.assessment, MarketDataIntegrityAssessment):
            raise MarketDataIntegrityValidationError(
                "certificate assessment must be MarketDataIntegrityAssessment"
            )
        expected_status = (
            MarketDataIntegrityCertificateStatus.CERTIFIED
            if self.assessment.state is MarketDataIntegrityState.VALID
            else MarketDataIntegrityCertificateStatus.NOT_CERTIFIED
        )
        if self.status is not expected_status:
            raise MarketDataIntegrityValidationError(
                "certificate status must reflect exact integrity assessment"
            )
        _validate_timestamp(self.issued_at, field_name="certificate issued_at")
        if self.issued_at < self.assessment.assessed_at:
            raise MarketDataIntegrityValidationError(
                "certificate cannot predate integrity assessment"
            )
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise MarketDataIntegrityValidationError(
                "certificate evidence_ref must be HostingReliabilityEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.certificate_id.logical_values(),
            self.status.value,
            self.assessment.logical_values(),
            self.issued_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class MarketDataQuarantineRecord:
    """Evidence-only quarantine record; it never repairs or replaces market data."""

    quarantine_id: MarketDataQuarantineId
    state: MarketDataIntegrityState
    origin_state: MarketDataIntegrityState
    assessment_id: MarketDataIntegrityAssessmentId
    snapshot: market_data.OhlcSnapshot
    quarantined_at: datetime
    evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.quarantine_id, MarketDataQuarantineId):
            raise MarketDataIntegrityValidationError(
                "quarantine_id must be MarketDataQuarantineId"
            )
        if self.state is not MarketDataIntegrityState.QUARANTINED:
            raise MarketDataIntegrityValidationError(
                "quarantine record state must be QUARANTINED"
            )
        if self.origin_state not in {
            MarketDataIntegrityState.DUPLICATE,
            MarketDataIntegrityState.OUT_OF_ORDER,
            MarketDataIntegrityState.CORRUPTED,
        }:
            raise MarketDataIntegrityValidationError(
                "quarantine origin must be duplicate/out_of_order/corrupted"
            )
        if not isinstance(self.assessment_id, MarketDataIntegrityAssessmentId):
            raise MarketDataIntegrityValidationError(
                "quarantine assessment_id must be MarketDataIntegrityAssessmentId"
            )
        if not isinstance(self.snapshot, market_data.OhlcSnapshot):
            raise MarketDataIntegrityValidationError(
                "quarantine snapshot must be canonical OhlcSnapshot"
            )
        _validate_timestamp(self.quarantined_at, field_name="quarantined_at")
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise MarketDataIntegrityValidationError(
                "quarantine evidence_ref must be HostingReliabilityEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.quarantine_id.logical_values(),
            self.state.value,
            self.origin_state.value,
            self.assessment_id.logical_values(),
            self.snapshot.logical_values(),
            self.quarantined_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


def _disposition_for_state(
    state: MarketDataIntegrityState,
) -> MarketDataIntegrityDisposition:
    if state is MarketDataIntegrityState.VALID:
        return MarketDataIntegrityDisposition.ACCEPT
    if state in {
        MarketDataIntegrityState.DELAYED,
        MarketDataIntegrityState.GAP_DETECTED,
    }:
        return MarketDataIntegrityDisposition.DEGRADE
    return MarketDataIntegrityDisposition.QUARANTINE


def _rationale_for_state(
    state: MarketDataIntegrityState,
) -> MarketDataIntegrityRationaleCode:
    values = {
        MarketDataIntegrityState.VALID: "market_data.valid",
        MarketDataIntegrityState.DELAYED: "market_data.delayed",
        MarketDataIntegrityState.GAP_DETECTED: "market_data.gap_detected",
        MarketDataIntegrityState.DUPLICATE: "market_data.duplicate",
        MarketDataIntegrityState.OUT_OF_ORDER: "market_data.out_of_order",
        MarketDataIntegrityState.CORRUPTED: "market_data.conflicting_interval",
    }
    return MarketDataIntegrityRationaleCode(values[state])


def _same_scope(
    left: market_data.OhlcSnapshot,
    right: market_data.OhlcSnapshot,
) -> bool:
    return (
        left.instrument == right.instrument
        and left.source == right.source
        and left.timeframe == right.timeframe
    )


def _same_bar_values(
    left: market_data.OhlcSnapshot,
    right: market_data.OhlcSnapshot,
) -> bool:
    return (
        left.opened_at == right.opened_at
        and left.closed_at == right.closed_at
        and left.open == right.open
        and left.high == right.high
        and left.low == right.low
        and left.close == right.close
    )


def _validate_accepted_history(
    history: tuple[MarketDataIngressRecord, ...],
    record: MarketDataIngressRecord,
) -> Result[None, MarketDataIntegrityError]:
    if not isinstance(history, tuple) or any(
        not isinstance(item, MarketDataIngressRecord) for item in history
    ):
        return Failure(
            MarketDataIntegrityValidationError(
                "accepted_history must be immutable MarketDataIngressRecord tuple"
            )
        )
    if any(not _same_scope(item.snapshot, record.snapshot) for item in history):
        return Failure(
            MarketDataIntegrityValidationError(
                "accepted history and candidate must share source/instrument/timeframe"
            )
        )
    for previous, current in zip(history[:-1], history[1:], strict=True):
        if current.snapshot.opened_at != previous.snapshot.closed_at:
            return Failure(
                MarketDataIntegrityValidationError(
                    "accepted history itself must be strictly contiguous"
                )
            )
    return Success(None)


def _classify_record(
    record: MarketDataIngressRecord,
    history: tuple[MarketDataIngressRecord, ...],
    policy: MarketDataIntegrityPolicy,
) -> tuple[
    MarketDataIntegrityState,
    market_data.MarketDataSnapshotId | None,
    datetime | None,
]:
    if not history:
        if record.delivery_delay > policy.max_delivery_delay:
            return MarketDataIntegrityState.DELAYED, None, None
        return MarketDataIntegrityState.VALID, None, None

    previous = history[-1]
    candidate = record.snapshot
    previous_snapshot = previous.snapshot
    expected_opened_at = previous_snapshot.closed_at

    if candidate.opened_at == previous_snapshot.opened_at:
        if _same_bar_values(candidate, previous_snapshot):
            return (
                MarketDataIntegrityState.DUPLICATE,
                previous_snapshot.snapshot_id,
                expected_opened_at,
            )
        return (
            MarketDataIntegrityState.CORRUPTED,
            previous_snapshot.snapshot_id,
            expected_opened_at,
        )
    if candidate.opened_at < previous_snapshot.closed_at:
        return (
            MarketDataIntegrityState.OUT_OF_ORDER,
            previous_snapshot.snapshot_id,
            expected_opened_at,
        )
    if candidate.opened_at > previous_snapshot.closed_at:
        return (
            MarketDataIntegrityState.GAP_DETECTED,
            previous_snapshot.snapshot_id,
            expected_opened_at,
        )
    if record.delivery_delay > policy.max_delivery_delay:
        return (
            MarketDataIntegrityState.DELAYED,
            previous_snapshot.snapshot_id,
            expected_opened_at,
        )
    return (
        MarketDataIntegrityState.VALID,
        previous_snapshot.snapshot_id,
        expected_opened_at,
    )


def evaluate_market_data_integrity(
    record: MarketDataIngressRecord,
    accepted_history: tuple[MarketDataIngressRecord, ...],
    policy: MarketDataIntegrityPolicy,
    *,
    assessment_id: MarketDataIntegrityAssessmentId,
    assessed_at: datetime,
) -> Result[MarketDataIntegrityAssessment, MarketDataIntegrityError]:
    """Classify one canonical OHLC record without repairing or mutating it."""

    if not isinstance(record, MarketDataIngressRecord):
        return Failure(
            MarketDataIntegrityValidationError(
                "record must be MarketDataIngressRecord"
            )
        )
    if not isinstance(policy, MarketDataIntegrityPolicy):
        return Failure(
            MarketDataIntegrityValidationError(
                "policy must be MarketDataIntegrityPolicy"
            )
        )
    history_validation = _validate_accepted_history(accepted_history, record)
    if isinstance(history_validation, Failure):
        return Failure(history_validation.error)
    try:
        _validate_timestamp(assessed_at, field_name="integrity assessed_at")
    except MarketDataIntegrityValidationError as error:
        return Failure(error)
    state, previous_snapshot_id, expected_opened_at = _classify_record(
        record,
        accepted_history,
        policy,
    )
    evidence_refs: tuple[HostingReliabilityEvidenceReference, ...]
    if accepted_history:
        previous_ref = accepted_history[-1].normalization_evidence_ref
        evidence_refs = (
            (record.normalization_evidence_ref,)
            if previous_ref == record.normalization_evidence_ref
            else (record.normalization_evidence_ref, previous_ref)
        )
    else:
        evidence_refs = (record.normalization_evidence_ref,)
    try:
        assessment = MarketDataIntegrityAssessment(
            assessment_id=assessment_id,
            state=state,
            disposition=_disposition_for_state(state),
            record=record,
            previous_snapshot_id=previous_snapshot_id,
            expected_opened_at=expected_opened_at,
            rationale_code=_rationale_for_state(state),
            evidence_refs=evidence_refs,
            assessed_at=assessed_at,
        )
    except MarketDataIntegrityValidationError as error:
        return Failure(error)
    return Success(assessment)


def issue_market_data_integrity_certificate(
    assessment: MarketDataIntegrityAssessment,
    *,
    certificate_id: MarketDataIntegrityCertificateId,
    issued_at: datetime,
    evidence_ref: HostingReliabilityEvidenceReference,
) -> Result[MarketDataIntegrityCertificate, MarketDataIntegrityError]:
    """Issue a certificate only from the exact immutable integrity assessment."""

    if not isinstance(assessment, MarketDataIntegrityAssessment):
        return Failure(
            MarketDataIntegrityValidationError(
                "assessment must be MarketDataIntegrityAssessment"
            )
        )
    status = (
        MarketDataIntegrityCertificateStatus.CERTIFIED
        if assessment.state is MarketDataIntegrityState.VALID
        else MarketDataIntegrityCertificateStatus.NOT_CERTIFIED
    )
    try:
        certificate = MarketDataIntegrityCertificate(
            certificate_id=certificate_id,
            status=status,
            assessment=assessment,
            issued_at=issued_at,
            evidence_ref=evidence_ref,
        )
    except MarketDataIntegrityValidationError as error:
        return Failure(error)
    return Success(certificate)


def quarantine_market_data_assessment(
    assessment: MarketDataIntegrityAssessment,
    *,
    quarantine_id: MarketDataQuarantineId,
    quarantined_at: datetime,
    evidence_ref: HostingReliabilityEvidenceReference,
) -> Result[MarketDataQuarantineRecord, MarketDataIntegrityError]:
    """Record quarantine evidence; never repairs, rewrites or replaces the snapshot."""

    if not isinstance(assessment, MarketDataIntegrityAssessment):
        return Failure(
            MarketDataIntegrityValidationError(
                "assessment must be MarketDataIntegrityAssessment"
            )
        )
    if assessment.disposition is not MarketDataIntegrityDisposition.QUARANTINE:
        return Failure(
            MarketDataIntegrityQuarantineError(
                "only QUARANTINE disposition may create quarantine record"
            )
        )
    try:
        quarantine = MarketDataQuarantineRecord(
            quarantine_id=quarantine_id,
            state=MarketDataIntegrityState.QUARANTINED,
            origin_state=assessment.state,
            assessment_id=assessment.assessment_id,
            snapshot=assessment.record.snapshot,
            quarantined_at=quarantined_at,
            evidence_ref=evidence_ref,
        )
    except MarketDataIntegrityValidationError as error:
        return Failure(error)
    return Success(quarantine)
