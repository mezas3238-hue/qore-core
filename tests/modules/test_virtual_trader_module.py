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
from qore.modules.trader.contracts import (
    ProduceVirtualTraderAnalysisCommand,
    TraderAnalysisProducedEvent,
    TraderValidationError,
)
from qore.modules.trader.module import (
    ProduceVirtualTraderAnalysisHandler,
    VirtualTraderModule,
)
from qore.specialist.analysis import (
    SpecialistAnalysis,
    SpecialistAnalysisId,
    SpecialistAnalysisStatus,
    SpecialistConfidence,
    SpecialistKind,
    SpecialistReason,
    SpecialistReasonCode,
)

_TIMESTAMP = datetime(2026, 8, 7, 22, 0, tzinfo=UTC)
_SOURCE_DECISION_ID = DecisionId(UUID("91000000-0000-0000-0000-000000000001"))
_ANALYSIS_ID = SpecialistAnalysisId(UUID("91000000-0000-0000-0000-000000000002"))
_COMMAND_ID = CommandId(UUID("91000000-0000-0000-0000-000000000003"))
_CORRELATION_ID = CorrelationId(UUID("91000000-0000-0000-0000-000000000004"))
_EVENT_ID = DomainEventId(UUID("91000000-0000-0000-0000-000000000005"))


def _source_decision(*, status: DecisionStatus = DecisionStatus.RESOLVED) -> FunctionalDecision:
    outcome = DecisionOutcome.APPROVED if status is DecisionStatus.RESOLVED else None
    reasons = (
        (
            DecisionReason(
                code=DecisionReasonCode("risk.approved"),
                summary="Internal governance approved",
            ),
        )
        if status is DecisionStatus.RESOLVED
        else ()
    )
    return FunctionalDecision(
        decision_id=_SOURCE_DECISION_ID,
        timestamp=_TIMESTAMP,
        decision_type=DecisionType("risk.governance"),
        status=status,
        priority=DecisionPriority.HIGH,
        metadata=DecisionMetadata(correlation_id=_CORRELATION_ID),
        reasons=reasons,
        outcome=outcome,
    )


def _reason() -> SpecialistReason:
    return SpecialistReason(
        code=SpecialistReasonCode("virtual-trader.explicit-inputs-aligned"),
        summary="Explicit internal inputs support the analysis",
        attributes={"source": "functional-governance"},
    )


def _command() -> ProduceVirtualTraderAnalysisCommand:
    source = _source_decision()
    return ProduceVirtualTraderAnalysisCommand(
        command_id=_COMMAND_ID,
        timestamp=_TIMESTAMP,
        name=CommandName("virtual-trader.produce-analysis"),
        metadata=CommandMetadata(
            correlation_id=_CORRELATION_ID,
            causation_id=CausationId(source.decision_id.value),
            attributes={"scope": "internal"},
        ),
        analysis_id=_ANALYSIS_ID,
        source_decision=source,
        kind=SpecialistKind("virtual-trader.structure"),
        confidence=SpecialistConfidence(0.8),
        reasons=(_reason(),),
    )


def test_command_projects_completed_analysis_with_trace() -> None:
    analysis = _command().to_analysis()

    assert analysis.analysis_id == _ANALYSIS_ID
    assert analysis.status is SpecialistAnalysisStatus.COMPLETED
    assert analysis.kind == SpecialistKind("virtual-trader.structure")
    assert analysis.confidence == SpecialistConfidence(0.8)
    assert analysis.reasons == (_reason(),)
    assert analysis.metadata.correlation_id == _CORRELATION_ID
    assert analysis.metadata.causation_id == CausationId(_SOURCE_DECISION_ID.value)
    assert tuple(analysis.metadata.attributes.items()) == (("scope", "internal"),)


def test_command_requires_resolved_source_decision() -> None:
    source = _source_decision(status=DecisionStatus.PENDING)

    with pytest.raises(TraderValidationError, match="resolved source"):
        ProduceVirtualTraderAnalysisCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("virtual-trader.produce-analysis"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION_ID,
                causation_id=CausationId(source.decision_id.value),
            ),
            analysis_id=_ANALYSIS_ID,
            source_decision=source,
            kind=SpecialistKind("virtual-trader.structure"),
            confidence=SpecialistConfidence(0.8),
            reasons=(_reason(),),
        )


def test_command_rejects_mismatched_correlation() -> None:
    source = _source_decision()
    other = CorrelationId(UUID("91000000-0000-0000-0000-000000000099"))

    with pytest.raises(TraderValidationError, match="correlation"):
        ProduceVirtualTraderAnalysisCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("virtual-trader.produce-analysis"),
            metadata=CommandMetadata(
                correlation_id=other,
                causation_id=CausationId(source.decision_id.value),
            ),
            analysis_id=_ANALYSIS_ID,
            source_decision=source,
            kind=SpecialistKind("virtual-trader.structure"),
            confidence=SpecialistConfidence(0.8),
            reasons=(_reason(),),
        )


def test_command_rejects_mismatched_causation() -> None:
    source = _source_decision()

    with pytest.raises(TraderValidationError, match="causation"):
        ProduceVirtualTraderAnalysisCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("virtual-trader.produce-analysis"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION_ID,
                causation_id=CausationId(
                    UUID("91000000-0000-0000-0000-000000000098")
                ),
            ),
            analysis_id=_ANALYSIS_ID,
            source_decision=source,
            kind=SpecialistKind("virtual-trader.structure"),
            confidence=SpecialistConfidence(0.8),
            reasons=(_reason(),),
        )


def test_command_rejects_source_identity_reuse() -> None:
    source = _source_decision()

    with pytest.raises(TraderValidationError, match="identity must differ"):
        ProduceVirtualTraderAnalysisCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("virtual-trader.produce-analysis"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION_ID,
                causation_id=CausationId(source.decision_id.value),
            ),
            analysis_id=SpecialistAnalysisId(source.decision_id.value),
            source_decision=source,
            kind=SpecialistKind("virtual-trader.structure"),
            confidence=SpecialistConfidence(0.8),
            reasons=(_reason(),),
        )


def test_command_requires_virtual_trader_kind_namespace() -> None:
    source = _source_decision()

    with pytest.raises(TraderValidationError, match="virtual-trader.* namespace"):
        ProduceVirtualTraderAnalysisCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("virtual-trader.produce-analysis"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION_ID,
                causation_id=CausationId(source.decision_id.value),
            ),
            analysis_id=_ANALYSIS_ID,
            source_decision=source,
            kind=SpecialistKind("validation.structure"),
            confidence=SpecialistConfidence(0.8),
            reasons=(_reason(),),
        )


def test_command_requires_non_empty_immutable_reasons() -> None:
    source = _source_decision()

    with pytest.raises(TraderValidationError, match="non-empty reason tuple"):
        ProduceVirtualTraderAnalysisCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("virtual-trader.produce-analysis"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION_ID,
                causation_id=CausationId(source.decision_id.value),
            ),
            analysis_id=_ANALYSIS_ID,
            source_decision=source,
            kind=SpecialistKind("virtual-trader.structure"),
            confidence=SpecialistConfidence(0.8),
            reasons=(),
        )

    with pytest.raises(TraderValidationError, match="non-empty reason tuple"):
        ProduceVirtualTraderAnalysisCommand(
            command_id=_COMMAND_ID,
            timestamp=_TIMESTAMP,
            name=CommandName("virtual-trader.produce-analysis"),
            metadata=CommandMetadata(
                correlation_id=_CORRELATION_ID,
                causation_id=CausationId(source.decision_id.value),
            ),
            analysis_id=_ANALYSIS_ID,
            source_decision=source,
            kind=SpecialistKind("virtual-trader.structure"),
            confidence=SpecialistConfidence(0.8),
            reasons=cast(tuple[SpecialistReason, ...], [_reason()]),
        )


def test_event_preserves_analysis_and_source_trace() -> None:
    analysis = _command().to_analysis()
    event = TraderAnalysisProducedEvent(
        event_id=_EVENT_ID,
        timestamp=_TIMESTAMP,
        event_version=DomainEventVersion("1"),
        metadata=DomainEventMetadata(
            category=DomainEventCategory("virtual-trader"),
            correlation_id=_CORRELATION_ID,
            causation_id=CausationId(_SOURCE_DECISION_ID.value),
        ),
        analysis=analysis,
        source_decision_id=_SOURCE_DECISION_ID,
    )

    assert event.event_name == "virtual-trader.analysis-produced"
    assert event.analysis is analysis
    assert event.source_decision_id == _SOURCE_DECISION_ID
    assert event.logical_values()[-2] == str(_SOURCE_DECISION_ID.value)
    assert event.logical_values()[-1] == analysis.logical_values()


def test_event_rejects_divergent_trace() -> None:
    analysis = _command().to_analysis()
    other_correlation = CorrelationId(
        UUID("91000000-0000-0000-0000-000000000097")
    )

    with pytest.raises(TraderValidationError, match="correlation"):
        TraderAnalysisProducedEvent(
            event_id=_EVENT_ID,
            timestamp=_TIMESTAMP,
            event_version=DomainEventVersion("1"),
            metadata=DomainEventMetadata(
                category=DomainEventCategory("virtual-trader"),
                correlation_id=other_correlation,
                causation_id=CausationId(_SOURCE_DECISION_ID.value),
            ),
            analysis=analysis,
            source_decision_id=_SOURCE_DECISION_ID,
        )

    with pytest.raises(TraderValidationError, match="causation"):
        TraderAnalysisProducedEvent(
            event_id=_EVENT_ID,
            timestamp=_TIMESTAMP,
            event_version=DomainEventVersion("1"),
            metadata=DomainEventMetadata(
                category=DomainEventCategory("virtual-trader"),
                correlation_id=_CORRELATION_ID,
                causation_id=CausationId(
                    UUID("91000000-0000-0000-0000-000000000096")
                ),
            ),
            analysis=analysis,
            source_decision_id=_SOURCE_DECISION_ID,
        )


def test_handler_is_pure_and_deterministic() -> None:
    handler = ProduceVirtualTraderAnalysisHandler()
    command = _command()

    first = handler.handle(command)
    second = handler.handle(command)

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.logical_values() == second.value.logical_values()


def test_module_descriptor_and_handler_registration() -> None:
    module = VirtualTraderModule()
    registry = HandlerRegistry()

    registration = module.register_handlers(registry)
    registered: CommandHandler[
        ProduceVirtualTraderAnalysisCommand, SpecialistAnalysis
    ] | None = registry.command_handler(ProduceVirtualTraderAnalysisCommand)

    assert isinstance(registration, Success)
    assert module.descriptor.name == ModuleName("virtual-trader")
    assert registered is module.analysis_handler


def test_bootstrap_composes_and_dispatches_virtual_trader() -> None:
    trader = VirtualTraderModule()
    boot = bootstrap(
        Configuration(application_name="qore-virtual-trader-test"),
        domain_modules=(trader,),
    )

    assert isinstance(boot, Success)
    dispatched: CommandResult[SpecialistAnalysis] = (
        boot.value.domain.message_bus.dispatch_command(_command())
    )

    assert isinstance(dispatched, Success)
    assert dispatched.value.analysis_id == _ANALYSIS_ID
    assert dispatched.value.metadata.correlation_id == _CORRELATION_ID
    assert dispatched.value.metadata.causation_id == CausationId(
        _SOURCE_DECISION_ID.value
    )
    assert boot.value.domain.module_catalog.get(ModuleName("virtual-trader")) is trader


def test_virtual_trader_does_not_enter_runtime_plan() -> None:
    boot = bootstrap(
        Configuration(application_name="qore-virtual-trader-test"),
        domain_modules=(VirtualTraderModule(),),
    )

    assert isinstance(boot, Success)
    assert len(boot.value.runtime_plan.components) == 1
    assert boot.value.runtime_plan.components[0].component is boot.value.engine


def test_virtual_trader_instances_do_not_share_handler_state() -> None:
    first = VirtualTraderModule()
    second = VirtualTraderModule()

    assert first.analysis_handler is not second.analysis_handler
