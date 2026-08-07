from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
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
    DecisionOutcome,
    DecisionType,
    FunctionalDecision,
)
from qore.kernel.result import Success
from qore.modules.cibo.module import CiboModule
from qore.modules.cio.module import CioModule
from qore.modules.portfolio.contracts import (
    AllocationIntent,
    AllocationIntentId,
    PortfolioTarget,
)
from qore.modules.portfolio.module import PortfolioModule
from qore.modules.risk.contracts import (
    AssessAllocationRiskCommand,
    RiskDecisionProducedEvent,
    RiskPolicy,
    RiskPolicyId,
    RiskValidationError,
)
from qore.modules.risk.module import AssessAllocationRiskHandler, RiskModule

_INTENT_ID = AllocationIntentId(UUID("40000000-0000-0000-0000-000000000001"))
_DECISION_ID = DecisionId(UUID("40000000-0000-0000-0000-000000000002"))
_POLICY_ID = RiskPolicyId(UUID("40000000-0000-0000-0000-000000000003"))
_COMMAND_ID = CommandId(UUID("40000000-0000-0000-0000-000000000004"))
_CORRELATION_ID = CorrelationId(UUID("40000000-0000-0000-0000-000000000005"))
_OTHER_CORRELATION_ID = CorrelationId(UUID("40000000-0000-0000-0000-000000000006"))
_EVENT_ID = DomainEventId(UUID("40000000-0000-0000-0000-000000000007"))
_SOURCE_DECISION_ID = DecisionId(UUID("40000000-0000-0000-0000-000000000008"))
_TIMESTAMP = datetime(2026, 8, 7, 22, 0, tzinfo=UTC)


def _policy() -> RiskPolicy:
    return RiskPolicy(
        policy_id=_POLICY_ID,
        soft_single_target_limit_bps=7_000,
        hard_single_target_limit_bps=8_000,
    )


def _intent(peak_weight_bps: int) -> AllocationIntent:
    return AllocationIntent(
        intent_id=_INTENT_ID,
        source_decision_id=_SOURCE_DECISION_ID,
        correlation_id=_CORRELATION_ID,
        timestamp=_TIMESTAMP,
        targets=(
            PortfolioTarget(name="core", weight_bps=peak_weight_bps),
            PortfolioTarget(name="reserve", weight_bps=10_000 - peak_weight_bps),
        ),
    )


def _command(peak_weight_bps: int) -> AssessAllocationRiskCommand:
    return AssessAllocationRiskCommand(
        command_id=_COMMAND_ID,
        timestamp=_TIMESTAMP,
        name=CommandName("risk.assess-allocation"),
        metadata=CommandMetadata(
            correlation_id=_CORRELATION_ID,
            causation_id=CausationId(_INTENT_ID.value),
        ),
        decision_id=_DECISION_ID,
        allocation_intent=_intent(peak_weight_bps),
        policy=_policy(),
    )


class TestRiskPolicy:
    def test_policy_rejects_non_integer_limits(self) -> None:
        with pytest.raises(RiskValidationError, match="soft limit must be an integer"):
            RiskPolicy(
                policy_id=_POLICY_ID,
                soft_single_target_limit_bps=cast(int, True),
                hard_single_target_limit_bps=8_000,
            )

    def test_policy_rejects_soft_above_hard(self) -> None:
        with pytest.raises(RiskValidationError, match="must not exceed"):
            RiskPolicy(
                policy_id=_POLICY_ID,
                soft_single_target_limit_bps=8_001,
                hard_single_target_limit_bps=8_000,
            )


class TestAssessAllocationRiskCommand:
    @pytest.mark.parametrize(
        ("peak_weight_bps", "expected"),
        [
            (7_000, DecisionOutcome.APPROVED),
            (7_500, DecisionOutcome.DEGRADED),
            (8_001, DecisionOutcome.BLOCKED),
        ],
    )
    def test_policy_evaluation_is_deterministic(
        self,
        peak_weight_bps: int,
        expected: DecisionOutcome,
    ) -> None:
        command = _command(peak_weight_bps)

        first = command.to_decision()
        second = command.to_decision()

        assert first.outcome is expected
        assert first.logical_values() == second.logical_values()
        assert first.decision_type == DecisionType("risk.allocation-governance")
        assert first.metadata.correlation_id == _CORRELATION_ID
        assert first.metadata.causation_id == CausationId(_INTENT_ID.value)
        assert first.metadata.attributes["policy_id"] == _POLICY_ID.value

    def test_command_rejects_source_identity_reuse(self) -> None:
        with pytest.raises(RiskValidationError, match="identity"):
            AssessAllocationRiskCommand(
                command_id=_COMMAND_ID,
                timestamp=_TIMESTAMP,
                name=CommandName("risk.assess-allocation"),
                metadata=CommandMetadata(
                    correlation_id=_CORRELATION_ID,
                    causation_id=CausationId(_INTENT_ID.value),
                ),
                decision_id=DecisionId(_INTENT_ID.value),
                allocation_intent=_intent(7_000),
                policy=_policy(),
            )

    def test_command_rejects_wrong_correlation(self) -> None:
        with pytest.raises(RiskValidationError, match="correlation"):
            AssessAllocationRiskCommand(
                command_id=_COMMAND_ID,
                timestamp=_TIMESTAMP,
                name=CommandName("risk.assess-allocation"),
                metadata=CommandMetadata(
                    correlation_id=_OTHER_CORRELATION_ID,
                    causation_id=CausationId(_INTENT_ID.value),
                ),
                decision_id=_DECISION_ID,
                allocation_intent=_intent(7_000),
                policy=_policy(),
            )

    def test_command_rejects_wrong_causation(self) -> None:
        with pytest.raises(RiskValidationError, match="causation"):
            AssessAllocationRiskCommand(
                command_id=_COMMAND_ID,
                timestamp=_TIMESTAMP,
                name=CommandName("risk.assess-allocation"),
                metadata=CommandMetadata(
                    correlation_id=_CORRELATION_ID,
                    causation_id=CausationId(
                        UUID("40000000-0000-0000-0000-000000000099")
                    ),
                ),
                decision_id=_DECISION_ID,
                allocation_intent=_intent(7_000),
                policy=_policy(),
            )


class TestRiskDecisionProducedEvent:
    def test_event_preserves_correlation_and_source_intent(self) -> None:
        decision = _command(7_000).to_decision()
        event = RiskDecisionProducedEvent(
            event_id=_EVENT_ID,
            timestamp=_TIMESTAMP,
            event_version=DomainEventVersion("1"),
            metadata=DomainEventMetadata(
                category=DomainEventCategory("risk"),
                correlation_id=_CORRELATION_ID,
                causation_id=CausationId(_INTENT_ID.value),
            ),
            decision=decision,
            source_intent_id=_INTENT_ID,
        )

        assert event.event_name == "risk.decision-produced"
        assert event.source_intent_id == _INTENT_ID
        assert event.decision is decision
        assert event.logical_values()[-2] == str(_INTENT_ID.value)
        assert event.logical_values()[-1] == decision.logical_values()

    def test_event_rejects_wrong_correlation(self) -> None:
        with pytest.raises(RiskValidationError, match="correlation"):
            RiskDecisionProducedEvent(
                event_id=_EVENT_ID,
                timestamp=_TIMESTAMP,
                event_version=DomainEventVersion("1"),
                metadata=DomainEventMetadata(
                    category=DomainEventCategory("risk"),
                    correlation_id=_OTHER_CORRELATION_ID,
                    causation_id=CausationId(_INTENT_ID.value),
                ),
                decision=_command(7_000).to_decision(),
                source_intent_id=_INTENT_ID,
            )


class TestRiskHandlerAndModule:
    def test_handler_is_pure_and_deterministic(self) -> None:
        handler = AssessAllocationRiskHandler()
        command = _command(7_500)

        first = handler.handle(command)
        second = handler.handle(command)

        assert isinstance(first, Success)
        assert isinstance(second, Success)
        assert first.value.logical_values() == second.value.logical_values()

    def test_module_descriptor_and_handler_registration(self) -> None:
        module = RiskModule()
        registry = HandlerRegistry()

        registration = module.register_handlers(registry)
        registered: CommandHandler[
            AssessAllocationRiskCommand, FunctionalDecision
        ] | None = registry.command_handler(AssessAllocationRiskCommand)

        assert isinstance(registration, Success)
        assert module.descriptor.name == ModuleName("risk")
        assert registered is module.assessment_handler

    def test_bootstrap_composes_full_foundation_and_dispatches_risk(self) -> None:
        cio = CioModule()
        cibo = CiboModule()
        portfolio = PortfolioModule()
        risk = RiskModule()
        boot = bootstrap(
            Configuration(application_name="qore-risk-test"),
            domain_modules=(cio, cibo, portfolio, risk),
        )

        assert isinstance(boot, Success)
        dispatched: CommandResult[FunctionalDecision] = (
            boot.value.domain.message_bus.dispatch_command(_command(7_500))
        )

        assert isinstance(dispatched, Success)
        assert dispatched.value.outcome is DecisionOutcome.DEGRADED
        assert dispatched.value.metadata.correlation_id == _CORRELATION_ID
        assert boot.value.domain.module_catalog.get(ModuleName("risk")) is risk

    def test_risk_does_not_enter_runtime_plan(self) -> None:
        boot = bootstrap(
            Configuration(application_name="qore-risk-test"),
            domain_modules=(CioModule(), CiboModule(), PortfolioModule(), RiskModule()),
        )

        assert isinstance(boot, Success)
        assert len(boot.value.runtime_plan.components) == 1
        assert boot.value.runtime_plan.components[0].component is boot.value.engine
