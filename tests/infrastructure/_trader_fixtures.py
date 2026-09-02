"""Shared deterministic fixtures for concrete trader producer/manager tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from qore.functional.decisions import FunctionalDecision
from qore.infrastructure.historical_dataset import (
    HistoricalDatasetId,
    HistoricalDatasetManifest,
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
from qore.infrastructure.research_evaluator_protocols import (
    ResearchDecisionEvaluatorProtocol,
)
from qore.infrastructure.research_execution_session import QualifiedReplayObservation
from qore.infrastructure.research_run import (
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    build_research_run_evidence,
)
from qore.infrastructure.research_schedule import W1_NO_WARMUP_V1
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

BASE = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
TIMEFRAME = Timeframe(60)
INSTRUMENT = Instrument("EURUSD")


def _uuid(suffix: int) -> UUID:
    return UUID(f"a0000000-0000-0000-0000-{suffix:012d}")


def _source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(10_000)),
        source_id=SourceId(_uuid(20_000)),
        port_name=PortName("market-data.trader-test"),
    )


def make_ohlc_snapshot(
    close: float,
    high: float,
    low: float,
    *,
    index: int,
    opened_at: datetime,
    closed_at: datetime,
) -> OhlcSnapshot:
    source = _source()
    return OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(30_000 + index)),
        instrument=INSTRUMENT,
        source=source,
        timeframe=TIMEFRAME,
        opened_at=opened_at,
        closed_at=closed_at,
        open=close,
        high=high,
        low=low,
        close=close,
    )


def make_replay_observation(
    snapshot: OhlcSnapshot,
    *,
    index: int,
) -> ReplayMarketDataObservation:
    return ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(40_000 + index)),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=snapshot.closed_at,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(
            _uuid(50_000 + index)
        ),
    )


def make_qualified_observation(
    manifest: HistoricalDatasetManifest,
    snapshot: OhlcSnapshot,
    *,
    index: int,
) -> QualifiedReplayObservation:
    return QualifiedReplayObservation(
        source_manifest=manifest,
        observation=make_replay_observation(snapshot, index=index),
    )


@dataclass(frozen=True, slots=True)
class TraderFixture:
    binding: ResearchRunStrategyBinding
    manifest: HistoricalDatasetManifest
    qualified_observations: tuple[QualifiedReplayObservation, ...]


def build_trader_fixture(
    *,
    software_revision: str,
    bars: tuple[tuple[float, float, float], ...],
) -> TraderFixture:
    """Build a binding plus contiguous M1 qualified observations for ``bars``.

    Each bar is ``(close, high, low)`` over a contiguous 60-second interval
    starting at ``BASE``.
    """
    source = _source()
    snapshots = tuple(
        make_ohlc_snapshot(
            close=close,
            high=high,
            low=low,
            index=index,
            opened_at=BASE + timedelta(seconds=60 * index),
            closed_at=BASE + timedelta(seconds=60 * (index + 1)),
        )
        for index, (close, high, low) in enumerate(bars)
    )
    observations = tuple(
        make_replay_observation(snapshot, index=index)
        for index, snapshot in enumerate(snapshots)
    )

    count = len(snapshots)
    window_closed_at = BASE + timedelta(seconds=60 * max(count, 1))
    dataset_result = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(60_000)),
        revision_id=HistoricalDatasetRevisionId(_uuid(70_000)),
        parent_revision_id=None,
        revision_reason=None,
        scope=HistoricalOhlcDatasetScope(
            source=source,
            window=HistoricalOhlcWindow(
                instrument=INSTRUMENT,
                timeframe=TIMEFRAME,
                opened_at=BASE,
                closed_at=window_closed_at,
            ),
        ),
        assembled_at=BASE + timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion("canonical-v1"),
        observations=observations,
    )
    assert isinstance(dataset_result, Success)

    configuration_id = ResearchStrategyConfigurationId(_uuid(80_000))
    manifest_result = build_research_strategy_configuration_manifest(
        configuration_id=configuration_id,
        schema_version=ResearchStrategySchemaVersion("v1"),
        parameters=(ResearchStrategyParameter("alpha", 1),),
        frozen_at=BASE + timedelta(hours=1),
        evidence_ref=ResearchStrategyFreezeEvidenceReference(_uuid(90_000)),
    )
    assert isinstance(manifest_result, Success)
    run_result = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(100_000)),
        created_at=BASE + timedelta(days=2),
        datasets=(dataset_result.value.manifest,),
        replay_policy_version=ResearchReplayPolicyVersion("point-in-time-v1"),
        simulated_start=BASE,
        simulated_end=window_closed_at,
        strategy_configuration_id=configuration_id,
        software_revision=ResearchSoftwareRevision(software_revision),
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

    qualified = tuple(
        make_qualified_observation(
            dataset_result.value.manifest,
            snapshot,
            index=index,
        )
        for index, snapshot in enumerate(snapshots)
    )
    return TraderFixture(
        binding=binding_result.value,
        manifest=dataset_result.value.manifest,
        qualified_observations=qualified,
    )


def evaluate_producer(
    producer: ResearchDecisionEvaluatorProtocol,
    *,
    software_revision: str,
    bars: tuple[tuple[float, float, float], ...],
) -> tuple[list[ResearchStrategyState], list[FunctionalDecision]]:
    """Run a producer over contiguous bars and return (states, decisions)."""
    fixture = build_trader_fixture(
        software_revision=software_revision,
        bars=bars,
    )
    state = producer.create_initial_state(
        strategy_binding=fixture.binding,
        start_policy=W1_NO_WARMUP_V1,
    )
    states = [state]
    decisions: list[FunctionalDecision] = []
    for observation in fixture.qualified_observations:
        state, produced = producer.evaluate(
            strategy_binding=fixture.binding,
            prior_state=state,
            newly_visible_inputs=(observation,),
            simulated_now=observation.observation.available_at,
        )
        states.append(state)
        decisions.extend(produced)
    return states, decisions
