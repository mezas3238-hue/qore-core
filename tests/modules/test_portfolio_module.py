from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
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
from qore.domain.message_bus import HandlerRegistry
from qore.domain.modules import ModuleName
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
from qore.kernel.result import Success
from qore.modules.cibo.module import CiboModule
from qore.modules.cio.module import CioModule
from qore.modules.portfolio.contracts import (
    AllocationIntent,
    AllocationIntentCreatedEvent,
    AllocationIntentId,
    CreateAllocationIntentCommand,
    PortfolioTarget,
    PortfolioValidationError,
)
from qore.modules.portfolio.module import CreateAllocationIntentHandler, PortfolioModule

_SOURCE_DECISION_ID = DecisionId(UUID("30000000-0000-0000-0000-000000000001"))
_INTENT_ID = AllocationIntentId(UUID("30000000-0000-0000-0000-000000000002"))
_COMMAND_ID = CommandId(UUID("30000000-0000-0000-0000-000000000003"))
_CORRELATION_ID = CorrelationId(UUID("30000000-0000-0000-0000-000000000004"))
_EVENT_ID = DomainEventId(UUID("30000000-0000-0000-0000-000000000005"))
_TIMESTAMP = datetime(2026, 8, 7, 21, 0, tzinfo=UTC)


def _source_decision(
    *,
    status: DecisionStatus = DecisionStatus.RESOLVED,
    outcome: DecisionOutcome | None = DecisionOutcome.APPROVED,
) -> FunctionalDecision:
    reasons: tuple[DecisionReason, ...] = ()
    if status is DecisionStatus.RESOLVED:
        reasons = (
            DecisionReason(
                code=DecisionReasonCode("cibo.business-accepted"),
                summary="Business review accepted",
            ),
        )
    return FunctionalDecision(
        decision_id=_SOURCE_DECISION_ID,
        timestamp=_TIMESTAMP,
        decision_type=DecisionType("cibo.business-review"),
        status=status,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(correlation_id=_CORRELATION_ID),
        reasons=reasons,
        outcome=outcome,
    )


def _targets() -> tuple[PortfolioTarget, ...]:
    return (
        PortfolioTarget(name="core", weight_bps=7000),
        PortfolioTarget(name="reserve", weight_bps=3000),
    )


def _command() -> CreateAllocationIntentCommand:
    return CreateAllocationIntentCommand(
        command_id=_COMMAND_ID,
        timestamp=_TIMESTAMP,
        name=CommandName("portfolio.create-allocation-intent"),
        metadata=CommandMetadata(
            correlation_id=_CORRELATION_ID,
            causation_id=CausationId(_SOURCE_DECISION_ID.value),
            attributes={"scope": "logical"},
        ),
        intent_id=_INTENT_ID,
        source_decision=_source_decision(),
        targets=_targets(),
    )


class TestPortfolioContracts:
    def test_target_requires_positive_bps(self) -> None:
        with pytest.raises(PortfolioValidationError, match="between 1 and 10000"):
            PortfolioTarget(name="core", weight_bps=0)

    def test_intent_requires_exact_100_percent(self) -> None:
        with pytest.raises(PortfolioValidationError, match="sum to 10000"):
            AllocationIntent(
                intent_id=_INTENT_ID,
                source_decision_id=_SOURCE_DECISION_ID,
                timestamp=_TIMESTAMP,
                targets=(PortfolioTarget(name="core", weight_bps=9999),),
            )

    def test_intent_rejects_duplicate_targets(self) -> None:
        with pytest.raises(PortfolioValidationError, match="unique"):
            AllocationIntent(
                intent_id=_INTENT_ID,
                source_decision_id=_SOURCE_DECISION_ID,
                timestamp=_TIMESTAMP,
                targets=(
                    PortfolioTarget(name="core", weight_bps=5000),
                    PortfolioTarget(name="core", weight_bps=5000),
                ),
            )

    def test_command_projects_deterministically_to_intent(self) -> None:
        command = _command()

        first = command.to_intent()
        second = command.to_intent()

        assert first.logical_values() == second.logical_values()
        assert first.targets == _targets()
        assert first.source_decision_id == _SOURCE_DECISION_ID

    def test_command_rejects_pending_source(self) -> None:
        with pytest.raises(PortfolioValidationError, match="resolved source"):
            CreateAllocationIntentCommand(
                command_id=_COMMAND_ID,
                timestamp=_TIMESTAMP,
                name=CommandName("portfolio.create-allocation-intent"),
                metadata=CommandMetadata(
                    correlation_id=_CORRELATION_ID,
                    causation_id=CausationId(_SOURCE_DECISION_ID.value),
                ),
                intent_id=_INTENT_ID,
                source_decision=_source_decision(
                    status=DecisionStatus.PENDING,
                    outcome=None,
                ),
                targets=_targets(),
            )

    def test_command_rejects_non_approved_source(self) -> None:
        with pytest.raises(PortfolioValidationError, match="approved source"):
            CreateAllocationIntentCommand(
                command_id=_COMMAND_ID,
                timestamp=_TIMESTAMP,
                name=CommandName("portfolio.create-allocation-intent"),
                metadata=CommandMetadata(
                    correlation_id=_CORRELATION_ID,
                    causation_id=CausationId(_SOURCE_DECISION_ID.value),
                ),
                intent_id=_INTENT_ID,
                source_decision=_source_decision(outcome=DecisionOutcome.BLOCKED),
                targets=_targets(),
            )

    def test_command_rejects_wrong_causation(self) -> None:
        with pytest.raises(PortfolioValidationError, match="causation"):
            CreateAllocationIntentCommand(
                command_id=_COMMAND_ID,
                timestamp=_TIMESTAMP,
                name=CommandName("portfolio.create-allocation-intent"),
                metadata=CommandMetadata(
                    correlation_id=_CORRELATION_ID,
                    causation_id=CausationId(
                        UUID("30000000-0000-0000-0000-000000000099")
                    ),
                ),
                intent_id=_INTENT_ID,
                source_decision=_source_decision(),
                targets=_targets(),
            )


class TestAllocationIntentCreatedEvent:
    def test_event_keeps_intent_and_causation(self) -> None:
        intent = _command().to_intent()
        event = AllocationIntentCreatedEvent(
            event_id=_EVENT_ID,
            timestamp=_TIMESTAMP,
            event_version=DomainEventVersion("1"),
            metadata=DomainEventMetadata(
                category=DomainEventCategory("portfolio"),
                correlation_id=_CORRELATION_ID,
                causation_id=CausationId(_SOURCE_DECISION_ID.value),
            ),
            intent=intent,
        )

        assert event.event_name == "portfolio.allocation-intent-created"
        assert event.intent is intent
        assert event.logical_values()[-1] == intent.logical_values()

    def test_event_rejects_wrong_causation(self) -> None:
        with pytest.raises(PortfolioValidationError, match="causation"):
            AllocationIntentCreatedEvent(
                event_id=_EVENT_ID,
                timestamp=_TIMESTAMP,
                event_version=DomainEventVersion("1"),
                metadata=DomainEventMetadata(
                    category=DomainEventCategory("portfolio"),
                    correlation_id=_CORRELATION_ID,
                ),
                intent=_command().to_intent(),
            )


class TestPortfolioHandlerAndModule:
    def test_handler_is_pure_and_deterministic(self) -> None:
        handler = CreateAllocationIntentHandler()
        command = _command()

        first = handler.handle(command)
        second = handler.handle(command)

        assert isinstance(first, Success)
        assert isinstance(second, Success)
        assert first.value.logical_values() == second.value.logical_values()

    def test_module_descriptor_and_handler_registration(self) -> None:
        module = PortfolioModule()
        registry = HandlerRegistry()

        registration = module.register_handlers(registry)
        registered: CommandHandler[
            CreateAllocationIntentCommand, AllocationIntent
        ] | None = registry.command_handler(CreateAllocationIntentCommand)

        assert isinstance(registration, Success)
        assert module.descriptor.name == ModuleName("portfolio")
        assert registered is module.allocation_handler

    def test_bootstrap_composes_cio_cibo_and_portfolio_and_dispatches(self) -> None:
        cio = CioModule()
        cibo = CiboModule()
        portfolio = PortfolioModule()
        boot = bootstrap(
            Configuration(application_name="qore-portfolio-test"),
            domain_modules=(cio, cibo, portfolio),
        )

        assert isinstance(boot, Success)
        dispatched: CommandResult[AllocationIntent] = (
            boot.value.domain.message_bus.dispatch_command(_command())
        )

        assert isinstance(dispatched, Success)
        assert dispatched.value.intent_id == _INTENT_ID
        assert dispatched.value.targets == _targets()
        assert boot.value.domain.module_catalog.get(ModuleName("portfolio")) is portfolio

    def test_portfolio_does_not_enter_runtime_plan(self) -> None:
        boot = bootstrap(
            Configuration(application_name="qore-portfolio-test"),
            domain_modules=(CioModule(), CiboModule(), PortfolioModule()),
        )

        assert isinstance(boot, Success)
        assert len(boot.value.runtime_plan.components) == 1
        assert boot.value.runtime_plan.components[0].component is boot.value.engine
