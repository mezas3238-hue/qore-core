"""Immutable Trader Lab candidate lifecycle and explicit transition table.

The lifecycle enforces the mandatory governed stage chain with no ability to
skip a stage. Transitions are pure, deterministic, evidence-backed, and fail
closed. A suspended/degraded/rejected candidate can only resume through a new
candidate version (a new binding and fingerprint), never by mutating the old
chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabError,
    TraderLabValidationError,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceReference,
    TraderLabStage,
    TraderLabStageEvidenceId,
    TraderLabStageEvidenceRecord,
)
from qore.kernel.result import Failure, Result, Success


class TraderLabState(StrEnum):
    """Exact governed candidate states (no inferred promotion from names)."""

    DRAFT = "draft"
    RESEARCH_READY = "research_ready"
    REPLAY_QUALIFIED = "replay_qualified"
    FAST_FORWARD_QUALIFIED = "fast_forward_qualified"
    OOS_QUALIFIED = "oos_qualified"
    STRESS_QUALIFIED = "stress_qualified"
    MONTE_CARLO_QUALIFIED = "monte_carlo_qualified"
    RISK_REVIEWED = "risk_reviewed"
    CIBO_REVIEWED = "cibo_reviewed"
    DEMO_ELIGIBLE = "demo_eligible"
    REJECTED = "rejected"
    DEGRADED = "degraded"
    SUSPENDED = "suspended"


MANDATORY_STAGES: tuple[TraderLabStage, ...] = (
    TraderLabStage.RESEARCH,
    TraderLabStage.REPLAY,
    TraderLabStage.FAST_FORWARD,
    TraderLabStage.OOS,
    TraderLabStage.STRESS,
    TraderLabStage.MONTE_CARLO,
    TraderLabStage.RISK_REVIEW,
    TraderLabStage.CIBO_REVIEW,
    TraderLabStage.INDEPENDENT_VALIDATION,
)

_STAGE_TARGET_STATE: dict[TraderLabStage, TraderLabState] = {
    TraderLabStage.RESEARCH: TraderLabState.RESEARCH_READY,
    TraderLabStage.REPLAY: TraderLabState.REPLAY_QUALIFIED,
    TraderLabStage.FAST_FORWARD: TraderLabState.FAST_FORWARD_QUALIFIED,
    TraderLabStage.OOS: TraderLabState.OOS_QUALIFIED,
    TraderLabStage.STRESS: TraderLabState.STRESS_QUALIFIED,
    TraderLabStage.MONTE_CARLO: TraderLabState.MONTE_CARLO_QUALIFIED,
    TraderLabStage.RISK_REVIEW: TraderLabState.RISK_REVIEWED,
    TraderLabStage.CIBO_REVIEW: TraderLabState.CIBO_REVIEWED,
    TraderLabStage.INDEPENDENT_VALIDATION: TraderLabState.DEMO_ELIGIBLE,
}

_STATE_NEXT_STAGE: dict[TraderLabState, TraderLabStage | None] = {
    TraderLabState.DRAFT: TraderLabStage.RESEARCH,
    TraderLabState.RESEARCH_READY: TraderLabStage.REPLAY,
    TraderLabState.REPLAY_QUALIFIED: TraderLabStage.FAST_FORWARD,
    TraderLabState.FAST_FORWARD_QUALIFIED: TraderLabStage.OOS,
    TraderLabState.OOS_QUALIFIED: TraderLabStage.STRESS,
    TraderLabState.STRESS_QUALIFIED: TraderLabStage.MONTE_CARLO,
    TraderLabState.MONTE_CARLO_QUALIFIED: TraderLabStage.RISK_REVIEW,
    TraderLabState.RISK_REVIEWED: TraderLabStage.CIBO_REVIEW,
    TraderLabState.CIBO_REVIEWED: TraderLabStage.INDEPENDENT_VALIDATION,
    TraderLabState.DEMO_ELIGIBLE: None,
    TraderLabState.REJECTED: None,
    TraderLabState.DEGRADED: None,
    TraderLabState.SUSPENDED: None,
}

_TERMINAL_BLOCKING_STATES = frozenset(
    {
        TraderLabState.REJECTED,
        TraderLabState.DEGRADED,
        TraderLabState.SUSPENDED,
    }
)


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise TraderLabValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise TraderLabValidationError(f"{field_name} must be timezone-aware")


def _expected_prior_state(stage: TraderLabStage) -> TraderLabState:
    if stage not in MANDATORY_STAGES:
        raise TraderLabValidationError(f"unknown mandatory stage: {stage}")
    index = MANDATORY_STAGES.index(stage)
    if index == 0:
        return TraderLabState.DRAFT
    return _STAGE_TARGET_STATE[MANDATORY_STAGES[index - 1]]


@dataclass(frozen=True, slots=True)
class TraderLabStageQualification:
    """One completed mandatory-stage qualification bound to its evidence."""

    stage: TraderLabStage
    evidence: TraderLabStageEvidenceRecord
    prior_state: TraderLabState
    next_state: TraderLabState

    def __post_init__(self) -> None:
        if not isinstance(self.stage, TraderLabStage):
            raise TraderLabValidationError("qualification stage must be TraderLabStage")
        if not isinstance(self.evidence, TraderLabStageEvidenceRecord):
            raise TraderLabValidationError(
                "qualification evidence must be TraderLabStageEvidenceRecord"
            )
        if self.evidence.stage is not self.stage:
            raise TraderLabValidationError(
                "qualification stage must match its evidence stage"
            )
        if not isinstance(self.prior_state, TraderLabState):
            raise TraderLabValidationError("prior_state must be TraderLabState")
        if not isinstance(self.next_state, TraderLabState):
            raise TraderLabValidationError("next_state must be TraderLabState")
        if self.prior_state is not _expected_prior_state(self.stage):
            raise TraderLabValidationError(
                "qualification prior state must be the exact preceding stage state"
            )
        if self.next_state is not _STAGE_TARGET_STATE[self.stage]:
            raise TraderLabValidationError(
                "qualification next state must be the exact stage target state"
            )

    @property
    def qualified_at(self) -> datetime:
        return self.evidence.produced_at

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.stage.value,
            self.evidence.fingerprint.logical_values(),
            self.prior_state.value,
            self.next_state.value,
        )


@dataclass(frozen=True, slots=True)
class TraderLabTerminalRecord:
    """Explicit rejection/degradation/suspension evidence."""

    outcome: TraderLabState
    evidence: TraderLabEvidenceReference
    decided_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, TraderLabState):
            raise TraderLabValidationError("terminal outcome must be TraderLabState")
        if self.outcome not in _TERMINAL_BLOCKING_STATES:
            raise TraderLabValidationError(
                "terminal outcome must be rejected, degraded, or suspended"
            )
        if not isinstance(self.evidence, TraderLabEvidenceReference):
            raise TraderLabValidationError(
                "terminal evidence must be TraderLabEvidenceReference"
            )
        _validate_timestamp(self.decided_at, field_name="terminal decided_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.outcome.value,
            self.evidence.logical_values(),
            self.decided_at.isoformat(),
        )


def _derive_forward_state(
    qualifications: tuple[TraderLabStageQualification, ...],
) -> TraderLabState:
    """Replay the mandatory chain from DRAFT, failing on any skip or reorder."""

    state = TraderLabState.DRAFT
    for qualification in qualifications:
        if not isinstance(qualification, TraderLabStageQualification):
            raise TraderLabValidationError(
                "qualification must be TraderLabStageQualification"
            )
        expected_stage = _STATE_NEXT_STAGE[state]
        if expected_stage is None:
            raise TraderLabValidationError(
                "qualification chain cannot continue from a terminal state"
            )
        if qualification.stage is not expected_stage:
            raise TraderLabValidationError(
                "mandatory stages cannot be skipped or reordered"
            )
        if qualification.prior_state is not state:
            raise TraderLabValidationError(
                "qualification prior state must equal the derived current state"
            )
        state = qualification.next_state
    return state


def _validate_lifecycle(lifecycle: TraderLabLifecycle) -> None:
    if not isinstance(lifecycle.candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError("lifecycle candidate must be a candidate binding")
    if not isinstance(lifecycle.qualifications, tuple) or any(
        not isinstance(item, TraderLabStageQualification)
        for item in lifecycle.qualifications
    ):
        raise TraderLabValidationError(
            "lifecycle qualifications must be an immutable qualification tuple"
        )
    if lifecycle.terminal is not None and not isinstance(
        lifecycle.terminal, TraderLabTerminalRecord
    ):
        raise TraderLabValidationError(
            "lifecycle terminal must be TraderLabTerminalRecord or None"
        )

    seen_evidence_ids: set[TraderLabStageEvidenceId] = set()
    seen_stages: set[TraderLabStage] = set()
    previous_at: datetime | None = None
    for qualification in lifecycle.qualifications:
        if qualification.evidence.candidate != lifecycle.candidate:
            raise TraderLabValidationError(
                "every qualification evidence must bind the lifecycle candidate"
            )
        if qualification.stage in seen_stages:
            raise TraderLabValidationError("duplicate stage qualification detected")
        if qualification.evidence.evidence_id in seen_evidence_ids:
            raise TraderLabValidationError("duplicate stage evidence detected")
        if previous_at is not None and qualification.qualified_at < previous_at:
            raise TraderLabValidationError(
                "qualification evidence cannot predate the preceding qualification"
            )
        seen_stages.add(qualification.stage)
        seen_evidence_ids.add(qualification.evidence.evidence_id)
        previous_at = qualification.qualified_at

    forward_state = _derive_forward_state(lifecycle.qualifications)
    if lifecycle.terminal is not None and forward_state is TraderLabState.DEMO_ELIGIBLE:
        raise TraderLabValidationError(
            "a demo-eligible candidate cannot carry a terminal blocking record"
        )


def validate_trader_lab_lifecycle(lifecycle: TraderLabLifecycle) -> None:
    """Re-validate a lifecycle at a trust boundary (reflective-corruption guard)."""

    if not isinstance(lifecycle, TraderLabLifecycle):
        raise TraderLabValidationError("lifecycle must be TraderLabLifecycle")
    _validate_lifecycle(lifecycle)


@dataclass(frozen=True, slots=True)
class TraderLabLifecycle:
    """Immutable candidate lifecycle: exact binding, qualification chain, terminal."""

    candidate: TraderLabCandidateBinding
    qualifications: tuple[TraderLabStageQualification, ...]
    terminal: TraderLabTerminalRecord | None = None

    def __post_init__(self) -> None:
        _validate_lifecycle(self)

    @property
    def state(self) -> TraderLabState:
        if self.terminal is not None:
            return self.terminal.outcome
        if not self.qualifications:
            return TraderLabState.DRAFT
        return self.qualifications[-1].next_state

    @property
    def completed_stages(self) -> tuple[TraderLabStage, ...]:
        return tuple(item.stage for item in self.qualifications)

    def logical_values(self) -> tuple[object, ...]:
        _validate_lifecycle(self)
        return (
            self.candidate.fingerprint.logical_values(),
            tuple(item.logical_values() for item in self.qualifications),
            self.terminal.logical_values() if self.terminal is not None else None,
        )


@dataclass(frozen=True, slots=True)
class TraderLabPromotionRequest:
    """A deterministic forward stage-transition request."""

    stage: TraderLabStage
    evidence: TraderLabStageEvidenceRecord

    def __post_init__(self) -> None:
        if not isinstance(self.stage, TraderLabStage):
            raise TraderLabValidationError("request stage must be TraderLabStage")
        if not isinstance(self.evidence, TraderLabStageEvidenceRecord):
            raise TraderLabValidationError(
                "request evidence must be TraderLabStageEvidenceRecord"
            )
        if self.evidence.stage is not self.stage:
            raise TraderLabValidationError("request stage must match evidence stage")


@dataclass(frozen=True, slots=True)
class TraderLabRejectionRequest:
    """A deterministic rejection/degradation/suspension request with evidence."""

    outcome: TraderLabState
    evidence: TraderLabEvidenceReference
    decided_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, TraderLabState):
            raise TraderLabValidationError("rejection outcome must be TraderLabState")
        if self.outcome not in _TERMINAL_BLOCKING_STATES:
            raise TraderLabValidationError(
                "rejection outcome must be rejected, degraded, or suspended"
            )
        if not isinstance(self.evidence, TraderLabEvidenceReference):
            raise TraderLabValidationError(
                "rejection evidence must be TraderLabEvidenceReference"
            )
        _validate_timestamp(self.decided_at, field_name="rejection decided_at")


def start_trader_lab_lifecycle(
    candidate: TraderLabCandidateBinding,
) -> TraderLabLifecycle:
    """Start a new lifecycle in DRAFT for one exact candidate binding."""

    if not isinstance(candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError("candidate must be TraderLabCandidateBinding")
    return TraderLabLifecycle(candidate=candidate, qualifications=(), terminal=None)


def apply_trader_lab_promotion(
    lifecycle: TraderLabLifecycle,
    request: TraderLabPromotionRequest,
) -> Result[TraderLabLifecycle, TraderLabError]:
    """Apply one forward stage transition, failing closed on any violation."""

    try:
        _validate_lifecycle(lifecycle)
        if not isinstance(request, TraderLabPromotionRequest):
            raise TraderLabValidationError(
                "request must be TraderLabPromotionRequest"
            )
        current = lifecycle.state
        if current is TraderLabState.DEMO_ELIGIBLE or current in _TERMINAL_BLOCKING_STATES:
            raise TraderLabValidationError(
                "no forward promotion is possible from a terminal state"
            )
        if request.evidence.candidate != lifecycle.candidate:
            raise TraderLabValidationError(
                "promotion evidence candidate binding does not match lifecycle"
            )
        expected_stage = _STATE_NEXT_STAGE[current]
        if expected_stage is None or request.stage is not expected_stage:
            raise TraderLabValidationError(
                "mandatory stages cannot be skipped: exact next stage is required"
            )
        if any(
            qualification.evidence.evidence_id == request.evidence.evidence_id
            for qualification in lifecycle.qualifications
        ):
            raise TraderLabValidationError("duplicate stage evidence rejected")
        if lifecycle.qualifications and (
            request.evidence.produced_at
            < lifecycle.qualifications[-1].qualified_at
        ):
            raise TraderLabValidationError(
                "stale stage evidence cannot advance the lifecycle"
            )
        qualification = TraderLabStageQualification(
            stage=request.stage,
            evidence=request.evidence,
            prior_state=current,
            next_state=_STAGE_TARGET_STATE[request.stage],
        )
        return Success(
            TraderLabLifecycle(
                candidate=lifecycle.candidate,
                qualifications=lifecycle.qualifications + (qualification,),
                terminal=lifecycle.terminal,
            )
        )
    except TraderLabError as error:
        return Failure(error)


def apply_trader_lab_rejection(
    lifecycle: TraderLabLifecycle,
    request: TraderLabRejectionRequest,
) -> Result[TraderLabLifecycle, TraderLabError]:
    """Apply a rejection/degradation/suspension, permanently blocking the chain."""

    try:
        _validate_lifecycle(lifecycle)
        if not isinstance(request, TraderLabRejectionRequest):
            raise TraderLabValidationError(
                "request must be TraderLabRejectionRequest"
            )
        current = lifecycle.state
        if current is TraderLabState.DEMO_ELIGIBLE:
            raise TraderLabValidationError(
                "a demo-eligible candidate cannot be rejected in the same chain"
            )
        if current in _TERMINAL_BLOCKING_STATES:
            raise TraderLabValidationError(
                "a candidate already in a terminal blocking state cannot be re-blocked"
            )
        if lifecycle.qualifications and (
            request.decided_at < lifecycle.qualifications[-1].qualified_at
        ):
            raise TraderLabValidationError(
                "terminal decision cannot predate the qualification chain"
            )
        terminal = TraderLabTerminalRecord(
            outcome=request.outcome,
            evidence=request.evidence,
            decided_at=request.decided_at,
        )
        return Success(
            TraderLabLifecycle(
                candidate=lifecycle.candidate,
                qualifications=lifecycle.qualifications,
                terminal=terminal,
            )
        )
    except TraderLabError as error:
        return Failure(error)
