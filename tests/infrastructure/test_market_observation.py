from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import (
    InstrumentMarketSpecification,
    InstrumentMarketSpecificationId,
    MarketBarOrigin,
    MarketObservationEvidenceReference,
    MarketObservationId,
    MarketObservationValidationError,
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


def _source(port_name: str = "market-data.test") -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(1)),
        source_id=SourceId(_uuid(2)),
        port_name=PortName(port_name),
    )


def _price(value: str) -> MarketPrice:
    return MarketPrice(Decimal(value))


def _field(
    validity: MarketOhlcFieldValidity,
    value: str | None = None,
) -> MarketOhlcField:
    return MarketOhlcField(
        validity=validity,
        price=_price(value) if value is not None else None,
    )


def _m5_bar(
    *,
    price_side: MarketPriceSide = MarketPriceSide.BID,
    origin: MarketBarOrigin = MarketBarOrigin.NATIVE,
    open_field: MarketOhlcField | None = None,
    high_field: MarketOhlcField | None = None,
    low_field: MarketOhlcField | None = None,
    close_field: MarketOhlcField | None = None,
) -> QualifiedOhlcBarObservation:
    opened_at = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
    return QualifiedOhlcBarObservation(
        observation_id=MarketObservationId(_uuid(10)),
        instrument=Instrument("EURUSD"),
        source=_source(),
        timeframe=MarketTimeframe(MarketTimeframeCode.M5),
        price_side=price_side,
        origin=origin,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=5),
        open=open_field or _field(MarketOhlcFieldValidity.VALID, "1.10000"),
        high=high_field or _field(MarketOhlcFieldValidity.VALID, "1.10100"),
        low=low_field or _field(MarketOhlcFieldValidity.VALID, "1.09900"),
        close=close_field or _field(MarketOhlcFieldValidity.VALID, "1.10050"),
        evidence_ref=MarketObservationEvidenceReference(_uuid(11)),
    )


def test_market_price_requires_exact_positive_decimal() -> None:
    price = MarketPrice(Decimal("1.23000"))

    assert price.canonical == "1.23"
    assert price.logical_values() == ("1.23",)

    with pytest.raises(MarketObservationValidationError):
        MarketPrice(cast(Decimal, 1.23))

    with pytest.raises(MarketObservationValidationError):
        MarketPrice(Decimal("0"))

    with pytest.raises(MarketObservationValidationError):
        MarketPrice(Decimal("NaN"))


@pytest.mark.parametrize(
    ("code", "seconds"),
    [
        (MarketTimeframeCode.M1, 60),
        (MarketTimeframeCode.M3, 180),
        (MarketTimeframeCode.M5, 300),
        (MarketTimeframeCode.M15, 900),
        (MarketTimeframeCode.M30, 1800),
        (MarketTimeframeCode.H1, 3600),
        (MarketTimeframeCode.H4, 14400),
        (MarketTimeframeCode.D, None),
        (MarketTimeframeCode.W, None),
        (MarketTimeframeCode.M, None),
    ],
)
def test_market_timeframe_does_not_fake_calendar_duration(
    code: MarketTimeframeCode,
    seconds: int | None,
) -> None:
    timeframe = MarketTimeframe(code)

    assert timeframe.fixed_seconds == seconds
    assert timeframe.logical_values() == (code.value, seconds)


def test_ohlc_field_supports_field_level_validity() -> None:
    valid = _field(MarketOhlcFieldValidity.VALID, "1.101")
    missing = _field(MarketOhlcFieldValidity.MISSING)
    invalid = _field(MarketOhlcFieldValidity.INVALID)

    assert valid.logical_values() == ("valid", ("1.101",))
    assert missing.logical_values() == ("missing", None)
    assert invalid.logical_values() == ("invalid", None)

    with pytest.raises(MarketObservationValidationError):
        MarketOhlcField(MarketOhlcFieldValidity.VALID, None)

    with pytest.raises(MarketObservationValidationError):
        MarketOhlcField(
            MarketOhlcFieldValidity.INVALID,
            _price("1.1"),
        )


def test_native_bid_m5_bar_is_explicit_and_exact() -> None:
    bar = _m5_bar()

    assert bar.is_native_bid
    assert bar.timeframe.code is MarketTimeframeCode.M5
    assert bar.price_side is MarketPriceSide.BID
    assert bar.origin is MarketBarOrigin.NATIVE


def test_bar_accepts_valid_high_with_invalid_low() -> None:
    bar = _m5_bar(
        high_field=_field(MarketOhlcFieldValidity.VALID, "1.101"),
        low_field=_field(MarketOhlcFieldValidity.INVALID),
    )

    assert bar.high.price == _price("1.101")
    assert bar.low.validity is MarketOhlcFieldValidity.INVALID


def test_bar_rejects_inconsistent_valid_range() -> None:
    with pytest.raises(MarketObservationValidationError):
        _m5_bar(
            high_field=_field(MarketOhlcFieldValidity.VALID, "1.099"),
            low_field=_field(MarketOhlcFieldValidity.VALID, "1.100"),
        )


def test_fixed_bar_interval_must_match_timeframe() -> None:
    opened_at = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)

    with pytest.raises(MarketObservationValidationError):
        QualifiedOhlcBarObservation(
            observation_id=MarketObservationId(_uuid(10)),
            instrument=Instrument("EURUSD"),
            source=_source(),
            timeframe=MarketTimeframe(MarketTimeframeCode.M5),
            price_side=MarketPriceSide.BID,
            origin=MarketBarOrigin.NATIVE,
            opened_at=opened_at,
            closed_at=opened_at + timedelta(minutes=6),
            open=_field(MarketOhlcFieldValidity.VALID, "1.100"),
            high=_field(MarketOhlcFieldValidity.VALID, "1.101"),
            low=_field(MarketOhlcFieldValidity.VALID, "1.099"),
            close=_field(MarketOhlcFieldValidity.VALID, "1.1005"),
            evidence_ref=MarketObservationEvidenceReference(_uuid(11)),
        )


def test_calendar_bar_retains_explicit_boundaries() -> None:
    opened_at = datetime(2026, 3, 1, 0, 0, tzinfo=UTC)
    bar = QualifiedOhlcBarObservation(
        observation_id=MarketObservationId(_uuid(10)),
        instrument=Instrument("EURUSD"),
        source=_source(),
        timeframe=MarketTimeframe(MarketTimeframeCode.M),
        price_side=MarketPriceSide.BID,
        origin=MarketBarOrigin.NATIVE,
        opened_at=opened_at,
        closed_at=datetime(2026, 4, 1, 0, 0, tzinfo=UTC),
        open=_field(MarketOhlcFieldValidity.VALID, "1.100"),
        high=_field(MarketOhlcFieldValidity.VALID, "1.120"),
        low=_field(MarketOhlcFieldValidity.VALID, "1.080"),
        close=_field(MarketOhlcFieldValidity.VALID, "1.110"),
        evidence_ref=MarketObservationEvidenceReference(_uuid(11)),
    )

    assert bar.timeframe.fixed_seconds is None
    assert bar.closed_at == datetime(2026, 4, 1, 0, 0, tzinfo=UTC)


def test_quote_retains_exact_bid_ask_and_spread() -> None:
    quote = QualifiedQuoteTickObservation(
        observation_id=MarketObservationId(_uuid(20)),
        instrument=Instrument("EURUSD"),
        source=_source(),
        observed_at=datetime(2026, 8, 12, 12, 0, tzinfo=UTC),
        bid=_price("1.10001"),
        ask=_price("1.10016"),
        evidence_ref=MarketObservationEvidenceReference(_uuid(21)),
    )

    assert quote.spread == Decimal("0.00015")
    assert quote.canonical_spread == "0.00015"
    assert quote.logical_values()[4:7] == (
        ("1.10001",),
        ("1.10016",),
        "0.00015",
    )


def test_quote_rejects_crossed_market() -> None:
    with pytest.raises(MarketObservationValidationError):
        QualifiedQuoteTickObservation(
            observation_id=MarketObservationId(_uuid(20)),
            instrument=Instrument("EURUSD"),
            source=_source(),
            observed_at=datetime(2026, 8, 12, 12, 0, tzinfo=UTC),
            bid=_price("1.1002"),
            ask=_price("1.1001"),
            evidence_ref=MarketObservationEvidenceReference(_uuid(21)),
        )


def test_market_observation_source_must_use_market_data_namespace() -> None:
    opened_at = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)

    with pytest.raises(MarketObservationValidationError):
        QualifiedOhlcBarObservation(
            observation_id=MarketObservationId(_uuid(10)),
            instrument=Instrument("EURUSD"),
            source=_source("execution.test"),
            timeframe=MarketTimeframe(MarketTimeframeCode.M5),
            price_side=MarketPriceSide.BID,
            origin=MarketBarOrigin.NATIVE,
            opened_at=opened_at,
            closed_at=opened_at + timedelta(minutes=5),
            open=_field(MarketOhlcFieldValidity.VALID, "1.100"),
            high=_field(MarketOhlcFieldValidity.VALID, "1.101"),
            low=_field(MarketOhlcFieldValidity.VALID, "1.099"),
            close=_field(MarketOhlcFieldValidity.VALID, "1.1005"),
            evidence_ref=MarketObservationEvidenceReference(_uuid(11)),
        )


def test_instrument_market_specification_retains_exact_tick_provenance() -> None:
    specification = InstrumentMarketSpecification(
        specification_id=InstrumentMarketSpecificationId(_uuid(30)),
        instrument=Instrument("EURUSD"),
        source=_source(),
        provider_symbol="EURUSD",
        provider_symbol_id="1",
        price_precision=5,
        minimum_price_increment=_price("0.00001"),
        effective_at=datetime(2026, 8, 12, 12, 0, tzinfo=UTC),
        evidence_ref=MarketObservationEvidenceReference(_uuid(31)),
    )

    assert specification.minimum_price_increment.canonical == "0.00001"
    assert specification.price_precision == 5
    assert specification.logical_values()[3:7] == (
        "EURUSD",
        "1",
        5,
        ("0.00001",),
    )


def test_instrument_market_specification_rejects_unrepresentable_increment() -> None:
    with pytest.raises(MarketObservationValidationError):
        InstrumentMarketSpecification(
            specification_id=InstrumentMarketSpecificationId(_uuid(30)),
            instrument=Instrument("TEST"),
            source=_source(),
            provider_symbol="TEST",
            provider_symbol_id=None,
            price_precision=2,
            minimum_price_increment=_price("0.001"),
            effective_at=datetime(2026, 8, 12, 12, 0, tzinfo=UTC),
            evidence_ref=MarketObservationEvidenceReference(_uuid(31)),
        )


def test_observation_logical_values_are_deterministic() -> None:
    bar = _m5_bar()

    assert bar.logical_values() == _m5_bar().logical_values()
