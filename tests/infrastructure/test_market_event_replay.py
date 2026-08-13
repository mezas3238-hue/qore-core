from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

import qore.infrastructure.market_event_replay as replay_module
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_event_replay import (
    MarketCaptureLineageId,
    MarketCaptureSessionId,
    MarketCaptureSessionOrdinal,
    MarketEventAvailabilityBasis,
    MarketEventAvailabilityEvidenceReference,
    MarketEventObservationId,
    MarketEventReplayValidationError,
    MarketIngressSequence,
    RetainedMarketEventObservation,
    derive_market_event_availability_instants,
    order_market_event_observations,
    visible_market_event_observations,
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


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(1)),
        source_id=SourceId(_uuid(2)),
        port_name=PortName("market-data.test"),
    )


def _price(value: str) -> MarketPrice:
    return MarketPrice(Decimal(value))


def _field(value: str) -> MarketOhlcField:
    return MarketOhlcField(
        validity=MarketOhlcFieldValidity.VALID,
        price=_price(value),
    )


def _quote(
    *,
    observation_id: int = 100,
    observed_at: datetime | None = None,
    bid: str = "1.10000",
    ask: str = "1.10010",
) -> QualifiedQuoteTickObservation:
    return QualifiedQuoteTickObservation(
        observation_id=MarketObservationId(_uuid(observation_id)),
        instrument=Instrument("EURUSD"),
        source=_source(),
        observed_at=observed_at
        or datetime(2026, 8, 12, 12, 0, tzinfo=UTC),
        bid=_price(bid),
        ask=_price(ask),
        evidence_ref=MarketObservationEvidenceReference(_uuid(observation_id + 1)),
    )


def _ohlc() -> QualifiedOhlcBarObservation:
    opened_at = datetime(2026, 8, 12, 11, 55, tzinfo=UTC)
    return QualifiedOhlcBarObservation(
        observation_id=MarketObservationId(_uuid(200)),
        instrument=Instrument("EURUSD"),
        source=_source(),
        timeframe=MarketTimeframe(MarketTimeframeCode.M5),
        price_side=MarketPriceSide.BID,
        origin=MarketBarOrigin.NATIVE,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=5),
        open=_field("1.10000"),
        high=_field("1.10100"),
        low=_field("1.09900"),
        close=_field("1.10050"),
        evidence_ref=MarketObservationEvidenceReference(_uuid(201)),
    )


def _specification() -> InstrumentMarketSpecification:
    return InstrumentMarketSpecification(
        specification_id=InstrumentMarketSpecificationId(_uuid(300)),
        instrument=Instrument("EURUSD"),
        source=_source(),
        provider_symbol="EURUSD",
        provider_symbol_id="1",
        price_precision=5,
        minimum_price_increment=_price("0.00001"),
        effective_at=datetime(2026, 8, 12, 11, 0, tzinfo=UTC),
        evidence_ref=MarketObservationEvidenceReference(_uuid(301)),
    )


def _event(
    payload: QualifiedQuoteTickObservation
    | QualifiedOhlcBarObservation
    | InstrumentMarketSpecification,
    *,
    event_id: int,
    session_id: int = 500,
    session_ordinal: int = 0,
    sequence: int = 0,
    received_at: datetime | None = None,
    core_ingress_at: datetime | None = None,
    availability_evidence_at: datetime | None = None,
    available_at: datetime | None = None,
    basis: MarketEventAvailabilityBasis = MarketEventAvailabilityBasis.CORE_INGRESS,
    lineage_id: int = 400,
) -> RetainedMarketEventObservation:
    resolved_received_at = received_at or datetime(
        2026,
        8,
        12,
        12,
        0,
        1,
        tzinfo=UTC,
    )
    resolved_core_ingress_at = core_ingress_at or (
        resolved_received_at + timedelta(milliseconds=1)
    )
    resolved_evidence_at = availability_evidence_at
    if resolved_evidence_at is None:
        if basis is MarketEventAvailabilityBasis.OBSERVED_RECEIPT:
            resolved_evidence_at = resolved_received_at
        else:
            resolved_evidence_at = resolved_core_ingress_at
    resolved_available_at = available_at or resolved_core_ingress_at
    return RetainedMarketEventObservation(
        event_id=MarketEventObservationId(_uuid(event_id)),
        payload=payload,
        capture_lineage_id=MarketCaptureLineageId(_uuid(lineage_id)),
        capture_session_id=MarketCaptureSessionId(_uuid(session_id)),
        capture_session_ordinal=MarketCaptureSessionOrdinal(session_ordinal),
        ingress_sequence=MarketIngressSequence(sequence),
        boundary_received_at=resolved_received_at,
        core_ingress_at=resolved_core_ingress_at,
        availability_evidence_at=resolved_evidence_at,
        available_at=resolved_available_at,
        availability_basis=basis,
        availability_evidence_ref=MarketEventAvailabilityEvidenceReference(
            _uuid(event_id + 1000)
        ),
    )


def test_mixed_payload_algebra_retains_quote_ohlc_and_specification() -> None:
    base = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)
    events = (
        _event(_quote(), event_id=10, sequence=0, received_at=base),
        _event(
            _ohlc(),
            event_id=11,
            sequence=1,
            received_at=base + timedelta(milliseconds=2),
        ),
        _event(
            _specification(),
            event_id=12,
            sequence=2,
            received_at=base + timedelta(milliseconds=4),
        ),
    )

    ordered = order_market_event_observations(events)

    assert tuple(item.payload_kind for item in ordered) == (
        "quote",
        "ohlc",
        "instrument_specification",
    )


def test_equal_available_at_conflicts_order_by_ingress_provenance() -> None:
    observed_at = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
    received_at = observed_at + timedelta(seconds=1)
    available_at = observed_at + timedelta(seconds=2)
    first = _event(
        _quote(observation_id=110, observed_at=observed_at, bid="1.1000", ask="1.1001"),
        event_id=900,
        sequence=1,
        received_at=received_at,
        core_ingress_at=received_at + timedelta(milliseconds=1),
        available_at=available_at,
    )
    second = _event(
        _quote(observation_id=120, observed_at=observed_at, bid="1.1002", ask="1.1003"),
        event_id=100,
        sequence=2,
        received_at=received_at + timedelta(milliseconds=2),
        core_ingress_at=received_at + timedelta(milliseconds=3),
        available_at=available_at,
    )

    visible = visible_market_event_observations(
        (second, first),
        simulated_now=available_at,
    )

    assert visible == (first, second)


def test_reversed_uuid_cannot_change_first_arrival_order() -> None:
    base = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)
    first = _event(
        _quote(observation_id=130),
        event_id=999,
        sequence=1,
        received_at=base,
    )
    second = _event(
        _quote(observation_id=140),
        event_id=1,
        sequence=2,
        received_at=base + timedelta(milliseconds=2),
    )

    assert order_market_event_observations((second, first)) == (first, second)


def test_cross_session_order_uses_session_ordinal_not_uuid() -> None:
    base = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)
    first_session = _event(
        _quote(observation_id=150),
        event_id=20,
        session_id=999,
        session_ordinal=4,
        sequence=9,
        received_at=base,
    )
    second_session = _event(
        _quote(observation_id=160),
        event_id=21,
        session_id=1,
        session_ordinal=5,
        sequence=0,
        received_at=base + timedelta(milliseconds=2),
    )

    assert order_market_event_observations((second_session, first_session)) == (
        first_session,
        second_session,
    )


def test_duplicate_arrival_provenance_fails_closed() -> None:
    base = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)
    first = _event(
        _quote(observation_id=170),
        event_id=30,
        sequence=7,
        received_at=base,
    )
    duplicate = _event(
        _quote(observation_id=180),
        event_id=31,
        sequence=7,
        received_at=base,
    )

    with pytest.raises(MarketEventReplayValidationError):
        order_market_event_observations((first, duplicate))


def test_session_ordinal_cannot_identify_two_sessions() -> None:
    base = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)
    first = _event(
        _quote(observation_id=190),
        event_id=40,
        session_id=10,
        session_ordinal=3,
        sequence=0,
        received_at=base,
    )
    second = _event(
        _quote(observation_id=191),
        event_id=41,
        session_id=11,
        session_ordinal=3,
        sequence=1,
        received_at=base + timedelta(milliseconds=2),
    )

    with pytest.raises(MarketEventReplayValidationError):
        order_market_event_observations((first, second))


def test_one_session_cannot_change_ordinal() -> None:
    base = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)
    first = _event(
        _quote(observation_id=192),
        event_id=42,
        session_id=12,
        session_ordinal=3,
        sequence=0,
        received_at=base,
    )
    second = _event(
        _quote(observation_id=193),
        event_id=43,
        session_id=12,
        session_ordinal=4,
        sequence=1,
        received_at=base + timedelta(milliseconds=2),
    )

    with pytest.raises(MarketEventReplayValidationError):
        order_market_event_observations((first, second))


def test_arrival_provenance_cannot_contradict_receipt_chronology() -> None:
    base = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)
    first_by_sequence = _event(
        _quote(observation_id=194),
        event_id=50,
        sequence=1,
        received_at=base + timedelta(milliseconds=5),
        core_ingress_at=base + timedelta(milliseconds=6),
    )
    second_by_sequence = _event(
        _quote(observation_id=195),
        event_id=51,
        sequence=2,
        received_at=base,
        core_ingress_at=base + timedelta(milliseconds=1),
    )

    with pytest.raises(MarketEventReplayValidationError):
        order_market_event_observations(
            (second_by_sequence, first_by_sequence)
        )


def test_arrival_provenance_cannot_contradict_core_ingress_chronology() -> None:
    base = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)
    first_by_sequence = _event(
        _quote(observation_id=196),
        event_id=52,
        sequence=1,
        received_at=base,
        core_ingress_at=base + timedelta(milliseconds=5),
    )
    second_by_sequence = _event(
        _quote(observation_id=197),
        event_id=53,
        sequence=2,
        received_at=base + timedelta(milliseconds=1),
        core_ingress_at=base + timedelta(milliseconds=2),
    )

    with pytest.raises(MarketEventReplayValidationError):
        order_market_event_observations(
            (first_by_sequence, second_by_sequence)
        )


def test_visibility_is_hidden_before_and_inclusive_at_available_at() -> None:
    base = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)
    available_at = base + timedelta(seconds=1)
    event = _event(
        _quote(observation_id=198),
        event_id=60,
        received_at=base,
        available_at=available_at,
    )

    assert visible_market_event_observations(
        (event,),
        simulated_now=available_at - timedelta(microseconds=1),
    ) == ()
    assert visible_market_event_observations(
        (event,),
        simulated_now=available_at,
    ) == (event,)


def test_visible_events_retain_arrival_order_not_available_order() -> None:
    base = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)
    first_arrival = _event(
        _quote(observation_id=199),
        event_id=70,
        sequence=1,
        received_at=base,
        available_at=base + timedelta(seconds=5),
    )
    second_arrival = _event(
        _quote(observation_id=210),
        event_id=71,
        sequence=2,
        received_at=base + timedelta(milliseconds=2),
        available_at=base + timedelta(seconds=3),
    )

    assert visible_market_event_observations(
        (second_arrival, first_arrival),
        simulated_now=base + timedelta(seconds=6),
    ) == (first_arrival, second_arrival)


def test_availability_instants_are_distinct_sorted_and_offset_equivalent() -> None:
    base = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)
    ny_offset = timezone(timedelta(hours=-4))
    same_instant_offset = datetime(2026, 8, 12, 8, 0, 3, tzinfo=ny_offset)
    first = _event(
        _quote(observation_id=220),
        event_id=80,
        sequence=1,
        received_at=base,
        available_at=base + timedelta(seconds=2),
    )
    second = _event(
        _quote(observation_id=230),
        event_id=81,
        sequence=2,
        received_at=base + timedelta(milliseconds=2),
        available_at=same_instant_offset,
    )
    third = _event(
        _quote(observation_id=240),
        event_id=82,
        sequence=3,
        received_at=base + timedelta(milliseconds=4),
        available_at=base + timedelta(seconds=2),
    )

    assert derive_market_event_availability_instants((third, second, first)) == (
        base + timedelta(seconds=2),
        base + timedelta(seconds=2, milliseconds=1000),
    )


def test_event_logical_values_canonicalize_offset_equivalent_times() -> None:
    utc_received = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)
    offset = timezone(timedelta(hours=-4))
    offset_received = datetime(2026, 8, 12, 8, 0, 1, tzinfo=offset)
    payload = _quote(observation_id=250)
    utc_event = _event(
        payload,
        event_id=90,
        received_at=utc_received,
    )
    offset_event = _event(
        payload,
        event_id=90,
        received_at=offset_received,
    )

    assert utc_event == offset_event
    assert utc_event.logical_values() == offset_event.logical_values()


def test_event_rejects_receipt_before_payload_boundary() -> None:
    payload = _quote(observation_id=260)

    with pytest.raises(MarketEventReplayValidationError):
        _event(
            payload,
            event_id=100,
            received_at=payload.observed_at - timedelta(microseconds=1),
        )


def test_event_rejects_core_ingress_before_receipt() -> None:
    base = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)

    with pytest.raises(MarketEventReplayValidationError):
        _event(
            _quote(observation_id=270),
            event_id=101,
            received_at=base,
            core_ingress_at=base - timedelta(microseconds=1),
        )


def test_event_rejects_replay_visibility_before_core_ingress() -> None:
    base = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)
    core_ingress = base + timedelta(milliseconds=1)

    with pytest.raises(MarketEventReplayValidationError):
        _event(
            _quote(observation_id=280),
            event_id=102,
            received_at=base,
            core_ingress_at=core_ingress,
            available_at=base,
        )


def test_observed_receipt_basis_must_bind_receipt_timestamp() -> None:
    base = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)

    with pytest.raises(MarketEventReplayValidationError):
        _event(
            _quote(observation_id=290),
            event_id=103,
            received_at=base,
            availability_evidence_at=base + timedelta(microseconds=1),
            basis=MarketEventAvailabilityBasis.OBSERVED_RECEIPT,
        )


def test_provider_evidence_may_delay_availability_beyond_core_ingress() -> None:
    base = datetime(2026, 8, 12, 12, 0, 1, tzinfo=UTC)
    evidence_at = base + timedelta(seconds=2)
    event = _event(
        _quote(observation_id=300),
        event_id=104,
        received_at=base,
        core_ingress_at=base + timedelta(milliseconds=1),
        availability_evidence_at=evidence_at,
        available_at=evidence_at,
        basis=MarketEventAvailabilityBasis.PROVIDER_EVIDENCE,
    )

    assert event.available_at == evidence_at


def test_module_has_no_hidden_clock_identity_or_runtime_side_effects() -> None:
    source = inspect.getsource(replay_module)

    for forbidden in (
        "datetime.now(",
        "datetime.utcnow(",
        "uuid4(",
        "sleep(",
        "threading",
        "asyncio",
        "requests.",
    ):
        assert forbidden not in source
