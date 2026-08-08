from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite
from re import fullmatch
from uuid import UUID

from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import (
    ExecutiveAttentionLevel,
    ExecutivePolicyVersionRef,
    ExecutiveProjectionMetadata,
    ExecutiveReadModelValidationError,
)


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveReadModelValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveReadModelValidationError(f"{field_name} must be timezone-aware")


def _validate_canonical_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._:/-]*", value) is None:
        raise ExecutiveReadModelValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    return value


def _validated_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ExecutiveReadModelValidationError(f"{field_name} must be an immutable tuple")
    normalized = tuple(
        _validate_canonical_text(value, field_name=field_name) for value in values
    )
    if not normalized:
        raise ExecutiveReadModelValidationError(f"{field_name} must not be empty")
    if len(set(normalized)) != len(normalized):
        raise ExecutiveReadModelValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validated_evidence_refs(
    values: tuple[ExecutiveEvidenceRef, ...],
    *,
    field_name: str,
    require_non_empty: bool,
) -> tuple[ExecutiveEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, ExecutiveEvidenceRef) for item in values
    ):
        raise ExecutiveReadModelValidationError(
            f"{field_name} must be an immutable tuple of ExecutiveEvidenceRef"
        )
    if require_non_empty and not values:
        raise ExecutiveReadModelValidationError(f"{field_name} must not be empty")
    if len(set(values)) != len(values):
        raise ExecutiveReadModelValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class ExecutiveValidationAssessmentRef:
    """Explicit identity of a Validation Lab assessment projection."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveReadModelValidationError(
                "validation assessment ref requires UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveValidationSubjectRef:
    """Opaque sanitized reference to the subject being validated."""

    value: str

    def __post_init__(self) -> None:
        _validate_canonical_text(self.value, field_name="validation subject ref")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class ExecutiveValidationVerdict(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExecutiveValidationConfidence:
    """Finite validation confidence projection independent from internal specialist types."""

    value: float

    def __post_init__(self) -> None:
        if type(self.value) is not float or not isfinite(self.value):
            raise ExecutiveReadModelValidationError(
                "validation confidence must be a finite float"
            )
        if not 0.0 <= self.value <= 1.0:
            raise ExecutiveReadModelValidationError(
                "validation confidence must be between 0.0 and 1.0"
            )

    def logical_values(self) -> tuple[float, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveValidationAssessmentSummary:
    """Evidence-backed validation result without retaining internal SpecialistAnalysis."""

    assessment_ref: ExecutiveValidationAssessmentRef
    subject_ref: ExecutiveValidationSubjectRef
    policy_version: ExecutivePolicyVersionRef
    verdict: ExecutiveValidationVerdict
    observed_confidence: ExecutiveValidationConfidence | None
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.assessment_ref, ExecutiveValidationAssessmentRef):
            raise ExecutiveReadModelValidationError(
                "validation summary requires ExecutiveValidationAssessmentRef"
            )
        if not isinstance(self.subject_ref, ExecutiveValidationSubjectRef):
            raise ExecutiveReadModelValidationError(
                "validation summary requires ExecutiveValidationSubjectRef"
            )
        if not isinstance(self.policy_version, ExecutivePolicyVersionRef):
            raise ExecutiveReadModelValidationError(
                "validation summary requires ExecutivePolicyVersionRef"
            )
        if not isinstance(self.verdict, ExecutiveValidationVerdict):
            raise ExecutiveReadModelValidationError(
                "validation summary requires ExecutiveValidationVerdict"
            )
        if self.observed_confidence is not None and not isinstance(
            self.observed_confidence,
            ExecutiveValidationConfidence,
        ):
            raise ExecutiveReadModelValidationError(
                "observed validation confidence must be ExecutiveValidationConfidence or None"
            )
        if self.verdict in {
            ExecutiveValidationVerdict.PASSED,
            ExecutiveValidationVerdict.FAILED,
        } and self.observed_confidence is None:
            raise ExecutiveReadModelValidationError(
                "passed or failed validation requires observed confidence"
            )
        object.__setattr__(
            self,
            "reason_codes",
            _validated_codes(self.reason_codes, field_name="validation reason codes"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(
                self.evidence_refs,
                field_name="validation evidence refs",
                require_non_empty=True,
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.assessment_ref.logical_values(),
            self.subject_ref.logical_values(),
            self.policy_version.logical_values(),
            self.verdict.value,
            (
                self.observed_confidence.logical_values()
                if self.observed_confidence is not None
                else None
            ),
            self.reason_codes,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveValidationLabReadModel:
    """Stable VALIDATION_LAB projection for executive clients."""

    metadata: ExecutiveProjectionMetadata
    attention: ExecutiveAttentionLevel
    assessments: tuple[ExecutiveValidationAssessmentSummary, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ExecutiveProjectionMetadata):
            raise ExecutiveReadModelValidationError(
                "validation lab read model requires ExecutiveProjectionMetadata"
            )
        if self.metadata.scope is not ExecutiveReadScope.VALIDATION_LAB:
            raise ExecutiveReadModelValidationError(
                "validation lab projection requires VALIDATION_LAB scope"
            )
        if not isinstance(self.attention, ExecutiveAttentionLevel):
            raise ExecutiveReadModelValidationError(
                "validation lab projection requires ExecutiveAttentionLevel"
            )
        if not isinstance(self.assessments, tuple) or any(
            not isinstance(item, ExecutiveValidationAssessmentSummary)
            for item in self.assessments
        ):
            raise ExecutiveReadModelValidationError(
                "validation assessments must be an immutable tuple of summaries"
            )
        identities = tuple(item.assessment_ref.value for item in self.assessments)
        if len(set(identities)) != len(identities):
            raise ExecutiveReadModelValidationError(
                "validation lab projection must not contain duplicate assessments"
            )
        object.__setattr__(
            self,
            "assessments",
            tuple(sorted(self.assessments, key=lambda item: str(item.assessment_ref.value))),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.logical_values(),
            self.attention.value,
            tuple(item.logical_values() for item in self.assessments),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveTradeForensicCaseId:
    """Explicit identity of an executive trade-forensics case."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveReadModelValidationError(
                "trade forensic case id requires UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveTradeRef:
    """Opaque public trade reference without broker/account identity."""

    value: str

    def __post_init__(self) -> None:
        _validate_canonical_text(self.value, field_name="executive trade ref")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class ExecutiveTradeForensicState(StrEnum):
    OPEN = "open"
    CONCLUDED = "concluded"
    INCONCLUSIVE = "inconclusive"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExecutiveTradeForensicCase:
    """Structured forensic conclusion with support and counter-evidence."""

    case_id: ExecutiveTradeForensicCaseId
    trade_ref: ExecutiveTradeRef
    opened_at: datetime
    concluded_at: datetime | None
    state: ExecutiveTradeForensicState
    outcome_code: str
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]
    counter_evidence_refs: tuple[ExecutiveEvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, ExecutiveTradeForensicCaseId):
            raise ExecutiveReadModelValidationError(
                "trade forensic case requires ExecutiveTradeForensicCaseId"
            )
        if not isinstance(self.trade_ref, ExecutiveTradeRef):
            raise ExecutiveReadModelValidationError(
                "trade forensic case requires ExecutiveTradeRef"
            )
        _validate_aware_datetime(self.opened_at, field_name="forensic opened_at")
        if self.concluded_at is not None:
            _validate_aware_datetime(self.concluded_at, field_name="forensic concluded_at")
            if self.concluded_at < self.opened_at:
                raise ExecutiveReadModelValidationError(
                    "forensic conclusion must not predate case opening"
                )
        if not isinstance(self.state, ExecutiveTradeForensicState):
            raise ExecutiveReadModelValidationError(
                "trade forensic case requires ExecutiveTradeForensicState"
            )
        if self.state is ExecutiveTradeForensicState.OPEN and self.concluded_at is not None:
            raise ExecutiveReadModelValidationError(
                "open forensic case must not have concluded_at"
            )
        if self.state in {
            ExecutiveTradeForensicState.CONCLUDED,
            ExecutiveTradeForensicState.INCONCLUSIVE,
        } and self.concluded_at is None:
            raise ExecutiveReadModelValidationError(
                "concluded or inconclusive forensic case requires concluded_at"
            )
        object.__setattr__(
            self,
            "outcome_code",
            _validate_canonical_text(self.outcome_code, field_name="forensic outcome code"),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _validated_codes(self.reason_codes, field_name="forensic reason codes"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(
                self.evidence_refs,
                field_name="forensic evidence refs",
                require_non_empty=True,
            ),
        )
        object.__setattr__(
            self,
            "counter_evidence_refs",
            _validated_evidence_refs(
                self.counter_evidence_refs,
                field_name="forensic counter-evidence refs",
                require_non_empty=False,
            ),
        )
        if set(self.evidence_refs) & set(self.counter_evidence_refs):
            raise ExecutiveReadModelValidationError(
                "forensic supporting and counter-evidence refs must be distinct"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.case_id.logical_values(),
            self.trade_ref.logical_values(),
            self.opened_at.isoformat(),
            self.concluded_at.isoformat() if self.concluded_at is not None else None,
            self.state.value,
            self.outcome_code,
            self.reason_codes,
            tuple(item.logical_values() for item in self.evidence_refs),
            tuple(item.logical_values() for item in self.counter_evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveTradeForensicsReadModel:
    """Stable TRADE_FORENSICS projection for executive clients."""

    metadata: ExecutiveProjectionMetadata
    attention: ExecutiveAttentionLevel
    cases: tuple[ExecutiveTradeForensicCase, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ExecutiveProjectionMetadata):
            raise ExecutiveReadModelValidationError(
                "trade forensics read model requires ExecutiveProjectionMetadata"
            )
        if self.metadata.scope is not ExecutiveReadScope.TRADE_FORENSICS:
            raise ExecutiveReadModelValidationError(
                "trade forensics projection requires TRADE_FORENSICS scope"
            )
        if not isinstance(self.attention, ExecutiveAttentionLevel):
            raise ExecutiveReadModelValidationError(
                "trade forensics projection requires ExecutiveAttentionLevel"
            )
        if not isinstance(self.cases, tuple) or any(
            not isinstance(item, ExecutiveTradeForensicCase) for item in self.cases
        ):
            raise ExecutiveReadModelValidationError(
                "forensic cases must be an immutable tuple of ExecutiveTradeForensicCase"
            )
        identities = tuple(item.case_id.value for item in self.cases)
        if len(set(identities)) != len(identities):
            raise ExecutiveReadModelValidationError(
                "trade forensics projection must not contain duplicate case ids"
            )
        object.__setattr__(
            self,
            "cases",
            tuple(sorted(self.cases, key=lambda item: str(item.case_id.value))),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.logical_values(),
            self.attention.value,
            tuple(item.logical_values() for item in self.cases),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveAuditRecordId:
    """Explicit identity of one executive audit record."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveReadModelValidationError("executive audit record id requires UUID")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveAuditCorrelationId:
    """Explicit correlation identity carried into the public audit surface."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveReadModelValidationError(
                "executive audit correlation id requires UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class ExecutiveAuditOutcome(StrEnum):
    APPLIED = "applied"
    REJECTED = "rejected"
    NO_ACTION = "no-action"
    OBSERVED = "observed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExecutiveAuditRecord:
    """Structured audit record without raw log, secret, or arbitrary payload exposure."""

    record_id: ExecutiveAuditRecordId
    occurred_at: datetime
    correlation_id: ExecutiveAuditCorrelationId
    actor_code: str
    category_code: str
    action_code: str
    outcome: ExecutiveAuditOutcome
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, ExecutiveAuditRecordId):
            raise ExecutiveReadModelValidationError(
                "audit record requires ExecutiveAuditRecordId"
            )
        _validate_aware_datetime(self.occurred_at, field_name="audit occurred_at")
        if not isinstance(self.correlation_id, ExecutiveAuditCorrelationId):
            raise ExecutiveReadModelValidationError(
                "audit record requires ExecutiveAuditCorrelationId"
            )
        object.__setattr__(
            self,
            "actor_code",
            _validate_canonical_text(self.actor_code, field_name="audit actor code"),
        )
        object.__setattr__(
            self,
            "category_code",
            _validate_canonical_text(self.category_code, field_name="audit category code"),
        )
        object.__setattr__(
            self,
            "action_code",
            _validate_canonical_text(self.action_code, field_name="audit action code"),
        )
        if not isinstance(self.outcome, ExecutiveAuditOutcome):
            raise ExecutiveReadModelValidationError(
                "audit record requires ExecutiveAuditOutcome"
            )
        object.__setattr__(
            self,
            "reason_codes",
            _validated_codes(self.reason_codes, field_name="audit reason codes"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(
                self.evidence_refs,
                field_name="audit evidence refs",
                require_non_empty=True,
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.record_id.logical_values(),
            self.occurred_at.isoformat(),
            self.correlation_id.logical_values(),
            self.actor_code,
            self.category_code,
            self.action_code,
            self.outcome.value,
            self.reason_codes,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveAuditReadModel:
    """Stable AUDIT projection, including auditable NO_ACTION outcomes."""

    metadata: ExecutiveProjectionMetadata
    attention: ExecutiveAttentionLevel
    records: tuple[ExecutiveAuditRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ExecutiveProjectionMetadata):
            raise ExecutiveReadModelValidationError(
                "audit read model requires ExecutiveProjectionMetadata"
            )
        if self.metadata.scope is not ExecutiveReadScope.AUDIT:
            raise ExecutiveReadModelValidationError(
                "audit projection requires AUDIT scope"
            )
        if not isinstance(self.attention, ExecutiveAttentionLevel):
            raise ExecutiveReadModelValidationError(
                "audit projection requires ExecutiveAttentionLevel"
            )
        if not isinstance(self.records, tuple) or any(
            not isinstance(item, ExecutiveAuditRecord) for item in self.records
        ):
            raise ExecutiveReadModelValidationError(
                "audit records must be an immutable tuple of ExecutiveAuditRecord"
            )
        identities = tuple(item.record_id.value for item in self.records)
        if len(set(identities)) != len(identities):
            raise ExecutiveReadModelValidationError(
                "audit projection must not contain duplicate record ids"
            )
        object.__setattr__(
            self,
            "records",
            tuple(
                sorted(
                    self.records,
                    key=lambda item: (item.occurred_at, str(item.record_id.value)),
                )
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.logical_values(),
            self.attention.value,
            tuple(item.logical_values() for item in self.records),
        )
