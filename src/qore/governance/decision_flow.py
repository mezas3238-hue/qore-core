from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.domain.commands import CommandId, CommandMetadata, CommandName
from qore.domain.events import CausationId, CorrelationId
from qore.domain.message_bus import MessageBus
from qore.functional.decisions import (
    DecisionId,
    DecisionOutcome,
    DecisionPriority,
    DecisionReason,
    DecisionStatus,
    DecisionType,
    FunctionalDecision,
)
from qore.kernel.errors import DomainError
from qore.kernel.result import Failure, Result, Success
from qore.modules.cibo.contracts import ReviewFunctionalDecisionCommand
from qore.modules.cio.contracts import CreateCioDecisionCommand
from qore.modules.portfolio.contracts import (
    AllocationIntent,
    AllocationIntentId,
    CreateAllocationIntentCommand,
    PortfolioTarget,
)
from qore.modules.risk.contracts import AssessAllocationRiskCommand, RiskPolicy


class GovernanceError(DomainError):
    """Error base del flujo funcional transversal."""

    __slots__ = ()


class GovernanceValidationError(GovernanceError):
    """Violación explícita de una invariante del flujo transversal."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class CrossModuleDecisionFlowPlan:
    """Entradas explícitas y deterministas del recorrido CIO→CIBO→Portfolio→Risk."""

    correlation_id: CorrelationId
    timestamp: datetime
    cio_command_id: CommandId
    cio_decision_id: DecisionId
    cio_decision_type: DecisionType
    cio_priority: DecisionPriority
    cio_reasons: tuple[DecisionReason, ...]
    cio_outcome: DecisionOutcome
    cibo_command_id: CommandId
    cibo_decision_id: DecisionId
    cibo_priority: DecisionPriority
    cibo_reasons: tuple[DecisionReason, ...]
    cibo_outcome: DecisionOutcome
    portfolio_command_id: CommandId
    allocation_intent_id: AllocationIntentId
    portfolio_targets: tuple[PortfolioTarget, ...]
    risk_command_id: CommandId
    risk_decision_id: DecisionId
    risk_policy: RiskPolicy
    risk_priority: DecisionPriority = DecisionPriority.HIGH

    def __post_init__(self) -> None:
        if self.cio_outcome is not DecisionOutcome.APPROVED:
            raise GovernanceValidationError(
                "cross-module flow requires an approved CIO decision"
            )
        if self.cibo_outcome is not DecisionOutcome.APPROVED:
            raise GovernanceValidationError(
                "cross-module flow requires an approved CIBO decision"
            )
        if not isinstance(self.cio_reasons, tuple) or not self.cio_reasons:
            raise GovernanceValidationError(
                "cross-module flow requires immutable CIO reasons"
            )
        if not isinstance(self.cibo_reasons, tuple) or not self.cibo_reasons:
            raise GovernanceValidationError(
                "cross-module flow requires immutable CIBO reasons"
            )
        causal_ids = (
            self.cio_decision_id.value,
            self.cibo_decision_id.value,
            self.allocation_intent_id.value,
            self.risk_decision_id.value,
        )
        if len(set(causal_ids)) != len(causal_ids):
            raise GovernanceValidationError(
                "cross-module causal object identities must be unique"
            )


@dataclass(frozen=True, slots=True)
class CrossModuleDecisionFlowResult:
    """Snapshot inmutable del resultado completo del flujo transversal."""

    correlation_id: CorrelationId
    cio_decision: FunctionalDecision
    cibo_decision: FunctionalDecision
    allocation_intent: AllocationIntent
    risk_decision: FunctionalDecision

    def __post_init__(self) -> None:
        expected = self.correlation_id
        if self.cio_decision.metadata.correlation_id != expected:
            raise GovernanceValidationError("CIO decision correlation mismatch")
        if self.cibo_decision.metadata.correlation_id != expected:
            raise GovernanceValidationError("CIBO decision correlation mismatch")
        if self.allocation_intent.correlation_id != expected:
            raise GovernanceValidationError("allocation intent correlation mismatch")
        if self.risk_decision.metadata.correlation_id != expected:
            raise GovernanceValidationError("risk decision correlation mismatch")
        if self.cio_decision.status is not DecisionStatus.RESOLVED or (
            self.cio_decision.outcome is not DecisionOutcome.APPROVED
        ):
            raise GovernanceValidationError("CIO decision must be resolved and approved")
        if self.cibo_decision.status is not DecisionStatus.RESOLVED or (
            self.cibo_decision.outcome is not DecisionOutcome.APPROVED
        ):
            raise GovernanceValidationError("CIBO decision must be resolved and approved")
        if self.cibo_decision.metadata.causation_id != CausationId(
            self.cio_decision.decision_id.value
        ):
            raise GovernanceValidationError("CIBO causation mismatch")
        if self.allocation_intent.source_decision_id != self.cibo_decision.decision_id:
            raise GovernanceValidationError("Portfolio causation mismatch")
        if self.risk_decision.metadata.causation_id != CausationId(
            self.allocation_intent.intent_id.value
        ):
            raise GovernanceValidationError("Risk causation mismatch")
        allowed_risk_outcomes = {
            DecisionOutcome.APPROVED,
            DecisionOutcome.DEGRADED,
            DecisionOutcome.BLOCKED,
        }
        if self.risk_decision.status is not DecisionStatus.RESOLVED or (
            self.risk_decision.outcome not in allowed_risk_outcomes
        ):
            raise GovernanceValidationError(
                "Risk decision must be resolved with a governance outcome"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.correlation_id.value),
            self.cio_decision.logical_values(),
            self.cibo_decision.logical_values(),
            self.allocation_intent.logical_values(),
            self.risk_decision.logical_values(),
        )


class CrossModuleDecisionFlow:
    """Orquestador síncrono que usa exclusivamente el MessageBus oficial."""

    def __init__(self, *, message_bus: MessageBus) -> None:
        self._message_bus = message_bus

    def execute(
        self,
        plan: CrossModuleDecisionFlowPlan,
    ) -> Result[CrossModuleDecisionFlowResult, DomainError]:
        try:
            return self._execute(plan)
        except DomainError as error:
            return Failure(error)

    def _execute(
        self,
        plan: CrossModuleDecisionFlowPlan,
    ) -> Result[CrossModuleDecisionFlowResult, DomainError]:
        cio_result: Result[FunctionalDecision, DomainError] = (
            self._message_bus.dispatch_command(
                CreateCioDecisionCommand(
                    command_id=plan.cio_command_id,
                    timestamp=plan.timestamp,
                    name=CommandName("cio.create-decision"),
                    metadata=CommandMetadata(correlation_id=plan.correlation_id),
                    decision_id=plan.cio_decision_id,
                    decision_type=plan.cio_decision_type,
                    priority=plan.cio_priority,
                    reasons=plan.cio_reasons,
                    requested_outcome=plan.cio_outcome,
                )
            )
        )
        if isinstance(cio_result, Failure):
            return Failure(cio_result.error)
        cio_decision = cio_result.value
        cio_error = self._validate_decision_result(
            stage="CIO",
            decision=cio_decision,
            expected_id=plan.cio_decision_id,
            correlation_id=plan.correlation_id,
            expected_causation=None,
            allowed_outcomes=frozenset({DecisionOutcome.APPROVED}),
        )
        if cio_error is not None:
            return Failure(cio_error)

        cibo_result: Result[FunctionalDecision, DomainError] = (
            self._message_bus.dispatch_command(
                ReviewFunctionalDecisionCommand(
                    command_id=plan.cibo_command_id,
                    timestamp=plan.timestamp,
                    name=CommandName("cibo.review-functional-decision"),
                    metadata=CommandMetadata(
                        correlation_id=plan.correlation_id,
                        causation_id=CausationId(cio_decision.decision_id.value),
                    ),
                    decision_id=plan.cibo_decision_id,
                    source_decision=cio_decision,
                    priority=plan.cibo_priority,
                    reasons=plan.cibo_reasons,
                    requested_outcome=plan.cibo_outcome,
                )
            )
        )
        if isinstance(cibo_result, Failure):
            return Failure(cibo_result.error)
        cibo_decision = cibo_result.value
        cibo_error = self._validate_decision_result(
            stage="CIBO",
            decision=cibo_decision,
            expected_id=plan.cibo_decision_id,
            correlation_id=plan.correlation_id,
            expected_causation=CausationId(cio_decision.decision_id.value),
            allowed_outcomes=frozenset({DecisionOutcome.APPROVED}),
        )
        if cibo_error is not None:
            return Failure(cibo_error)

        portfolio_result: Result[AllocationIntent, DomainError] = (
            self._message_bus.dispatch_command(
                CreateAllocationIntentCommand(
                    command_id=plan.portfolio_command_id,
                    timestamp=plan.timestamp,
                    name=CommandName("portfolio.create-allocation-intent"),
                    metadata=CommandMetadata(
                        correlation_id=plan.correlation_id,
                        causation_id=CausationId(cibo_decision.decision_id.value),
                    ),
                    intent_id=plan.allocation_intent_id,
                    source_decision=cibo_decision,
                    targets=plan.portfolio_targets,
                )
            )
        )
        if isinstance(portfolio_result, Failure):
            return Failure(portfolio_result.error)
        allocation_intent = portfolio_result.value
        if allocation_intent.intent_id != plan.allocation_intent_id:
            return Failure(GovernanceValidationError("Portfolio intent identity mismatch"))
        if allocation_intent.correlation_id != plan.correlation_id:
            return Failure(GovernanceValidationError("Portfolio correlation mismatch"))
        if allocation_intent.source_decision_id != cibo_decision.decision_id:
            return Failure(GovernanceValidationError("Portfolio causation mismatch"))

        risk_result: Result[FunctionalDecision, DomainError] = (
            self._message_bus.dispatch_command(
                AssessAllocationRiskCommand(
                    command_id=plan.risk_command_id,
                    timestamp=plan.timestamp,
                    name=CommandName("risk.assess-allocation"),
                    metadata=CommandMetadata(
                        correlation_id=plan.correlation_id,
                        causation_id=CausationId(allocation_intent.intent_id.value),
                    ),
                    decision_id=plan.risk_decision_id,
                    allocation_intent=allocation_intent,
                    policy=plan.risk_policy,
                    priority=plan.risk_priority,
                )
            )
        )
        if isinstance(risk_result, Failure):
            return Failure(risk_result.error)
        risk_decision = risk_result.value
        risk_error = self._validate_decision_result(
            stage="Risk",
            decision=risk_decision,
            expected_id=plan.risk_decision_id,
            correlation_id=plan.correlation_id,
            expected_causation=CausationId(allocation_intent.intent_id.value),
            allowed_outcomes=frozenset(
                {
                    DecisionOutcome.APPROVED,
                    DecisionOutcome.DEGRADED,
                    DecisionOutcome.BLOCKED,
                }
            ),
        )
        if risk_error is not None:
            return Failure(risk_error)

        return Success(
            CrossModuleDecisionFlowResult(
                correlation_id=plan.correlation_id,
                cio_decision=cio_decision,
                cibo_decision=cibo_decision,
                allocation_intent=allocation_intent,
                risk_decision=risk_decision,
            )
        )

    @staticmethod
    def _validate_decision_result(
        *,
        stage: str,
        decision: FunctionalDecision,
        expected_id: DecisionId,
        correlation_id: CorrelationId,
        expected_causation: CausationId | None,
        allowed_outcomes: frozenset[DecisionOutcome],
    ) -> GovernanceValidationError | None:
        if decision.decision_id != expected_id:
            return GovernanceValidationError(f"{stage} decision identity mismatch")
        if decision.metadata.correlation_id != correlation_id:
            return GovernanceValidationError(f"{stage} decision correlation mismatch")
        if decision.metadata.causation_id != expected_causation:
            return GovernanceValidationError(f"{stage} decision causation mismatch")
        if decision.status is not DecisionStatus.RESOLVED:
            return GovernanceValidationError(f"{stage} decision must be resolved")
        if decision.outcome not in allowed_outcomes:
            return GovernanceValidationError(f"{stage} decision outcome is not allowed")
        return None
