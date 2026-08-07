from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from qore.domain.commands import Command
from qore.domain.events import (
    BusinessDomainEvent,
    CausationId,
    DomainEventId,
    DomainEventMetadata,
    DomainEventVersion,
)
from qore.functional.decisions import (
    DecisionId,
    DecisionMetadata,
    DecisionOutcome,
    DecisionPriority,
    DecisionReason,
    DecisionReasonCode,
    DecisionStatus,
    DecisionType,
    FunctionalDecision,
)
from qore.kernel.errors import DomainError
from qore.modules.portfolio.contracts import AllocationIntent, AllocationIntentId


class RiskError(DomainError):
    """Error base de los contratos funcionales de Risk Governance."""

    __slots__ = ()


class RiskValidationError(RiskError):
    """Violación explícita de una invariante de Risk Governance."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class RiskPolicyId:
    """Identidad explícita de una política lógica de riesgo."""

    value: UUID


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    """Política determinista de concentración, sin market data ni ejecución."""

    policy_id: RiskPolicyId
    soft_single_target_limit_bps: int
    hard_single_target_limit_bps: int

    def __post_init__(self) -> None:
        if type(self.soft_single_target_limit_bps) is not int:
            raise RiskValidationError("risk soft limit must be an integer")
        if type(self.hard_single_target_limit_bps) is not int:
            raise RiskValidationError("risk hard limit must be an integer")
        if not 1 <= self.soft_single_target_limit_bps <= 10_000:
            raise RiskValidationError("risk soft limit must be between 1 and 10000")
        if not 1 <= self.hard_single_target_limit_bps <= 10_000:
            raise RiskValidationError("risk hard limit must be between 1 and 10000")
        if self.soft_single_target_limit_bps > self.hard_single_target_limit_bps:
            raise RiskValidationError("risk soft limit must not exceed hard limit")

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.policy_id.value),
            self.soft_single_target_limit_bps,
            self.hard_single_target_limit_bps,
        )


@dataclass(frozen=True, slots=True)
class AssessAllocationRiskCommand(Command):
    """Solicitud explícita para evaluar una AllocationIntent con una política fija."""

    decision_id: DecisionId
    allocation_intent: AllocationIntent
    policy: RiskPolicy
    priority: DecisionPriority = DecisionPriority.HIGH

    def __post_init__(self) -> None:
        if self.metadata.correlation_id != self.allocation_intent.correlation_id:
            raise RiskValidationError(
                "risk command correlation must match the allocation intent"
            )
        expected_causation = CausationId(self.allocation_intent.intent_id.value)
        if self.metadata.causation_id != expected_causation:
            raise RiskValidationError(
                "risk command causation must match the allocation intent"
            )

    def to_decision(self) -> FunctionalDecision:
        """Evaluar concentración de forma pura y determinista."""
        peak_weight = max(target.weight_bps for target in self.allocation_intent.targets)
        if peak_weight > self.policy.hard_single_target_limit_bps:
            outcome = DecisionOutcome.BLOCKED
            reason = DecisionReason(
                code=DecisionReasonCode("risk.hard-concentration-limit-exceeded"),
                summary="Allocation exceeds the hard concentration limit",
                attributes={
                    "peak_weight_bps": peak_weight,
                    "hard_limit_bps": self.policy.hard_single_target_limit_bps,
                },
            )
        elif peak_weight > self.policy.soft_single_target_limit_bps:
            outcome = DecisionOutcome.DEGRADED
            reason = DecisionReason(
                code=DecisionReasonCode("risk.soft-concentration-limit-exceeded"),
                summary="Allocation exceeds the soft concentration limit",
                attributes={
                    "peak_weight_bps": peak_weight,
                    "soft_limit_bps": self.policy.soft_single_target_limit_bps,
                },
            )
        else:
            outcome = DecisionOutcome.APPROVED
            reason = DecisionReason(
                code=DecisionReasonCode("risk.within-concentration-limits"),
                summary="Allocation is within concentration limits",
                attributes={
                    "peak_weight_bps": peak_weight,
                    "soft_limit_bps": self.policy.soft_single_target_limit_bps,
                    "hard_limit_bps": self.policy.hard_single_target_limit_bps,
                },
            )

        return FunctionalDecision(
            decision_id=self.decision_id,
            timestamp=self.timestamp,
            decision_type=DecisionType("risk.allocation-governance"),
            status=DecisionStatus.RESOLVED,
            priority=self.priority,
            metadata=DecisionMetadata(
                correlation_id=self.allocation_intent.correlation_id,
                causation_id=CausationId(self.allocation_intent.intent_id.value),
                attributes={"policy_id": self.policy.policy_id.value},
            ),
            reasons=(reason,),
            outcome=outcome,
        )


class RiskDecisionProducedEvent(BusinessDomainEvent):
    """Evento explícito que representa una decisión de Risk Governance."""

    __slots__ = ("_decision", "_source_intent_id")
    _decision: FunctionalDecision
    _source_intent_id: AllocationIntentId

    def __init__(
        self,
        *,
        event_id: DomainEventId,
        timestamp: datetime,
        event_version: DomainEventVersion,
        metadata: DomainEventMetadata,
        decision: FunctionalDecision,
        source_intent_id: AllocationIntentId,
    ) -> None:
        expected_causation = CausationId(source_intent_id.value)
        if metadata.correlation_id != decision.metadata.correlation_id:
            raise RiskValidationError(
                "risk event correlation must match the represented decision"
            )
        if decision.metadata.causation_id != expected_causation:
            raise RiskValidationError(
                "risk decision causation must match the source allocation intent"
            )
        if metadata.causation_id != expected_causation:
            raise RiskValidationError(
                "risk event causation must match the source allocation intent"
            )
        object.__setattr__(self, "_decision", decision)
        object.__setattr__(self, "_source_intent_id", source_intent_id)
        super().__init__(
            timestamp=timestamp,
            event_name="risk.decision-produced",
            event_id=event_id,
            event_version=event_version,
            metadata=metadata,
        )

    @property
    def decision(self) -> FunctionalDecision:
        return self._decision

    @property
    def source_intent_id(self) -> AllocationIntentId:
        return self._source_intent_id

    def logical_values(self) -> tuple[object, ...]:
        return (
            *super().logical_values(),
            str(self._source_intent_id.value),
            self._decision.logical_values(),
        )
