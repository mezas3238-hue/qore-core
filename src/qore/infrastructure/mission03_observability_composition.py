from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.cibo_operational_supervision_evidence import (
    CiboOperationalSupervisionOutcome,
    CiboOperationalSupervisionRecord,
)
from qore.infrastructure.execution_boundary import ExecutionStatus
from qore.infrastructure.execution_reconciliation import (
    ExecutionReconciliationSnapshot,
    ExecutionReconciliationStatus,
)
from qore.infrastructure.market_data import QuoteSnapshot
from qore.infrastructure.market_test_observability import (
    MarketTestObservabilityError,
    MarketTestObservabilityEvidence,
    MarketTestObservation,
    MarketTestObservationCategory,
    MarketTestObservationState,
    build_market_test_observability_evidence,
)
from qore.infrastructure.operational_safety_certification_preparation import (
    OperationalSafetyCertificationPreparationEvidence,
    OperationalSafetyPreparationStatus,
)
from qore.infrastructure.real_market_decision_runtime import (
    RealMarketDecisionOutcome,
    RealMarketDecisionStatus,
)
from qore.kernel.result import Failure, Result, Success


class Mission03ObservabilityCompositionError(MarketTestObservabilityError):
    """Base error for deterministic MISSION-03 observability composition."""

    __slots__ = ()


class Mission03ObservabilityCompositionValidationError(
    Mission03ObservabilityCompositionError
):
    """Cross-surface observability evidence is incomplete or contradictory."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise Mission03ObservabilityCompositionValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise Mission03ObservabilityCompositionValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class Mission03ObservabilityCycle:
    """Typed inputs for one offline-composable MISSION-03 observation cycle."""

    quote: QuoteSnapshot
    supervision: CiboOperationalSupervisionRecord
    safety: OperationalSafetyCertificationPreparationEvidence
    decision: RealMarketDecisionOutcome | None = None
    reconciliation: ExecutionReconciliationSnapshot | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.quote, QuoteSnapshot):
            raise Mission03ObservabilityCompositionValidationError(
                "observability cycle requires QuoteSnapshot"
            )
        if not isinstance(self.supervision, CiboOperationalSupervisionRecord):
            raise Mission03ObservabilityCompositionValidationError(
                "observability cycle requires CiboOperationalSupervisionRecord"
            )
        if not isinstance(
            self.safety,
            OperationalSafetyCertificationPreparationEvidence,
        ):
            raise Mission03ObservabilityCompositionValidationError(
                "observability cycle requires operational safety preparation evidence"
            )
        if self.supervision.market_snapshot_id != self.quote.snapshot_id:
            raise Mission03ObservabilityCompositionValidationError(
                "supervision market snapshot must match observed quote"
            )
        if self.supervision.instrument != self.quote.instrument.symbol:
            raise Mission03ObservabilityCompositionValidationError(
                "supervision instrument must match observed quote"
            )
        if self.supervision.decided_at < self.quote.observed_at:
            raise Mission03ObservabilityCompositionValidationError(
                "supervision decision must not predate observed quote"
            )

        if self.decision is None:
            if self.supervision.outcome not in {
                CiboOperationalSupervisionOutcome.BLOCKED,
                CiboOperationalSupervisionOutcome.FAILED,
            }:
                raise Mission03ObservabilityCompositionValidationError(
                    "missing decision outcome requires blocked or failed supervision"
                )
            if self.reconciliation is not None:
                raise Mission03ObservabilityCompositionValidationError(
                    "blocked decision cycle must not carry reconciliation"
                )
            return

        if not isinstance(self.decision, RealMarketDecisionOutcome):
            raise Mission03ObservabilityCompositionValidationError(
                "decision must be RealMarketDecisionOutcome or None"
            )
        if self.decision.quote != self.quote:
            raise Mission03ObservabilityCompositionValidationError(
                "decision quote must match observability quote exactly"
            )
        if self.decision.decided_at != self.supervision.decided_at:
            raise Mission03ObservabilityCompositionValidationError(
                "decision timestamp must match supervision record"
            )

        if self.decision.status is RealMarketDecisionStatus.NO_ACTION:
            if self.supervision.outcome is not CiboOperationalSupervisionOutcome.NO_ACTION:
                raise Mission03ObservabilityCompositionValidationError(
                    "NO_ACTION decision requires NO_ACTION supervision evidence"
                )
            if self.reconciliation is not None:
                raise Mission03ObservabilityCompositionValidationError(
                    "NO_ACTION decision must not carry reconciliation"
                )
            return

        if self.supervision.outcome is not CiboOperationalSupervisionOutcome.DELEGATED:
            raise Mission03ObservabilityCompositionValidationError(
                "submitted decision requires delegated supervision evidence"
            )
        if self.decision.intent is None or self.decision.receipt is None:
            raise Mission03ObservabilityCompositionValidationError(
                "submitted decision requires intent and receipt"
            )
        if self.supervision.intent_id != self.decision.intent.intent_id:
            raise Mission03ObservabilityCompositionValidationError(
                "supervision intent id must match submitted decision"
            )
        if not isinstance(self.reconciliation, ExecutionReconciliationSnapshot):
            raise Mission03ObservabilityCompositionValidationError(
                "submitted decision requires reconciliation snapshot"
            )
        if self.reconciliation.expected != self.decision.receipt:
            raise Mission03ObservabilityCompositionValidationError(
                "reconciliation expected receipt must match submitted decision"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.quote.logical_values(),
            self.supervision.logical_values(),
            self.safety.logical_values(),
            self.decision.logical_values() if self.decision is not None else None,
            (
                self.reconciliation.logical_values()
                if self.reconciliation is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class Mission03ObservabilityPreparationEvidence:
    """Complete observability bundle that remains explicitly non-operational."""

    evidence: MarketTestObservabilityEvidence

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, MarketTestObservabilityEvidence):
            raise Mission03ObservabilityCompositionValidationError(
                "MISSION-03 observability preparation requires evidence bundle"
            )

    @property
    def operationally_observed(self) -> bool:
        return False

    def logical_values(self) -> tuple[object, ...]:
        return (self.evidence.logical_values(), self.operationally_observed)


def _market_data_observation(cycle: Mission03ObservabilityCycle) -> MarketTestObservation:
    return MarketTestObservation(
        category=MarketTestObservationCategory.MARKET_DATA,
        state=MarketTestObservationState.HEALTHY,
        observed_at=cycle.quote.observed_at,
        message="market-data.snapshot-available",
        reference=str(cycle.quote.snapshot_id.value),
    )


def _decision_observation(cycle: Mission03ObservabilityCycle) -> MarketTestObservation:
    if cycle.decision is None:
        return MarketTestObservation(
            category=MarketTestObservationCategory.DECISION,
            state=MarketTestObservationState.BLOCKED,
            observed_at=cycle.supervision.decided_at,
            message="decision.blocked-before-outcome",
            reference=cycle.supervision.attempt_ref,
        )
    if cycle.decision.status is RealMarketDecisionStatus.NO_ACTION:
        message = "decision.no-action"
        reference = str(cycle.quote.snapshot_id.value)
    else:
        if cycle.decision.intent is None:
            raise Mission03ObservabilityCompositionValidationError(
                "submitted observation requires intent"
            )
        message = "decision.submitted"
        reference = str(cycle.decision.intent.intent_id.value)
    return MarketTestObservation(
        category=MarketTestObservationCategory.DECISION,
        state=MarketTestObservationState.HEALTHY,
        observed_at=cycle.decision.decided_at,
        message=message,
        reference=reference,
    )


def _supervision_observation(cycle: Mission03ObservabilityCycle) -> MarketTestObservation:
    blocked = cycle.supervision.outcome in {
        CiboOperationalSupervisionOutcome.BLOCKED,
        CiboOperationalSupervisionOutcome.FAILED,
    }
    return MarketTestObservation(
        category=MarketTestObservationCategory.SUPERVISION,
        state=(
            MarketTestObservationState.BLOCKED
            if blocked
            else MarketTestObservationState.HEALTHY
        ),
        observed_at=cycle.supervision.decided_at,
        message=f"supervision.{cycle.supervision.outcome.value}",
        reference=cycle.supervision.attempt_ref,
    )


def _safety_observation(cycle: Mission03ObservabilityCycle) -> MarketTestObservation:
    prepared = cycle.safety.status is OperationalSafetyPreparationStatus.PREPARED
    return MarketTestObservation(
        category=MarketTestObservationCategory.SAFETY,
        state=(
            MarketTestObservationState.HEALTHY
            if prepared
            else MarketTestObservationState.BLOCKED
        ),
        observed_at=cycle.safety.evaluated_at,
        message=("safety.prepared" if prepared else "safety.blocked"),
        reference=str(cycle.safety.preparation_id.value),
    )


def _execution_observation(cycle: Mission03ObservabilityCycle) -> MarketTestObservation:
    if cycle.decision is None:
        return MarketTestObservation(
            category=MarketTestObservationCategory.EXECUTION,
            state=MarketTestObservationState.BLOCKED,
            observed_at=cycle.supervision.decided_at,
            message="execution.not-attempted-upstream-blocked",
            reference=cycle.supervision.attempt_ref,
        )
    if cycle.decision.status is RealMarketDecisionStatus.NO_ACTION:
        return MarketTestObservation(
            category=MarketTestObservationCategory.EXECUTION,
            state=MarketTestObservationState.HEALTHY,
            observed_at=cycle.decision.decided_at,
            message="execution.not-required-no-action",
            reference=str(cycle.quote.snapshot_id.value),
        )
    if cycle.decision.receipt is None:
        raise Mission03ObservabilityCompositionValidationError(
            "submitted execution observation requires receipt"
        )
    accepted = cycle.decision.receipt.status is ExecutionStatus.ACCEPTED
    return MarketTestObservation(
        category=MarketTestObservationCategory.EXECUTION,
        state=(
            MarketTestObservationState.HEALTHY
            if accepted
            else MarketTestObservationState.DEGRADED
        ),
        observed_at=cycle.decision.receipt.recorded_at,
        message=("execution.accepted" if accepted else "execution.cancelled"),
        reference=str(cycle.decision.receipt.receipt_id.value),
    )


def _reconciliation_observation(
    cycle: Mission03ObservabilityCycle,
) -> MarketTestObservation:
    if cycle.decision is None:
        return MarketTestObservation(
            category=MarketTestObservationCategory.RECONCILIATION,
            state=MarketTestObservationState.BLOCKED,
            observed_at=cycle.supervision.decided_at,
            message="reconciliation.not-applicable-upstream-blocked",
            reference=cycle.supervision.attempt_ref,
        )
    if cycle.decision.status is RealMarketDecisionStatus.NO_ACTION:
        return MarketTestObservation(
            category=MarketTestObservationCategory.RECONCILIATION,
            state=MarketTestObservationState.HEALTHY,
            observed_at=cycle.decision.decided_at,
            message="reconciliation.not-required-no-action",
            reference=str(cycle.quote.snapshot_id.value),
        )
    if cycle.reconciliation is None:
        raise Mission03ObservabilityCompositionValidationError(
            "submitted reconciliation observation requires snapshot"
        )
    matched = cycle.reconciliation.status is ExecutionReconciliationStatus.MATCHED
    return MarketTestObservation(
        category=MarketTestObservationCategory.RECONCILIATION,
        state=(
            MarketTestObservationState.HEALTHY
            if matched
            else MarketTestObservationState.BLOCKED
        ),
        observed_at=cycle.reconciliation.reconciled_at,
        message=f"reconciliation.{cycle.reconciliation.status.value}",
        reference=(
            str(cycle.decision.receipt.receipt_id.value)
            if cycle.decision.receipt is not None
            else cycle.supervision.attempt_ref
        ),
    )


def build_mission03_observability_preparation(
    cycle: Mission03ObservabilityCycle,
    *,
    evaluated_at: datetime,
) -> Result[Mission03ObservabilityPreparationEvidence, MarketTestObservabilityError]:
    """Compose existing typed surfaces into one complete offline observation bundle."""

    if not isinstance(cycle, Mission03ObservabilityCycle):
        return Failure(
            Mission03ObservabilityCompositionValidationError(
                "MISSION-03 observability composition requires typed cycle"
            )
        )
    try:
        _validate_timestamp(evaluated_at, field_name="evaluated_at")
        observations = (
            _market_data_observation(cycle),
            _decision_observation(cycle),
            _supervision_observation(cycle),
            _safety_observation(cycle),
            _execution_observation(cycle),
            _reconciliation_observation(cycle),
        )
    except MarketTestObservabilityError as error:
        return Failure(error)
    evidence_result = build_market_test_observability_evidence(
        observations,
        evaluated_at=evaluated_at,
    )
    if isinstance(evidence_result, Failure):
        return Failure(evidence_result.error)
    try:
        prepared = Mission03ObservabilityPreparationEvidence(
            evidence=evidence_result.value
        )
    except MarketTestObservabilityError as error:
        return Failure(error)
    return Success(prepared)
