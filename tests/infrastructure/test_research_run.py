from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.historical_dataset import (
    HistoricalDatasetId,
    HistoricalDatasetManifest,
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
from qore.infrastructure.research_run import (
    ResearchExecutionModelId,
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunError,
    ResearchRunEvidence,
    ResearchRunId,
    ResearchRunInputFingerprint,
    ResearchRunValidationError,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    ResearchTransactionCostModelId,
    build_research_run_evidence,
)
from qore.kernel.result import Failure, Result, Success

_BASE = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("65000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("65000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.research-run-test"),
)
_POLICY = ResearchReplayPolicyVersion("point-in-time-v1")
_STRATEGY = ResearchStrategyConfigurationId(
    UUID("65000000-0000-0000-0000-000000000003")
)
_SOFTWARE = ResearchSoftwareRevision("b672d218766e3e39650f06ae911071cae508682d")


def _uuid(suffix: int) -> UUID:
    return UUID(f"65000000-0000-0000-0000-{suffix:012d}")


def _dataset(
    *,
    dataset_suffix: int,
    revision_suffix: int,
    observation_suffix: int,
    instrument: str,
    opened_at: datetime = _BASE,
) -> HistoricalOhlcReplayDataset:
    canonical_instrument = Instrument(instrument)
    timeframe = Timeframe(300)
    scope = HistoricalOhlcDatasetScope(
        source=_SOURCE,
        window=HistoricalOhlcWindow(
            instrument=canonical_instrument,
            timeframe=timeframe,
            opened_at=opened_at,
            closed_at=opened_at + timedelta(minutes=15),
        ),
    )
    snapshot = OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(100 + observation_suffix)),
        instrument=canonical_instrument,
        source=_SOURCE,
        timeframe=timeframe,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=5),
        open=1.155,
        high=1.165,
        low=1.15,
        close=1.16,
    )
    replay = ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(200 + observation_suffix)),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=snapshot.closed_at,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(
            _uuid(300 + observation_suffix)
        ),
    )
    built = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(dataset_suffix)),
        revision_id=HistoricalDatasetRevisionId(_uuid(revision_suffix)),
        parent_revision_id=None,
        revision_reason=None,
        scope=scope,
        assembled_at=opened_at + timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion(
            "canonical-ingestion-v1"
        ),
        observations=(replay,),
    )
    assert isinstance(built, Success)
    return built.value


def _datasets() -> tuple[HistoricalOhlcReplayDataset, HistoricalOhlcReplayDataset]:
    return (
        _dataset(
            dataset_suffix=10,
            revision_suffix=11,
            observation_suffix=12,
            instrument="EURUSD",
        ),
        _dataset(
            dataset_suffix=20,
            revision_suffix=21,
            observation_suffix=22,
            instrument="GBPUSD",
        ),
    )


def _build(
    *,
    run_suffix: int = 30,
    created_at: datetime = _BASE + timedelta(days=2),
    datasets: tuple[HistoricalOhlcReplayDataset, ...] | None = None,
    replay_policy: ResearchReplayPolicyVersion = _POLICY,
    simulated_start: datetime = _BASE,
    simulated_end: datetime = _BASE + timedelta(minutes=5),
    strategy: ResearchStrategyConfigurationId = _STRATEGY,
    software: ResearchSoftwareRevision = _SOFTWARE,
    execution_model: ResearchExecutionModelId | None = None,
    cost_model: ResearchTransactionCostModelId | None = None,
    randomness_mode: ResearchRandomnessMode = ResearchRandomnessMode.DETERMINISTIC,
    random_seed: int | None = None,
) -> Result[ResearchRunEvidence, ResearchRunError]:
    resolved = datasets if datasets is not None else _datasets()
    return build_research_run_evidence(
        run_id=ResearchRunId(_uuid(run_suffix)),
        created_at=created_at,
        datasets=tuple(item.manifest for item in resolved),
        replay_policy_version=replay_policy,
        simulated_start=simulated_start,
        simulated_end=simulated_end,
        strategy_configuration_id=strategy,
        software_revision=software,
        execution_model_id=execution_model,
        transaction_cost_model_id=cost_model,
        randomness_mode=randomness_mode,
        random_seed=random_seed,
    )


def test_builder_canonicalizes_dataset_order_and_binds_exact_manifests() -> None:
    first, second = _datasets()
    built = _build(datasets=(second, first))
    assert isinstance(built, Success)
    run = built.value
    assert run.datasets == (first.manifest, second.manifest)
    assert run.simulated_start == _BASE
    assert run.simulated_end == _BASE + timedelta(minutes=5)
    assert run.replay_policy_version == _POLICY
    assert run.strategy_configuration_id == _STRATEGY
    assert run.software_revision == _SOFTWARE


def test_same_research_inputs_share_fingerprint() -> None:
    first, second = _datasets()
    left = _build(
        run_suffix=40,
        created_at=_BASE + timedelta(days=2),
        datasets=(second, first),
    )
    right = _build(
        run_suffix=41,
        created_at=_BASE + timedelta(days=3),
        datasets=(first, second),
    )
    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value.run_id != right.value.run_id
    assert left.value.created_at != right.value.created_at
    assert left.value.input_fingerprint == right.value.input_fingerprint


def test_material_input_changes_change_fingerprint() -> None:
    first, second = _datasets()
    baseline = _build(datasets=(first, second))
    assert isinstance(baseline, Success)
    revised_first = replace(
        first.manifest,
        revision_id=HistoricalDatasetRevisionId(_uuid(50)),
    )
    revised = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(51)),
        created_at=_BASE + timedelta(days=2),
        datasets=(revised_first, second.manifest),
        replay_policy_version=_POLICY,
        simulated_start=_BASE,
        simulated_end=_BASE + timedelta(minutes=5),
        strategy_configuration_id=_STRATEGY,
        software_revision=_SOFTWARE,
        execution_model_id=None,
        transaction_cost_model_id=None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    policy = _build(replay_policy=ResearchReplayPolicyVersion("point-in-time-v2"))
    strategy = _build(strategy=ResearchStrategyConfigurationId(_uuid(52)))
    software = _build(software=ResearchSoftwareRevision("software-v2"))
    execution = _build(execution_model=ResearchExecutionModelId(_uuid(53)))
    costs = _build(cost_model=ResearchTransactionCostModelId(_uuid(54)))
    seeded = _build(
        randomness_mode=ResearchRandomnessMode.SEEDED,
        random_seed=7,
    )
    assert isinstance(revised, Success)
    assert isinstance(policy, Success)
    assert isinstance(strategy, Success)
    assert isinstance(software, Success)
    assert isinstance(execution, Success)
    assert isinstance(costs, Success)
    assert isinstance(seeded, Success)
    fingerprints = {
        baseline.value.input_fingerprint,
        revised.value.input_fingerprint,
        policy.value.input_fingerprint,
        strategy.value.input_fingerprint,
        software.value.input_fingerprint,
        execution.value.input_fingerprint,
        costs.value.input_fingerprint,
        seeded.value.input_fingerprint,
    }
    assert len(fingerprints) == 8


def test_optional_execution_and_cost_references_are_explicit_not_implied() -> None:
    unbound = _build()
    bound = _build(
        execution_model=ResearchExecutionModelId(_uuid(60)),
        cost_model=ResearchTransactionCostModelId(_uuid(61)),
    )
    assert isinstance(unbound, Success)
    assert isinstance(bound, Success)
    assert unbound.value.binds_execution_model is False
    assert unbound.value.binds_transaction_cost_model is False
    assert bound.value.binds_execution_model is True
    assert bound.value.binds_transaction_cost_model is True


def test_run_rejects_duplicate_dataset_identity_even_when_revision_differs() -> None:
    first, second = _datasets()
    duplicate_identity = replace(
        second.manifest,
        dataset_id=first.manifest.dataset_id,
        revision_id=HistoricalDatasetRevisionId(_uuid(70)),
    )
    built = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(71)),
        created_at=_BASE + timedelta(days=2),
        datasets=(first.manifest, duplicate_identity),
        replay_policy_version=_POLICY,
        simulated_start=_BASE,
        simulated_end=_BASE + timedelta(minutes=5),
        strategy_configuration_id=_STRATEGY,
        software_revision=_SOFTWARE,
        execution_model_id=None,
        transaction_cost_model_id=None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    assert isinstance(built, Failure)
    assert isinstance(built.error, ResearchRunValidationError)
    assert "each dataset_id exactly once" in str(built.error)


def test_every_dataset_window_must_cover_the_simulated_run_window() -> None:
    built = _build(simulated_end=_BASE + timedelta(minutes=16))
    assert isinstance(built, Failure)
    assert isinstance(built.error, ResearchRunValidationError)
    assert "must cover" in str(built.error)


def test_temporal_contract_fails_closed_before_datetime_comparison() -> None:
    first, second = _datasets()
    naive = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(80)),
        created_at=_BASE + timedelta(days=2),
        datasets=(first.manifest, second.manifest),
        replay_policy_version=_POLICY,
        simulated_start=datetime(2026, 8, 9, 12, 0),
        simulated_end=_BASE + timedelta(minutes=5),
        strategy_configuration_id=_STRATEGY,
        software_revision=_SOFTWARE,
        execution_model_id=None,
        transaction_cost_model_id=None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    reversed_window = _build(
        simulated_start=_BASE + timedelta(minutes=5),
        simulated_end=_BASE,
    )
    assert isinstance(naive, Failure)
    assert isinstance(naive.error, ResearchRunValidationError)
    assert "timezone-aware" in str(naive.error)
    assert isinstance(reversed_window, Failure)
    assert isinstance(reversed_window.error, ResearchRunValidationError)
    assert "must be after" in str(reversed_window.error)


def test_created_at_must_be_timezone_aware() -> None:
    built = _build(created_at=datetime(2026, 8, 11, 12, 0))
    assert isinstance(built, Failure)
    assert isinstance(built.error, ResearchRunValidationError)
    assert "timezone-aware" in str(built.error)


def test_randomness_mode_distinguishes_deterministic_from_seeded_runs() -> None:
    deterministic_with_seed = _build(random_seed=1)
    seeded_without_seed = _build(randomness_mode=ResearchRandomnessMode.SEEDED)
    seeded_negative = _build(
        randomness_mode=ResearchRandomnessMode.SEEDED,
        random_seed=-1,
    )
    seeded_bool = _build(
        randomness_mode=ResearchRandomnessMode.SEEDED,
        random_seed=cast(int, True),
    )
    seeded_zero = _build(
        randomness_mode=ResearchRandomnessMode.SEEDED,
        random_seed=0,
    )
    for item in (
        deterministic_with_seed,
        seeded_without_seed,
        seeded_negative,
        seeded_bool,
    ):
        assert isinstance(item, Failure)
        assert isinstance(item.error, ResearchRunValidationError)
    assert isinstance(seeded_zero, Success)
    assert seeded_zero.value.random_seed == 0


def test_equivalent_timezone_instants_share_fingerprint() -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    local_start = _BASE.astimezone(offset)
    local_end = (_BASE + timedelta(minutes=5)).astimezone(offset)
    utc_run = _build()
    local_run = _build(
        simulated_start=local_start,
        simulated_end=local_end,
    )
    assert isinstance(utc_run, Success)
    assert isinstance(local_run, Success)
    assert utc_run.value.input_fingerprint == local_run.value.input_fingerprint
    assert local_run.value.simulated_start.isoformat().endswith("+05:30")


def test_direct_evidence_rejects_tampering_and_noncanonical_order() -> None:
    first, second = _datasets()
    built = _build(datasets=(first, second))
    assert isinstance(built, Success)
    run = built.value
    with pytest.raises(ResearchRunValidationError, match="fingerprint"):
        replace(
            run,
            input_fingerprint=ResearchRunInputFingerprint("0" * 64),
        )
    with pytest.raises(ResearchRunValidationError, match="canonical dataset order"):
        replace(run, datasets=tuple(reversed(run.datasets)))


def test_runtime_type_bypasses_and_invalid_tokens_fail_closed() -> None:
    first, second = _datasets()
    wrong_datasets = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(90)),
        created_at=_BASE + timedelta(days=2),
        datasets=cast(
            tuple[HistoricalDatasetManifest, ...],
            [first.manifest, second.manifest],
        ),
        replay_policy_version=_POLICY,
        simulated_start=_BASE,
        simulated_end=_BASE + timedelta(minutes=5),
        strategy_configuration_id=_STRATEGY,
        software_revision=_SOFTWARE,
        execution_model_id=None,
        transaction_cost_model_id=None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    assert isinstance(wrong_datasets, Failure)
    assert isinstance(wrong_datasets.error, ResearchRunValidationError)
    with pytest.raises(ResearchRunValidationError, match="canonical token"):
        ResearchReplayPolicyVersion(" point in time ")
    with pytest.raises(ResearchRunValidationError, match="canonical token"):
        ResearchSoftwareRevision("revision with spaces")


def test_research_run_has_no_execution_or_statistics_authority() -> None:
    prohibited = {
        "advance_to",
        "buy",
        "compute_sharpe",
        "dispatch",
        "execute",
        "fill",
        "sell",
        "submit_order",
    }
    assert prohibited.isdisjoint(set(dir(ResearchRunEvidence)))
    fields = set(ResearchRunEvidence.__dataclass_fields__)
    assert "performance_metrics" not in fields
    assert "result_digest" not in fields
