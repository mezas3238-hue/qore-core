from __future__ import annotations

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
from qore.infrastructure.research_execution_session import (
    ResearchExecutionSession,
    derive_schedule_a_instants,
    order_qualified_replay_observations,
)
from qore.infrastructure.research_lineage_errors import (
    ResearchExecutionSessionValidationError,
)
from qore.infrastructure.research_run import (
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    build_research_run_evidence,
)
from qore.infrastructure.research_strategy_freeze import (
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyParameter,
    ResearchStrategySchemaVersion,
    build_research_run_strategy_binding,
    build_research_strategy_configuration_manifest,
)
from qore.kernel.result import Success


_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("57000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("57000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.research-lineage-test"),
)
_INSTRUMENT = Instrument("EURUSD")
_TIMEFRAME = Timeframe(300)


def _uuid(suffix: int) -> UUID:
    return UUID(f"57000000-0000-0000-0000-{suffix:012d}")


def _dataset(*, suffix: int = 1, available_delay: int = 0) -> HistoricalOhlcReplayDataset:
    scope = HistoricalOhlcDatasetScope(
        source=_SOURCE,
        window=HistoricalOhlcWindow(
            instrument=_INSTRUMENT,
            timeframe=_TIMEFRAME,
            opened_at=_BASE,
            closed_at=_BASE + timedelta(minutes=15),
        ),
    )
    snapshot = OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(100 + suffix)),
        instrument=_INSTRUMENT,
        source=_SOURCE,
        timeframe=_TIMEFRAME,
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=5),
        open=1.10,
        high=1.11,
        low=1.09,
        close=1.105,
    )
    observation = ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(200 + suffix)),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=snapshot.closed_at + timedelta(seconds=available_delay),
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(
            _uuid(300 + suffix)
        ),
    )
    built = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(400 + suffix)),
        revision_id=HistoricalDatasetRevisionId(_uuid(500 + suffix)),
        parent_revision_id=None,
        revision_reason=None,
        scope=scope,
        assembled_at=_BASE + timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion("canonical-v1"),
        observations=(observation,),
    )
    assert isinstance(built, Success)
    return built.value


def _session(
    *,
    run_suffix: int = 1,
    frozen_at: datetime = _BASE + timedelta(hours=1),
    parameter: Decimal = Decimal("0.5"),
) -> ResearchExecutionSession:
    dataset = _dataset(suffix=run_suffix)
    configuration_id = ResearchStrategyConfigurationId(_uuid(600 + run_suffix))
    manifest_result = build_research_strategy_configuration_manifest(
        configuration_id=configuration_id,
        schema_version=ResearchStrategySchemaVersion("v1"),
        parameters=(ResearchStrategyParameter("alpha", parameter),),
        frozen_at=frozen_at,
        evidence_ref=ResearchStrategyFreezeEvidenceReference(_uuid(700 + run_suffix)),
    )
    assert isinstance(manifest_result, Success)
    run_result = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(800 + run_suffix)),
        created_at=_BASE + timedelta(days=2),
        datasets=(dataset.manifest,),
        replay_policy_version=ResearchReplayPolicyVersion("point-in-time-v1"),
        simulated_start=_BASE,
        simulated_end=_BASE + timedelta(minutes=10),
        strategy_configuration_id=configuration_id,
        software_revision=ResearchSoftwareRevision("revision-1"),
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
        replay_datasets=(dataset,),
    )


def test_session_derives_qualified_provenance_and_schedule_a() -> None:
    session = _session()
    assert len(session.qualified_observations) == 1
    qualified = session.qualified_observations[0]
    assert qualified.source_manifest == session.replay_datasets[0].manifest
    assert derive_schedule_a_instants(session) == (
        qualified.observation.available_at,
    )


def test_session_rejects_missing_dataset_and_wrong_runtime_type() -> None:
    session = _session()
    with pytest.raises(ResearchExecutionSessionValidationError):
        ResearchExecutionSession(
            strategy_binding=session.strategy_binding,
            replay_datasets=(),
        )
    with pytest.raises(ResearchExecutionSessionValidationError):
        ResearchExecutionSession(
            strategy_binding=session.strategy_binding,
            replay_datasets=(object(),),  # type: ignore[arg-type]
        )


def test_session_exact_fingerprint_binds_run_and_strategy_admin_evidence() -> None:
    first = _session(run_suffix=1)
    different_run = _session(run_suffix=2)
    different_frozen = _session(
        run_suffix=1,
        frozen_at=_BASE + timedelta(hours=2),
    )
    different_parameter = _session(
        run_suffix=1,
        parameter=Decimal("0.6"),
    )
    assert first.session_fingerprint != different_run.session_fingerprint
    assert first.session_fingerprint != different_frozen.session_fingerprint
    assert first.session_fingerprint != different_parameter.session_fingerprint


def test_qualified_ordering_preserves_existing_replay_key_before_dataset_tiebreak() -> None:
    first = _session(run_suffix=3).qualified_observations[0]
    later_session = _session(run_suffix=4)
    later = later_session.qualified_observations[0]
    ordered = order_qualified_replay_observations((later, first))
    assert ordered == tuple(sorted((later, first), key=lambda item: (
        item.observation.available_at,
        item.observation.canonical_boundary,
        str(item.observation.source.adapter_id.value),
        str(item.observation.source.source_id.value),
        item.observation.source.port_name.value,
        item.observation.instrument.symbol,
        str(item.observation.snapshot_id.value),
        str(item.observation.observation_id.value),
        str(item.source_manifest.dataset_id.value),
    )))
