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
from qore.kernel.result import Failure, Success

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
    return MarketOhlcField(
        validity=MarketOhlcFieldValidity.VALID,
        price=_price(value),
    )


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
    available_delay_ms: int = 0,
    session_id: int = 700,
    session_ordinal: int = 0,
) -> RetainedMarketEventObservation:
    received_at = _BASE + timedelta(seconds=1, milliseconds=received_offset_ms)
    core_ingress_at = received_at + timedelta(milliseconds=1)
    return RetainedMarketEventObservation(
        event_id=MarketEventObservationId(_uuid(700 + suffix)),
        payload=payload,
        capture_lineage_id=_LINEAGE,
        capture_session_id=MarketCaptureSessionId(_uuid(session_id)),
        capture_session_ordinal=MarketCaptureSessionOrdinal(session_ordinal),
        ingress_sequence=MarketIngressSequence(sequence),
        boundary_received_at=received_at,
        core_ingress_at=core_ingress_at,
        availability_evidence_at=core_ingress_at,
        available_at=core_ingress_at + timedelta(milliseconds=available_delay_ms),
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
):
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


def test_dataset_retains_quote_ohlc_and_instrument_specification() -> None:
    quote = _event(_quote(suffix=1), suffix=1, sequence=1, received_offset_ms=0)
    ohlc = _event(_ohlc(suffix=2), suffix=2, sequence=2, received_offset_ms=2)
    spec = _event(_spec(suffix=3), suffix=3, sequence=3, received_offset_ms=4)

    built = _build((spec, quote, ohlc))

    assert isinstance(built, Success)
    assert built.value.observations == (quote, ohlc, spec)
    assert tuple(item.payload_kind for item in built.value.observations) == (
        "quote",
        "ohlc",
        "instrument_specification",
    )


def test_exact_duplicate_payloads_are_retained_as_distinct_arrivals() -> None:
    payload = _quote(suffix=10)
    first = _event(payload, suffix=10, sequence=1, received_offset_ms=0)
    second = _event(payload, suffix=11, sequence=2, received_offset_ms=2)

    built = _build((second, first))

    assert isinstance(built, Success)
    assert built.value.observations == (first, second)
    assert built.value.manifest.observation_count == 2
    assert first.payload.logical_values() == second.payload.logical_values()


def test_conflicting_same_timestamp_payloads_are_retained_in_arrival_order() -> None:
    first = _event(
        _quote(suffix=20, bid="1.1000"),
        suffix=20,
        sequence=1,
        received_offset_ms=0,
    )
    second = _event(
        _quote(suffix=21, bid="1.1002"),
        suffix=21,
        sequence=2,
        received_offset_ms=2,
    )

    built = _build((second, first))

    assert isinstance(built, Success)
    assert built.value.observations == (first, second)
    assert first.canonical_boundary == second.canonical_boundary
    assert first.payload.logical_values() != second.payload.logical_values()


def test_digest_is_deterministic_under_incidental_input_permutation() -> None:
    first = _event(_quote(suffix=30), suffix=30, sequence=1, received_offset_ms=0)
    second = _event(_ohlc(suffix=31), suffix=31, sequence=2, received_offset_ms=2)

    left = _build(
        (second, first),
        dataset_suffix=31,
        revision_suffix=32,
    )
    right = _build(
        (first, second),
        dataset_suffix=33,
        revision_suffix=34,
        assembled_at=_BASE + timedelta(minutes=7),
    )

    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value.manifest.dataset_id != right.value.manifest.dataset_id
    assert left.value.manifest.revision_id != right.value.manifest.revision_id
    assert left.value.manifest.assembled_at != right.value.manifest.assembled_at
    assert left.value.manifest.evidence_digest == right.value.manifest.evidence_digest


def test_digest_changes_when_payload_content_changes() -> None:
    baseline = _event(
        _quote(suffix=40, bid="1.1000"),
        suffix=40,
        sequence=1,
        received_offset_ms=0,
    )
    changed = replace(
        baseline,
        payload=_quote(suffix=40, bid="1.1001"),
    )

    baseline_built = _build((baseline,))
    changed_built = _build((changed,))

    assert isinstance(baseline_built, Success)
    assert isinstance(changed_built, Success)
    assert (
        baseline_built.value.manifest.evidence_digest
        != changed_built.value.manifest.evidence_digest
    )


def test_digest_changes_when_arrival_sequence_changes() -> None:
    base_time = _BASE + timedelta(seconds=1)
    first = _event(
        _quote(suffix=50),
        suffix=50,
        sequence=1,
        received_offset_ms=0,
    )
    second = _event(
        _quote(suffix=51),
        suffix=51,
        sequence=2,
        received_offset_ms=0,
    )
    first_swapped = replace(first, ingress_sequence=MarketIngressSequence(2))
    second_swapped = replace(second, ingress_sequence=MarketIngressSequence(1))
    first_swapped = replace(
        first_swapped,
        boundary_received_at=base_time,
        core_ingress_at=base_time + timedelta(milliseconds=1),
        availability_evidence_at=base_time + timedelta(milliseconds=1),
        available_at=base_time + timedelta(milliseconds=1),
    )
    second_swapped = replace(
        second_swapped,
        boundary_received_at=base_time,
        core_ingress_at=base_time + timedelta(milliseconds=1),
        availability_evidence_at=base_time + timedelta(milliseconds=1),
        available_at=base_time + timedelta(milliseconds=1),
    )

    baseline = _build((first, second))
    swapped = _build((first_swapped, second_swapped))

    assert isinstance(baseline, Success)
    assert isinstance(swapped, Success)
    assert baseline.value.manifest.evidence_digest != swapped.value.manifest.evidence_digest


def test_digest_changes_when_available_at_changes() -> None:
    event = _event(
        _quote(suffix=60),
        suffix=60,
        sequence=1,
        received_offset_ms=0,
    )
    delayed = replace(event, available_at=event.available_at + timedelta(seconds=1))

    baseline = _build((event,))
    changed = _build((delayed,))

    assert isinstance(baseline, Success)
    assert isinstance(changed, Success)
    assert baseline.value.manifest.evidence_digest != changed.value.manifest.evidence_digest


def test_digest_canonicalizes_timezone_offset_equivalent_instants() -> None:
    event = _event(
        _quote(suffix=70),
        suffix=70,
        sequence=1,
        received_offset_ms=0,
    )
    offset = timezone(timedelta(hours=-4))
    offset_event = replace(
        event,
        boundary_received_at=event.boundary_received_at.astimezone(offset),
        core_ingress_at=event.core_ingress_at.astimezone(offset),
        availability_evidence_at=event.availability_evidence_at.astimezone(offset),
        available_at=event.available_at.astimezone(offset),
    )
    offset_scope = HistoricalMarketEventDatasetScope(
        source=_SOURCE,
        instrument=_INSTRUMENT,
        capture_lineage_id=_LINEAGE,
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


def test_duplicate_arrival_provenance_returns_failure() -> None:
    first = _event(_quote(suffix=80), suffix=80, sequence=1, received_offset_ms=0)
    duplicate = _event(
        _quote(suffix=81),
        suffix=81,
        sequence=1,
        received_offset_ms=0,
    )

    built = _build((first, duplicate))

    assert isinstance(built, Failure)
    assert isinstance(built.error, HistoricalMarketEventDatasetValidationError)


def test_scope_rejects_wrong_source_instrument_lineage_and_ingress_window() -> None:
    event = _event(_quote(suffix=90), suffix=90, sequence=1, received_offset_ms=0)
    other_source = ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(901)),
        source_id=SourceId(_uuid(902)),
        port_name=PortName("market-data.other"),
    )
    other_lineage = MarketCaptureLineageId(_uuid(903))

    assert isinstance(_build((event,), scope=_scope(source=other_source)), Failure)
    assert isinstance(
        _build((event,), scope=_scope(instrument=Instrument("GBPUSD"))),
        Failure,
    )
    assert isinstance(_build((event,), scope=_scope(lineage=other_lineage)), Failure)
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


def test_dataset_constructor_rejects_noncanonical_observation_order() -> None:
    first = _event(_quote(suffix=100), suffix=100, sequence=1, received_offset_ms=0)
    second = _event(_quote(suffix=101), suffix=101, sequence=2, received_offset_ms=2)
    built = _build((second, first))

    assert isinstance(built, Success)

    with pytest.raises(HistoricalMarketEventDatasetValidationError):
        replace(built.value, observations=(second, first))


def test_manifest_digest_detects_retained_evidence_mutation() -> None:
    event = _event(_quote(suffix=110), suffix=110, sequence=1, received_offset_ms=0)
    built = _build((event,))

    assert isinstance(built, Success)
    changed = replace(event, available_at=event.available_at + timedelta(seconds=1))

    with pytest.raises(HistoricalMarketEventDatasetValidationError):
        replace(built.value, observations=(changed,))


def test_assembled_at_must_follow_capture_window() -> None:
    event = _event(_quote(suffix=120), suffix=120, sequence=1, received_offset_ms=0)

    built = _build((event,), assembled_at=_BASE + timedelta(minutes=4))

    assert isinstance(built, Failure)


def test_admin_identity_is_not_part_of_evidence_digest() -> None:
    event = _event(_quote(suffix=130), suffix=130, sequence=1, received_offset_ms=0)
    left = _build(
        (event,),
        dataset_suffix=130,
        revision_suffix=131,
        assembled_at=_BASE + timedelta(minutes=6),
    )
    right = _build(
        (event,),
        dataset_suffix=132,
        revision_suffix=133,
        assembled_at=_BASE + timedelta(minutes=9),
    )

    assert isinstance(left, Success)
    assert isinstance(right, Success)
    assert left.value.manifest.evidence_digest == right.value.manifest.evidence_digest
