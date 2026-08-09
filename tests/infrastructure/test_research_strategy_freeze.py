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
    ResearchStrategyConfigurationDigest,
    ResearchStrategyConfigurationManifest,
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyFreezeValidationError,
    ResearchStrategyParameter,
    ResearchStrategySchemaVersion,
    build_research_run_strategy_binding,
    build_research_strategy_configuration_manifest,
    compute_research_strategy_configuration_digest,
)
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
_PROCESS_TIME = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("71000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("71000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.research-strategy-freeze-test"),
)
_SCHEMA = ResearchStrategySchemaVersion("strategy-config-v1")


def _uuid(suffix: int) -> UUID:
    return UUID(f"71000000-0000-0000-0000-{suffix:012d}")


def _configuration_id(suffix: int = 10) -> ResearchStrategyConfigurationId:
    return ResearchStrategyConfigurationId(_uuid(suffix))


def _run(
    *,
    configuration_id: ResearchStrategyConfigurationId | None = None,
    created_at: datetime = _PROCESS_TIME,
) -> ResearchRunEvidence:
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
    built = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(25)),
        created_at=created_at,
        datasets=(dataset.value.manifest,),
        replay_policy_version=ResearchReplayPolicyVersion("point-in-time-v1"),
        simulated_start=_BASE,
        simulated_end=_BASE + timedelta(minutes=30),
        strategy_configuration_id=configuration_id or _configuration_id(),
        software_revision=ResearchSoftwareRevision("a8a17b1c"),
        execution_model_id=None,
        transaction_cost_model_id=None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    assert isinstance(built, Success)
    return built.value


def _parameters() -> tuple[ResearchStrategyParameter, ...]:
    return (
        ResearchStrategyParameter("entry.threshold", Decimal("0.7500")),
        ResearchStrategyParameter("risk.enabled", True),
        ResearchStrategyParameter("risk.max_positions", 2),
        ResearchStrategyParameter("session.name", "new-york"),
    )


def _manifest(
    *,
    configuration_id: ResearchStrategyConfigurationId | None = None,
    frozen_at: datetime = _PROCESS_TIME - timedelta(minutes=1),
) -> ResearchStrategyConfigurationManifest:
    built = build_research_strategy_configuration_manifest(
        configuration_id=configuration_id or _configuration_id(),
        schema_version=_SCHEMA,
        parameters=tuple(reversed(_parameters())),
        frozen_at=frozen_at,
        evidence_ref=ResearchStrategyFreezeEvidenceReference(_uuid(30)),
    )
    assert isinstance(built, Success)
    return built.value


def test_manifest_canonicalizes_parameters_and_hashes_exact_typed_content() -> None:
    manifest = _manifest()
    assert tuple(item.name for item in manifest.parameters) == (
        "entry.threshold",
        "risk.enabled",
        "risk.max_positions",
        "session.name",
    )
    same_logical_decimal = tuple(
        ResearchStrategyParameter(item.name, Decimal("0.75"))
        if item.name == "entry.threshold"
        else item
        for item in _parameters()
    )
    same_digest = compute_research_strategy_configuration_digest(
        schema_version=_SCHEMA,
        parameters=tuple(reversed(same_logical_decimal)),
    )
    assert same_digest == manifest.content_digest

    int_digest = compute_research_strategy_configuration_digest(
        schema_version=_SCHEMA,
        parameters=(ResearchStrategyParameter("flag", 1),),
    )
    bool_digest = compute_research_strategy_configuration_digest(
        schema_version=_SCHEMA,
        parameters=(ResearchStrategyParameter("flag", True),),
    )
    assert int_digest != bool_digest


def test_content_digest_excludes_administrative_identity_and_freeze_time() -> None:
    first = _manifest()
    second = build_research_strategy_configuration_manifest(
        configuration_id=_configuration_id(40),
        schema_version=_SCHEMA,
        parameters=_parameters(),
        frozen_at=_PROCESS_TIME - timedelta(days=1),
        evidence_ref=ResearchStrategyFreezeEvidenceReference(_uuid(41)),
    )
    assert isinstance(second, Success)
    assert first.content_digest == second.value.content_digest


def test_manifest_rejects_digest_tampering_and_naive_freeze_time() -> None:
    manifest = _manifest()
    with pytest.raises(ResearchStrategyFreezeValidationError):
        replace(
            manifest,
            content_digest=ResearchStrategyConfigurationDigest("0" * 64),
        )

    naive = build_research_strategy_configuration_manifest(
        configuration_id=_configuration_id(),
        schema_version=_SCHEMA,
        parameters=_parameters(),
        frozen_at=datetime(2026, 8, 9, 11, 59),
        evidence_ref=ResearchStrategyFreezeEvidenceReference(_uuid(50)),
    )
    assert isinstance(naive, Failure)
    assert "timezone-aware" in str(naive.error)


def test_run_binding_requires_exact_configuration_identity() -> None:
    run = _run()
    mismatched = _manifest(configuration_id=_configuration_id(60))
    built = build_research_run_strategy_binding(run=run, manifest=mismatched)
    assert isinstance(built, Failure)
    assert "configuration id must match" in str(built.error)


def test_run_binding_uses_process_time_not_historical_simulated_time() -> None:
    run = _run(created_at=_PROCESS_TIME)
    manifest = _manifest(frozen_at=_PROCESS_TIME - timedelta(seconds=1))
    assert manifest.frozen_at > run.simulated_end

    built = build_research_run_strategy_binding(run=run, manifest=manifest)
    assert isinstance(built, Success)
    assert built.value.manifest == manifest
    assert built.value.run == run


def test_run_binding_rejects_configuration_frozen_after_run_creation() -> None:
    run = _run(created_at=_PROCESS_TIME)
    manifest = _manifest(frozen_at=_PROCESS_TIME + timedelta(seconds=1))
    built = build_research_run_strategy_binding(run=run, manifest=manifest)
    assert isinstance(built, Failure)
    assert "no later than research run creation" in str(built.error)


def test_strategy_freeze_claims_no_oos_blindness_or_execution_authority() -> None:
    binding = build_research_run_strategy_binding(run=_run(), manifest=_manifest())
    assert isinstance(binding, Success)
    evidence = binding.value
    assert not hasattr(evidence, "analyst_blind")
    assert not hasattr(evidence, "pre_registered_before_data_access")
    assert not hasattr(evidence, "execute")
    assert not hasattr(evidence, "submit_order")
