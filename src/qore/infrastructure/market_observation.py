from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.market_data import Instrument
from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.kernel.errors import InfrastructureError


class MarketObservationError(InfrastructureError):
    """Base error for exact retained market-observation evidence."""

    __slots__ = ()


class MarketObservationValidationError(MarketObservationError):
    """Violation of an exact market-observation evidence invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise MarketObservationValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise MarketObservationValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_market_data_source(
    value: ExternalSourceDescriptor,
    *,
    field_name: str,
) -> None:
    if not isinstance(value, ExternalSourceDescriptor):
        raise MarketObservationValidationError(
            f"{field_name} must be ExternalSourceDescriptor"
        )
    port_name = value.port_name.value
    if port_name != "market-data" and not port_name.startswith("market-data."):
        raise MarketObservationValidationError(
            f"{field_name} must use the market-data namespace"
        )


def _canonical_decimal(value: Decimal) -> str:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise MarketObservationValidationError(
            "market decimal must be finite Decimal"
        )
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class MarketObservationId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise MarketObservationValidationError(
                "market observation id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class MarketObservationEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise MarketObservationValidationError(
                "market observation evidence reference must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class InstrumentMarketSpecificationId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise MarketObservationValidationError(
                "instrument market specification id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class MarketPrice:
    """Exact positive decimal market price or price increment."""

    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise MarketObservationValidationError(
                "market price must be Decimal"
            )
        if not self.value.is_finite() or self.value <= 0:
            raise MarketObservationValidationError(
                "market price must be positive and finite"
            )

    @property
    def canonical(self) -> str:
        return _canonical_decimal(self.value)

    def logical_values(self) -> tuple[str, ...]:
        return (self.canonical,)


class MarketPriceSide(StrEnum):
    BID = "bid"
    ASK = "ask"
    MID = "mid"


class MarketBarOrigin(StrEnum):
    NATIVE = "native"
    AGGREGATED = "aggregated"


class MarketOhlcFieldValidity(StrEnum):
    VALID = "valid"
    MISSING = "missing"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class MarketOhlcField:
    validity: MarketOhlcFieldValidity
    price: MarketPrice | None

    def __post_init__(self) -> None:
        if not isinstance(self.validity, MarketOhlcFieldValidity):
            raise MarketObservationValidationError(
                "OHLC field validity must be MarketOhlcFieldValidity"
            )
        if self.validity is MarketOhlcFieldValidity.VALID:
            if not isinstance(self.price, MarketPrice):
                raise MarketObservationValidationError(
                    "valid OHLC field must carry MarketPrice"
                )
        elif self.price is not None:
            raise MarketObservationValidationError(
                "missing or invalid OHLC field must not carry price"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.validity.value,
            self.price.logical_values() if self.price is not None else None,
        )


class MarketTimeframeCode(StrEnum):
    M1 = "M1"
    M3 = "M3"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D = "D"
    W = "W"
    M = "M"


_FIXED_TIMEFRAME_SECONDS: dict[MarketTimeframeCode, int] = {
    MarketTimeframeCode.M1: 60,
    MarketTimeframeCode.M3: 180,
    MarketTimeframeCode.M5: 300,
    MarketTimeframeCode.M15: 900,
    MarketTimeframeCode.M30: 1800,
    MarketTimeframeCode.H1: 3600,
    MarketTimeframeCode.H4: 14400,
}


@dataclass(frozen=True, slots=True)
class MarketTimeframe:
    """Canonical timeframe identity without faking calendar durations."""

    code: MarketTimeframeCode

    def __post_init__(self) -> None:
        if not isinstance(self.code, MarketTimeframeCode):
            raise MarketObservationValidationError(
                "market timeframe code must be MarketTimeframeCode"
            )

    @property
    def fixed_seconds(self) -> int | None:
        return _FIXED_TIMEFRAME_SECONDS.get(self.code)

    def logical_values(self) -> tuple[object, ...]:
        return (self.code.value, self.fixed_seconds)


def _valid_price(field: MarketOhlcField) -> Decimal | None:
    if field.validity is not MarketOhlcFieldValidity.VALID:
        return None
    if field.price is None:  # pragma: no cover - guarded by field invariant
        raise MarketObservationValidationError("valid OHLC field lost price")
    return field.price.value


@dataclass(frozen=True, slots=True)
class QualifiedOhlcBarObservation:
    """Typed OHLC evidence with explicit price side, origin, and field validity."""

    observation_id: MarketObservationId
    instrument: Instrument
    source: ExternalSourceDescriptor
    timeframe: MarketTimeframe
    price_side: MarketPriceSide
    origin: MarketBarOrigin
    opened_at: datetime
    closed_at: datetime
    open: MarketOhlcField
    high: MarketOhlcField
    low: MarketOhlcField
    close: MarketOhlcField
    evidence_ref: MarketObservationEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, MarketObservationId):
            raise MarketObservationValidationError(
                "OHLC observation_id must be MarketObservationId"
            )
        if not isinstance(self.instrument, Instrument):
            raise MarketObservationValidationError(
                "OHLC instrument must be Instrument"
            )
        _validate_market_data_source(self.source, field_name="OHLC source")
        if not isinstance(self.timeframe, MarketTimeframe):
            raise MarketObservationValidationError(
                "OHLC timeframe must be MarketTimeframe"
            )
        if not isinstance(self.price_side, MarketPriceSide):
            raise MarketObservationValidationError(
                "OHLC price_side must be MarketPriceSide"
            )
        if not isinstance(self.origin, MarketBarOrigin):
            raise MarketObservationValidationError(
                "OHLC origin must be MarketBarOrigin"
            )
        _validate_timestamp(self.opened_at, field_name="OHLC opened_at")
        _validate_timestamp(self.closed_at, field_name="OHLC closed_at")
        if self.closed_at <= self.opened_at:
            raise MarketObservationValidationError(
                "OHLC closed_at must be after opened_at"
            )
        fixed_seconds = self.timeframe.fixed_seconds
        if (
            fixed_seconds is not None
            and (self.closed_at - self.opened_at).total_seconds()
            != fixed_seconds
        ):
            raise MarketObservationValidationError(
                "fixed OHLC interval must exactly match timeframe"
            )
        for field_name, field_value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            if not isinstance(field_value, MarketOhlcField):
                raise MarketObservationValidationError(
                    f"OHLC {field_name} must be MarketOhlcField"
                )
        if not isinstance(
            self.evidence_ref,
            MarketObservationEvidenceReference,
        ):
            raise MarketObservationValidationError(
                "OHLC evidence_ref must be MarketObservationEvidenceReference"
            )

        high = _valid_price(self.high)
        low = _valid_price(self.low)
        open_price = _valid_price(self.open)
        close_price = _valid_price(self.close)
        if high is not None and low is not None and low > high:
            raise MarketObservationValidationError(
                "valid OHLC low must not exceed valid high"
            )
        if (
            high is not None
            and low is not None
            and open_price is not None
            and not low <= open_price <= high
        ):
            raise MarketObservationValidationError(
                "valid OHLC open must be within valid low/high"
            )
        if (
            high is not None
            and low is not None
            and close_price is not None
            and not low <= close_price <= high
        ):
            raise MarketObservationValidationError(
                "valid OHLC close must be within valid low/high"
            )

    @property
    def is_native_bid(self) -> bool:
        return (
            self.price_side is MarketPriceSide.BID
            and self.origin is MarketBarOrigin.NATIVE
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.observation_id.logical_values(),
            self.instrument.symbol,
            self.source.logical_values(),
            self.timeframe.logical_values(),
            self.price_side.value,
            self.origin.value,
            self.opened_at.isoformat(),
            self.closed_at.isoformat(),
            self.open.logical_values(),
            self.high.logical_values(),
            self.low.logical_values(),
            self.close.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class QualifiedQuoteTickObservation:
    """Exact retained Bid/Ask quote evidence from one market-data source."""

    observation_id: MarketObservationId
    instrument: Instrument
    source: ExternalSourceDescriptor
    observed_at: datetime
    bid: MarketPrice
    ask: MarketPrice
    evidence_ref: MarketObservationEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, MarketObservationId):
            raise MarketObservationValidationError(
                "quote observation_id must be MarketObservationId"
            )
        if not isinstance(self.instrument, Instrument):
            raise MarketObservationValidationError(
                "quote instrument must be Instrument"
            )
        _validate_market_data_source(self.source, field_name="quote source")
        _validate_timestamp(self.observed_at, field_name="quote observed_at")
        if not isinstance(self.bid, MarketPrice):
            raise MarketObservationValidationError(
                "quote bid must be MarketPrice"
            )
        if not isinstance(self.ask, MarketPrice):
            raise MarketObservationValidationError(
                "quote ask must be MarketPrice"
            )
        if self.bid.value > self.ask.value:
            raise MarketObservationValidationError(
                "quote bid must not exceed ask"
            )
        if not isinstance(
            self.evidence_ref,
            MarketObservationEvidenceReference,
        ):
            raise MarketObservationValidationError(
                "quote evidence_ref must be MarketObservationEvidenceReference"
            )

    @property
    def spread(self) -> Decimal:
        return self.ask.value - self.bid.value

    @property
    def canonical_spread(self) -> str:
        return _canonical_decimal(self.spread)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.observation_id.logical_values(),
            self.instrument.symbol,
            self.source.logical_values(),
            self.observed_at.isoformat(),
            self.bid.logical_values(),
            self.ask.logical_values(),
            self.canonical_spread,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class InstrumentMarketSpecification:
    """Exact provider-qualified price precision and minimum increment evidence."""

    specification_id: InstrumentMarketSpecificationId
    instrument: Instrument
    source: ExternalSourceDescriptor
    provider_symbol: str
    provider_symbol_id: str | None
    price_precision: int
    minimum_price_increment: MarketPrice
    effective_at: datetime
    evidence_ref: MarketObservationEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(
            self.specification_id,
            InstrumentMarketSpecificationId,
        ):
            raise MarketObservationValidationError(
                "instrument specification_id must be InstrumentMarketSpecificationId"
            )
        if not isinstance(self.instrument, Instrument):
            raise MarketObservationValidationError(
                "instrument specification instrument must be Instrument"
            )
        _validate_market_data_source(
            self.source,
            field_name="instrument specification source",
        )
        if (
            not isinstance(self.provider_symbol, str)
            or not self.provider_symbol
            or self.provider_symbol != self.provider_symbol.strip()
        ):
            raise MarketObservationValidationError(
                "provider_symbol must be a non-empty trimmed string"
            )
        if self.provider_symbol_id is not None and (
            not isinstance(self.provider_symbol_id, str)
            or not self.provider_symbol_id
            or self.provider_symbol_id != self.provider_symbol_id.strip()
        ):
            raise MarketObservationValidationError(
                "provider_symbol_id must be a non-empty trimmed string or None"
            )
        if type(self.price_precision) is not int or self.price_precision < 0:
            raise MarketObservationValidationError(
                "price_precision must be a non-negative int"
            )
        if not isinstance(self.minimum_price_increment, MarketPrice):
            raise MarketObservationValidationError(
                "minimum_price_increment must be MarketPrice"
            )
        quantum = Decimal(1).scaleb(-self.price_precision)
        units = self.minimum_price_increment.value / quantum
        if units != units.to_integral_value():
            raise MarketObservationValidationError(
                "minimum_price_increment must be representable at price_precision"
            )
        _validate_timestamp(self.effective_at, field_name="specification effective_at")
        if not isinstance(
            self.evidence_ref,
            MarketObservationEvidenceReference,
        ):
            raise MarketObservationValidationError(
                "instrument specification evidence_ref must be "
                "MarketObservationEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.specification_id.logical_values(),
            self.instrument.symbol,
            self.source.logical_values(),
            self.provider_symbol,
            self.provider_symbol_id,
            self.price_precision,
            self.minimum_price_increment.logical_values(),
            self.effective_at.isoformat(),
            self.evidence_ref.logical_values(),
        )
