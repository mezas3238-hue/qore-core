from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.client_accounts import (
    ExecutionRuntimeReference,
    TradingAccountId,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class HostingReliabilityLabError(InfrastructureError):
    """Base error for Hosting Reliability Lab contracts."""

    __slots__ = ()


class HostingReliabilityLabValidationError(HostingReliabilityLabError):
    """Violation of a Hosting Reliability Lab invariant."""

    __slots__ = ()


class HostingReliabilityLabAuthorizationError(HostingReliabilityLabError):
    """Requested infrastructure action is not authorized by reliability evidence/policy."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HostingReliabilityLabValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostingReliabilityLabValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise HostingReliabilityLabValidationError(f"{field_name} must be UUID")


def _validate_text(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise HostingReliabilityLabValidationError(
            f"{field_name} must be a non-empty string"
        )


@dataclass(frozen=True, slots=True)
class HostingReliabilityObservationId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="reliability observation id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingReliabilityAssessmentId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="reliability assessment id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingReliabilityActionId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="reliability action id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingReliabilityEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="reliability evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingReliabilityPolicyReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="reliability policy reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class HostingReliabilityRationaleCode:
    value: str

    def __post_init__(self) -> None:
        _validate_text(self.value, field_name="reliability rationale code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class HostingReliabilityBoundary(StrEnum):
    RUNTIME = "runtime"
    NETWORK_INGRESS = "network_ingress"
    INTERNAL_PIPELINE = "internal_pipeline"
    NETWORK_EGRESS = "network_egress"
    ROUND_TRIP = "round_trip"
    MARKET_DATA = "market_data"
    AVAILABILITY_FAILOVER = "availability_failover"


class HostingReliabilityCondition(StrEnum):
    NORMAL = "normal"
    ANOMALOUS = "anomalous"
    UNKNOWN = "unknown"


class HostingReliabilitySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class HostingReliabilityInfrastructureAction(StrEnum):
    """Lab-authorized infrastructure intent; never a trading action or lease mutation."""

    NO_ACTION = "no_action"
    CONTAIN_NEW_WORK = "contain_new_work"
    RUN_STABILIZATION = "run_stabilization"
    INITIATE_FAILOVER_EVALUATION = "initiate_failover_evaluation"


class HostingReliabilityActionOutcome(StrEnum):
    NO_ACTION_RECORDED = "no_action_recorded"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class HostingReliabilityObservation:
    """Immutable observed reliability fact bound to one account/runtime/boundary."""

    observation_id: HostingReliabilityObservationId
    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    boundary: HostingReliabilityBoundary
    condition: HostingReliabilityCondition
    severity: HostingReliabilitySeverity
    observed_at: datetime
    evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, HostingReliabilityObservationId):
            raise HostingReliabilityLabValidationError(
                "observation_id must be HostingReliabilityObservationId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise HostingReliabilityLabValidationError(
                "observation account_id must be TradingAccountId"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise HostingReliabilityLabValidationError(
                "observation runtime_ref must be ExecutionRuntimeReference"
            )
        if not isinstance(self.boundary, HostingReliabilityBoundary):
            raise HostingReliabilityLabValidationError(
                "observation boundary must be HostingReliabilityBoundary"
            )
        if not isinstance(self.condition, HostingReliabilityCondition):
            raise HostingReliabilityLabValidationError(
                "observation condition must be HostingReliabilityCondition"
            )
        if not isinstance(self.severity, HostingReliabilitySeverity):
            raise HostingReliabilityLabValidationError(
                "observation severity must be HostingReliabilitySeverity"
            )
        _validate_timestamp(self.observed_at, field_name="observation observed_at")
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise HostingReliabilityLabValidationError(
                "observation evidence_ref must be HostingReliabilityEvidenceReference"
            )
        if self.condition is HostingReliabilityCondition.NORMAL and self.severity not in {
            HostingReliabilitySeverity.INFO,
            HostingReliabilitySeverity.WARNING,
        }:
            raise HostingReliabilityLabValidationError(
                "NORMAL observation cannot carry degraded/critical/unknown severity"
            )
        if (
            self.condition is HostingReliabilityCondition.UNKNOWN
            and self.severity is not HostingReliabilitySeverity.UNKNOWN
        ):
            raise HostingReliabilityLabValidationError(
                "UNKNOWN observation requires UNKNOWN severity"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.observation_id.logical_values(),
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            self.boundary.value,
            self.condition.value,
            self.severity.value,
            self.observed_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class HostingReliabilityPolicySnapshot:
    """Versioned authorization policy for Reliability Lab infrastructure intents."""

    policy_ref: HostingReliabilityPolicyReference
    version: int
    allowed_actions: tuple[HostingReliabilityInfrastructureAction, ...]
    effective_at: datetime
    expires_at: datetime | None

    def __post_init__(self) -> None:
        if not isinstance(self.policy_ref, HostingReliabilityPolicyReference):
            raise HostingReliabilityLabValidationError(
                "policy_ref must be HostingReliabilityPolicyReference"
            )
        if type(self.version) is not int or self.version <= 0:
            raise HostingReliabilityLabValidationError(
                "reliability policy version must be a positive integer"
            )
        if not isinstance(self.allowed_actions, tuple) or any(
            not isinstance(action, HostingReliabilityInfrastructureAction)
            for action in self.allowed_actions
        ):
            raise HostingReliabilityLabValidationError(
                "allowed_actions must be an immutable reliability action tuple"
            )
        if len(self.allowed_actions) != len(set(self.allowed_actions)):
            raise HostingReliabilityLabValidationError(
                "reliability policy actions must be unique"
            )
        if HostingReliabilityInfrastructureAction.NO_ACTION not in self.allowed_actions:
            raise HostingReliabilityLabValidationError(
                "reliability policy must allow evidence-backed NO_ACTION"
            )
        _validate_timestamp(self.effective_at, field_name="policy effective_at")
        if self.expires_at is not None:
            _validate_timestamp(self.expires_at, field_name="policy expires_at")
            if self.expires_at <= self.effective_at:
                raise HostingReliabilityLabValidationError(
                    "policy expires_at must be after effective_at"
                )

    def is_effective_at(self, evaluated_at: datetime) -> bool:
        _validate_timestamp(evaluated_at, field_name="policy evaluated_at")
        return self.effective_at <= evaluated_at and (
            self.expires_at is None or evaluated_at < self.expires_at
        )

    def authorizes(
        self,
        action: HostingReliabilityInfrastructureAction,
        *,
        evaluated_at: datetime,
    ) -> bool:
        if not isinstance(action, HostingReliabilityInfrastructureAction):
            return False
        return self.is_effective_at(evaluated_at) and action in self.allowed_actions

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.policy_ref.logical_values(),
            self.version,
            tuple(action.value for action in self.allowed_actions),
            self.effective_at.isoformat(),
            self.expires_at.isoformat() if self.expires_at else None,
        )


@dataclass(frozen=True, slots=True)
class HostingReliabilityAssessment:
    """Evidence + policy-bound Lab assessment; it does not execute infrastructure I/O."""

    assessment_id: HostingReliabilityAssessmentId
    observation_id: HostingReliabilityObservationId
    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    policy_ref: HostingReliabilityPolicyReference
    authorized_action: HostingReliabilityInfrastructureAction
    rationale_code: HostingReliabilityRationaleCode
    evidence_refs: tuple[HostingReliabilityEvidenceReference, ...]
    assessed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.assessment_id, HostingReliabilityAssessmentId):
            raise HostingReliabilityLabValidationError(
                "assessment_id must be HostingReliabilityAssessmentId"
            )
        if not isinstance(self.observation_id, HostingReliabilityObservationId):
            raise HostingReliabilityLabValidationError(
                "assessment observation_id must be HostingReliabilityObservationId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise HostingReliabilityLabValidationError(
                "assessment account_id must be TradingAccountId"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise HostingReliabilityLabValidationError(
                "assessment runtime_ref must be ExecutionRuntimeReference"
            )
        if not isinstance(self.policy_ref, HostingReliabilityPolicyReference):
            raise HostingReliabilityLabValidationError(
                "assessment policy_ref must be HostingReliabilityPolicyReference"
            )
        if not isinstance(
            self.authorized_action,
            HostingReliabilityInfrastructureAction,
        ):
            raise HostingReliabilityLabValidationError(
                "assessment authorized_action must be reliability infrastructure action"
            )
        if not isinstance(self.rationale_code, HostingReliabilityRationaleCode):
            raise HostingReliabilityLabValidationError(
                "assessment rationale_code must be HostingReliabilityRationaleCode"
            )
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs or any(
            not isinstance(ref, HostingReliabilityEvidenceReference)
            for ref in self.evidence_refs
        ):
            raise HostingReliabilityLabValidationError(
                "assessment requires immutable non-empty reliability evidence refs"
            )
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise HostingReliabilityLabValidationError(
                "assessment reliability evidence refs must be unique"
            )
        _validate_timestamp(self.assessed_at, field_name="assessment assessed_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.assessment_id.logical_values(),
            self.observation_id.logical_values(),
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            self.policy_ref.logical_values(),
            self.authorized_action.value,
            self.rationale_code.logical_values(),
            tuple(ref.logical_values() for ref in self.evidence_refs),
            self.assessed_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class HostingReliabilityActionRecord:
    """Result evidence for an assessment-authorized infrastructure intent."""

    action_id: HostingReliabilityActionId
    assessment_id: HostingReliabilityAssessmentId
    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    action: HostingReliabilityInfrastructureAction
    outcome: HostingReliabilityActionOutcome
    occurred_at: datetime
    evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, HostingReliabilityActionId):
            raise HostingReliabilityLabValidationError(
                "action_id must be HostingReliabilityActionId"
            )
        if not isinstance(self.assessment_id, HostingReliabilityAssessmentId):
            raise HostingReliabilityLabValidationError(
                "action assessment_id must be HostingReliabilityAssessmentId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise HostingReliabilityLabValidationError(
                "action account_id must be TradingAccountId"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise HostingReliabilityLabValidationError(
                "action runtime_ref must be ExecutionRuntimeReference"
            )
        if not isinstance(self.action, HostingReliabilityInfrastructureAction):
            raise HostingReliabilityLabValidationError(
                "action must be HostingReliabilityInfrastructureAction"
            )
        if not isinstance(self.outcome, HostingReliabilityActionOutcome):
            raise HostingReliabilityLabValidationError(
                "outcome must be HostingReliabilityActionOutcome"
            )
        _validate_timestamp(self.occurred_at, field_name="action occurred_at")
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise HostingReliabilityLabValidationError(
                "action evidence_ref must be HostingReliabilityEvidenceReference"
            )
        if self.action is HostingReliabilityInfrastructureAction.NO_ACTION:
            if self.outcome is not HostingReliabilityActionOutcome.NO_ACTION_RECORDED:
                raise HostingReliabilityLabValidationError(
                    "NO_ACTION requires NO_ACTION_RECORDED outcome"
                )
        elif self.outcome is HostingReliabilityActionOutcome.NO_ACTION_RECORDED:
            raise HostingReliabilityLabValidationError(
                "executed infrastructure action cannot use NO_ACTION_RECORDED outcome"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.action_id.logical_values(),
            self.assessment_id.logical_values(),
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            self.action.value,
            self.outcome.value,
            self.occurred_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


def assess_hosting_reliability_observation(
    observation: HostingReliabilityObservation,
    policy: HostingReliabilityPolicySnapshot,
    *,
    assessment_id: HostingReliabilityAssessmentId,
    authorized_action: HostingReliabilityInfrastructureAction,
    rationale_code: HostingReliabilityRationaleCode,
    assessed_at: datetime,
    supporting_evidence_refs: tuple[HostingReliabilityEvidenceReference, ...] = (),
) -> Result[HostingReliabilityAssessment, HostingReliabilityLabError]:
    """Create an evidence-backed policy authorization without executing infrastructure I/O."""

    if not isinstance(observation, HostingReliabilityObservation):
        return Failure(
            HostingReliabilityLabValidationError(
                "observation must be HostingReliabilityObservation"
            )
        )
    if not isinstance(policy, HostingReliabilityPolicySnapshot):
        return Failure(
            HostingReliabilityLabValidationError(
                "policy must be HostingReliabilityPolicySnapshot"
            )
        )
    try:
        _validate_timestamp(assessed_at, field_name="assessment assessed_at")
    except HostingReliabilityLabValidationError as error:
        return Failure(error)
    if assessed_at < observation.observed_at:
        return Failure(
            HostingReliabilityLabValidationError(
                "assessment cannot predate reliability observation"
            )
        )
    if not policy.authorizes(authorized_action, evaluated_at=assessed_at):
        return Failure(
            HostingReliabilityLabAuthorizationError(
                "reliability policy does not authorize requested infrastructure action"
            )
        )
    if (
        observation.condition is HostingReliabilityCondition.NORMAL
        and authorized_action is not HostingReliabilityInfrastructureAction.NO_ACTION
    ):
        return Failure(
            HostingReliabilityLabAuthorizationError(
                "NORMAL observation cannot authorize infrastructure intervention"
            )
        )
    evidence_refs = (observation.evidence_ref, *supporting_evidence_refs)
    if len(evidence_refs) != len(set(evidence_refs)):
        return Failure(
            HostingReliabilityLabValidationError(
                "assessment evidence refs must be unique"
            )
        )
    try:
        assessment = HostingReliabilityAssessment(
            assessment_id=assessment_id,
            observation_id=observation.observation_id,
            account_id=observation.account_id,
            runtime_ref=observation.runtime_ref,
            policy_ref=policy.policy_ref,
            authorized_action=authorized_action,
            rationale_code=rationale_code,
            evidence_refs=evidence_refs,
            assessed_at=assessed_at,
        )
    except HostingReliabilityLabValidationError as error:
        return Failure(error)
    return Success(assessment)


def record_hosting_reliability_action(
    assessment: HostingReliabilityAssessment,
    *,
    action_id: HostingReliabilityActionId,
    action: HostingReliabilityInfrastructureAction,
    outcome: HostingReliabilityActionOutcome,
    occurred_at: datetime,
    evidence_ref: HostingReliabilityEvidenceReference,
) -> Result[HostingReliabilityActionRecord, HostingReliabilityLabError]:
    """Record result evidence; this function performs no provider/runtime mutation."""

    if not isinstance(assessment, HostingReliabilityAssessment):
        return Failure(
            HostingReliabilityLabValidationError(
                "assessment must be HostingReliabilityAssessment"
            )
        )
    if action is not assessment.authorized_action:
        return Failure(
            HostingReliabilityLabAuthorizationError(
                "recorded action must match assessment-authorized action"
            )
        )
    try:
        _validate_timestamp(occurred_at, field_name="action occurred_at")
    except HostingReliabilityLabValidationError as error:
        return Failure(error)
    if occurred_at < assessment.assessed_at:
        return Failure(
            HostingReliabilityLabValidationError(
                "action record cannot predate reliability assessment"
            )
        )
    try:
        record = HostingReliabilityActionRecord(
            action_id=action_id,
            assessment_id=assessment.assessment_id,
            account_id=assessment.account_id,
            runtime_ref=assessment.runtime_ref,
            action=action,
            outcome=outcome,
            occurred_at=occurred_at,
            evidence_ref=evidence_ref,
        )
    except HostingReliabilityLabValidationError as error:
        return Failure(error)
    return Success(record)
