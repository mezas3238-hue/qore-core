from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.domain.commands import (
    CommandHandler,
    CommandId,
    CommandMetadata,
    CommandName,
    CommandResult,
)
from qore.domain.events import (
    CausationId,
    CorrelationId,
    DomainEventCategory,
    DomainEventId,
    DomainEventMetadata,
    DomainEventVersion,
)
from qore.domain.message_bus import HandlerRegistry, MessageBus
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
from qore.governance.decision_flow import (
    CrossModuleDecisionFlow,
    CrossModuleDecisionFlowPlan,
    GovernanceValidationError,
)
from qore.kernel.result import Failure, Success
from qore.modules.cibo.contracts import (
    CiboValidationError,
    ReviewFunctionalDecisionCommand,
)
from qore.modules.cio.contracts import (
    CioDecisionProducedEvent,
    CioValidationError,
    CreateCioDecisionCommand,
)
from qore.modules.portfolio.contracts import (
    AllocationIntentId,
    CreateAllocationIntentCommand,
    PortfolioTarget,
    PortfolioValidationError,
)
from qore.modules.risk.contracts import RiskPolicy, RiskPolicyId

_TIMESTAMP = datetime(2026, 8, 7, 20, 0, tzinfo=UTC)
_CORRELATION_ID = CorrelationId(UUID("80000000-0000-0000-0000-000000000001"))
_SOURCE_DECISION_ID = DecisionId(UUID("80000000-0000-0000-0000-000000000002"))
_CIBO_DECISION_ID = DecisionId(UUID("80000000-0000-0000-0000-000000000003"))


def _reason(code: str) -> DecisionReason:
    return DecisionReason(
        code=DecisionReasonCode(code),
        summary=code,
    )


def _approved_source() -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=_SOURCE_DECISION_ID,
        timestamp=_TIMESTAMP,
        decision_type=DecisionType("cio.strategic-direction"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.HIGH,
        metadata=DecisionMetadata(correlation_id=_CORRELATION_ID),
        reasons=(_reason("cio.approved"),),
        outcome=DecisionOutcome.APPROVED,
    )


def test_cibo_command_rejects_causation_that_does_not_match_source() -> None:
    source = _approved_source()

    with pytest.raises(CiboValidationError, match="causation"):
        ReviewFunctionalDecisionCommand(
            command_id=CommandId(UUID("80000000-0000-0000-0000-000000000010")),
            timestamp=_TIMESTAMP,
            name=CommandName("cibo.review-functional-decision"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION_ID,
                causation_id=CausationId(
                    UUID("80000000-0000-0000-0000-000000000099")
                ),
            ),
            decision_id=_CIBO_DECISION_ID,
            source_decision=source,
            priority=DecisionPriority.NORMAL,
            reasons=(_reason("cibo.approved"),),
            requested_outcome=DecisionOutcome.APPROVED,
        )


def test_portfolio_command_rejects_source_identity_reuse() -> None:
    source = _approved_source()

    with pytest.raises(PortfolioValidationError, match="identity must differ"):
        CreateAllocationIntentCommand(
            command_id=CommandId(UUID("80000000-0000-0000-0000-000000000011")),
            timestamp=_TIMESTAMP,
            name=CommandName("portfolio.create-allocation-intent"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION_ID,
                causation_id=CausationId(source.decision_id.value),
            ),
            intent_id=AllocationIntentId(source.decision_id.value),
            source_decision=source,
            targets=(
                PortfolioTarget(name="core", weight_bps=7_000),
                PortfolioTarget(name="reserve", weight_bps=3_000),
            ),
        )


def test_cio_event_rejects_causation_divergent_from_decision() -> None:
    cause = CausationId(UUID("80000000-0000-0000-0000-000000000012"))
    command = CreateCioDecisionCommand(
        command_id=CommandId(UUID("80000000-0000-0000-0000-000000000013")),
        timestamp=_TIMESTAMP,
        name=CommandName("cio.create-decision"),
        metadata=CommandMetadata(
            correlation_id=_CORRELATION_ID,
            causation_id=cause,
        ),
        decision_id=_SOURCE_DECISION_ID,
        decision_type=DecisionType("cio.strategic-direction"),
        priority=DecisionPriority.HIGH,
        reasons=(_reason("cio.approved"),),
        requested_outcome=DecisionOutcome.APPROVED,
    )

    with pytest.raises(CioValidationError, match="causation"):
        CioDecisionProducedEvent(
            event_id=DomainEventId(
                UUID("80000000-0000-0000-0000-000000000014")
            ),
            timestamp=_TIMESTAMP,
            event_version=DomainEventVersion("1"),
            metadata=DomainEventMetadata(
                category=DomainEventCategory("cio"),
                correlation_id=_CORRELATION_ID,
                causation_id=None,
            ),
            decision=command.to_decision(),
        )


class _RejectingCioHandler:
    def handle(
        self,
        command: CreateCioDecisionCommand,
    ) -> CommandResult[FunctionalDecision]:
        return Success(
            FunctionalDecision(
                decision_id=command.decision_id,
                timestamp=command.timestamp,
                decision_type=command.decision_type,
                status=DecisionStatus.RESOLVED,
                priority=command.priority,
                metadata=DecisionMetadata(
                    correlation_id=command.metadata.correlation_id,
                    causation_id=command.metadata.causation_id,
                ),
                reasons=(_reason("cio.rejected"),),
                outcome=DecisionOutcome.REJECTED,
            )
        )


def _flow_plan() -> CrossModuleDecisionFlowPlan:
    return CrossModuleDecisionFlowPlan(
        correlation_id=_CORRELATION_ID,
        timestamp=_TIMESTAMP,
        cio_command_id=CommandId(UUID("80000000-0000-0000-0000-000000000020")),
        cio_decision_id=_SOURCE_DECISION_ID,
        cio_decision_type=DecisionType("cio.strategic-direction"),
        cio_priority=DecisionPriority.HIGH,
        cio_reasons=(_reason("cio.approved"),),
        cio_outcome=DecisionOutcome.APPROVED,
        cibo_command_id=CommandId(UUID("80000000-0000-0000-0000-000000000021")),
        cibo_decision_id=_CIBO_DECISION_ID,
        cibo_priority=DecisionPriority.NORMAL,
        cibo_reasons=(_reason("cibo.approved"),),
        cibo_outcome=DecisionOutcome.APPROVED,
        portfolio_command_id=CommandId(
            UUID("80000000-0000-0000-0000-000000000022")
        ),
        allocation_intent_id=AllocationIntentId(
            UUID("80000000-0000-0000-0000-000000000023")
        ),
        portfolio_targets=(
            PortfolioTarget(name="core", weight_bps=7_000),
            PortfolioTarget(name="reserve", weight_bps=3_000),
        ),
        risk_command_id=CommandId(UUID("80000000-0000-0000-0000-000000000024")),
        risk_decision_id=DecisionId(UUID("80000000-0000-0000-0000-000000000025")),
        risk_policy=RiskPolicy(
            policy_id=RiskPolicyId(
                UUID("80000000-0000-0000-0000-000000000026")
            ),
            soft_single_target_limit_bps=7_000,
            hard_single_target_limit_bps=8_000,
        ),
    )


def test_governance_stops_when_actual_cio_result_is_not_approved() -> None:
    registry = HandlerRegistry()
    handler: CommandHandler[CreateCioDecisionCommand, FunctionalDecision] = (
        _RejectingCioHandler()
    )
    registry.register_command(CreateCioDecisionCommand, handler)
    flow = CrossModuleDecisionFlow(message_bus=MessageBus(registry=registry))

    result = flow.execute(_flow_plan())

    assert isinstance(result, Failure)
    assert isinstance(result.error, GovernanceValidationError)
    assert "CIO decision outcome" in str(result.error)
