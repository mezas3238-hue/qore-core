from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from uuid import UUID

import pytest

from qore.domain.events import CausationId, CorrelationId
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
from qore.infrastructure.historical_dataset import (
    HistoricalDatasetId,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
    HistoricalOhlcDatasetScope,
    build_historical_ohlc_replay_dataset,
)
from qore.infrastructure.historical_market_data import HistoricalOhlcWindow
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.replay_availability import (
    ReplayAvailabilityBasis,
    ReplayAvailabilityEvidenceReference,
    ReplayMarketDataObservation,
    ReplayObservationId,
)
from qore.infrastructure.research_analysis_lineage import (
    ResearchAnalysisLineageRecord,
    compute_research_trader_command_fingerprint,
    construct_research_trader_command,
    verify_command_reproducibility,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
    ResearchSpecialistEvaluatorFamily,
    ResearchSpecialistEvaluatorIdentity,
    ResearchSpecialistEvaluatorSchemaVersion,
)
from qore.infrastructure.research_execution_session import ResearchExecutionSession
from qore.infrastructure.research_execution_trace import ResearchExecutionTrace
from qore.infrastructure.research_lineage_errors import ResearchLineageValidationError
from qore.infrastructure.research_run import (
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    build_research_run_evidence,
)
from qore.infrastructure.research_schedule import SCHEDULE_A_V1, W1_NO_WARMUP_V1
from qore.infrastructure.research_specialist_boundary import (
    ResearchAnalysisInputEvidence,
    ResearchAnalysisSpecification,
)
from qore.infrastructure.research_strategy_freeze import (
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyParameter,
    ResearchStrategySchemaVersion,
    build_research_run_strategy_binding,
    build_research_strategy_configuration_manifest,
)
from qore.infrastructure.research_strategy_state import ResearchStrategyState
from qore.infrastructure.research_transition_evidence import ResearchStateTransitionEvidence
from qore.kernel.result import Success
from qore.specialist.analysis import (
    SpecialistAnalysisId,
    SpecialistConfidence,
    SpecialistKind,
    SpecialistReason,
    SpecialistReasonCode,
)


_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_REVISION = ResearchSoftwareRevision("revision-1")


@dataclass(frozen=True, slots=True)
class _Content:
    value: int

    def logical_values(self) -> Mapping[str, object]:
        return {"value": self.value}


def _decision_identity() -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily("test.reference"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=_REVISION,
    )


def _specialist_identity() -> ResearchSpecialistEvaluatorIdentity:
    return ResearchSpecialistEvaluatorIdentity(
        family=ResearchSpecialistEvaluatorFamily("test.specialist"),
        schema_version=ResearchSpecialistEvaluatorSchemaVersion("v1"),
        software_revision=_REVISION,
    )


def _state(sequence: int) -> ResearchStrategyState:
    return ResearchStrategyState(
        evaluator_identity=_decision_identity(),
        evaluation_sequence_number=sequence,
        state_schema_version="v1",
        exact_content=_Content(sequence),
    )


def _decision(status: DecisionStatus = DecisionStatus.RESOLVED) -> FunctionalDecision:
    resolved = status is DecisionStatus.RESOLVED
    return FunctionalDecision(
        decision_id=DecisionId(UUID("5a000000-0000-0000-0000-000000000001")),
        timestamp=_BASE + timedelta(minutes=5),
        decision_type=DecisionType("research.test"),
        status=status,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(
            correlation_id=CorrelationId(
                UUID("5a000000-0000-0000-0000-000000000002")
            ),
            attributes=MappingProxyType({}),
        ),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("research.test"),
                summary="resolved decision",
                attributes=MappingProxyType({}),
            ),
        )
        if resolved
        else (),
        outcome=DecisionOutcome.APPROVED if resolved else None,
    )


def _session() -> ResearchExecutionSession:
    source = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("5a000000-0000-0000-0000-000000000010")),
        source_id=SourceId(UUID("5a000000-0000-0000-0000-000000000011")),
        port_name=PortName("market-data.lineage-test"),
    )
    instrument = Instrument("EURUSD")
    timeframe = Timeframe(300)
    snapshot = OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID("5a000000-0000-0000-0000-000000000012")
        ),
        instrument=instrument,
        source=source,
        timeframe=timeframe,
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=5),
        open=1.10,
        high=1.11,
        low=1.09,
        close=1.105,
    )
    observation = ReplayMarketDataObservation(
        observation_id=ReplayObservationId(
            UUID("5a000000-0000-0000-0000-000000000013")
        ),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=snapshot.closed_at,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(
            UUID("5a000000-0000-0000-0000-000000000014")
        ),
    )
    dataset_result = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(
            UUID("5a000000-0000-0000-0000-000000000015")
        ),
        revision_id=HistoricalDatasetRevisionId(
            UUID("5a000000-0000-0000-0000-000000000016")
        ),
        parent_revision_id=None,
        revision_reason=None,
        scope=HistoricalOhlcDatasetScope(
            source=source,
            window=HistoricalOhlcWindow(
                instrument=instrument,
                timeframe=timeframe,
                opened_at=_BASE,
                closed_at=_BASE + timedelta(minutes=15),
            ),
        ),
        assembled_at=_BASE + timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion("canonical-v1"),
        observations=(observation,),
    )
    assert isinstance(dataset_result, Success)
    configuration_id = ResearchStrategyConfigurationId(
        UUID("5a000000-0000-0000-0000-000000000017")
    )
    manifest_result = build_research_strategy_configuration_manifest(
        configuration_id=configuration_id,
        schema_version=ResearchStrategySchemaVersion("v1"),
        parameters=(ResearchStrategyParameter("alpha", 1),),
        frozen_at=_BASE + timedelta(hours=1),
        evidence_ref=ResearchStrategyFreezeEvidenceReference(
            UUID("5a000000-0000-0000-0000-000000000018")
        ),
    )
    assert isinstance(manifest_result, Success)
    run_result = build_research_run_evidence(
        run_id=ResearchRunId(UUID("5a000000-0000-0000-0000-000000000019")),
        created_at=_BASE + timedelta(days=2),
        datasets=(dataset_result.value.manifest,),
        replay_policy_version=ResearchReplayPolicyVersion("point-in-time-v1"),
        simulated_start=_BASE,
        simulated_end=_BASE + timedelta(minutes=10),
        strategy_configuration_id=configuration_id,
        software_revision=_REVISION,
        execution_model_id=None,
        transaction_cost_model_id=None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    assert isinstance(run_result, Success)
    binding_result = build_research_run_strategy_binding(
        run=run_result.value,
        manifest=manifest_result.value,
    )
    assert isinstance(binding_result, Success)
    return ResearchExecutionSession(
        strategy_binding=binding_result.value,
        replay_datasets=(dataset_result.value,),
    )


def _trace(status: DecisionStatus = DecisionStatus.RESOLVED) -> ResearchExecutionTrace:
    session = _session()
    initial = _state(0)
    final = _state(1)
    transition = ResearchStateTransitionEvidence(
        evaluation_sequence_number=0,
        evaluator_identity=_decision_identity(),
        simulated_now=session.qualified_observations[0].observation.available_at,
        prior_state=initial,
        newly_visible_inputs=session.qualified_observations,
        next_state=final,
        decisions=(_decision(status),),
    )
    return ResearchExecutionTrace(
        execution_session=session,
        evaluator_identity=_decision_identity(),
        start_policy=W1_NO_WARMUP_V1,
        schedule_semantics=SCHEDULE_A_V1,
        initial_state=initial,
        transitions=(transition,),
        final_state=final,
    )


def _reason(code: str = "research.analysis") -> SpecialistReason:
    return SpecialistReason(
        code=SpecialistReasonCode(code),
        summary=code,
        attributes=MappingProxyType({}),
    )


def _evidence(trace: ResearchExecutionTrace, reason: str = "research.analysis") -> ResearchAnalysisInputEvidence:
    return ResearchAnalysisInputEvidence(
        evaluator_identity=_specialist_identity(),
        source_decision=trace.transitions[0].decisions[0],
        analysis_specification=ResearchAnalysisSpecification(
            kind=SpecialistKind("virtual-trader.research"),
            confidence=SpecialistConfidence(0.75),
            reasons=(_reason(reason),),
        ),
    )


def test_deterministic_command_reconstruction_preserves_domain_provenance() -> None:
    trace = _trace()
    evidence = _evidence(trace)
    command = construct_research_trader_command(trace, 0, 0, evidence)
    selected = trace.transitions[0].decisions[0]
    assert command.metadata.correlation_id == selected.metadata.correlation_id
    assert command.metadata.causation_id == CausationId(selected.decision_id.value)
    assert verify_command_reproducibility(command, trace, 0, 0, evidence)
    assert compute_research_trader_command_fingerprint(command).value


def test_specialist_content_changes_deterministic_command_identity() -> None:
    trace = _trace()
    first = construct_research_trader_command(trace, 0, 0, _evidence(trace, "research.a"))
    second = construct_research_trader_command(trace, 0, 0, _evidence(trace, "research.b"))
    assert first.command_id != second.command_id
    assert first.analysis_id != second.analysis_id


def test_lineage_record_requires_exact_command_and_analysis_chain() -> None:
    trace = _trace()
    evidence = _evidence(trace)
    command = construct_research_trader_command(trace, 0, 0, evidence)
    analysis = command.to_analysis()
    record = ResearchAnalysisLineageRecord(
        trace=trace,
        decision_transition_index=0,
        decision_index_within_transition=0,
        analysis_input_evidence=evidence,
        trader_command=command,
        analysis=analysis,
    )
    assert record.lineage_fingerprint.value

    wrong_analysis = replace(
        analysis,
        analysis_id=SpecialistAnalysisId(
            UUID("5a000000-0000-0000-0000-000000000099")
        ),
    )
    with pytest.raises(ResearchLineageValidationError):
        ResearchAnalysisLineageRecord(
            trace=trace,
            decision_transition_index=0,
            decision_index_within_transition=0,
            analysis_input_evidence=evidence,
            trader_command=command,
            analysis=wrong_analysis,
        )


def test_pending_decision_cannot_enter_analysis_lineage() -> None:
    trace = _trace(DecisionStatus.PENDING)
    evidence = _evidence(trace)
    with pytest.raises(ResearchLineageValidationError):
        construct_research_trader_command(trace, 0, 0, evidence)


def test_lineage_indices_fail_closed_before_indexing() -> None:
    trace = _trace()
    evidence = _evidence(trace)
    command = construct_research_trader_command(trace, 0, 0, evidence)
    with pytest.raises(ResearchLineageValidationError):
        ResearchAnalysisLineageRecord(
            trace=trace,
            decision_transition_index=99,
            decision_index_within_transition=0,
            analysis_input_evidence=evidence,
            trader_command=command,
            analysis=command.to_analysis(),
        )
