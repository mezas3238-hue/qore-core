from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

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
from qore.infrastructure.research_evaluation_freeze import (
    ResearchEvaluationFreezeEvidenceId,
    ResearchEvaluationFreezeFingerprint,
    ResearchEvaluationFreezeValidationError,
    build_research_evaluation_freeze_evidence,
)
from qore.infrastructure.research_run import (
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunEvidence,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    build_research_run_evidence,
)
from qore.infrastructure.research_strategy_freeze import (
    ResearchRunStrategyBinding,
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyParameter,
    ResearchStrategySchemaVersion,
    build_research_run_strategy_binding,
    build_research_strategy_configuration_manifest,
)
from qore.infrastructure.research_temporal_evaluation import (
    ResearchEvaluationWindow,
    ResearchTemporalEvaluationPlan,
    ResearchTemporalEvaluationPlanId,
    ResearchWalkForwardFold,
    build_research_temporal_evaluation_plan,
)
from qore.kernel.result import Failure, Success

_SIMULATED = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
_PROCESS = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("72000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("72000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.research-evaluation-freeze-test"),
)
_CONFIG_ID = ResearchStrategyConfigurationId(
    UUID("72000000-0000-0000-0000-000000000003")
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"72000000-0000-0000-0000-{suffix:012d}")


def _run(
    *,
    run_suffix: int = 10,
    created_at: datetime = _PROCESS - timedelta(minutes=2),
) -> ResearchRunEvidence:
    instrument = Instrument("EURUSD")
    timeframe = Timeframe(300)
    window = HistoricalOhlcWindow(
        instrument=instrument,
        timeframe=timeframe,
        opened_at=_SIMULATED,
        closed_at=_SIMULATED + timedelta(hours=2),
    )
    snapshot = OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(20)),
        instrument=instrument,
        source=_SOURCE,
        timeframe=timeframe,
        opened_at=_SIMULATED,
        closed_at=_SIMULATED + timedelta(minutes=5),
        open=1.10,
        high=1.11,
        low=1.09,
        close=1.105,
    )
    replay = ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(21)),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=snapshot.closed_at,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(_uuid(22)),
    )
    dataset = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(23)),
        revision_id=HistoricalDatasetRevisionId(_uuid(24)),
        parent_revision_id=None,
        revision_reason=None,
        scope=HistoricalOhlcDatasetScope(source=_SOURCE, window=window),
        assembled_at=_PROCESS - timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion("ingestion-v1"),
        observations=(replay,),
    )
    assert isinstance(dataset, Success)
    built = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(run_suffix)),
        created_at=created_at,
        datasets=(dataset.value.manifest,),
        replay_policy_version=ResearchReplayPolicyVersion("point-in-time-v1"),
        simulated_start=_SIMULATED,
        simulated_end=_SIMULATED + timedelta(hours=1),
        strategy_configuration_id=_CONFIG_ID,
        software_revision=ResearchSoftwareRevision("58d9355a"),
        execution_model_id=None,
        transaction_cost_model_id=None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    assert isinstance(built, Success)
    return built.value


def _binding(run: ResearchRunEvidence) -> ResearchRunStrategyBinding:
    manifest = build_research_strategy_configuration_manifest(
        configuration_id=_CONFIG_ID,
        schema_version=ResearchStrategySchemaVersion("strategy-config-v1"),
        parameters=(
            ResearchStrategyParameter("entry.threshold", Decimal("0.75")),
            ResearchStrategyParameter("risk.enabled", True),
        ),
        frozen_at=run.created_at - timedelta(minutes=1),
        evidence_ref=ResearchStrategyFreezeEvidenceReference(_uuid(30)),
    )
    assert isinstance(manifest, Success)
    binding = build_research_run_strategy_binding(run=run, manifest=manifest.value)
    assert isinstance(binding, Success)
    return binding.value


def _plan(
    run: ResearchRunEvidence,
    *,
    created_at: datetime,
) -> ResearchTemporalEvaluationPlan:
    fold = ResearchWalkForwardFold(
        fold_number=1,
        in_sample=ResearchEvaluationWindow(
            opened_at=_SIMULATED,
            closed_at=_SIMULATED + timedelta(minutes=30),
        ),
        out_of_sample=ResearchEvaluationWindow(
            opened_at=_SIMULATED + timedelta(minutes=30),
            closed_at=_SIMULATED + timedelta(minutes=45),
        ),
    )
    built = build_research_temporal_evaluation_plan(
        plan_id=ResearchTemporalEvaluationPlanId(_uuid(40)),
        run=run,
        folds=(fold,),
        created_at=created_at,
    )
    assert isinstance(built, Success)
    return built.value


def test_evaluation_freeze_binds_exact_strategy_before_temporal_plan() -> None:
    run = _run()
    binding = _binding(run)
    plan = _plan(run, created_at=_PROCESS - timedelta(minutes=1))
    built = build_research_evaluation_freeze_evidence(
        evidence_id=ResearchEvaluationFreezeEvidenceId(_uuid(50)),
        strategy_binding=binding,
        plan=plan,
        established_at=_PROCESS,
    )
    assert isinstance(built, Success)
    evidence = built.value
    assert binding.manifest.frozen_at <= run.created_at <= plan.created_at
    assert evidence.strategy_binding == binding
    assert evidence.plan == plan


def test_process_chronology_is_independent_from_historical_simulated_time() -> None:
    run = _run()
    binding = _binding(run)
    plan = _plan(run, created_at=_PROCESS - timedelta(minutes=1))
    assert binding.manifest.frozen_at > run.simulated_end
    assert plan.created_at > run.simulated_end

    built = build_research_evaluation_freeze_evidence(
        evidence_id=ResearchEvaluationFreezeEvidenceId(_uuid(60)),
        strategy_binding=binding,
        plan=plan,
        established_at=_PROCESS,
    )
    assert isinstance(built, Success)


def test_evaluation_freeze_rejects_plan_created_before_run_record() -> None:
    run = _run(created_at=_PROCESS - timedelta(minutes=2))
    binding = _binding(run)
    plan = _plan(run, created_at=_PROCESS - timedelta(minutes=3))
    built = build_research_evaluation_freeze_evidence(
        evidence_id=ResearchEvaluationFreezeEvidenceId(_uuid(70)),
        strategy_binding=binding,
        plan=plan,
        established_at=_PROCESS,
    )
    assert isinstance(built, Failure)
    assert "must not predate research run creation" in str(built.error)


def test_evaluation_freeze_rejects_cross_run_plan() -> None:
    run = _run(run_suffix=80)
    other_run = _run(run_suffix=81)
    binding = _binding(run)
    plan = _plan(other_run, created_at=_PROCESS - timedelta(minutes=1))
    built = build_research_evaluation_freeze_evidence(
        evidence_id=ResearchEvaluationFreezeEvidenceId(_uuid(82)),
        strategy_binding=binding,
        plan=plan,
        established_at=_PROCESS,
    )
    assert isinstance(built, Failure)
    assert "must bind the strategy research run" in str(built.error)


def test_evaluation_freeze_rejects_fingerprint_tampering_and_overclaims() -> None:
    run = _run()
    binding = _binding(run)
    plan = _plan(run, created_at=_PROCESS - timedelta(minutes=1))
    built = build_research_evaluation_freeze_evidence(
        evidence_id=ResearchEvaluationFreezeEvidenceId(_uuid(90)),
        strategy_binding=binding,
        plan=plan,
        established_at=_PROCESS,
    )
    assert isinstance(built, Success)
    with pytest.raises(ResearchEvaluationFreezeValidationError):
        replace(
            built.value,
            fingerprint=ResearchEvaluationFreezeFingerprint("0" * 64),
        )
    assert not hasattr(built.value, "analyst_blind")
    assert not hasattr(built.value, "statistically_significant")
    assert not hasattr(built.value, "production_ready")
