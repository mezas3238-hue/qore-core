"""Shared fixture factories for Trader Lab tests."""

from __future__ import annotations

from collections.abc import Callable
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
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabCandidateId,
    TraderLabCandidateVersion,
    build_trader_lab_candidate_binding,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceDigest,
    TraderLabEvidenceKind,
    TraderLabEvidenceReference,
    TraderLabStage,
    TraderLabStageEvidenceId,
    TraderLabStageEvidenceRecord,
    build_trader_lab_stage_evidence,
)
from qore.kernel.result import Success

_PROCESS_TIME = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
_BASE = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("71000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("71000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.trader-lab-test"),
)
_SCHEMA = ResearchStrategySchemaVersion("strategy-config-v1")


def _uuid(suffix: int) -> UUID:
    return UUID(f"71000000-0000-0000-0000-{suffix:012d}")


@pytest.fixture
def strategy_binding_factory() -> Callable[..., ResearchRunStrategyBinding]:
    """Return a factory that builds a valid ResearchRunStrategyBinding."""

    def _build(
        *,
        configuration_id_suffix: int = 10,
        created_at: datetime = _PROCESS_TIME,
    ) -> ResearchRunStrategyBinding:
        instrument = Instrument("EURUSD")
        timeframe = Timeframe(300)
        window = HistoricalOhlcWindow(
            instrument=instrument,
            timeframe=timeframe,
            opened_at=_BASE,
            closed_at=_BASE + timedelta(hours=1),
        )
        snapshot = OhlcSnapshot(
            snapshot_id=MarketDataSnapshotId(_uuid(20)),
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
            assembled_at=_PROCESS_TIME - timedelta(days=2),
            schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
            normalization_version=HistoricalDatasetNormalizationVersion("ingestion-v1"),
            observations=(replay,),
        )
        assert isinstance(dataset, Success)
        configuration_id = ResearchStrategyConfigurationId(
            _uuid(configuration_id_suffix)
        )
        built_run = build_research_run_evidence(
            run_id=ResearchRunId(_uuid(25)),
            created_at=created_at,
            datasets=(dataset.value.manifest,),
            replay_policy_version=ResearchReplayPolicyVersion("point-in-time-v1"),
            simulated_start=_BASE,
            simulated_end=_BASE + timedelta(minutes=30),
            strategy_configuration_id=configuration_id,
            software_revision=ResearchSoftwareRevision("a8a17b1c"),
            execution_model_id=None,
            transaction_cost_model_id=None,
            randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
            random_seed=None,
        )
        assert isinstance(built_run, Success)
        run: ResearchRunEvidence = built_run.value
        manifest = build_research_strategy_configuration_manifest(
            configuration_id=configuration_id,
            schema_version=_SCHEMA,
            parameters=(
                ResearchStrategyParameter("entry.threshold", Decimal("0.7500")),
                ResearchStrategyParameter("risk.enabled", True),
                ResearchStrategyParameter("risk.max_positions", 2),
                ResearchStrategyParameter("session.name", "new-york"),
            ),
            frozen_at=_PROCESS_TIME - timedelta(minutes=1),
            evidence_ref=ResearchStrategyFreezeEvidenceReference(_uuid(30)),
        )
        assert isinstance(manifest, Success)
        built_binding = build_research_run_strategy_binding(
            run=run,
            manifest=manifest.value,
        )
        assert isinstance(built_binding, Success)
        return built_binding.value

    return _build


@pytest.fixture
def candidate_factory(
    strategy_binding_factory: Callable[..., ResearchRunStrategyBinding],
) -> Callable[..., TraderLabCandidateBinding]:
    """Return a factory that builds a TraderLabCandidateBinding."""

    def _build(
        *,
        candidate_suffix: int = 1,
        version: str = "v1",
        binding: ResearchRunStrategyBinding | None = None,
    ) -> TraderLabCandidateBinding:
        strategy_binding = binding if binding is not None else strategy_binding_factory()
        built = build_trader_lab_candidate_binding(
            candidate_id=_make_candidate_id(candidate_suffix),
            version=TraderLabCandidateVersion(version),
            strategy_binding=strategy_binding,
        )
        assert isinstance(built, Success)
        return built.value

    return _build


def _make_candidate_id(suffix: int) -> TraderLabCandidateId:
    return TraderLabCandidateId(_uuid(suffix))


@pytest.fixture
def stage_evidence_factory() -> Callable[..., TraderLabStageEvidenceRecord]:
    """Return a factory that builds a TraderLabStageEvidenceRecord."""

    def _build(
        *,
        stage: TraderLabStage,
        candidate: TraderLabCandidateBinding,
        evidence_suffix: int,
        produced_at: datetime = _PROCESS_TIME,
        kind: TraderLabEvidenceKind = TraderLabEvidenceKind.REPLAY_CHRONOLOGY,
        reference_id_suffix: int | None = None,
    ) -> TraderLabStageEvidenceRecord:
        reference = TraderLabEvidenceReference(
            kind=kind,
            reference_id=_uuid(reference_id_suffix or evidence_suffix + 500),
            content_digest=TraderLabEvidenceDigest("1" * 64),
            schema_version="test.v1",
        )
        built = build_trader_lab_stage_evidence(
            evidence_id=TraderLabStageEvidenceId(_uuid(evidence_suffix)),
            stage=stage,
            candidate=candidate,
            source_reference=reference,
            produced_at=produced_at,
        )
        assert isinstance(built, Success)
        return built.value

    return _build
