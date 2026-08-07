from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.commands import CommandId, CommandMetadata, CommandName
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
    DecisionOutcome,
    DecisionPriority,
    DecisionReason,
    DecisionReasonCode,
    DecisionStatus,
    DecisionType,
    FunctionalDecision,
)
from qore.kernel.result import Success
from qore.modules.cio.contracts import CreateCioDecisionCommand, CioDecisionProducedEvent
from qore.modules.cio.module import CioModule, CreateCioDecisionHandler

_COMMAND_ID = CommandId(UUID("10000000-0000-0000-0000-000000000001"))
_DECISION_ID = DecisionId(UUID("10000000-0000-0000-0000-000000000002"))
_CORRELATION_ID = CorrelationId(UUID("10000000-0000-0000-0000-000000000003"))
_CAUSATION_ID = CausationId(UUID("10000000-0000-0000-0000-000000000004"))
_EVENT_ID = DomainEventId(UUID("10000000-0000-0000-0000-000000000005"))
_TIMESTAMP = datetime(2026, 8, 7, 19, 0, tzinfo=UTC)


def _reason() -> DecisionReason:
    return DecisionReason(
        code=DecisionReasonCode("cio.context-accepted"),
        summary="Explicit context accepted by CIO",
        attributes={"source": "internal"},
    )


def _command(*, outcome: DecisionOutcome | None) -> CreateCioDecisionCommand:
    return CreateCioDecisionCommand(
        command_id=_COMMAND_ID,
        timestamp=_TIMESTAMP,
        name=CommandName("cio.create-decision"),
        metadata=CommandMetadata(
            correlation_id=_CORRELATION_ID,
            causation_id=_CAUSATION_ID,
            attributes={"scope": "strategic"},
        ),
        decision_id=_DECISION_ID,
        decision_type=DecisionType("cio.strategic-review"),
        priority=DecisionPriority.HIGH,
        reasons=() if outcome is None else (_reason(),),
        requested_outcome=outcome,
    )


class TestCreateCioDecisionCommand:
    def test_pending_request_projects_to_pending_functional_decision(self) -> None:
        decision = _command(outcome=None).to_decision()

        assert decision.decision_id == _DECISION_ID
        assert decision.status is DecisionStatus.PENDING
        assert decision.outcome is None
        assert decision.metadata.correlation_id == _CORRELATION_ID
        assert decision.metadata.causation_id == _CAUSATION_ID
        assert tuple(decision.metadata.attributes.items()) == (("scope", "strategic"),)

    @pytest.mark.parametrize(
        "outcome",
        [
            DecisionOutcome.APPROVED,
            DecisionOutcome.REJECTED,
            DecisionOutcome.BLOCKED,
            DecisionOutcome.DEGRADED,
        ],
    )
    def test_resolved_request_projects_every_shared_outcome(
        self,
        outcome: DecisionOutcome,
    ) -> None:
        decision = _command(outcome=outcome).to_decision()

        assert decision.status is DecisionStatus.RESOLVED
        assert decision.outcome is outcome
        assert decision.reasons == (_reason(),)

    def test_resolved_request_requires_reason(self) -> None:
        with pytest.raises(ValueError, match="requires at least one reason"):
            CreateCioDecisionCommand(
                command_id=_COMMAND_ID,
                timestamp=_TIMESTAMP,
                name=CommandName("cio.create-decision"),
                metadata=CommandMetadata(correlation_id=_CORRELATION_ID),
                decision_id=_DECISION_ID,
                decision_type=DecisionType("cio.strategic-review"),
                priority=DecisionPriority.NORMAL,
                requested_outcome=DecisionOutcome.APPROVED,
            )


class TestCioDecisionProducedEvent:
    def test_event_keeps_explicit_identity_time_and_decision(self) -> None:
        decision = _command(outcome=DecisionOutcome.APPROVED).to_decision()
        event = CioDecisionProducedEvent(
            event_id=_EVENT_ID,
            timestamp=_TIMESTAMP,
            event_version=DomainEventVersion("1"),
            metadata=DomainEventMetadata(
                category=DomainEventCategory("cio"),
                correlation_id=_CORRELATION_ID,
                causation_id=_CAUSATION_ID,
            ),
            decision=decision,
        )

        assert event.domain_event_id == _EVENT_ID
        assert event.timestamp == _TIMESTAMP
        assert event.event_name == "cio.decision-produced"
        assert event.decision is decision
        assert event.logical_values()[-1] == decision.logical_values()


class TestCioHandlerAndModule:
    def test_handler_is_pure_and_deterministic(self) -> None:
        handler = CreateCioDecisionHandler()
        command = _command(outcome=DecisionOutcome.APPROVED)

        first = handler.handle(command)
        second = handler.handle(command)

        assert isinstance(first, Success)
        assert isinstance(second, Success)
        assert first.value.logical_values() == second.value.logical_values()

    def test_module_descriptor_and_handler_registration(self) -> None:
        module = CioModule()
        registry = HandlerRegistry()

        registration = module.register_handlers(registry)

        assert isinstance(registration, Success)
        assert module.descriptor.name == ModuleName("cio")
        assert registry.command_handler(CreateCioDecisionCommand) is module.decision_handler

    def test_bootstrap_composes_cio_and_dispatches_through_official_bus(self) -> None:
        module = CioModule()
        boot = bootstrap(
            Configuration(application_name="qore-cio-test"),
            domain_modules=(module,),
        )

        assert isinstance(boot, Success)
        dispatched = boot.value.domain.message_bus.dispatch_command[
            CreateCioDecisionCommand, FunctionalDecision
        ](_command(outcome=DecisionOutcome.APPROVED))

        assert isinstance(dispatched, Success)
        assert dispatched.value.outcome is DecisionOutcome.APPROVED
        assert dispatched.value.metadata.correlation_id == _CORRELATION_ID
        assert dispatched.value.metadata.causation_id == _CAUSATION_ID
        assert boot.value.domain.module_catalog.get(ModuleName("cio")) is module

    def test_cio_module_does_not_enter_runtime_plan(self) -> None:
        module = CioModule()
        boot = bootstrap(
            Configuration(application_name="qore-cio-test"),
            domain_modules=(module,),
        )

        assert isinstance(boot, Success)
        assert len(boot.value.runtime_plan.components) == 1
        assert boot.value.runtime_plan.components[0].component is boot.value.engine
