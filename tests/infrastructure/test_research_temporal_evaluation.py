from __future__ import annotations

from datetime import UTC, datetime, timedelta
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
from qore.infrastructure.research_run import (
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunEvidence,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    build_research_run_evidence,
)
from qore.infrastructure.research_temporal_evaluation import (
    ResearchEvaluationWindow,
    ResearchTemporalEvaluationPlanId,
    ResearchTemporalEvaluationValidationError,
    ResearchWalkForwardFold,
    build_research_temporal_evaluation_plan,
)
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("69000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("69000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.research-temporal-test"),
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"69000000-0000-0000-0000-{suffix:012d}")


def _run() -> ResearchRunEvidence:
    instrument = Instrument("EURUSD")
    timeframe = Timeframe(300)
    window = HistoricalOhlcWindow(
        instrument=instrument,
        timeframe=timeframe,
        opened_at=_BASE,
        closed_at=_BASE + timedelta(hours=4),
    )
    scope = HistoricalOhlcDatasetScope(source=_SOURCE, window=window)
    snapshot = OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(10)),
        instrument=instrument,
        source=_SOURCE,
        timeframe=timeframe,
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=5),
        open=1.10,
        high=1.11,
        low=1.09,
        close=1.105,
    )
    replay = ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(11)),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=snapshot.closed_at,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(_uuid(12)),
    )
    dataset = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(13)),
        revision_id=HistoricalDatasetRevisionId(_uuid(14)),
        parent_revision_id=None,
        revision_reason=None,
        scope=scope,
        assembled_at=_BASE + timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion("ingestion-v1"),
        observations=(replay,),
    )
    assert isinstance(dataset, Success)
    built = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(15)),
        created_at=_BASE + timedelta(days=2),
        datasets=(dataset.value.manifest,),
        replay_policy_version=ResearchReplayPolicyVersion("point-in-time-v1"),
        simulated_start=_BASE,
        simulated_end=_BASE + timedelta(hours=4),
        strategy_configuration_id=ResearchStrategyConfigurationId(_uuid(16)),
        software_revision=ResearchSoftwareRevision("fddb7b79"),
        execution_model_id=None,
        transaction_cost_model_id=None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    assert isinstance(built, Success)
    return built.value


def _window(start_minutes: int, end_minutes: int) -> ResearchEvaluationWindow:
    return ResearchEvaluationWindow(
        opened_at=_BASE + timedelta(minutes=start_minutes),
        closed_at=_BASE + timedelta(minutes=end_minutes),
    )


def test_plan_canonicalizes_chronological_walk_forward_folds() -> None:
    run = _run()
    first = ResearchWalkForwardFold(
        fold_number=1,
        in_sample=_window(0, 60),
        out_of_sample=_window(60, 90),
    )
    second = ResearchWalkForwardFold(
        fold_number=2,
        in_sample=_window(30, 90),
        out_of_sample=_window(90, 120),
    )
    built = build_research_temporal_evaluation_plan(
        plan_id=ResearchTemporalEvaluationPlanId(_uuid(100)),
        run=run,
        folds=(second, first),
        created_at=_BASE + timedelta(days=3),
    )
    assert isinstance(built, Success)
    assert built.value.folds == (first, second)
    assert built.value.run == run


def test_fold_rejects_in_sample_overlap_with_out_of_sample() -> None:
    with pytest.raises(ResearchTemporalEvaluationValidationError):
        ResearchWalkForwardFold(
            fold_number=1,
            in_sample=_window(0, 70),
            out_of_sample=_window(60, 90),
        )


def test_plan_rejects_overlapping_out_of_sample_windows() -> None:
    run = _run()
    first = ResearchWalkForwardFold(
        fold_number=1,
        in_sample=_window(0, 60),
        out_of_sample=_window(60, 100),
    )
    second = ResearchWalkForwardFold(
        fold_number=2,
        in_sample=_window(0, 80),
        out_of_sample=_window(90, 120),
    )
    built = build_research_temporal_evaluation_plan(
        plan_id=ResearchTemporalEvaluationPlanId(_uuid(200)),
        run=run,
        folds=(first, second),
        created_at=_BASE + timedelta(days=3),
    )
    assert isinstance(built, Failure)
    assert "must not overlap" in str(built.error)


def test_plan_rejects_windows_outside_research_run() -> None:
    run = _run()
    fold = ResearchWalkForwardFold(
        fold_number=1,
        in_sample=_window(0, 180),
        out_of_sample=_window(180, 300),
    )
    built = build_research_temporal_evaluation_plan(
        plan_id=ResearchTemporalEvaluationPlanId(_uuid(300)),
        run=run,
        folds=(fold,),
        created_at=_BASE + timedelta(days=3),
    )
    assert isinstance(built, Failure)
    assert "inside research run bounds" in str(built.error)


def test_plan_rejects_noncontiguous_fold_numbering_and_claims_no_training() -> None:
    run = _run()
    fold = ResearchWalkForwardFold(
        fold_number=2,
        in_sample=_window(0, 60),
        out_of_sample=_window(60, 90),
    )
    built = build_research_temporal_evaluation_plan(
        plan_id=ResearchTemporalEvaluationPlanId(_uuid(400)),
        run=run,
        folds=(fold,),
        created_at=_BASE + timedelta(days=3),
    )
    assert isinstance(built, Failure)
    assert "contiguous numbering" in str(built.error)
    assert not hasattr(fold, "train")
    assert not hasattr(fold, "optimize")
    assert not hasattr(fold, "fit")
