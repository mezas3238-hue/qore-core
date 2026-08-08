from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import (
    ExecutiveAttentionLevel,
    ExecutiveProjectionMetadata,
    ExecutiveReadModelValidationError,
)


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise ExecutiveReadModelValidationError(f"{field_name} requires UUID")


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9.-]*", value) is None:
        raise ExecutiveReadModelValidationError(
            f"{field_name} must use lowercase canonical syntax"
        )
    return value


def _validate_bps(value: int, *, field_name: str) -> None:
    if type(value) is not int or not 1 <= value <= 10_000:
        raise ExecutiveReadModelValidationError(
            f"{field_name} must be an integer between 1 and 10000 basis points"
        )


def _validated_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not values:
        raise ExecutiveReadModelValidationError(
            f"{field_name} must be a non-empty immutable tuple"
        )
    normalized = tuple(_validate_code(value, field_name=field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise ExecutiveReadModelValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validated_evidence_refs(
    values: tuple[ExecutiveEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[ExecutiveEvidenceRef, ...]:
    if not isinstance(values, tuple) or not values or any(
        not isinstance(item, ExecutiveEvidenceRef) for item in values
    ):
        raise ExecutiveReadModelValidationError(
            f"{field_name} must be a non-empty immutable tuple of ExecutiveEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise ExecutiveReadModelValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class ExecutivePortfolioAllocationRef:
    """Explicit reference to one logical portfolio allocation intent."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="portfolio allocation ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutivePortfolioSourceDecisionRef:
    """Explicit reference to the decision that originated an allocation intent."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="portfolio source decision ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class ExecutivePortfolioGovernanceState(StrEnum):
    PENDING_RISK = "pending-risk"
    APPROVED = "approved"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExecutivePortfolioTargetSummary:
    """Executive-safe logical allocation target expressed in basis points."""

    target_code: str
    weight_bps: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_code",
            _validate_code(self.target_code, field_name="portfolio target code"),
        )
        _validate_bps(self.weight_bps, field_name="portfolio target weight")

    def logical_values(self) -> tuple[object, ...]:
        return (self.target_code, self.weight_bps)


@dataclass(frozen=True, slots=True)
class ExecutivePortfolioAllocationSummary:
    """Projection of one logical allocation intent, not positions or broker exposure."""

    allocation_ref: ExecutivePortfolioAllocationRef
    source_decision_ref: ExecutivePortfolioSourceDecisionRef
    state: ExecutivePortfolioGovernanceState
    targets: tuple[ExecutivePortfolioTargetSummary, ...]
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.allocation_ref, ExecutivePortfolioAllocationRef):
            raise ExecutiveReadModelValidationError(
                "portfolio allocation requires ExecutivePortfolioAllocationRef"
            )
        if not isinstance(self.source_decision_ref, ExecutivePortfolioSourceDecisionRef):
            raise ExecutiveReadModelValidationError(
                "portfolio allocation requires ExecutivePortfolioSourceDecisionRef"
            )
        if self.allocation_ref.value == self.source_decision_ref.value:
            raise ExecutiveReadModelValidationError(
                "portfolio allocation and source decision identities must differ"
            )
        if not isinstance(self.state, ExecutivePortfolioGovernanceState):
            raise ExecutiveReadModelValidationError(
                "portfolio allocation requires ExecutivePortfolioGovernanceState"
            )
        if not isinstance(self.targets, tuple) or not self.targets or any(
            not isinstance(item, ExecutivePortfolioTargetSummary) for item in self.targets
        ):
            raise ExecutiveReadModelValidationError(
                "portfolio targets must be a non-empty immutable tuple of summaries"
            )
        target_codes = tuple(item.target_code for item in self.targets)
        if len(set(target_codes)) != len(target_codes):
            raise ExecutiveReadModelValidationError(
                "portfolio target codes must not contain duplicates"
            )
        if sum(item.weight_bps for item in self.targets) != 10_000:
            raise ExecutiveReadModelValidationError(
                "portfolio target weights must sum to 10000 basis points"
            )
        object.__setattr__(
            self,
            "targets",
            tuple(sorted(self.targets, key=lambda item: item.target_code)),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _validated_codes(self.reason_codes, field_name="portfolio reason codes"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(
                self.evidence_refs,
                field_name="portfolio evidence refs",
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.allocation_ref.logical_values(),
            self.source_decision_ref.logical_values(),
            self.state.value,
            tuple(item.logical_values() for item in self.targets),
            self.reason_codes,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutivePortfolioReadModel:
    """Stable PORTFOLIO read projection for logical proprietary governance state."""

    metadata: ExecutiveProjectionMetadata
    attention: ExecutiveAttentionLevel
    allocations: tuple[ExecutivePortfolioAllocationSummary, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ExecutiveProjectionMetadata):
            raise ExecutiveReadModelValidationError(
                "portfolio read model requires ExecutiveProjectionMetadata"
            )
        if self.metadata.scope is not ExecutiveReadScope.PORTFOLIO:
            raise ExecutiveReadModelValidationError(
                "portfolio projection requires PORTFOLIO scope"
            )
        if not isinstance(self.attention, ExecutiveAttentionLevel):
            raise ExecutiveReadModelValidationError(
                "portfolio projection requires ExecutiveAttentionLevel"
            )
        if not isinstance(self.allocations, tuple) or any(
            not isinstance(item, ExecutivePortfolioAllocationSummary)
            for item in self.allocations
        ):
            raise ExecutiveReadModelValidationError(
                "portfolio allocations must be an immutable tuple of summaries"
            )
        allocation_ids = tuple(item.allocation_ref.value for item in self.allocations)
        if len(set(allocation_ids)) != len(allocation_ids):
            raise ExecutiveReadModelValidationError(
                "portfolio projection must not contain duplicate allocation refs"
            )
        object.__setattr__(
            self,
            "allocations",
            tuple(sorted(self.allocations, key=lambda item: str(item.allocation_ref.value))),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.logical_values(),
            self.attention.value,
            tuple(item.logical_values() for item in self.allocations),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveRiskDecisionRef:
    """Explicit identity of one resolved risk-governance decision."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="risk decision ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveRiskPolicyRef:
    """Explicit identity of the deterministic risk policy used for an assessment."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="risk policy ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class ExecutiveRiskAssessmentOutcome(StrEnum):
    APPROVED = "approved"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class ExecutiveRiskState(StrEnum):
    CLEAR = "clear"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExecutiveRiskConcentrationAssessment:
    """Deterministic executive projection of current single-target concentration policy."""

    decision_ref: ExecutiveRiskDecisionRef
    allocation_ref: ExecutivePortfolioAllocationRef
    policy_ref: ExecutiveRiskPolicyRef
    soft_single_target_limit_bps: int
    hard_single_target_limit_bps: int
    observed_peak_weight_bps: int
    outcome: ExecutiveRiskAssessmentOutcome
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.decision_ref, ExecutiveRiskDecisionRef):
            raise ExecutiveReadModelValidationError(
                "risk assessment requires ExecutiveRiskDecisionRef"
            )
        if not isinstance(self.allocation_ref, ExecutivePortfolioAllocationRef):
            raise ExecutiveReadModelValidationError(
                "risk assessment requires ExecutivePortfolioAllocationRef"
            )
        if self.decision_ref.value == self.allocation_ref.value:
            raise ExecutiveReadModelValidationError(
                "risk decision and allocation identities must differ"
            )
        if not isinstance(self.policy_ref, ExecutiveRiskPolicyRef):
            raise ExecutiveReadModelValidationError(
                "risk assessment requires ExecutiveRiskPolicyRef"
            )
        _validate_bps(
            self.soft_single_target_limit_bps,
            field_name="risk soft single-target limit",
        )
        _validate_bps(
            self.hard_single_target_limit_bps,
            field_name="risk hard single-target limit",
        )
        _validate_bps(
            self.observed_peak_weight_bps,
            field_name="risk observed peak weight",
        )
        if self.soft_single_target_limit_bps > self.hard_single_target_limit_bps:
            raise ExecutiveReadModelValidationError(
                "risk soft limit must not exceed hard limit"
            )
        if not isinstance(self.outcome, ExecutiveRiskAssessmentOutcome):
            raise ExecutiveReadModelValidationError(
                "risk assessment requires ExecutiveRiskAssessmentOutcome"
            )
        expected = (
            ExecutiveRiskAssessmentOutcome.BLOCKED
            if self.observed_peak_weight_bps > self.hard_single_target_limit_bps
            else ExecutiveRiskAssessmentOutcome.DEGRADED
            if self.observed_peak_weight_bps > self.soft_single_target_limit_bps
            else ExecutiveRiskAssessmentOutcome.APPROVED
        )
        if self.outcome is not expected:
            raise ExecutiveReadModelValidationError(
                "risk assessment outcome must match deterministic concentration policy"
            )
        object.__setattr__(
            self,
            "reason_codes",
            _validated_codes(self.reason_codes, field_name="risk reason codes"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(
                self.evidence_refs,
                field_name="risk evidence refs",
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.decision_ref.logical_values(),
            self.allocation_ref.logical_values(),
            self.policy_ref.logical_values(),
            self.soft_single_target_limit_bps,
            self.hard_single_target_limit_bps,
            self.observed_peak_weight_bps,
            self.outcome.value,
            self.reason_codes,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveRiskReadModel:
    """Stable RISK projection; descriptive only and never an execution authority."""

    metadata: ExecutiveProjectionMetadata
    attention: ExecutiveAttentionLevel
    state: ExecutiveRiskState
    assessments: tuple[ExecutiveRiskConcentrationAssessment, ...]
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ExecutiveProjectionMetadata):
            raise ExecutiveReadModelValidationError(
                "risk read model requires ExecutiveProjectionMetadata"
            )
        if self.metadata.scope is not ExecutiveReadScope.RISK:
            raise ExecutiveReadModelValidationError("risk projection requires RISK scope")
        if not isinstance(self.attention, ExecutiveAttentionLevel):
            raise ExecutiveReadModelValidationError(
                "risk projection requires ExecutiveAttentionLevel"
            )
        if not isinstance(self.state, ExecutiveRiskState):
            raise ExecutiveReadModelValidationError(
                "risk projection requires ExecutiveRiskState"
            )
        if not isinstance(self.assessments, tuple) or any(
            not isinstance(item, ExecutiveRiskConcentrationAssessment)
            for item in self.assessments
        ):
            raise ExecutiveReadModelValidationError(
                "risk assessments must be an immutable tuple of concentration assessments"
            )
        decision_ids = tuple(item.decision_ref.value for item in self.assessments)
        if len(set(decision_ids)) != len(decision_ids):
            raise ExecutiveReadModelValidationError(
                "risk projection must not contain duplicate decision refs"
            )
        object.__setattr__(
            self,
            "assessments",
            tuple(sorted(self.assessments, key=lambda item: str(item.decision_ref.value))),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _validated_codes(self.reason_codes, field_name="risk state reason codes"),
        )
        if self.state is ExecutiveRiskState.CLEAR and any(
            item.outcome is not ExecutiveRiskAssessmentOutcome.APPROVED
            for item in self.assessments
        ):
            raise ExecutiveReadModelValidationError(
                "clear risk state cannot contain degraded or blocked assessments"
            )
        if self.state is ExecutiveRiskState.BLOCKED and not any(
            item.outcome is ExecutiveRiskAssessmentOutcome.BLOCKED
            for item in self.assessments
        ):
            raise ExecutiveReadModelValidationError(
                "blocked risk state requires at least one blocked assessment"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.logical_values(),
            self.attention.value,
            self.state.value,
            tuple(item.logical_values() for item in self.assessments),
            self.reason_codes,
        )
