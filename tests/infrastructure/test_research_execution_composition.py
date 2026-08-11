from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
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
from qore.infrastructure.dataset_integrity_qualification import (
    DatasetIntegrityQualification,
    IntegrityQualifiedResearchRun,
    IntegrityQualifiedResearchRunFingerprint,
)
from qore.infrastructure.historical_dataset import (
    HistoricalDatasetId,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
    HistoricalOhlcDatasetScope,
    HistoricalOhlcReplayDataset,
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
    ResearchSpecialistEvaluatorFamily,
    ResearchSpecialistEvaluatorIdentity,
    ResearchSpecialistEvaluatorSchemaVersion,
)
from qore.infrastructure.research_execution_composition import (
    ResearchExecutionComposition,
    ResearchProducerLineageOutcomeFingerprint,
    ResearchProducerLineageVerifier,
    _compute_outcome_fingerprint,
    _revalidate_retained_lineage_record,
    _validate_outcome_graph,
    _verify_specialist_side,
)
from qore.infrastructure.research_execution_session import (
    QualifiedReplayObservation,
    ResearchExecutionSession,
)
from qore.infrastructure.research_lineage_errors import (
    ResearchEvaluatorIdentityMismatchError,
    ResearchLineageFingerprintError,
    ResearchLineageValidationError,
    ResearchSpecialistEvaluatorIdentityMismatchError,
)
from qore.infrastructure.research_lineage_fingerprints import (
    ResearchAnalysisLineageFingerprint,
)
from qore.infrastructure.research_producer_admission import (
    ResearchProducerAdmissionEvidence,
    ResearchProducerAdmissionFingerprint,
)
from qore.infrastructure.research_run import (
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    build_research_run_evidence,
)
from qore.infrastructure.research_schedule import ResearchStartPolicy, W1_NO_WARMUP_V1
from qore.infrastructure.research_specialist_boundary import ResearchAnalysisSpecification
from qore.infrastructure.research_strategy_freeze import (
    ResearchRunStrategyBinding,
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyParameter,
    ResearchStrategySchemaVersion,
    build_research_run_strategy_binding,
    build_research_strategy_configuration_manifest,
)
from qore.infrastructure.research_strategy_state import ResearchStrategyState
from qore.kernel.result import Success
from qore.modules.trader.contracts import ProduceVirtualTraderAnalysisCommand
from qore.specialist.analysis import (
    SpecialistAnalysis,
    SpecialistConfidence,
    SpecialistKind,
    SpecialistReason,
    SpecialistReasonCode,
)

_BASE = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
_DECISION_REVISION = ResearchSoftwareRevision("phase1b-decision-revision")
_SPECIALIST_REVISION = ResearchSoftwareRevision("phase1b-specialist-revision")


@dataclass(frozen=True, slots=True)
class _Content:
    value: int

    def logical_values(self) -> Mapping[str, object]:
        return {"value": self.value}


def _uuid(suffix: int) -> UUID:
    return UUID(f"8c000000-0000-0000-0000-{suffix:012d}")


def _decision_identity(
    family: str = "test.phase1b-decision",
) -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily(family),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=_DECISION_REVISION,
    )


def _specialist_identity(
    family: str = "test.phase1b-specialist",
) -> ResearchSpecialistEvaluatorIdentity:
    return ResearchSpecialistEvaluatorIdentity(
        family=ResearchSpecialistEvaluatorFamily(family),
        schema_version=ResearchSpecialistEvaluatorSchemaVersion("v1"),
        software_revision=_SPECIALIST_REVISION,
    )


def _state(sequence: int, value: int) -> ResearchStrategyState:
    return ResearchStrategyState(
        evaluator_identity=_decision_identity(),
        evaluation_sequence_number=sequence,
        state_schema_version="v1",
        exact_content=_Content(value),
    )


def _decision(index: int, simulated_now: datetime) -> FunctionalDecision:
    return FunctionalDecision(
        decision_id=DecisionId(_uuid(200_000 + index)),
        timestamp=simulated_now,
        decision_type=DecisionType("research.phase1b"),
        status=DecisionStatus.RESOLVED,
        priority=DecisionPriority.NORMAL,
        metadata=DecisionMetadata(
            correlation_id=CorrelationId(_uuid(210_000 + index)),
            attributes=MappingProxyType({}),
        ),
        reasons=(
            DecisionReason(
                code=DecisionReasonCode("research.phase1b"),
                summary=f"resolved decision {index}",
                attributes=MappingProxyType({}),
            ),
        ),
        outcome=DecisionOutcome.APPROVED,
    )


def _reason(code: str) -> SpecialistReason:
    return SpecialistReason(
        code=SpecialistReasonCode(code),
        summary=code,
        attributes=MappingProxyType({}),
    )


def _specification(code: str = "research.phase1b") -> ResearchAnalysisSpecification:
    return ResearchAnalysisSpecification(
        kind=SpecialistKind("virtual-trader.phase1b"),
        confidence=SpecialistConfidence(0.75),
        reasons=(_reason(code),),
    )


def _binding_and_dataset() -> tuple[ResearchRunStrategyBinding, HistoricalOhlcReplayDataset]:
    source = ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(10_000)),
        source_id=SourceId(_uuid(20_000)),
        port_name=PortName("market-data.phase1b-composition-test"),
    )
    instrument = Instrument("EURUSD")
    timeframe = Timeframe(60)
    snapshot = OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(30_000)),
        instrument=instrument,
        source=source,
        timeframe=timeframe,
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=1),
        open=1.10,
        high=1.11,
        low=1.09,
        close=1.105,
    )
    observation = ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(40_000)),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=snapshot.closed_at,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(
            _uuid(50_000)
        ),
    )
    dataset_result = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(60_000)),
        revision_id=HistoricalDatasetRevisionId(_uuid(70_000)),
        parent_revision_id=None,
        revision_reason=None,
        scope=HistoricalOhlcDatasetScope(
            source=source,
            window=HistoricalOhlcWindow(
                instrument=instrument,
                timeframe=timeframe,
                opened_at=_BASE,
                closed_at=_BASE + timedelta(minutes=2),
            ),
        ),
        assembled_at=_BASE + timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion("canonical-v1"),
        observations=(observation,),
    )
    assert isinstance(dataset_result, Success)

    configuration_id = ResearchStrategyConfigurationId(_uuid(80_000))
    manifest_result = build_research_strategy_configuration_manifest(
        configuration_id=configuration_id,
        schema_version=ResearchStrategySchemaVersion("v1"),
        parameters=(ResearchStrategyParameter("alpha", 1),),
        frozen_at=_BASE + timedelta(hours=1),
        evidence_ref=ResearchStrategyFreezeEvidenceReference(_uuid(90_000)),
    )
    assert isinstance(manifest_result, Success)
    run_result = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(100_000)),
        created_at=_BASE + timedelta(days=2),
        datasets=(dataset_result.value.manifest,),
        replay_policy_version=ResearchReplayPolicyVersion("point-in-time-v1"),
        simulated_start=_BASE,
        simulated_end=_BASE + timedelta(minutes=2),
        strategy_configuration_id=configuration_id,
        software_revision=_DECISION_REVISION,
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
    return binding_result.value, dataset_result.value


def _admission() -> ResearchProducerAdmissionEvidence:
    binding, dataset = _binding_and_dataset()
    qualification = cast(
        DatasetIntegrityQualification,
        object.__new__(DatasetIntegrityQualification),
    )
    object.__setattr__(qualification, "dataset", dataset)
    qualified_run = cast(
        IntegrityQualifiedResearchRun,
        object.__new__(IntegrityQualifiedResearchRun),
    )
    object.__setattr__(qualified_run, "run", binding.run)
    object.__setattr__(qualified_run, "qualifications", (qualification,))
    object.__setattr__(
        qualified_run,
        "fingerprint",
        IntegrityQualifiedResearchRunFingerprint("a" * 64),
    )
    return ResearchProducerAdmissionEvidence(
        integrity_qualified_run=qualified_run,
        strategy_binding=binding,
    )


class _DecisionEvaluator:
    @property
    def identity(self) -> ResearchDecisionEvaluatorIdentity:
        return _decision_identity()

    def create_initial_state(
        self,
        *,
        strategy_binding: ResearchRunStrategyBinding,
        start_policy: ResearchStartPolicy,
    ) -> ResearchStrategyState:
        assert strategy_binding.run.software_revision == _DECISION_REVISION
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
        assert strategy_binding.run.software_revision == _DECISION_REVISION
        assert prior_state == _state(0, 0)
        assert newly_visible_inputs
        return _state(1, 1), (
            _decision(1, simulated_now),
            _decision(2, simulated_now),
        )


class _DifferentDecisionEvaluator(_DecisionEvaluator):
    def evaluate(
        self,
        *,
        strategy_binding: ResearchRunStrategyBinding,
        prior_state: ResearchStrategyState,
        newly_visible_inputs: tuple[QualifiedReplayObservation, ...],
        simulated_now: datetime,
    ) -> tuple[ResearchStrategyState, tuple[FunctionalDecision, ...]]:
        assert strategy_binding.run.software_revision == _DECISION_REVISION
        assert newly_visible_inputs
        return _state(1, 99), (
            _decision(1, simulated_now),
            _decision(2, simulated_now),
        )


class _SpecialistEvaluator:
    def __init__(self, *, code: str = "research.phase1b") -> None:
        self.code = code
        self.evaluate_calls = 0

    @property
    def identity(self) -> ResearchSpecialistEvaluatorIdentity:
        return _specialist_identity()

    def evaluate(
        self,
        *,
        source_decision: FunctionalDecision,
    ) -> ResearchAnalysisSpecification:
        assert source_decision.status is DecisionStatus.RESOLVED
        self.evaluate_calls += 1
        return _specification(self.code)


class _FinalDriftSpecialist(_SpecialistEvaluator):
    def __init__(self) -> None:
        super().__init__(code="research.changed")
        self.identity_reads = 0

    @property
    def identity(self) -> ResearchSpecialistEvaluatorIdentity:
        self.identity_reads += 1
        if self.identity_reads >= 6:
            return _specialist_identity("test.phase1b-specialist-drifted")
        return _specialist_identity()


def _outcome() -> tuple[object, _DecisionEvaluator, _SpecialistEvaluator]:
    decision_evaluator = _DecisionEvaluator()
    specialist_evaluator = _SpecialistEvaluator()
    outcome = ResearchExecutionComposition(
        admission_evidence=_admission(),
        decision_evaluator=decision_evaluator,
        specialist_evaluator=specialist_evaluator,
    ).produce()
    return outcome, decision_evaluator, specialist_evaluator


def test_composition_produces_complete_trace_and_one_record_per_resolved_decision() -> None:
    outcome_raw, decision_evaluator, specialist_evaluator = _outcome()
    outcome = cast("ResearchProducerLineageOutcome", outcome_raw)
    assert len(outcome.trace.transitions) == 1
    assert outcome.trace.transitions[0].evaluation_sequence_number == 0
    assert len(outcome.lineage_records) == 2
    assert specialist_evaluator.evaluate_calls == 2
    assert ResearchProducerLineageVerifier.verify(
        outcome,
        decision_evaluator,
        _SpecialistEvaluator(),
    )


def test_model_b_retains_independent_specialist_revision() -> None:
    outcome_raw, _, _ = _outcome()
    outcome = cast("ResearchProducerLineageOutcome", outcome_raw)
    assert (
        outcome.decision_evaluator_identity.software_revision
        == _DECISION_REVISION
    )
    assert (
        outcome.specialist_evaluator_identity.software_revision
        == _SPECIALIST_REVISION
    )
    assert _SPECIALIST_REVISION != _DECISION_REVISION


def test_outcome_fingerprint_uses_single_module_helper() -> None:
    outcome_raw, _, _ = _outcome()
    outcome = cast("ResearchProducerLineageOutcome", outcome_raw)
    assert outcome.outcome_fingerprint == _compute_outcome_fingerprint(
        outcome.admission_evidence.admission_fingerprint,
        outcome.decision_evaluator_identity,
        outcome.specialist_evaluator_identity,
        outcome.trace.trace_fingerprint,
        outcome.lineage_records,
    )


def test_public_verifier_runs_specialist_side_after_decision_false() -> None:
    outcome_raw, _, _ = _outcome()
    outcome = cast("ResearchProducerLineageOutcome", outcome_raw)
    specialist = _SpecialistEvaluator()
    assert not ResearchProducerLineageVerifier.verify(
        outcome,
        _DifferentDecisionEvaluator(),
        specialist,
    )
    assert specialist.evaluate_calls == 2


def test_wrong_evaluator_identities_raise_typed_errors() -> None:
    outcome_raw, _, _ = _outcome()
    outcome = cast("ResearchProducerLineageOutcome", outcome_raw)

    class _WrongDecision(_DecisionEvaluator):
        @property
        def identity(self) -> ResearchDecisionEvaluatorIdentity:
            return _decision_identity("test.phase1b-other")

    class _WrongSpecialist(_SpecialistEvaluator):
        @property
        def identity(self) -> ResearchSpecialistEvaluatorIdentity:
            return _specialist_identity("test.phase1b-other-specialist")

    with pytest.raises(ResearchEvaluatorIdentityMismatchError):
        ResearchProducerLineageVerifier.verify(
            outcome,
            _WrongDecision(),
            _SpecialistEvaluator(),
        )
    with pytest.raises(ResearchSpecialistEvaluatorIdentityMismatchError):
        ResearchProducerLineageVerifier.verify(
            outcome,
            _DecisionEvaluator(),
            _WrongSpecialist(),
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("decision_transition_index", True),
        ("decision_transition_index", False),
        ("decision_index_within_transition", True),
        ("decision_index_within_transition", False),
    ],
)
def test_outcome_graph_rejects_bool_lineage_indices(
    field_name: str,
    value: bool,
) -> None:
    outcome_raw, _, _ = _outcome()
    outcome = cast("ResearchProducerLineageOutcome", outcome_raw)
    object.__setattr__(outcome.lineage_records[0], field_name, value)
    with pytest.raises(ResearchLineageValidationError):
        _validate_outcome_graph(outcome)


def test_retained_record_revalidation_detects_lineage_fingerprint_tamper() -> None:
    outcome_raw, _, _ = _outcome()
    outcome = cast("ResearchProducerLineageOutcome", outcome_raw)
    record = outcome.lineage_records[0]
    object.__setattr__(
        record,
        "lineage_fingerprint",
        ResearchAnalysisLineageFingerprint("f" * 64),
    )
    with pytest.raises(ResearchLineageValidationError):
        _revalidate_retained_lineage_record(record)


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("analysis", object()),
        ("trader_command", object()),
        ("analysis_input_evidence", object()),
    ],
)
def test_later_malformed_record_raises_after_earlier_computational_false(
    field_name: str,
    replacement: object,
) -> None:
    outcome_raw, _, _ = _outcome()
    outcome = cast("ResearchProducerLineageOutcome", outcome_raw)
    second = outcome.lineage_records[1]
    if field_name == "analysis":
        object.__setattr__(second, field_name, cast(SpecialistAnalysis, replacement))
    elif field_name == "trader_command":
        object.__setattr__(
            second,
            field_name,
            cast(ProduceVirtualTraderAnalysisCommand, replacement),
        )
    else:
        object.__setattr__(second, field_name, replacement)
    with pytest.raises(ResearchLineageValidationError):
        _verify_specialist_side(
            outcome,
            _SpecialistEvaluator(code="research.changed"),
        )


def test_computational_mismatch_plus_final_identity_drift_raises_identity_error() -> None:
    outcome_raw, _, _ = _outcome()
    outcome = cast("ResearchProducerLineageOutcome", outcome_raw)
    with pytest.raises(ResearchSpecialistEvaluatorIdentityMismatchError):
        _verify_specialist_side(outcome, _FinalDriftSpecialist())


def test_fingerprint_tampering_fails_before_reproduction() -> None:
    outcome_raw, decision_evaluator, _ = _outcome()
    outcome = cast("ResearchProducerLineageOutcome", outcome_raw)
    object.__setattr__(
        outcome,
        "outcome_fingerprint",
        ResearchProducerLineageOutcomeFingerprint("0" * 64),
    )
    with pytest.raises(ResearchLineageFingerprintError):
        ResearchProducerLineageVerifier.verify(
            outcome,
            decision_evaluator,
            _SpecialistEvaluator(),
        )

    fresh_raw, decision_evaluator, _ = _outcome()
    fresh = cast("ResearchProducerLineageOutcome", fresh_raw)
    object.__setattr__(
        fresh.admission_evidence,
        "admission_fingerprint",
        ResearchProducerAdmissionFingerprint("0" * 64),
    )
    with pytest.raises(ResearchLineageFingerprintError):
        ResearchProducerLineageVerifier.verify(
            fresh,
            decision_evaluator,
            _SpecialistEvaluator(),
        )


def test_composition_source_has_no_ellipsis_pass_or_unapproved_public_properties() -> None:
    path = Path("src/qore/infrastructure/research_execution_composition.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert not any(
        isinstance(node, ast.Constant) and node.value is Ellipsis
        for node in ast.walk(tree)
    )
    assert not any(isinstance(node, ast.Pass) for node in ast.walk(tree))
    assert "admission_evidence" not in ResearchExecutionComposition.__dict__
    assert "decision_evaluator" not in ResearchExecutionComposition.__dict__
    assert "specialist_evaluator" not in ResearchExecutionComposition.__dict__
