from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.historical_dataset import (
    HistoricalCoverageGap,
    HistoricalDatasetDigest,
    HistoricalDatasetError,
    HistoricalDatasetId,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
    HistoricalDatasetValidationError,
    HistoricalOhlcDatasetScope,
    HistoricalOhlcReplayDataset,
    build_historical_ohlc_replay_dataset,
    compute_historical_dataset_evidence_digest,
)
from qore.infrastructure.historical_market_data import HistoricalOhlcWindow
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    QuoteSnapshot,
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
from qore.kernel.result import Failure, Result, Success

_BASE = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
_TIMEFRAME = Timeframe(300)
_INSTRUMENT = Instrument("EURUSD")
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("64000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("64000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.historical-dataset-test"),
)
_SCHEMA = HistoricalDatasetSchemaVersion("ohlc-replay-v1")
_NORMALIZATION = HistoricalDatasetNormalizationVersion("canonical-ingestion-v1")


def _uuid(suffix: int) -> UUID:
    return UUID(f"64000000-0000-0000-0000-{suffix:012d}")


def _scope(
    *,
    source: ExternalSourceDescriptor = _SOURCE,
    instrument: Instrument = _INSTRUMENT,
    timeframe: Timeframe = _TIMEFRAME,
    opened_at: datetime = _BASE,
    closed_at: datetime | None = None,
) -> HistoricalOhlcDatasetScope:
    resolved_close = closed_at if closed_at is not None else opened_at + timedelta(minutes=15)
    return HistoricalOhlcDatasetScope(
        source=source,
        window=HistoricalOhlcWindow(
            instrument=instrument,
            timeframe=timeframe,
            opened_at=opened_at,
            closed_at=resolved_close,
        ),
    )


def _observation(
    index: int,
    *,
    suffix: int,
    opened_at: datetime | None = None,
    source: ExternalSourceDescriptor = _SOURCE,
    instrument: Instrument = _INSTRUMENT,
    timeframe: Timeframe = _TIMEFRAME,
    available_delay: timedelta = timedelta(0),
    close_price: float = 1.16,
) -> ReplayMarketDataObservation:
    resolved_open = opened_at if opened_at is not None else _BASE + timedelta(minutes=5 * index)
    snapshot = OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(100 + suffix)),
        instrument=instrument,
        source=source,
        timeframe=timeframe,
        opened_at=resolved_open,
        closed_at=resolved_open + timedelta(seconds=timeframe.seconds),
        open=1.155,
        high=1.165,
        low=1.15,
        close=close_price,
    )
    return ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(200 + suffix)),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=snapshot.closed_at + available_delay,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(
            _uuid(300 + suffix)
        ),
    )


def _build(
    observations: tuple[ReplayMarketDataObservation, ...],
    *,
    dataset_suffix: int = 1,
    revision_suffix: int = 2,
    assembled_at: datetime = _BASE + timedelta(days=1),
    scope: HistoricalOhlcDatasetScope | None = None,
    schema: HistoricalDatasetSchemaVersion = _SCHEMA,
    normalization: HistoricalDatasetNormalizationVersion = _NORMALIZATION,
) -> Result[HistoricalOhlcReplayDataset, HistoricalDatasetError]:
    return build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(dataset_suffix)),
        revision_id=HistoricalDatasetRevisionId(_uuid(revision_suffix)),
        parent_revision_id=None,
        revision_reason=None,
        scope=scope if scope is not None else _scope(),
        assembled_at=assembled_at,
        schema_version=schema,
        normalization_version=normalization,
        observations=observations,
    )


def test_builder_canonicalizes_incidental_input_order_and_derives_complete_coverage() -> None:
    first = _observation(0, suffix=10)
    second = _observation(1, suffix=11)
    third = _observation(2, suffix=12)

    built = _build((third, first, second))

    assert isinstance(built, Success)
    dataset = built.value
    assert dataset.observations == (first, second, third)
    assert dataset.manifest.observation_count == 3
    assert dataset.manifest.actual_opened_at == _BASE
    assert dataset.manifest.actual_closed_at == _BASE + timedelta(minutes=15)
    assert dataset.manifest.gaps == ()


def test_dataset_derives_leading_middle_and_trailing_gaps_without_filling_them() -> None:
    scope = _scope(
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=25),
    )
    second = _observation(1, suffix=20)
    fourth = _observation(3, suffix=21)

    built = _build((fourth, second), scope=scope)

    assert isinstance(built, Success)
    assert built.value.manifest.gaps == (
        HistoricalCoverageGap(_BASE, _BASE + timedelta(minutes=5)),
        HistoricalCoverageGap(
            _BASE + timedelta(minutes=10),
            _BASE + timedelta(minutes=15),
        ),
        HistoricalCoverageGap(
            _BASE + timedelta(minutes=20),
            _BASE + timedelta(minutes=25),
        ),
    )


def test_same_semantic_evidence_hashes_identically_across_input_order_and_admin_identity() -> None:
    first = _observation(0, suffix=30)
    second = _observation(1, suffix=31, available_delay=timedelta(seconds=2))

    left = _build(
        (second, first),
        dataset_suffix=40,
        revision_suffix=41,
        assembled_at=_BASE + timedelta(days=1),
    )
    right = _build(
        (first, second),
        dataset_suffix=42,
        revision_suffix=43,
        assembled_at=_BASE + timedelta(days=2),
    )

    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value.manifest.dataset_id != right.value.manifest.dataset_id
    assert left.value.manifest.revision_id != right.value.manifest.revision_id
    assert left.value.manifest.assembled_at != right.value.manifest.assembled_at
    assert left.value.manifest.evidence_digest == right.value.manifest.evidence_digest


def test_digest_normalizes_equivalent_timezone_instants_without_mutating_contract_times() -> None:
    offset = timezone(timedelta(hours=5, minutes=30))
    local_base = _BASE.astimezone(offset)
    utc_observation = _observation(0, suffix=50, opened_at=_BASE)
    local_observation = _observation(0, suffix=50, opened_at=local_base)
    utc_scope = _scope(opened_at=_BASE)
    local_scope = _scope(opened_at=local_base)

    utc_digest = compute_historical_dataset_evidence_digest(
        utc_scope,
        (utc_observation,),
        schema_version=_SCHEMA,
        normalization_version=_NORMALIZATION,
    )
    local_digest = compute_historical_dataset_evidence_digest(
        local_scope,
        (local_observation,),
        schema_version=_SCHEMA,
        normalization_version=_NORMALIZATION,
    )

    assert utc_digest == local_digest
    assert isinstance(local_observation.payload, OhlcSnapshot)
    assert local_observation.payload.opened_at.isoformat().endswith("+05:30")


def test_digest_changes_when_market_value_availability_or_processing_version_changes() -> None:
    base = _observation(0, suffix=60)
    price_changed = _observation(0, suffix=60, close_price=1.161)
    availability_changed = _observation(
        0,
        suffix=60,
        available_delay=timedelta(seconds=1),
    )

    baseline = _build((base,))
    changed_price = _build((price_changed,))
    changed_availability = _build((availability_changed,))
    changed_schema = _build(
        (base,),
        schema=HistoricalDatasetSchemaVersion("ohlc-replay-v2"),
    )
    changed_normalization = _build(
        (base,),
        normalization=HistoricalDatasetNormalizationVersion("canonical-ingestion-v2"),
    )

    for item in (
        baseline,
        changed_price,
        changed_availability,
        changed_schema,
        changed_normalization,
    ):
        assert isinstance(item, Success)
    digests = {
        baseline.value.manifest.evidence_digest,
        changed_price.value.manifest.evidence_digest,
        changed_availability.value.manifest.evidence_digest,
        changed_schema.value.manifest.evidence_digest,
        changed_normalization.value.manifest.evidence_digest,
    }
    assert len(digests) == 5


def test_dataset_rejects_source_instrument_timeframe_or_window_scope_mismatch() -> None:
    other_source = ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(70)),
        source_id=SourceId(_uuid(71)),
        port_name=PortName("market-data.other-dataset-test"),
    )
    cases = (
        _observation(0, suffix=72, source=other_source),
        _observation(0, suffix=73, instrument=Instrument("GBPUSD")),
        _observation(0, suffix=74, timeframe=Timeframe(60)),
        _observation(0, suffix=75, opened_at=_BASE - timedelta(minutes=5)),
    )

    for observation in cases:
        built = _build((observation,))
        assert isinstance(built, Failure)
        assert isinstance(built.error, HistoricalDatasetValidationError)


def test_dataset_rejects_overlapping_or_duplicate_evidence_identities() -> None:
    first = _observation(0, suffix=80)
    overlap = _observation(
        0,
        suffix=81,
        opened_at=_BASE + timedelta(minutes=1),
    )
    overlapping = _build((first, overlap))
    assert isinstance(overlapping, Failure)
    assert isinstance(overlapping.error, HistoricalDatasetValidationError)
    assert "must not overlap" in str(overlapping.error)

    duplicate = _build((first, first))
    assert isinstance(duplicate, Failure)
    assert isinstance(duplicate.error, HistoricalDatasetValidationError)
    assert "identities must be unique" in str(duplicate.error)


def test_historical_ohlc_dataset_rejects_quote_payloads() -> None:
    quote = QuoteSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(90)),
        instrument=_INSTRUMENT,
        source=_SOURCE,
        observed_at=_BASE,
        bid=1.16,
        ask=1.1602,
    )
    replay = ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(91)),
        payload=quote,
        availability_evidence_at=quote.observed_at,
        available_at=quote.observed_at,
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(_uuid(92)),
    )

    built = _build((replay,))

    assert isinstance(built, Failure)
    assert isinstance(built.error, HistoricalDatasetValidationError)
    assert "requires OhlcSnapshot" in str(built.error)


def test_manifest_revision_lineage_is_explicit_and_cannot_self_parent() -> None:
    observation = _observation(0, suffix=100)
    built = _build((observation,))
    assert isinstance(built, Success)
    manifest = built.value.manifest

    with pytest.raises(HistoricalDatasetValidationError, match="present together"):
        replace(
            manifest,
            parent_revision_id=HistoricalDatasetRevisionId(_uuid(101)),
            revision_reason=None,
        )
    with pytest.raises(HistoricalDatasetValidationError, match="own parent"):
        replace(
            manifest,
            parent_revision_id=manifest.revision_id,
            revision_reason="provider correction",
        )


def test_dataset_rejects_tampered_manifest_digest_coverage_or_order() -> None:
    first = _observation(0, suffix=110)
    second = _observation(1, suffix=111)
    built = _build((first, second))
    assert isinstance(built, Success)
    dataset = built.value

    with pytest.raises(HistoricalDatasetValidationError, match="digest"):
        HistoricalOhlcReplayDataset(
            replace(
                dataset.manifest,
                evidence_digest=HistoricalDatasetDigest("0" * 64),
            ),
            dataset.observations,
        )
    with pytest.raises(HistoricalDatasetValidationError, match="actual coverage"):
        HistoricalOhlcReplayDataset(
            replace(
                dataset.manifest,
                actual_closed_at=dataset.manifest.actual_closed_at - timedelta(minutes=5),
            ),
            dataset.observations,
        )
    with pytest.raises(HistoricalDatasetValidationError, match="canonical replay order"):
        HistoricalOhlcReplayDataset(
            dataset.manifest,
            tuple(reversed(dataset.observations)),
        )


def test_builder_rejects_naive_assembly_time_and_runtime_type_bypasses() -> None:
    observation = _observation(0, suffix=120)
    naive = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(121)),
        revision_id=HistoricalDatasetRevisionId(_uuid(122)),
        parent_revision_id=None,
        revision_reason=None,
        scope=_scope(),
        assembled_at=datetime(2026, 8, 10, 12, 0),
        schema_version=_SCHEMA,
        normalization_version=_NORMALIZATION,
        observations=(observation,),
    )
    wrong_id = build_historical_ohlc_replay_dataset(
        dataset_id=cast(HistoricalDatasetId, object()),
        revision_id=HistoricalDatasetRevisionId(_uuid(123)),
        parent_revision_id=None,
        revision_reason=None,
        scope=_scope(),
        assembled_at=_BASE + timedelta(days=1),
        schema_version=_SCHEMA,
        normalization_version=_NORMALIZATION,
        observations=(observation,),
    )

    assert isinstance(naive, Failure)
    assert isinstance(naive.error, HistoricalDatasetValidationError)
    assert isinstance(wrong_id, Failure)
    assert isinstance(wrong_id.error, HistoricalDatasetValidationError)


def test_dataset_contract_has_no_storage_network_replay_clock_or_trading_authority() -> None:
    prohibited = {
        "advance_to",
        "buy",
        "core_decision",
        "fetch",
        "read_external_ohlc",
        "sell",
        "store",
        "submit_order",
    }
    assert prohibited.isdisjoint(set(dir(HistoricalOhlcReplayDataset)))
