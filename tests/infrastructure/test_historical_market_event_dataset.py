from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.historical_dataset import (
    HistoricalDatasetId,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
)
from qore.infrastructure.historical_market_event_dataset import (
    HistoricalMarketEventDataset,
    HistoricalMarketEventDatasetError,
    HistoricalMarketEventDatasetScope,
    HistoricalMarketEventDatasetValidationError,
    build_historical_market_event_dataset,
    compute_historical_market_event_evidence_digest,
)
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_event_replay import (
    MarketCaptureLineageId,
    MarketCaptureSessionId,
    MarketCaptureSessionOrdinal,
    MarketEventAvailabilityBasis,
    MarketEventAvailabilityEvidenceReference,
    MarketEventObservationId,
    MarketIngressSequence,
    RetainedMarketEventObservation,
)
from qore.infrastructure.market_observation import (
    InstrumentMarketSpecification,
    InstrumentMarketSpecificationId,
    MarketBarOrigin,
    MarketObservationEvidenceReference,
    MarketObservationId,
    MarketOhlcField,
    MarketOhlcFieldValidity,
    MarketPrice,
    MarketPriceSide,
    MarketTimeframe,
    MarketTimeframeCode,
    QualifiedOhlcBarObservation,
    QualifiedQuoteTickObservation,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.kernel.result import Failure, Result, Success

_BASE = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("65000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("65000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.mixed-dataset-test"),
)
_INSTRUMENT = Instrument("EURUSD")
_LINEAGE = MarketCaptureLineageId(UUID("65000000-0000-0000-0000-000000000003"))
_SCHEMA = HistoricalDatasetSchemaVersion("market-event-replay-v1")
_NORMALIZATION = HistoricalDatasetNormalizationVersion("market-evidence-v2")


def _uuid(suffix: int) -> UUID:
    return UUID(f"65000000-0000-0000-0000-{suffix:012d}")


def _price(value: str) -> MarketPrice:
    return MarketPrice(Decimal(value))


def _field(value: str) -> MarketOhlcField:
    return MarketOhlcField(MarketOhlcFieldValidity.VALID, _price(value))


def _quote(*, suffix: int, bid: str = "1.1000") -> QualifiedQuoteTickObservation:
    return QualifiedQuoteTickObservation(
        observation_id=MarketObservationId(_uuid(100 + suffix)),
        instrument=_INSTRUMENT,
        source=_SOURCE,
        observed_at=_BASE,
        bid=_price(bid),
        ask=_price(str(Decimal(bid) + Decimal("0.0001"))),
        evidence_ref=MarketObservationEvidenceReference(_uuid(200 + suffix)),
    )


def _ohlc(*, suffix: int) -> QualifiedOhlcBarObservation:
    opened_at = _BASE - timedelta(minutes=5)
    return QualifiedOhlcBarObservation(
        observation_id=MarketObservationId(_uuid(300 + suffix)),
        instrument=_INSTRUMENT,
        source=_SOURCE,
        timeframe=MarketTimeframe(MarketTimeframeCode.M5),
        price_side=MarketPriceSide.BID,
        origin=MarketBarOrigin.NATIVE,
        opened_at=opened_at,
        closed_at=_BASE,
        open=_field("1.1000"),
        high=_field("1.1010"),
        low=_field("1.0990"),
        close=_field("1.1005"),
        evidence_ref=MarketObservationEvidenceReference(_uuid(400 + suffix)),
    )


def _spec(*, suffix: int) -> InstrumentMarketSpecification:
    return InstrumentMarketSpecification(
        specification_id=InstrumentMarketSpecificationId(_uuid(500 + suffix)),
        instrument=_INSTRUMENT,
        source=_SOURCE,
        provider_symbol="EURUSD",
        provider_symbol_id="1",
        price_precision=5,
        minimum_price_increment=_price("0.00001"),
        effective_at=_BASE - timedelta(hours=1),
        evidence_ref=MarketObservationEvidenceReference(_uuid(600 + suffix)),
    )


def _event(
    payload: QualifiedQuoteTickObservation
    | QualifiedOhlcBarObservation
    | InstrumentMarketSpecification,
    *,
    suffix: int,
    sequence: int,
    received_offset_ms: int,
) -> RetainedMarketEventObservation:
    received_at = _BASE + timedelta(seconds=1, milliseconds=received_offset_ms)
    core_ingress_at = received_at + timedelta(milliseconds=1)
    return RetainedMarketEventObservation(
        event_id=MarketEventObservationId(_uuid(700 + suffix)),
        payload=payload,
        capture_lineage_id=_LINEAGE,
        capture_session_id=MarketCaptureSessionId(_uuid(700)),
        capture_session_ordinal=MarketCaptureSessionOrdinal(0),
        ingress_sequence=MarketIngressSequence(sequence),
        boundary_received_at=received_at,
        core_ingress_at=core_ingress_at,
        availability_evidence_at=core_ingress_at,
        available_at=core_ingress_at,
        availability_basis=MarketEventAvailabilityBasis.CORE_INGRESS,
        availability_evidence_ref=MarketEventAvailabilityEvidenceReference(
            _uuid(800 + suffix)
        ),
    )


def _scope(
    *,
    source: ExternalSourceDescriptor = _SOURCE,
    instrument: Instrument = _INSTRUMENT,
    lineage: MarketCaptureLineageId = _LINEAGE,
    opened_at: datetime = _BASE,
    closed_at: datetime = _BASE + timedelta(minutes=5),
) -> HistoricalMarketEventDatasetScope:
    return HistoricalMarketEventDatasetScope(
        source=source,
        instrument=instrument,
        capture_lineage_id=lineage,
        opened_at=opened_at,
        closed_at=closed_at,
    )


def _build(
    observations: tuple[RetainedMarketEventObservation, ...],
    *,
    dataset_suffix: int = 1,
    revision_suffix: int = 2,
    scope: HistoricalMarketEventDatasetScope | None = None,
    assembled_at: datetime = _BASE + timedelta(minutes=6),
) -> Result[HistoricalMarketEventDataset, HistoricalMarketEventDatasetError]:
    return build_historical_market_event_dataset(
        dataset_id=HistoricalDatasetId(_uuid(dataset_suffix)),
        revision_id=HistoricalDatasetRevisionId(_uuid(revision_suffix)),
        parent_revision_id=None,
        revision_reason=None,
        scope=scope if scope is not None else _scope(),
        assembled_at=assembled_at,
        schema_version=_SCHEMA,
        normalization_version=_NORMALIZATION,
        observations=observations,
    )


def test_dataset_retains_mixed_payloads_duplicates_and_conflicts() -> None:
    quote = _event(_quote(suffix=1), suffix=1, sequence=1, received_offset_ms=0)
    ohlc = _event(_ohlc(suffix=2), suffix=2, sequence=2, received_offset_ms=2)
    spec = _event(_spec(suffix=3), suffix=3, sequence=3, received_offset_ms=4)
    duplicate_payload = _quote(suffix=10)
    duplicate_first = _event(
        duplicate_payload, suffix=10, sequence=4, received_offset_ms=6
    )
    duplicate_second = _event(
        duplicate_payload, suffix=11, sequence=5, received_offset_ms=8
    )
    conflict = _event(
        _quote(suffix=12, bid="1.1002"),
        suffix=12,
        sequence=6,
        received_offset_ms=10,
    )

    built = _build((conflict, duplicate_second, spec, quote, duplicate_first, ohlc))

    assert isinstance(built, Success)
    assert built.value.observations == (
        quote,
        ohlc,
        spec,
        duplicate_first,
        duplicate_second,
        conflict,
    )
    assert (
        duplicate_first.payload.logical_values()
        == duplicate_second.payload.logical_values()
    )
    assert conflict.canonical_boundary == duplicate_first.canonical_boundary
    assert conflict.payload.logical_values() != duplicate_first.payload.logical_values()


def test_digest_is_order_independent_and_excludes_admin_identity() -> None:
    first = _event(_quote(suffix=20), suffix=20, sequence=1, received_offset_ms=0)
    second = _event(_ohlc(suffix=21), suffix=21, sequence=2, received_offset_ms=2)
    left = _build((second, first), dataset_suffix=30, revision_suffix=31)
    right = _build(
        (first, second),
        dataset_suffix=32,
        revision_suffix=33,
        assembled_at=_BASE + timedelta(minutes=7),
    )

    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value.manifest.dataset_id != right.value.manifest.dataset_id
    assert left.value.manifest.revision_id != right.value.manifest.revision_id
    assert left.value.manifest.assembled_at != right.value.manifest.assembled_at
    assert left.value.manifest.evidence_digest == right.value.manifest.evidence_digest


def test_digest_changes_with_payload_arrival_or_visibility_evidence() -> None:
    baseline = _event(
        _quote(suffix=40, bid="1.1000"), suffix=40, sequence=1, received_offset_ms=0
    )
    payload_changed = replace(
        baseline, payload=_quote(suffix=40, bid="1.1001")
    )
    sequence_changed = replace(baseline, ingress_sequence=MarketIngressSequence(2))
    visibility_changed = replace(
        baseline, available_at=baseline.available_at + timedelta(seconds=1)
    )

    digests = []
    for observation in (
        baseline,
        payload_changed,
        sequence_changed,
        visibility_changed,
    ):
        built = _build((observation,))
        assert isinstance(built, Success)
        digests.append(built.value.manifest.evidence_digest)

    assert len(set(digests)) == 4


def test_digest_canonicalizes_timezone_equivalent_instants() -> None:
    event = _event(_quote(suffix=50), suffix=50, sequence=1, received_offset_ms=0)
    offset = timezone(timedelta(hours=-4))
    offset_event = replace(
        event,
        boundary_received_at=event.boundary_received_at.astimezone(offset),
        core_ingress_at=event.core_ingress_at.astimezone(offset),
        availability_evidence_at=event.availability_evidence_at.astimezone(offset),
        available_at=event.available_at.astimezone(offset),
    )
    offset_scope = _scope(
        opened_at=_scope().opened_at.astimezone(offset),
        closed_at=_scope().closed_at.astimezone(offset),
    )

    utc_digest = compute_historical_market_event_evidence_digest(
        _scope(),
        (event,),
        schema_version=_SCHEMA,
        normalization_version=_NORMALIZATION,
    )
    offset_digest = compute_historical_market_event_evidence_digest(
        offset_scope,
        (offset_event,),
        schema_version=_SCHEMA,
        normalization_version=_NORMALIZATION,
    )

    assert utc_digest == offset_digest


def test_duplicate_arrival_provenance_returns_typed_failure() -> None:
    first = _event(_quote(suffix=60), suffix=60, sequence=1, received_offset_ms=0)
    duplicate = _event(
        _quote(suffix=61), suffix=61, sequence=1, received_offset_ms=0
    )

    built = _build((first, duplicate))

    assert isinstance(built, Failure)
    assert isinstance(built.error, HistoricalMarketEventDatasetValidationError)


def test_scope_fail_closed_on_source_instrument_lineage_and_ingress_window() -> None:
    event = _event(_quote(suffix=70), suffix=70, sequence=1, received_offset_ms=0)
    other_source = ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(901)),
        source_id=SourceId(_uuid(902)),
        port_name=PortName("market-data.other"),
    )

    assert isinstance(_build((event,), scope=_scope(source=other_source)), Failure)
    assert isinstance(
        _build((event,), scope=_scope(instrument=Instrument("GBPUSD"))), Failure
    )
    assert isinstance(
        _build((event,), scope=_scope(lineage=MarketCaptureLineageId(_uuid(903)))),
        Failure,
    )
    assert isinstance(
        _build(
            (event,),
            scope=_scope(
                opened_at=_BASE + timedelta(minutes=1),
                closed_at=_BASE + timedelta(minutes=2),
            ),
        ),
        Failure,
    )


def test_dataset_constructor_requires_canonical_arrival_order_and_digest() -> None:
    first = _event(_quote(suffix=80), suffix=80, sequence=1, received_offset_ms=0)
    second = _event(_quote(suffix=81), suffix=81, sequence=2, received_offset_ms=2)
    built = _build((second, first))
    assert isinstance(built, Success)

    with pytest.raises(HistoricalMarketEventDatasetValidationError):
        replace(built.value, observations=(second, first))
    changed_first = replace(
        first,
        available_at=first.available_at + timedelta(seconds=1),
    )
    with pytest.raises(HistoricalMarketEventDatasetValidationError):
        replace(built.value, observations=(changed_first, second))


def test_manifest_cannot_be_assembled_before_declared_capture_window_closes() -> None:
    event = _event(_quote(suffix=90), suffix=90, sequence=1, received_offset_ms=0)

    assert isinstance(
        _build((event,), assembled_at=_BASE + timedelta(minutes=4)), Failure
    )
