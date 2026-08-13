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

_BASE = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


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
    return MarketOhlcField(MarketOhlcFieldValidity.VALID, _price(value))


def _quote(
    *,
    observation_id: int,
    observed_at: datetime = _BASE,
    bid: str = "1.10000",
    ask: str = "1.10010",
) -> QualifiedQuoteTickObservation:
    return QualifiedQuoteTickObservation(
        observation_id=MarketObservationId(_uuid(observation_id)),
        instrument=Instrument("EURUSD"),
        source=_source(),
        observed_at=observed_at,
        bid=_price(bid),
        ask=_price(ask),
        evidence_ref=MarketObservationEvidenceReference(_uuid(observation_id + 1000)),
    )


def _ohlc() -> QualifiedOhlcBarObservation:
    opened_at = _BASE - timedelta(minutes=5)
    return QualifiedOhlcBarObservation(
        observation_id=MarketObservationId(_uuid(200)),
        instrument=Instrument("EURUSD"),
        source=_source(),
        timeframe=MarketTimeframe(MarketTimeframeCode.M5),
        price_side=MarketPriceSide.BID,
        origin=MarketBarOrigin.NATIVE,
        opened_at=opened_at,
        closed_at=_BASE,
        open=_field("1.10000"),
        high=_field("1.10100"),
        low=_field("1.09900"),
        close=_field("1.10050"),
        evidence_ref=MarketObservationEvidenceReference(_uuid(1200)),
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
        effective_at=_BASE - timedelta(hours=1),
        evidence_ref=MarketObservationEvidenceReference(_uuid(1300)),
    )


def _event(
    payload: QualifiedQuoteTickObservation
    | QualifiedOhlcBarObservation
    | InstrumentMarketSpecification,
    *,
    event_id: int,
    sequence: int,
    received_at: datetime,
    session_id: int = 500,
    session_ordinal: int = 0,
    lineage_id: int = 400,
    core_ingress_at: datetime | None = None,
    availability_evidence_at: datetime | None = None,
    available_at: datetime | None = None,
    basis: MarketEventAvailabilityBasis = MarketEventAvailabilityBasis.CORE_INGRESS,
) -> RetainedMarketEventObservation:
    ingress = core_ingress_at or received_at + timedelta(milliseconds=1)
    evidence = availability_evidence_at
    if evidence is None:
        evidence = (
            received_at
            if basis is MarketEventAvailabilityBasis.OBSERVED_RECEIPT
            else ingress
        )
    visibility = available_at or ingress
    return RetainedMarketEventObservation(
        event_id=MarketEventObservationId(_uuid(event_id)),
        payload=payload,
        capture_lineage_id=MarketCaptureLineageId(_uuid(lineage_id)),
        capture_session_id=MarketCaptureSessionId(_uuid(session_id)),
        capture_session_ordinal=MarketCaptureSessionOrdinal(session_ordinal),
        ingress_sequence=MarketIngressSequence(sequence),
        boundary_received_at=received_at,
        core_ingress_at=ingress,
        availability_evidence_at=evidence,
        available_at=visibility,
        availability_basis=basis,
        availability_evidence_ref=MarketEventAvailabilityEvidenceReference(
            _uuid(event_id + 2000)
        ),
    )


def test_mixed_payload_algebra_retains_all_three_market_evidence_types() -> None:
    received = _BASE + timedelta(seconds=1)
    events = (
        _event(_quote(observation_id=100), event_id=10, sequence=0, received_at=received),
        _event(_ohlc(), event_id=11, sequence=1, received_at=received + timedelta(milliseconds=2)),
        _event(
            _specification(),
            event_id=12,
            sequence=2,
            received_at=received + timedelta(milliseconds=4),
        ),
    )

    assert tuple(item.payload_kind for item in order_market_event_observations(events)) == (
        "quote",
        "ohlc",
        "instrument_specification",
    )


def test_equal_available_at_conflicts_use_arrival_provenance_not_uuid() -> None:
    received = _BASE + timedelta(seconds=1)
    visible_at = _BASE + timedelta(seconds=2)
    first = _event(
        _quote(observation_id=110, bid="1.1000", ask="1.1001"),
        event_id=999,
        sequence=1,
        received_at=received,
        available_at=visible_at,
    )
    second = _event(
        _quote(observation_id=120, bid="1.1002", ask="1.1003"),
        event_id=1,
        sequence=2,
        received_at=received + timedelta(milliseconds=2),
        available_at=visible_at,
    )

    assert visible_market_event_observations(
        (second, first), simulated_now=visible_at
    ) == (first, second)


def test_cross_session_order_uses_session_ordinal_not_session_uuid() -> None:
    received = _BASE + timedelta(seconds=1)
    first = _event(
        _quote(observation_id=130),
        event_id=20,
        sequence=9,
        session_id=999,
        session_ordinal=4,
        received_at=received,
    )
    second = _event(
        _quote(observation_id=140),
        event_id=21,
        sequence=0,
        session_id=1,
        session_ordinal=5,
        received_at=received + timedelta(milliseconds=2),
    )

    assert order_market_event_observations((second, first)) == (first, second)


def test_duplicate_arrival_provenance_fails_closed() -> None:
    received = _BASE + timedelta(seconds=1)
    first = _event(
        _quote(observation_id=150), event_id=30, sequence=7, received_at=received
    )
    duplicate = _event(
        _quote(observation_id=160), event_id=31, sequence=7, received_at=received
    )

    with pytest.raises(MarketEventReplayValidationError):
        order_market_event_observations((first, duplicate))


@pytest.mark.parametrize(
    ("first_session", "first_ordinal", "second_session", "second_ordinal"),
    [
        (10, 3, 11, 3),
        (12, 3, 12, 4),
    ],
)
def test_capture_session_and_ordinal_mapping_is_bijective(
    first_session: int,
    first_ordinal: int,
    second_session: int,
    second_ordinal: int,
) -> None:
    received = _BASE + timedelta(seconds=1)
    first = _event(
        _quote(observation_id=170),
        event_id=40,
        sequence=0,
        session_id=first_session,
        session_ordinal=first_ordinal,
        received_at=received,
    )
    second = _event(
        _quote(observation_id=180),
        event_id=41,
        sequence=1,
        session_id=second_session,
        session_ordinal=second_ordinal,
        received_at=received + timedelta(milliseconds=2),
    )

    with pytest.raises(MarketEventReplayValidationError):
        order_market_event_observations((first, second))


@pytest.mark.parametrize("contradiction", ["receipt", "core_ingress"])
def test_arrival_provenance_cannot_contradict_retained_chronology(
    contradiction: str,
) -> None:
    base = _BASE + timedelta(seconds=1)
    first_received = base + timedelta(milliseconds=5) if contradiction == "receipt" else base
    second_received = base if contradiction == "receipt" else base + timedelta(milliseconds=1)
    first_ingress = base + timedelta(milliseconds=6) if contradiction == "receipt" else base + timedelta(milliseconds=5)
    second_ingress = base + timedelta(milliseconds=7) if contradiction == "receipt" else base + timedelta(milliseconds=2)
    first = _event(
        _quote(observation_id=190),
        event_id=50,
        sequence=1,
        received_at=first_received,
        core_ingress_at=first_ingress,
    )
    second = _event(
        _quote(observation_id=191),
        event_id=51,
        sequence=2,
        received_at=second_received,
        core_ingress_at=second_ingress,
    )

    with pytest.raises(MarketEventReplayValidationError):
        order_market_event_observations((first, second))


def test_visibility_is_inclusive_and_visible_set_keeps_arrival_order() -> None:
    base = _BASE + timedelta(seconds=1)
    first = _event(
        _quote(observation_id=200),
        event_id=60,
        sequence=1,
        received_at=base,
        available_at=base + timedelta(seconds=5),
    )
    second = _event(
        _quote(observation_id=210),
        event_id=61,
        sequence=2,
        received_at=base + timedelta(milliseconds=2),
        available_at=base + timedelta(seconds=3),
    )

    assert visible_market_event_observations(
        (second, first), simulated_now=base + timedelta(seconds=3)
    ) == (second,)
    assert visible_market_event_observations(
        (second, first), simulated_now=base + timedelta(seconds=5)
    ) == (first, second)


def test_availability_instants_are_distinct_sorted_by_time_not_arrival() -> None:
    base = _BASE + timedelta(seconds=1)
    offset = timezone(timedelta(hours=-4))
    first = _event(
        _quote(observation_id=220),
        event_id=70,
        sequence=1,
        received_at=base,
        available_at=base + timedelta(seconds=3),
    )
    second = _event(
        _quote(observation_id=230),
        event_id=71,
        sequence=2,
        received_at=base + timedelta(milliseconds=2),
        available_at=(base + timedelta(seconds=2)).astimezone(offset),
    )
    third = _event(
        _quote(observation_id=240),
        event_id=72,
        sequence=3,
        received_at=base + timedelta(milliseconds=4),
        available_at=base + timedelta(seconds=2),
    )

    assert derive_market_event_availability_instants((third, first, second)) == (
        base + timedelta(seconds=2),
        base + timedelta(seconds=3),
    )


def test_logical_values_canonicalize_offset_equivalent_instants() -> None:
    utc_received = _BASE + timedelta(seconds=1)
    offset_received = utc_received.astimezone(timezone(timedelta(hours=-4)))
    payload = _quote(observation_id=250)
    utc_event = _event(
        payload, event_id=80, sequence=1, received_at=utc_received
    )
    offset_event = _event(
        payload, event_id=80, sequence=1, received_at=offset_received
    )

    assert utc_event == offset_event
    assert utc_event.logical_values() == offset_event.logical_values()


def test_event_temporal_guards_fail_closed() -> None:
    payload = _quote(observation_id=260)
    received = _BASE + timedelta(seconds=1)

    with pytest.raises(MarketEventReplayValidationError):
        _event(
            payload,
            event_id=90,
            sequence=1,
            received_at=payload.observed_at - timedelta(microseconds=1),
        )
    with pytest.raises(MarketEventReplayValidationError):
        _event(
            payload,
            event_id=91,
            sequence=1,
            received_at=received,
            core_ingress_at=received - timedelta(microseconds=1),
        )
    with pytest.raises(MarketEventReplayValidationError):
        _event(
            payload,
            event_id=92,
            sequence=1,
            received_at=received,
            core_ingress_at=received + timedelta(milliseconds=1),
            available_at=received,
        )


def test_availability_basis_binds_evidence_timestamp() -> None:
    received = _BASE + timedelta(seconds=1)
    with pytest.raises(MarketEventReplayValidationError):
        _event(
            _quote(observation_id=270),
            event_id=100,
            sequence=1,
            received_at=received,
            basis=MarketEventAvailabilityBasis.OBSERVED_RECEIPT,
            availability_evidence_at=received + timedelta(microseconds=1),
        )

    ingress = received + timedelta(milliseconds=1)
    provider_evidence_at = received + timedelta(seconds=2)
    retained = _event(
        _quote(observation_id=280),
        event_id=101,
        sequence=1,
        received_at=received,
        core_ingress_at=ingress,
        basis=MarketEventAvailabilityBasis.PROVIDER_EVIDENCE,
        availability_evidence_at=provider_evidence_at,
        available_at=provider_evidence_at,
    )
    assert retained.available_at == provider_evidence_at


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
