from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from qore.infrastructure.ctrader_demo_market_data import CTraderTrendbar
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import MarketTimeframe, MarketTimeframeCode
from qore.infrastructure.ports import (
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
)
from qore.infrastructure.provider_instrument_catalog import (
    ProviderCatalogScope,
    ProviderInstrumentCatalog,
    ProviderInstrumentCatalogValidationError,
    ProviderInstrumentEvidenceReference,
)
from qore.kernel.result import Failure, Result, Success


class CTraderNativeMarketDataError(ExternalPortError):
    """Base error for catalog-governed cTrader native trendbar reads."""

    __slots__ = ()


class CTraderNativeMarketDataValidationError(CTraderNativeMarketDataError):
    """cTrader native market-data evidence violates an exact invariant."""

    __slots__ = ()


class CTraderNativeMarketDataUnsupportedError(CTraderNativeMarketDataError):
    """Requested native timeframe is not verified for this provider/account."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise CTraderNativeMarketDataValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise CTraderNativeMarketDataValidationError(
            f"{field_name} must be timezone-aware"
        )
    return value.astimezone(UTC)


def _positive_int(value: int, *, field_name: str) -> None:
    if type(value) is not int or value <= 0:
        raise CTraderNativeMarketDataValidationError(
            f"{field_name} must be a positive int"
        )


class CTraderNativeTrendbarPeriod(StrEnum):
    """Official cTrader Open API ProtoOATrendbarPeriod identity."""

    M1 = "M1"
    M2 = "M2"
    M3 = "M3"
    M4 = "M4"
    M5 = "M5"
    M10 = "M10"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    H12 = "H12"
    D1 = "D1"
    W1 = "W1"
    MN1 = "MN1"


_CTRADER_PERIOD_ORDER = tuple(CTraderNativeTrendbarPeriod)


def canonical_ctrader_periods(
    periods: tuple[CTraderNativeTrendbarPeriod, ...],
) -> tuple[CTraderNativeTrendbarPeriod, ...]:
    if not isinstance(periods, tuple) or any(
        not isinstance(item, CTraderNativeTrendbarPeriod)
        for item in periods
    ):
        raise CTraderNativeMarketDataValidationError(
            "cTrader native periods must be immutable CTraderNativeTrendbarPeriod tuple"
        )
    if len(set(periods)) != len(periods):
        raise CTraderNativeMarketDataValidationError(
            "cTrader native periods must not contain duplicates"
        )
    return tuple(
        sorted(
            periods,
            key=_CTRADER_PERIOD_ORDER.index,
        )
    )


def ctrader_period_for_timeframe(
    timeframe: MarketTimeframe,
) -> CTraderNativeTrendbarPeriod:
    """Map canonical timeframe identity to cTrader; capability is checked separately."""

    if not isinstance(timeframe, MarketTimeframe):
        raise CTraderNativeMarketDataValidationError(
            "cTrader period mapping requires MarketTimeframe"
        )
    try:
        return CTraderNativeTrendbarPeriod(timeframe.code.value)
    except ValueError as error:
        raise CTraderNativeMarketDataUnsupportedError(
            "QORE timeframe has no cTrader native period mapping"
        ) from error


def market_timeframe_for_ctrader_period(
    period: CTraderNativeTrendbarPeriod,
) -> MarketTimeframe:
    """Map an official cTrader period identity to QORE without fake durations."""

    if not isinstance(period, CTraderNativeTrendbarPeriod):
        raise CTraderNativeMarketDataValidationError(
            "QORE timeframe mapping requires CTraderNativeTrendbarPeriod"
        )
    try:
        return MarketTimeframe(MarketTimeframeCode(period.value))
    except ValueError as error:  # pragma: no cover - guarded by aligned closed enums
        raise CTraderNativeMarketDataUnsupportedError(
            "cTrader period has no canonical QORE timeframe mapping"
        ) from error


@dataclass(frozen=True, slots=True)
class CTraderNativeTrendbarReadRequest:
    """QORE identity plus an explicit provider query window."""

    instrument: Instrument
    timeframe: MarketTimeframe
    from_timestamp: datetime
    to_timestamp: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, Instrument):
            raise CTraderNativeMarketDataValidationError(
                "cTrader native request instrument must be Instrument"
            )
        if not isinstance(self.timeframe, MarketTimeframe):
            raise CTraderNativeMarketDataValidationError(
                "cTrader native request timeframe must be MarketTimeframe"
            )
        start = _validate_timestamp(
            self.from_timestamp,
            field_name="cTrader native from_timestamp",
        )
        end = _validate_timestamp(
            self.to_timestamp,
            field_name="cTrader native to_timestamp",
        )
        if end <= start:
            raise CTraderNativeMarketDataValidationError(
                "cTrader native to_timestamp must be after from_timestamp"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.instrument.symbol,
            self.timeframe.logical_values(),
            self.from_timestamp.astimezone(UTC).isoformat(timespec="microseconds"),
            self.to_timestamp.astimezone(UTC).isoformat(timespec="microseconds"),
        )


@dataclass(frozen=True, slots=True)
class CTraderNativeTrendbarProviderRequest:
    """Provider request after catalog symbol resolution and exact period mapping."""

    symbol_id: int
    period: CTraderNativeTrendbarPeriod
    from_timestamp: datetime
    to_timestamp: datetime

    def __post_init__(self) -> None:
        _positive_int(
            self.symbol_id,
            field_name="cTrader provider request symbol_id",
        )
        if not isinstance(self.period, CTraderNativeTrendbarPeriod):
            raise CTraderNativeMarketDataValidationError(
                "cTrader provider request period must be CTraderNativeTrendbarPeriod"
            )
        start = _validate_timestamp(
            self.from_timestamp,
            field_name="cTrader provider from_timestamp",
        )
        end = _validate_timestamp(
            self.to_timestamp,
            field_name="cTrader provider to_timestamp",
        )
        if end <= start:
            raise CTraderNativeMarketDataValidationError(
                "cTrader provider to_timestamp must be after from_timestamp"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.symbol_id,
            self.period.value,
            self.from_timestamp.astimezone(UTC).isoformat(timespec="microseconds"),
            self.to_timestamp.astimezone(UTC).isoformat(timespec="microseconds"),
        )


@dataclass(frozen=True, slots=True)
class CTraderNativeTrendbarReadResult:
    """Sanitized cTrader trendbar result with explicit retained evidence."""

    symbol_id: int
    period: CTraderNativeTrendbarPeriod
    trendbars: tuple[CTraderTrendbar, ...]
    has_more: bool
    observed_at: datetime
    evidence_ref: ProviderInstrumentEvidenceReference

    def __post_init__(self) -> None:
        _positive_int(self.symbol_id, field_name="cTrader result symbol_id")
        if not isinstance(self.period, CTraderNativeTrendbarPeriod):
            raise CTraderNativeMarketDataValidationError(
                "cTrader result period must be CTraderNativeTrendbarPeriod"
            )
        if not isinstance(self.trendbars, tuple) or any(
            not isinstance(item, CTraderTrendbar) for item in self.trendbars
        ):
            raise CTraderNativeMarketDataValidationError(
                "cTrader result trendbars must be immutable CTraderTrendbar tuple"
            )
        open_minutes = tuple(
            item.utc_timestamp_in_minutes for item in self.trendbars
        )
        if len(set(open_minutes)) != len(open_minutes):
            raise CTraderNativeMarketDataValidationError(
                "cTrader result trendbar open timestamps must be unique"
            )
        canonical_trendbars = tuple(
            sorted(
                self.trendbars,
                key=lambda item: item.utc_timestamp_in_minutes,
            )
        )
        if canonical_trendbars != self.trendbars:
            object.__setattr__(self, "trendbars", canonical_trendbars)
        if type(self.has_more) is not bool:
            raise CTraderNativeMarketDataValidationError(
                "cTrader result has_more must be strict bool"
            )
        _validate_timestamp(
            self.observed_at,
            field_name="cTrader trendbar result observed_at",
        )
        if not isinstance(
            self.evidence_ref,
            ProviderInstrumentEvidenceReference,
        ):
            raise CTraderNativeMarketDataValidationError(
                "cTrader trendbar evidence_ref must be ProviderInstrumentEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.symbol_id,
            self.period.value,
            tuple(item.logical_values() for item in self.trendbars),
            self.has_more,
            self.observed_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CTraderNativeTrendbarDelivery:
    """Canonical QORE identity plus untouched provider-native trendbar evidence."""

    instrument: Instrument
    provider_symbol: str
    provider_symbol_id: int
    timeframe: MarketTimeframe
    trendbars: tuple[CTraderTrendbar, ...]
    observed_at: datetime
    evidence_ref: ProviderInstrumentEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, Instrument):
            raise CTraderNativeMarketDataValidationError(
                "cTrader native delivery instrument must be Instrument"
            )
        if (
            not isinstance(self.provider_symbol, str)
            or not self.provider_symbol
            or self.provider_symbol != self.provider_symbol.strip()
        ):
            raise CTraderNativeMarketDataValidationError(
                "cTrader native delivery provider_symbol must be non-empty and trimmed"
            )
        _positive_int(
            self.provider_symbol_id,
            field_name="cTrader native delivery provider_symbol_id",
        )
        if not isinstance(self.timeframe, MarketTimeframe):
            raise CTraderNativeMarketDataValidationError(
                "cTrader native delivery timeframe must be MarketTimeframe"
            )
        if not isinstance(self.trendbars, tuple) or any(
            not isinstance(item, CTraderTrendbar) for item in self.trendbars
        ):
            raise CTraderNativeMarketDataValidationError(
                "cTrader native delivery trendbars must be immutable CTraderTrendbar tuple"
            )
        _validate_timestamp(
            self.observed_at,
            field_name="cTrader native delivery observed_at",
        )
        if not isinstance(
            self.evidence_ref,
            ProviderInstrumentEvidenceReference,
        ):
            raise CTraderNativeMarketDataValidationError(
                "cTrader native delivery evidence_ref is invalid"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.instrument.symbol,
            self.provider_symbol,
            self.provider_symbol_id,
            self.timeframe.logical_values(),
            tuple(item.logical_values() for item in self.trendbars),
            self.observed_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.evidence_ref.logical_values(),
        )


class CTraderNativeTrendbarClientBoundary(Protocol):
    """Injected cTrader trendbar client bound to one explicit account/server."""

    @property
    def descriptor(self) -> ExternalSourceDescriptor: ...

    @property
    def scope(self) -> ProviderCatalogScope: ...

    def read_native_trendbars(
        self,
        request: CTraderNativeTrendbarProviderRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderNativeTrendbarReadResult, ExternalPortError]: ...


@dataclass(frozen=True, slots=True)
class CTraderNativeMarketDataFlow:
    """Catalog-governed native-period reads without fabricating calendar seconds."""

    catalog: ProviderInstrumentCatalog
    client: CTraderNativeTrendbarClientBoundary

    def __post_init__(self) -> None:
        if not isinstance(self.catalog, ProviderInstrumentCatalog):
            raise CTraderNativeMarketDataValidationError(
                "cTrader native flow requires ProviderInstrumentCatalog"
            )
        descriptor = getattr(self.client, "descriptor", None)
        if not isinstance(descriptor, ExternalSourceDescriptor):
            raise CTraderNativeMarketDataValidationError(
                "cTrader native client descriptor must be ExternalSourceDescriptor"
            )
        if descriptor != self.catalog.source:
            raise CTraderNativeMarketDataValidationError(
                "cTrader native client descriptor must match catalog source"
            )
        if getattr(self.client, "scope", None) != self.catalog.scope:
            raise CTraderNativeMarketDataValidationError(
                "cTrader native client scope must match catalog scope"
            )
        if not callable(getattr(self.client, "read_native_trendbars", None)):
            raise CTraderNativeMarketDataValidationError(
                "cTrader native client must expose read_native_trendbars"
            )

    def read_native_trendbars(
        self,
        request: CTraderNativeTrendbarReadRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderNativeTrendbarDelivery, ExternalPortError]:
        if not isinstance(request, CTraderNativeTrendbarReadRequest):
            return Failure(
                CTraderNativeMarketDataValidationError(
                    "cTrader native read requires CTraderNativeTrendbarReadRequest"
                )
            )
        try:
            entry = self.catalog.entry_for_instrument(request.instrument)
        except ProviderInstrumentCatalogValidationError:
            return Failure(
                CTraderNativeMarketDataValidationError(
                    "cTrader native read instrument must exist exactly once in catalog"
                )
            )
        if request.timeframe not in entry.native_timeframes:
            return Failure(
                CTraderNativeMarketDataUnsupportedError(
                    "cTrader timeframe is not verified for this provider/account catalog"
                )
            )
        provider_symbol_id_text = entry.provider_symbol_id
        if provider_symbol_id_text is None:
            return Failure(
                CTraderNativeMarketDataValidationError(
                    "cTrader catalog entry must retain provider symbol id"
                )
            )
        try:
            provider_symbol_id = int(provider_symbol_id_text)
        except ValueError:
            return Failure(
                CTraderNativeMarketDataValidationError(
                    "cTrader provider symbol id must be canonical integer text"
                )
            )
        if (
            provider_symbol_id <= 0
            or str(provider_symbol_id) != provider_symbol_id_text
        ):
            return Failure(
                CTraderNativeMarketDataValidationError(
                    "cTrader provider symbol id must be canonical positive integer text"
                )
            )
        try:
            period = ctrader_period_for_timeframe(request.timeframe)
            provider_request = CTraderNativeTrendbarProviderRequest(
                symbol_id=provider_symbol_id,
                period=period,
                from_timestamp=request.from_timestamp,
                to_timestamp=request.to_timestamp,
            )
        except CTraderNativeMarketDataError as error:
            return Failure(error)
        try:
            raw = self.client.read_native_trendbars(
                provider_request,
                metadata=metadata,
            )
        except ExternalPortError as error:
            return Failure(error)
        if isinstance(raw, Failure):
            return Failure(raw.error)
        if not isinstance(raw, Success) or not isinstance(
            raw.value,
            CTraderNativeTrendbarReadResult,
        ):
            return Failure(
                CTraderNativeMarketDataValidationError(
                    "cTrader native client must return CTraderNativeTrendbarReadResult"
                )
            )
        response = raw.value
        if response.symbol_id != provider_symbol_id:
            return Failure(
                CTraderNativeMarketDataValidationError(
                    "cTrader native result symbol id must match catalog-resolved request"
                )
            )
        if response.period is not period:
            return Failure(
                CTraderNativeMarketDataValidationError(
                    "cTrader native result period must match requested native period"
                )
            )
        if response.has_more:
            return Failure(
                CTraderNativeMarketDataValidationError(
                    "cTrader native result must not be truncated"
                )
            )
        start = request.from_timestamp.astimezone(UTC)
        end = request.to_timestamp.astimezone(UTC)
        for trendbar in response.trendbars:
            try:
                opened_at = datetime.fromtimestamp(
                    trendbar.utc_timestamp_in_minutes * 60,
                    tz=UTC,
                )
            except (OverflowError, OSError, ValueError):
                return Failure(
                    CTraderNativeMarketDataValidationError(
                        "cTrader trendbar open timestamp is outside datetime range"
                    )
                )
            if opened_at < start or opened_at >= end:
                return Failure(
                    CTraderNativeMarketDataValidationError(
                        "cTrader trendbar open timestamp must lie inside requested range"
                    )
                )
        try:
            delivery = CTraderNativeTrendbarDelivery(
                instrument=request.instrument,
                provider_symbol=entry.provider_symbol,
                provider_symbol_id=provider_symbol_id,
                timeframe=request.timeframe,
                trendbars=response.trendbars,
                observed_at=response.observed_at,
                evidence_ref=response.evidence_ref,
            )
        except CTraderNativeMarketDataError as error:
            return Failure(error)
        return Success(delivery)
