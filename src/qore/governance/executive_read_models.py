from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.kernel.errors import DomainError


class ExecutiveReadModelError(DomainError):
    """Base error for transport-neutral executive read-model contracts."""

    __slots__ = ()


class ExecutiveReadModelValidationError(ExecutiveReadModelError):
    """An executive projection violates a deterministic public-read invariant."""

    __slots__ = ()


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveReadModelValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveReadModelValidationError(f"{field_name} must be timezone-aware")


def _validate_canonical_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._-]*", value) is None:
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
    if len(set(normalized)) != len(normalized):
        raise ExecutiveReadModelValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validated_evidence_refs(
    values: tuple[ExecutiveEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[ExecutiveEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, ExecutiveEvidenceRef) for item in values
    ):
        raise ExecutiveReadModelValidationError(
            f"{field_name} must be an immutable tuple of ExecutiveEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise ExecutiveReadModelValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class ExecutiveProjectionId:
    """Explicit identity of one immutable executive projection."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveReadModelValidationError(
                "executive projection id requires UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveProjectionVersion:
    """Version of the stable executive projection contract."""

    value: str

    def __post_init__(self) -> None:
        _validate_canonical_text(self.value, field_name="projection version")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutivePolicyVersionRef:
    """Sanitized policy-version reference included in an executive projection."""

    value: str

    def __post_init__(self) -> None:
        _validate_canonical_text(self.value, field_name="policy version reference")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class ExecutiveSourceFreshness(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


class ExecutiveAttentionLevel(StrEnum):
    INFORMATION = "information"
    ATTENTION = "attention"
    IMPORTANT = "important"
    DECISION_REQUIRED = "decision-required"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class ExecutiveProjectionMetadata:
    """Common provenance shared by every stable executive read model."""

    projection_id: ExecutiveProjectionId
    projection_version: ExecutiveProjectionVersion
    scope: ExecutiveReadScope
    source_observed_at: datetime
    projected_at: datetime
    freshness: ExecutiveSourceFreshness
    evidence_refs: tuple[ExecutiveEvidenceRef, ...] = ()
    policy_versions: tuple[ExecutivePolicyVersionRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.projection_id, ExecutiveProjectionId):
            raise ExecutiveReadModelValidationError(
                "projection metadata requires ExecutiveProjectionId"
            )
        if not isinstance(self.projection_version, ExecutiveProjectionVersion):
            raise ExecutiveReadModelValidationError(
                "projection metadata requires ExecutiveProjectionVersion"
            )
        if not isinstance(self.scope, ExecutiveReadScope):
            raise ExecutiveReadModelValidationError(
                "projection metadata requires ExecutiveReadScope"
            )
        _validate_aware_datetime(self.source_observed_at, field_name="source_observed_at")
        _validate_aware_datetime(self.projected_at, field_name="projected_at")
        if self.projected_at < self.source_observed_at:
            raise ExecutiveReadModelValidationError(
                "projection time must not predate source observation"
            )
        if not isinstance(self.freshness, ExecutiveSourceFreshness):
            raise ExecutiveReadModelValidationError(
                "projection metadata requires explicit source freshness"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(
                self.evidence_refs,
                field_name="projection evidence refs",
            ),
        )
        if not isinstance(self.policy_versions, tuple) or any(
            not isinstance(item, ExecutivePolicyVersionRef)
            for item in self.policy_versions
        ):
            raise ExecutiveReadModelValidationError(
                "policy versions must be an immutable tuple of ExecutivePolicyVersionRef"
            )
        if len(set(self.policy_versions)) != len(self.policy_versions):
            raise ExecutiveReadModelValidationError(
                "policy versions must not contain duplicates"
            )
        object.__setattr__(
            self,
            "policy_versions",
            tuple(sorted(self.policy_versions, key=lambda item: item.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.projection_id.logical_values(),
            self.projection_version.logical_values(),
            self.scope.value,
            self.source_observed_at.isoformat(),
            self.projected_at.isoformat(),
            self.freshness.value,
            tuple(item.logical_values() for item in self.evidence_refs),
            tuple(item.logical_values() for item in self.policy_versions),
        )


class ExecutiveSystemHealthState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ExecutiveReadinessState(StrEnum):
    READY = "ready"
    NOT_READY = "not-ready"
    UNKNOWN = "unknown"


class ExecutiveComponentHealthState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExecutiveComponentHealth:
    """Public component health without exposing the internal RuntimeSnapshot."""

    component_id: str
    state: ExecutiveComponentHealthState
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "component_id",
            _validate_canonical_text(self.component_id, field_name="component id"),
        )
        if not isinstance(self.state, ExecutiveComponentHealthState):
            raise ExecutiveReadModelValidationError(
                "component health requires ExecutiveComponentHealthState"
            )
        object.__setattr__(
            self,
            "reason_codes",
            _validated_codes(self.reason_codes, field_name="component reason codes"),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (self.component_id, self.state.value, self.reason_codes)


@dataclass(frozen=True, slots=True)
class ExecutiveSystemHealthReadModel:
    """Stable executive projection for the SYSTEM_HEALTH read scope."""

    metadata: ExecutiveProjectionMetadata
    health: ExecutiveSystemHealthState
    readiness: ExecutiveReadinessState
    attention: ExecutiveAttentionLevel
    reason_codes: tuple[str, ...]
    components: tuple[ExecutiveComponentHealth, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ExecutiveProjectionMetadata):
            raise ExecutiveReadModelValidationError(
                "system health read model requires ExecutiveProjectionMetadata"
            )
        if self.metadata.scope is not ExecutiveReadScope.SYSTEM_HEALTH:
            raise ExecutiveReadModelValidationError(
                "system health projection requires SYSTEM_HEALTH scope"
            )
        if not isinstance(self.health, ExecutiveSystemHealthState):
            raise ExecutiveReadModelValidationError(
                "system health requires ExecutiveSystemHealthState"
            )
        if not isinstance(self.readiness, ExecutiveReadinessState):
            raise ExecutiveReadModelValidationError(
                "system health requires ExecutiveReadinessState"
            )
        if not isinstance(self.attention, ExecutiveAttentionLevel):
            raise ExecutiveReadModelValidationError(
                "system health requires ExecutiveAttentionLevel"
            )
        object.__setattr__(
            self,
            "reason_codes",
            _validated_codes(self.reason_codes, field_name="system health reason codes"),
        )
        if not isinstance(self.components, tuple) or any(
            not isinstance(item, ExecutiveComponentHealth) for item in self.components
        ):
            raise ExecutiveReadModelValidationError(
                "system components must be an immutable tuple of ExecutiveComponentHealth"
            )
        component_ids = tuple(item.component_id for item in self.components)
        if len(set(component_ids)) != len(component_ids):
            raise ExecutiveReadModelValidationError(
                "system components must not contain duplicate component ids"
            )
        object.__setattr__(
            self,
            "components",
            tuple(sorted(self.components, key=lambda item: item.component_id)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.logical_values(),
            self.health.value,
            self.readiness.value,
            self.attention.value,
            self.reason_codes,
            tuple(item.logical_values() for item in self.components),
        )


class ExecutiveCiboOperationalState(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class ExecutiveCiboJudgment(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    HOLD = "hold"
    NO_ACTION = "no-action"
    UNKNOWN = "unknown"


class ExecutiveCiboConfidenceState(StrEnum):
    CONFIDENT = "confident"
    CAUTIOUS = "cautious"
    UNCERTAIN = "uncertain"
    CONCERNED = "concerned"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ExecutiveUncertaintyState(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"


class ExecutiveCiboAuthorizationState(StrEnum):
    AUTHORIZED = "authorized"
    NOT_AUTHORIZED = "not-authorized"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not-applicable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExecutiveCiboReadModel:
    """Evidence-backed CIBO state without private chain-of-thought or mutable internals."""

    metadata: ExecutiveProjectionMetadata
    state: ExecutiveCiboOperationalState
    judgment: ExecutiveCiboJudgment
    confidence: ExecutiveCiboConfidenceState
    uncertainty: ExecutiveUncertaintyState
    attention: ExecutiveAttentionLevel
    authorization_state: ExecutiveCiboAuthorizationState
    reason_codes: tuple[str, ...]
    counter_evidence_refs: tuple[ExecutiveEvidenceRef, ...]
    risk_factor_codes: tuple[str, ...]
    recommendation_code: str

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ExecutiveProjectionMetadata):
            raise ExecutiveReadModelValidationError(
                "CIBO read model requires ExecutiveProjectionMetadata"
            )
        if self.metadata.scope is not ExecutiveReadScope.CIBO_STATE:
            raise ExecutiveReadModelValidationError(
                "CIBO projection requires CIBO_STATE scope"
            )
        if not isinstance(self.state, ExecutiveCiboOperationalState):
            raise ExecutiveReadModelValidationError(
                "CIBO projection requires ExecutiveCiboOperationalState"
            )
        if not isinstance(self.judgment, ExecutiveCiboJudgment):
            raise ExecutiveReadModelValidationError(
                "CIBO projection requires ExecutiveCiboJudgment"
            )
        if not isinstance(self.confidence, ExecutiveCiboConfidenceState):
            raise ExecutiveReadModelValidationError(
                "CIBO projection requires ExecutiveCiboConfidenceState"
            )
        if not isinstance(self.uncertainty, ExecutiveUncertaintyState):
            raise ExecutiveReadModelValidationError(
                "CIBO projection requires ExecutiveUncertaintyState"
            )
        if not isinstance(self.attention, ExecutiveAttentionLevel):
            raise ExecutiveReadModelValidationError(
                "CIBO projection requires ExecutiveAttentionLevel"
            )
        if not isinstance(self.authorization_state, ExecutiveCiboAuthorizationState):
            raise ExecutiveReadModelValidationError(
                "CIBO projection requires ExecutiveCiboAuthorizationState"
            )
        object.__setattr__(
            self,
            "reason_codes",
            _validated_codes(self.reason_codes, field_name="CIBO reason codes"),
        )
        object.__setattr__(
            self,
            "counter_evidence_refs",
            _validated_evidence_refs(
                self.counter_evidence_refs,
                field_name="CIBO counter-evidence refs",
            ),
        )
        if set(self.metadata.evidence_refs) & set(self.counter_evidence_refs):
            raise ExecutiveReadModelValidationError(
                "CIBO supporting and counter-evidence refs must be distinct"
            )
        object.__setattr__(
            self,
            "risk_factor_codes",
            _validated_codes(self.risk_factor_codes, field_name="CIBO risk factor codes"),
        )
        object.__setattr__(
            self,
            "recommendation_code",
            _validate_canonical_text(
                self.recommendation_code,
                field_name="CIBO recommendation code",
            ),
        )
        if self.judgment is not ExecutiveCiboJudgment.UNKNOWN and not self.metadata.evidence_refs:
            raise ExecutiveReadModelValidationError(
                "non-unknown CIBO judgment requires supporting evidence refs"
            )
        if self.judgment is not ExecutiveCiboJudgment.UNKNOWN and not self.reason_codes:
            raise ExecutiveReadModelValidationError(
                "non-unknown CIBO judgment requires structured reason codes"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.logical_values(),
            self.state.value,
            self.judgment.value,
            self.confidence.value,
            self.uncertainty.value,
            self.attention.value,
            self.authorization_state.value,
            self.reason_codes,
            tuple(item.logical_values() for item in self.counter_evidence_refs),
            self.risk_factor_codes,
            self.recommendation_code,
        )
