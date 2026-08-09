from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.client_accounts import (
    ExecutionRuntimeReference,
    TradingAccountId,
)
from qore.infrastructure.hosting_reliability_lab import (
    HostingReliabilityAssessment,
    HostingReliabilityAssessmentId,
    HostingReliabilityBoundary,
    HostingReliabilityCondition,
    HostingReliabilityEvidenceReference,
    HostingReliabilityInfrastructureAction,
    HostingReliabilityObservation,
    HostingReliabilityObservationId,
    HostingReliabilityPolicyReference,
    HostingReliabilityPolicySnapshot,
    HostingReliabilityRationaleCode,
    HostingReliabilitySeverity,
    assess_hosting_reliability_observation,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_BASIS_POINTS = 10_000
PROVISIONAL_CATASTROPHIC_HARD_CEILING_US = 300_000


class HostingLatencySafetyError(InfrastructureError):
    """Base error for Hosting latency safety envelope contracts."""

    __slots__ = ()


class HostingLatencySafetyValidationError(HostingLatencySafetyError):
    """Violation of a latency distribution/envelope invariant."""

    __slots__ = ()


class HostingLatencySafetyAuthorizationError(HostingLatencySafetyError):
    """Latency evidence could not produce the required policy-bound Lab intent."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise HostingLatencySafetyValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostingLatencySafetyValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True, order=True)
class HostingLatencyDuration:
    """Deterministic latency duration expressed as integer microseconds."""

    microseconds: int

    def __post_init__(self) -> None:
        if type(self.microseconds) is not int or self.microseconds < 0:
            raise HostingLatencySafetyValidationError(
                "latency microseconds must be a non-negative integer"
            )

    @classmethod
    def from_milliseconds(cls, milliseconds: int) -> HostingLatencyDuration:
        if type(milliseconds) is not int or milliseconds < 0:
            raise HostingLatencySafetyValidationError(
                "latency milliseconds must be a non-negative integer"
            )
        return cls(milliseconds * 1_000)

    def scaled_basis_points(self, basis_points: int) -> HostingLatencyDuration:
        if type(basis_points) is not int or basis_points <= 0:
            raise HostingLatencySafetyValidationError(
                "latency scale basis_points must be a positive integer"
            )
        return HostingLatencyDuration(
            self.microseconds * basis_points // _BASIS_POINTS
        )

    def logical_values(self) -> tuple[int, ...]:
        return (self.microseconds,)


PROVISIONAL_CATASTROPHIC_HARD_CEILING = HostingLatencyDuration(
    PROVISIONAL_CATASTROPHIC_HARD_CEILING_US
)

_LATENCY_BOUNDARIES = frozenset(
    {
        HostingReliabilityBoundary.NETWORK_INGRESS,
        HostingReliabilityBoundary.INTERNAL_PIPELINE,
        HostingReliabilityBoundary.NETWORK_EGRESS,
        HostingReliabilityBoundary.ROUND_TRIP,
    }
)


@dataclass(frozen=True, slots=True)
class HostingLatencyDistribution:
    """Immutable latency-window distribution for one account/runtime/path."""

    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    boundary: HostingReliabilityBoundary
    sample_count: int
    minimum: HostingLatencyDuration
    p50: HostingLatencyDuration
    p95: HostingLatencyDuration
    p99: HostingLatencyDuration
    maximum: HostingLatencyDuration
    jitter: HostingLatencyDuration
    window_started_at: datetime
    window_ended_at: datetime
    evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, TradingAccountId):
            raise HostingLatencySafetyValidationError(
                "latency account_id must be TradingAccountId"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise HostingLatencySafetyValidationError(
                "latency runtime_ref must be ExecutionRuntimeReference"
            )
        if self.boundary not in _LATENCY_BOUNDARIES:
            raise HostingLatencySafetyValidationError(
                "latency boundary must be ingress/internal/egress/round_trip"
            )
        if type(self.sample_count) is not int or self.sample_count <= 0:
            raise HostingLatencySafetyValidationError(
                "latency sample_count must be a positive integer"
            )
        durations = (
            self.minimum,
            self.p50,
            self.p95,
            self.p99,
            self.maximum,
            self.jitter,
        )
        if any(not isinstance(value, HostingLatencyDuration) for value in durations):
            raise HostingLatencySafetyValidationError(
                "latency distribution values must be HostingLatencyDuration"
            )
        if not (
            self.minimum <= self.p50 <= self.p95 <= self.p99 <= self.maximum
        ):
            raise HostingLatencySafetyValidationError(
                "latency distribution must satisfy min <= p50 <= p95 <= p99 <= max"
            )
        _validate_timestamp(
            self.window_started_at,
            field_name="latency window_started_at",
        )
        _validate_timestamp(
            self.window_ended_at,
            field_name="latency window_ended_at",
        )
        if self.window_ended_at <= self.window_started_at:
            raise HostingLatencySafetyValidationError(
                "latency window_ended_at must be after window_started_at"
            )
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise HostingLatencySafetyValidationError(
                "latency evidence_ref must be HostingReliabilityEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            self.boundary.value,
            self.sample_count,
            self.minimum.logical_values(),
            self.p50.logical_values(),
            self.p95.logical_values(),
            self.p99.logical_values(),
            self.maximum.logical_values(),
            self.jitter.logical_values(),
            self.window_started_at.isoformat(),
            self.window_ended_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class HostingLatencyBaseline:
    """Evidence-backed certified normal valley used for relative deterioration."""

    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    boundary: HostingReliabilityBoundary
    reference_p50: HostingLatencyDuration
    reference_p95: HostingLatencyDuration
    reference_p99: HostingLatencyDuration
    certified_at: datetime
    evidence_ref: HostingReliabilityEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.account_id, TradingAccountId):
            raise HostingLatencySafetyValidationError(
                "latency baseline account_id must be TradingAccountId"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise HostingLatencySafetyValidationError(
                "latency baseline runtime_ref must be ExecutionRuntimeReference"
            )
        if self.boundary not in _LATENCY_BOUNDARIES:
            raise HostingLatencySafetyValidationError(
                "latency baseline boundary must be ingress/internal/egress/round_trip"
            )
        values = (self.reference_p50, self.reference_p95, self.reference_p99)
        if any(not isinstance(value, HostingLatencyDuration) for value in values):
            raise HostingLatencySafetyValidationError(
                "latency baseline values must be HostingLatencyDuration"
            )
        if not self.reference_p50 <= self.reference_p95 <= self.reference_p99:
            raise HostingLatencySafetyValidationError(
                "latency baseline must satisfy p50 <= p95 <= p99"
            )
        if self.reference_p99.microseconds <= 0:
            raise HostingLatencySafetyValidationError(
                "latency baseline reference_p99 must be positive"
            )
        _validate_timestamp(self.certified_at, field_name="latency baseline certified_at")
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise HostingLatencySafetyValidationError(
                "latency baseline evidence_ref must be HostingReliabilityEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            self.boundary.value,
            self.reference_p50.logical_values(),
            self.reference_p95.logical_values(),
            self.reference_p99.logical_values(),
            self.certified_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class HostingLatencyEnvelopePolicy:
    """Absolute + relative latency thresholds; thresholds do not self-authorize actions."""

    policy_ref: HostingReliabilityPolicyReference
    evidence_ref: HostingReliabilityEvidenceReference
    absolute_warning: HostingLatencyDuration
    absolute_degraded: HostingLatencyDuration
    catastrophic_hard_ceiling: HostingLatencyDuration
    relative_warning_basis_points: int
    relative_degraded_basis_points: int
    contain_on_degraded: bool
    effective_at: datetime
    expires_at: datetime | None

    def __post_init__(self) -> None:
        if not isinstance(self.policy_ref, HostingReliabilityPolicyReference):
            raise HostingLatencySafetyValidationError(
                "latency policy_ref must be HostingReliabilityPolicyReference"
            )
        if not isinstance(self.evidence_ref, HostingReliabilityEvidenceReference):
            raise HostingLatencySafetyValidationError(
                "latency policy evidence_ref must be HostingReliabilityEvidenceReference"
            )
        thresholds = (
            self.absolute_warning,
            self.absolute_degraded,
            self.catastrophic_hard_ceiling,
        )
        if any(not isinstance(value, HostingLatencyDuration) for value in thresholds):
            raise HostingLatencySafetyValidationError(
                "latency policy thresholds must be HostingLatencyDuration"
            )
        if not (
            self.absolute_warning
            < self.absolute_degraded
            < self.catastrophic_hard_ceiling
        ):
            raise HostingLatencySafetyValidationError(
                "latency policy requires warning < degraded < hard ceiling"
            )
        if self.catastrophic_hard_ceiling > PROVISIONAL_CATASTROPHIC_HARD_CEILING:
            raise HostingLatencySafetyValidationError(
                "non-production catastrophic hard ceiling cannot exceed 300 ms"
            )
        if (
            type(self.relative_warning_basis_points) is not int
            or type(self.relative_degraded_basis_points) is not int
            or not (
                _BASIS_POINTS
                < self.relative_warning_basis_points
                < self.relative_degraded_basis_points
            )
        ):
            raise HostingLatencySafetyValidationError(
                "relative thresholds require 10000 < warning_bps < degraded_bps"
            )
        if type(self.contain_on_degraded) is not bool:
            raise HostingLatencySafetyValidationError(
                "contain_on_degraded must be bool"
            )
        _validate_timestamp(self.effective_at, field_name="latency policy effective_at")
        if self.expires_at is not None:
            _validate_timestamp(self.expires_at, field_name="latency policy expires_at")
            if self.expires_at <= self.effective_at:
                raise HostingLatencySafetyValidationError(
                    "latency policy expires_at must be after effective_at"
                )

    def is_effective_at(self, evaluated_at: datetime) -> bool:
        _validate_timestamp(evaluated_at, field_name="latency policy evaluated_at")
        return self.effective_at <= evaluated_at and (
            self.expires_at is None or evaluated_at < self.expires_at
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.policy_ref.logical_values(),
            self.evidence_ref.logical_values(),
            self.absolute_warning.logical_values(),
            self.absolute_degraded.logical_values(),
            self.catastrophic_hard_ceiling.logical_values(),
            self.relative_warning_basis_points,
            self.relative_degraded_basis_points,
            self.contain_on_degraded,
            self.effective_at.isoformat(),
            self.expires_at.isoformat() if self.expires_at else None,
        )


class HostingLatencyEnvelopeState(StrEnum):
    CERTIFIED = "certified"
    WARNING = "warning"
    DEGRADED = "degraded"
    EMERGENCY = "emergency"


@dataclass(frozen=True, slots=True)
class HostingLatencyEnvelopeAssessment:
    """Latency classification composed with a policy-bound Reliability Lab assessment."""

    state: HostingLatencyEnvelopeState
    distribution: HostingLatencyDistribution
    baseline: HostingLatencyBaseline
    effective_warning: HostingLatencyDuration
    effective_degraded: HostingLatencyDuration
    catastrophic_hard_ceiling: HostingLatencyDuration
    reliability_observation: HostingReliabilityObservation
    reliability_assessment: HostingReliabilityAssessment
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.state, HostingLatencyEnvelopeState):
            raise HostingLatencySafetyValidationError(
                "latency state must be HostingLatencyEnvelopeState"
            )
        if not isinstance(self.distribution, HostingLatencyDistribution):
            raise HostingLatencySafetyValidationError(
                "latency assessment distribution must be HostingLatencyDistribution"
            )
        if not isinstance(self.baseline, HostingLatencyBaseline):
            raise HostingLatencySafetyValidationError(
                "latency assessment baseline must be HostingLatencyBaseline"
            )
        if not isinstance(self.effective_warning, HostingLatencyDuration):
            raise HostingLatencySafetyValidationError(
                "effective_warning must be HostingLatencyDuration"
            )
        if not isinstance(self.effective_degraded, HostingLatencyDuration):
            raise HostingLatencySafetyValidationError(
                "effective_degraded must be HostingLatencyDuration"
            )
        if not isinstance(self.catastrophic_hard_ceiling, HostingLatencyDuration):
            raise HostingLatencySafetyValidationError(
                "catastrophic_hard_ceiling must be HostingLatencyDuration"
            )
        if not self.effective_warning < self.effective_degraded:
            raise HostingLatencySafetyValidationError(
                "effective warning threshold must be below degraded threshold"
            )
        if not isinstance(self.reliability_observation, HostingReliabilityObservation):
            raise HostingLatencySafetyValidationError(
                "reliability_observation must be HostingReliabilityObservation"
            )
        if not isinstance(self.reliability_assessment, HostingReliabilityAssessment):
            raise HostingLatencySafetyValidationError(
                "reliability_assessment must be HostingReliabilityAssessment"
            )
        _validate_timestamp(self.evaluated_at, field_name="latency evaluated_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.state.value,
            self.distribution.logical_values(),
            self.baseline.logical_values(),
            self.effective_warning.logical_values(),
            self.effective_degraded.logical_values(),
            self.catastrophic_hard_ceiling.logical_values(),
            self.reliability_observation.logical_values(),
            self.reliability_assessment.logical_values(),
            self.evaluated_at.isoformat(),
        )


def _same_scope(
    distribution: HostingLatencyDistribution,
    baseline: HostingLatencyBaseline,
) -> bool:
    return (
        distribution.account_id == baseline.account_id
        and distribution.runtime_ref == baseline.runtime_ref
        and distribution.boundary is baseline.boundary
    )


def _effective_thresholds(
    baseline: HostingLatencyBaseline,
    policy: HostingLatencyEnvelopePolicy,
) -> tuple[HostingLatencyDuration, HostingLatencyDuration]:
    relative_warning = baseline.reference_p99.scaled_basis_points(
        policy.relative_warning_basis_points
    )
    relative_degraded = baseline.reference_p99.scaled_basis_points(
        policy.relative_degraded_basis_points
    )
    warning = min(policy.absolute_warning, relative_warning)
    degraded = min(policy.absolute_degraded, relative_degraded)
    if warning >= degraded:
        raise HostingLatencySafetyValidationError(
            "effective relative/absolute thresholds collapse warning and degraded"
        )
    return warning, degraded


def _classify_latency(
    distribution: HostingLatencyDistribution,
    policy: HostingLatencyEnvelopePolicy,
    *,
    effective_warning: HostingLatencyDuration,
    effective_degraded: HostingLatencyDuration,
) -> HostingLatencyEnvelopeState:
    if distribution.maximum >= policy.catastrophic_hard_ceiling:
        return HostingLatencyEnvelopeState.EMERGENCY
    if (
        distribution.p99 >= effective_degraded
        or distribution.maximum >= policy.absolute_degraded
    ):
        return HostingLatencyEnvelopeState.DEGRADED
    if (
        distribution.p99 >= effective_warning
        or distribution.maximum >= policy.absolute_warning
    ):
        return HostingLatencyEnvelopeState.WARNING
    return HostingLatencyEnvelopeState.CERTIFIED


def _state_semantics(
    state: HostingLatencyEnvelopeState,
    policy: HostingLatencyEnvelopePolicy,
) -> tuple[
    HostingReliabilityCondition,
    HostingReliabilitySeverity,
    HostingReliabilityInfrastructureAction,
    HostingReliabilityRationaleCode,
]:
    if state is HostingLatencyEnvelopeState.CERTIFIED:
        return (
            HostingReliabilityCondition.NORMAL,
            HostingReliabilitySeverity.INFO,
            HostingReliabilityInfrastructureAction.NO_ACTION,
            HostingReliabilityRationaleCode("latency.certified"),
        )
    if state is HostingLatencyEnvelopeState.WARNING:
        return (
            HostingReliabilityCondition.ANOMALOUS,
            HostingReliabilitySeverity.WARNING,
            HostingReliabilityInfrastructureAction.NO_ACTION,
            HostingReliabilityRationaleCode("latency.warning"),
        )
    if state is HostingLatencyEnvelopeState.DEGRADED:
        action = (
            HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK
            if policy.contain_on_degraded
            else HostingReliabilityInfrastructureAction.NO_ACTION
        )
        return (
            HostingReliabilityCondition.ANOMALOUS,
            HostingReliabilitySeverity.DEGRADED,
            action,
            HostingReliabilityRationaleCode("latency.degraded"),
        )
    return (
        HostingReliabilityCondition.ANOMALOUS,
        HostingReliabilitySeverity.CRITICAL,
        HostingReliabilityInfrastructureAction.CONTAIN_NEW_WORK,
        HostingReliabilityRationaleCode("latency.catastrophic_hard_ceiling"),
    )


def _unique_supporting_evidence(
    distribution: HostingLatencyDistribution,
    baseline: HostingLatencyBaseline,
    policy: HostingLatencyEnvelopePolicy,
) -> tuple[HostingReliabilityEvidenceReference, ...]:
    references: list[HostingReliabilityEvidenceReference] = []
    for reference in (baseline.evidence_ref, policy.evidence_ref):
        if reference != distribution.evidence_ref and reference not in references:
            references.append(reference)
    return tuple(references)


def evaluate_hosting_latency_envelope(
    distribution: HostingLatencyDistribution,
    baseline: HostingLatencyBaseline,
    envelope_policy: HostingLatencyEnvelopePolicy,
    reliability_policy: HostingReliabilityPolicySnapshot,
    *,
    observation_id: HostingReliabilityObservationId,
    assessment_id: HostingReliabilityAssessmentId,
    evaluated_at: datetime,
) -> Result[HostingLatencyEnvelopeAssessment, HostingLatencySafetyError]:
    """Classify latency and request only the evidence/policy-authorized Lab intent."""

    if not isinstance(distribution, HostingLatencyDistribution):
        return Failure(
            HostingLatencySafetyValidationError(
                "distribution must be HostingLatencyDistribution"
            )
        )
    if not isinstance(baseline, HostingLatencyBaseline):
        return Failure(
            HostingLatencySafetyValidationError(
                "baseline must be HostingLatencyBaseline"
            )
        )
    if not isinstance(envelope_policy, HostingLatencyEnvelopePolicy):
        return Failure(
            HostingLatencySafetyValidationError(
                "envelope_policy must be HostingLatencyEnvelopePolicy"
            )
        )
    if not isinstance(reliability_policy, HostingReliabilityPolicySnapshot):
        return Failure(
            HostingLatencySafetyValidationError(
                "reliability_policy must be HostingReliabilityPolicySnapshot"
            )
        )
    try:
        _validate_timestamp(evaluated_at, field_name="latency evaluated_at")
    except HostingLatencySafetyValidationError as error:
        return Failure(error)
    if evaluated_at < distribution.window_ended_at:
        return Failure(
            HostingLatencySafetyValidationError(
                "latency evaluation cannot predate distribution window end"
            )
        )
    if not _same_scope(distribution, baseline):
        return Failure(
            HostingLatencySafetyValidationError(
                "latency distribution and baseline scope must match exactly"
            )
        )
    if not envelope_policy.is_effective_at(evaluated_at):
        return Failure(
            HostingLatencySafetyAuthorizationError(
                "latency envelope policy is not effective at evaluation time"
            )
        )
    try:
        effective_warning, effective_degraded = _effective_thresholds(
            baseline,
            envelope_policy,
        )
    except HostingLatencySafetyValidationError as error:
        return Failure(error)
    state = _classify_latency(
        distribution,
        envelope_policy,
        effective_warning=effective_warning,
        effective_degraded=effective_degraded,
    )
    condition, severity, action, rationale = _state_semantics(
        state,
        envelope_policy,
    )
    try:
        observation = HostingReliabilityObservation(
            observation_id=observation_id,
            account_id=distribution.account_id,
            runtime_ref=distribution.runtime_ref,
            boundary=distribution.boundary,
            condition=condition,
            severity=severity,
            observed_at=distribution.window_ended_at,
            evidence_ref=distribution.evidence_ref,
        )
    except Exception as error:
        return Failure(HostingLatencySafetyValidationError(str(error)))
    reliability_assessment = assess_hosting_reliability_observation(
        observation,
        reliability_policy,
        assessment_id=assessment_id,
        authorized_action=action,
        rationale_code=rationale,
        assessed_at=evaluated_at,
        supporting_evidence_refs=_unique_supporting_evidence(
            distribution,
            baseline,
            envelope_policy,
        ),
    )
    if isinstance(reliability_assessment, Failure):
        return Failure(
            HostingLatencySafetyAuthorizationError(
                f"Reliability Lab rejected latency intent: {reliability_assessment.error}"
            )
        )
    try:
        assessment = HostingLatencyEnvelopeAssessment(
            state=state,
            distribution=distribution,
            baseline=baseline,
            effective_warning=effective_warning,
            effective_degraded=effective_degraded,
            catastrophic_hard_ceiling=envelope_policy.catastrophic_hard_ceiling,
            reliability_observation=observation,
            reliability_assessment=reliability_assessment.value,
            evaluated_at=evaluated_at,
        )
    except HostingLatencySafetyValidationError as error:
        return Failure(error)
    return Success(assessment)


def recalibrate_hosting_latency_baseline(
    assessment: HostingLatencyEnvelopeAssessment,
    *,
    certified_at: datetime,
    evidence_ref: HostingReliabilityEvidenceReference,
) -> Result[HostingLatencyBaseline, HostingLatencySafetyError]:
    """Recalibrate the normal valley only from an already CERTIFIED assessment."""

    if not isinstance(assessment, HostingLatencyEnvelopeAssessment):
        return Failure(
            HostingLatencySafetyValidationError(
                "assessment must be HostingLatencyEnvelopeAssessment"
            )
        )
    if assessment.state is not HostingLatencyEnvelopeState.CERTIFIED:
        return Failure(
            HostingLatencySafetyAuthorizationError(
                "only CERTIFIED latency evidence may recalibrate the baseline"
            )
        )
    try:
        _validate_timestamp(certified_at, field_name="baseline certified_at")
    except HostingLatencySafetyValidationError as error:
        return Failure(error)
    if certified_at < assessment.evaluated_at:
        return Failure(
            HostingLatencySafetyValidationError(
                "baseline certification cannot predate latency assessment"
            )
        )
    distribution = assessment.distribution
    try:
        baseline = HostingLatencyBaseline(
            account_id=distribution.account_id,
            runtime_ref=distribution.runtime_ref,
            boundary=distribution.boundary,
            reference_p50=distribution.p50,
            reference_p95=distribution.p95,
            reference_p99=distribution.p99,
            certified_at=certified_at,
            evidence_ref=evidence_ref,
        )
    except HostingLatencySafetyValidationError as error:
        return Failure(error)
    return Success(baseline)
