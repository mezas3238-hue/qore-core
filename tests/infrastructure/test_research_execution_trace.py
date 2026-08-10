from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.functional.decisions import FunctionalDecision
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
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_execution_session import (
    QualifiedReplayObservation,
    ResearchExecutionSession,
)
from qore.infrastructure.research_execution_trace import (
    ResearchExecutionTrace,
    verify_trace_reproducibility,
)
from qore.infrastructure.research_lineage_errors import (
    ResearchEvaluatorIdentityMismatchError,
    ResearchExecutionTraceValidationError,
    ResearchLineageValidationError,
)
from qore.infrastructure.research_run import (
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    build_research_run_evidence,
)
from qore.infrastructure.research_schedule import (
    SCHEDULE_A_V1,
    W1_NO_WARMUP_V1,
    ResearchStartPolicy,
)
from qore.infrastructure.research_strategy_freeze import (
    ResearchRunStrategyBinding,
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyParameter,
    ResearchStrategySchemaVersion,
    build_research_run_strategy_binding,
    build_research_strategy_configuration_manifest,
)
from qore.infrastructure.research_strategy_state import ResearchStrategyState
from qore.infrastructure.research_transition_evidence import ResearchStateTransitionEvidence
from qore.kernel.result import Success

_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_REVISION = ResearchSoftwareRevision("revision-1")


@dataclass(frozen=True, slots=True)
class _Content:
    value: int

    def logical_values(self) -> Mapping[str, object]:
        return {"value": self.value}


def _identity(family: str = "test.reference") -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily(family),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=_REVISION,
    )


def _session() -> ResearchExecutionSession:
    source = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("59000000-0000-0000-0000-000000000001")),
        source_id=SourceId(UUID("59000000-0000-0000-0000-000000000002")),
        port_name=PortName("market-data.research-trace-test"),
    )
    instrument = Instrument("EURUSD")
    timeframe = Timeframe(300)
    snapshot = OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(
            UUID("59000000-0000-0000-0000-000000000003")
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
            UUID("59000000-0000-0000-0000-000000000004")
        ),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=snapshot.closed_at,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(
            UUID("59000000-0000-0000-0000-000000000005")
        ),
    )
    scope = HistoricalOhlcDatasetScope(
        source=source,
        window=HistoricalOhlcWindow(
            instrument=instrument,
            timeframe=timeframe,
            opened_at=_BASE,
            closed_at=_BASE + timedelta(minutes=15),
        ),
    )
    dataset_result = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(
            UUID("59000000-0000-0000-0000-000000000006")
        ),
        revision_id=HistoricalDatasetRevisionId(
            UUID("59000000-0000-0000-0000-000000000007")
        ),
        parent_revision_id=None,
        revision_reason=None,
        scope=scope,
        assembled_at=_BASE + timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion("canonical-v1"),
        observations=(observation,),
    )
    assert isinstance(dataset_result, Success)
    configuration_id = ResearchStrategyConfigurationId(
        UUID("59000000-0000-0000-0000-000000000008")
    )
    manifest_result = build_research_strategy_configuration_manifest(
        configuration_id=configuration_id,
        schema_version=ResearchStrategySchemaVersion("v1"),
        parameters=(ResearchStrategyParameter("alpha", 1),),
        frozen_at=_BASE + timedelta(hours=1),
        evidence_ref=ResearchStrategyFreezeEvidenceReference(
            UUID("59000000-0000-0000-0000-000000000009")
        ),
    )
    assert isinstance(manifest_result, Success)
    run_result = build_research_run_evidence(
        run_id=ResearchRunId(
            UUID("59000000-0000-0000-0000-000000000010")
        ),
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


def _state(sequence: int, value: int) -> ResearchStrategyState:
    return ResearchStrategyState(
        evaluator_identity=_identity(),
        evaluation_sequence_number=sequence,
        state_schema_version="v1",
        exact_content=_Content(value),
    )


def _trace() -> ResearchExecutionTrace:
    session = _session()
    initial = _state(0, 0)
    final = _state(1, 1)
    transition = ResearchStateTransitionEvidence(
        evaluation_sequence_number=0,
        evaluator_identity=_identity(),
        simulated_now=session.qualified_observations[0].observation.available_at,
        prior_state=initial,
        newly_visible_inputs=session.qualified_observations,
        next_state=final,
        decisions=(),
    )
    return ResearchExecutionTrace(
        execution_session=session,
        evaluator_identity=_identity(),
        start_policy=W1_NO_WARMUP_V1,
        schedule_semantics=SCHEDULE_A_V1,
        initial_state=initial,
        transitions=(transition,),
        final_state=final,
    )


class _Evaluator:
    @property
    def identity(self) -> ResearchDecisionEvaluatorIdentity:
        return _identity()

    def create_initial_state(
        self,
        *,
        strategy_binding: ResearchRunStrategyBinding,
        start_policy: ResearchStartPolicy,
    ) -> ResearchStrategyState:
        assert strategy_binding.run.software_revision == _REVISION
        assert start_policy == W1_NO_WARMUP_V1
        return _state(0, 0)

    def evaluate(
        self,
        *,
        strategy_binding: ResearchRunStrategyBinding,
        prior_state: ResearchStrategyState,
        newly_visible_inputs: tuple[QualifiedReplayObservation, ...],
        simulated_now: datetime,
    ) -> tuple[ResearchStrategyState, tuple[FunctionalDecision, ...]]:
        assert strategy_binding.run.software_revision == _REVISION
        assert prior_state == _state(0, 0)
        assert newly_visible_inputs
        assert simulated_now == newly_visible_inputs[0].observation.available_at
        return _state(1, 1), ()


def test_trace_enforces_exact_schedule_and_session_derived_input_membership() -> None:
    trace = _trace()
    assert len(trace.transitions) == 1
    assert trace.transitions[0].newly_visible_inputs == (
        trace.execution_session.qualified_observations
    )


def test_trace_rejects_missing_transition() -> None:
    trace = _trace()
    with pytest.raises(ResearchExecutionTraceValidationError):
        ResearchExecutionTrace(
            execution_session=trace.execution_session,
            evaluator_identity=trace.evaluator_identity,
            start_policy=trace.start_policy,
            schedule_semantics=trace.schedule_semantics,
            initial_state=trace.initial_state,
            transitions=(),
            final_state=trace.initial_state,
        )


def test_reproduction_recreates_initial_state_and_propagates_state() -> None:
    assert verify_trace_reproducibility(_trace(), _Evaluator()) is True


def test_reproduction_rejects_evaluator_identity_mismatch() -> None:
    class _Other(_Evaluator):
        @property
        def identity(self) -> ResearchDecisionEvaluatorIdentity:
            return _identity("test.other")

    with pytest.raises(ResearchEvaluatorIdentityMismatchError):
        verify_trace_reproducibility(_trace(), _Other())


def test_reproduction_malformed_output_and_decision_elements_fail_typed() -> None:
    class _Malformed(_Evaluator):
        def evaluate(
            self,
            *,
            strategy_binding: ResearchRunStrategyBinding,
            prior_state: ResearchStrategyState,
            newly_visible_inputs: tuple[QualifiedReplayObservation, ...],
            simulated_now: datetime,
        ) -> tuple[ResearchStrategyState, tuple[FunctionalDecision, ...]]:
            return cast(
                tuple[ResearchStrategyState, tuple[FunctionalDecision, ...]],
                "bad",
            )

    class _BadDecision(_Evaluator):
        def evaluate(
            self,
            *,
            strategy_binding: ResearchRunStrategyBinding,
            prior_state: ResearchStrategyState,
            newly_visible_inputs: tuple[QualifiedReplayObservation, ...],
            simulated_now: datetime,
        ) -> tuple[ResearchStrategyState, tuple[FunctionalDecision, ...]]:
            malformed = (_state(1, 1), (object(),))
            return cast(
                tuple[ResearchStrategyState, tuple[FunctionalDecision, ...]],
                malformed,
            )

    with pytest.raises(ResearchLineageValidationError):
        verify_trace_reproducibility(_trace(), _Malformed())
    with pytest.raises(ResearchLineageValidationError):
        verify_trace_reproducibility(_trace(), _BadDecision())
