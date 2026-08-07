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
from qore.modules.cibo.contracts import (
    CiboDecisionProducedEvent,
    CiboValidationError,
    ReviewFunctionalDecisionCommand,
)
from qore.modules.cibo.module import CiboModule, ReviewFunctionalDecisionHandler
from qore.modules.cio.module import CioModule

_SOURCE_DECISION_ID = DecisionId(UUID("20000000-0000-0000-0000-000000000001"))
_CIBO_DECISION_ID = DecisionId(UUID("20000000-0000-0000-0000-000000000002"))
_COMMAND_ID = CommandId(UUID("20000000-0000-0000-0000-000000000003"))
_CORRELATION_ID = CorrelationId(UUID("20000000-0000-0000-0000-000000000004"))
_OTHER_CORRELATION_ID = CorrelationId(UUID("20000000-0000-0000-0000-000000000005"))
_EVENT_ID = DomainEventId(UUID("20000000-0000-0000-0000-000000000006"))
_TIMESTAMP = datetime(2026, 8, 7, 20, 0, tzinfo=UTC)


def _source_decision() -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=_SOURCE_DECISION_ID,
        timestamp=_TIMESTAMP,
        decision_type=DecisionType("cio.strategic-review"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.HIGH,
        metadata=DecisionMetadata(correlation_id=_CORRELATION_ID),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("cio.context-accepted"),
                summary="Strategic context accepted",
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )


def _pending_source_decision() -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=_SOURCE_DECISION_ID,
        timestamp=_TIMESTAMP,
        decision_type=DecisionType("cio.strategic-review"),
        status=DecisionStatus.PENDING,
        priority=DecisionPriority.HIGH,
        metadata=DecisionMetadata(correlation_id=_CORRELATION_ID),
    )


def _reason() -> DecisionReason:
    return DecisionReason(
        code=DecisionReasonCode("cibo.business-accepted"),
        summary="Business review accepted",
        attributes={"scope": "portfolio"},
    )


def _command(*, outcome: DecisionOutcome | None) -> ReviewFunctionalDecisionCommand:
    return ReviewFunctionalDecisionCommand(
        command_id=_COMMAND_ID,
        timestamp=_TIMESTAMP,
        name=CommandName("cibo.review-functional-decision"),
        metadata=CommandMetadata(
            correlation_id=_CORRELATION_ID,
            attributes={"channel": "internal"},
        ),
        decision_id=_CIBO_DECISION_ID,
        source_decision=_source_decision(),
        priority=DecisionPriority.NORMAL,
        reasons=() if outcome is None else (_reason(),),
        requested_outcome=outcome,
    )


class TestReviewFunctionalDecisionCommand:
    def test_pending_review_preserves_correlation_and_sets_source_causation(self) -> None:
        decision = _command(outcome=None).to_decision()

        assert decision.decision_id == _CIBO_DECISION_ID
        assert decision.decision_type == DecisionType("cibo.business-review")
        assert decision.status is DecisionStatus.PENDING
        assert decision.outcome is None
        assert decision.metadata.correlation_id == _CORRELATION_ID
        assert decision.metadata.causation_id == CausationId(_SOURCE_DECISION_ID.value)
        assert tuple(decision.metadata.attributes.items()) == (("channel", "internal"),)

    @pytest.mark.parametrize(
        "outcome",
        [
            DecisionOutcome.APPROVED,
            DecisionOutcome.REJECTED,
            DecisionOutcome.BLOCKED,
            DecisionOutcome.DEGRADED,
        ],
    )
    def test_resolved_review_supports_shared_outcomes(
        self,
        outcome: DecisionOutcome,
    ) -> None:
        decision = _command(outcome=outcome).to_decision()

        assert decision.status is DecisionStatus.RESOLVED
        assert decision.outcome is outcome
        assert decision.reasons == (_reason(),)

    def test_command_requires_resolved_source_decision(self) -> None:
        with pytest.raises(CiboValidationError, match="resolved source"):
            ReviewFunctionalDecisionCommand(
                command_id=_COMMAND_ID,
                timestamp=_TIMESTAMP,
                name=CommandName("cibo.review-functional-decision"),
                metadata=CommandMetadata(correlation_id=_CORRELATION_ID),
                decision_id=_CIBO_DECISION_ID,
                source_decision=_pending_source_decision(),
                priority=DecisionPriority.NORMAL,
            )

    def test_command_rejects_reusing_source_identity(self) -> None:
        with pytest.raises(CiboValidationError, match="identity"):
            ReviewFunctionalDecisionCommand(
                command_id=_COMMAND_ID,
                timestamp=_TIMESTAMP,
                name=CommandName("cibo.review-functional-decision"),
                metadata=CommandMetadata(correlation_id=_CORRELATION_ID),
                decision_id=_SOURCE_DECISION_ID,
                source_decision=_source_decision(),
                priority=DecisionPriority.NORMAL,
            )

    def test_command_rejects_mismatched_correlation(self) -> None:
        with pytest.raises(CiboValidationError, match="correlation"):
            ReviewFunctionalDecisionCommand(
                command_id=_COMMAND_ID,
                timestamp=_TIMESTAMP,
                name=CommandName("cibo.review-functional-decision"),
                metadata=CommandMetadata(correlation_id=_OTHER_CORRELATION_ID),
                decision_id=_CIBO_DECISION_ID,
                source_decision=_source_decision(),
                priority=DecisionPriority.NORMAL,
            )

    def test_resolved_review_requires_reason(self) -> None:
        with pytest.raises(CiboValidationError, match="at least one reason"):
            ReviewFunctionalDecisionCommand(
                command_id=_COMMAND_ID,
                timestamp=_TIMESTAMP,
                name=CommandName("cibo.review-functional-decision"),
                metadata=CommandMetadata(correlation_id=_CORRELATION_ID),
                decision_id=_CIBO_DECISION_ID,
                source_decision=_source_decision(),
                priority=DecisionPriority.NORMAL,
                requested_outcome=DecisionOutcome.APPROVED,
            )


class TestCiboDecisionProducedEvent:
    def test_event_keeps_source_identity_and_decision(self) -> None:
        decision = _command(outcome=DecisionOutcome.APPROVED).to_decision()
        event = CiboDecisionProducedEvent(
            event_id=_EVENT_ID,
            timestamp=_TIMESTAMP,
            event_version=DomainEventVersion("1"),
            metadata=DomainEventMetadata(
                category=DomainEventCategory("cibo"),
                correlation_id=_CORRELATION_ID,
                causation_id=CausationId(_SOURCE_DECISION_ID.value),
            ),
            decision=decision,
            source_decision_id=_SOURCE_DECISION_ID,
        )

        assert event.event_name == "cibo.decision-produced"
        assert event.source_decision_id == _SOURCE_DECISION_ID
        assert event.decision is decision
        assert event.logical_values()[-2] == str(_SOURCE_DECISION_ID.value)
        assert event.logical_values()[-1] == decision.logical_values()

    def test_event_rejects_source_different_from_decision_causation(self) -> None:
        decision = _command(outcome=DecisionOutcome.APPROVED).to_decision()
        other_source = DecisionId(UUID("20000000-0000-0000-0000-000000000007"))

        with pytest.raises(CiboValidationError, match="source"):
            CiboDecisionProducedEvent(
                event_id=_EVENT_ID,
                timestamp=_TIMESTAMP,
                event_version=DomainEventVersion("1"),
                metadata=DomainEventMetadata(
                    category=DomainEventCategory("cibo"),
                    correlation_id=_CORRELATION_ID,
                    causation_id=CausationId(other_source.value),
                ),
                decision=decision,
                source_decision_id=other_source,
            )

    def test_event_requires_metadata_causation_to_match_source(self) -> None:
        decision = _command(outcome=DecisionOutcome.APPROVED).to_decision()

        with pytest.raises(CiboValidationError, match="event causation"):
            CiboDecisionProducedEvent(
                event_id=_EVENT_ID,
                timestamp=_TIMESTAMP,
                event_version=DomainEventVersion("1"),
                metadata=DomainEventMetadata(
                    category=DomainEventCategory("cibo"),
                    correlation_id=_CORRELATION_ID,
                    causation_id=None,
                ),
                decision=decision,
                source_decision_id=_SOURCE_DECISION_ID,
            )


class TestCiboHandlerAndModule:
    def test_handler_is_pure_and_deterministic(self) -> None:
        handler = ReviewFunctionalDecisionHandler()
        command = _command(outcome=DecisionOutcome.APPROVED)

        first = handler.handle(command)
        second = handler.handle(command)

        assert isinstance(first, Success)
        assert isinstance(second, Success)
        assert first.value.logical_values() == second.value.logical_values()

    def test_module_descriptor_and_handler_registration(self) -> None:
        module = CiboModule()
        registry = HandlerRegistry()

        registration = module.register_handlers(registry)
        registered: CommandHandler[
            ReviewFunctionalDecisionCommand, FunctionalDecision
        ] | None = registry.command_handler(ReviewFunctionalDecisionCommand)

        assert isinstance(registration, Success)
        assert module.descriptor.name == ModuleName("cibo")
        assert registered is module.review_handler

    def test_bootstrap_composes_cio_and_cibo_and_dispatches_cibo(self) -> None:
        cio = CioModule()
        cibo = CiboModule()
        boot = bootstrap(
            Configuration(application_name="qore-cibo-test"),
            domain_modules=(cio, cibo),
        )

        assert isinstance(boot, Success)
        dispatched: CommandResult[FunctionalDecision] = (
            boot.value.domain.message_bus.dispatch_command(
                _command(outcome=DecisionOutcome.APPROVED)
            )
        )

        assert isinstance(dispatched, Success)
        assert dispatched.value.decision_type == DecisionType("cibo.business-review")
        assert dispatched.value.metadata.correlation_id == _CORRELATION_ID
        assert dispatched.value.metadata.causation_id == CausationId(
            _SOURCE_DECISION_ID.value
        )
        assert boot.value.domain.module_catalog.get(ModuleName("cibo")) is cibo

    def test_cibo_does_not_enter_runtime_plan(self) -> None:
        boot = bootstrap(
            Configuration(application_name="qore-cibo-test"),
            domain_modules=(CioModule(), CiboModule()),
        )

        assert isinstance(boot, Success)
        assert len(boot.value.runtime_plan.components) == 1
        assert boot.value.runtime_plan.components[0].component is boot.value.engine
