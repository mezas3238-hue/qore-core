from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoRuntimeConfiguration,
    CTraderSymbolMapping,
)
from qore.infrastructure.ctrader_demo_market_data import (
    CTraderDemoMarketDataError,
    CTraderDemoMarketDataValidationError,
    CTraderTrendbar,
    CTraderTrendbarPeriod,
    CTraderTrendbarReadResult,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiMessageClientBoundary,
)
from qore.infrastructure.ingestion import ExternalQuotePayload
from qore.infrastructure.market_data import OhlcRequest, QuoteRequest
from qore.infrastructure.ports import (
    ExternalHealth,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
)
from qore.kernel.result import Failure, Result, Success

_PERIOD_VALUES = {
    CTraderTrendbarPeriod.M1: 1,
    CTraderTrendbarPeriod.M5: 5,
    CTraderTrendbarPeriod.M15: 7,
    CTraderTrendbarPeriod.M30: 8,
    CTraderTrendbarPeriod.H1: 9,
    CTraderTrendbarPeriod.H4: 10,
    CTraderTrendbarPeriod.D1: 12,
}
_RELATIVE_PRICE_SCALE = Decimal(100_000)


def _field(value: object, name: str) -> object:
    return getattr(value, name)


def _int_field(value: object, name: str) -> int:
    result = _field(value, name)
    if type(result) is not int:
        raise TypeError(f"{name} must be an int")
    return result


def _configured_account_id(configuration: CTraderDemoRuntimeConfiguration) -> int:
    try:
        account_id = int(configuration.account.account_ref)
    except ValueError as error:
        raise CTraderDemoMarketDataValidationError(
            "cTrader DEMO account_ref must be numeric"
        ) from error
    if account_id <= 0:
        raise CTraderDemoMarketDataValidationError(
            "cTrader DEMO account_ref must be a positive numeric id"
        )
    return account_id


class CTraderOpenApiMarketDataClient:
    """Concrete DEMO quote/trendbar client over one authenticated Open API session."""

    __slots__ = ("_client", "_clock", "_configuration", "_descriptor")

    def __init__(
        self,
        *,
        descriptor: ExternalSourceDescriptor,
        configuration: CTraderDemoRuntimeConfiguration,
        client: CTraderOpenApiMessageClientBoundary,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(descriptor, ExternalSourceDescriptor):
            raise CTraderDemoMarketDataValidationError(
                "descriptor must be ExternalSourceDescriptor"
            )
        if not descriptor.port_name.value.startswith("market-data.ctrader"):
            raise CTraderDemoMarketDataValidationError(
                "descriptor must use market-data.ctrader namespace"
            )
        if not isinstance(configuration, CTraderDemoRuntimeConfiguration):
            raise CTraderDemoMarketDataValidationError(
                "configuration must be CTraderDemoRuntimeConfiguration"
            )
        if client.account_id != _configured_account_id(configuration):
            raise CTraderDemoMarketDataValidationError(
                "market-data client account must match runtime configuration"
            )
        self._descriptor = descriptor
        self._configuration = configuration
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return self._descriptor

    def _ready(self) -> Result[None, ExternalPortError]:
        if self._client.is_ready:
            return Success(None)
        result = self._client.connect_and_authenticate()
        if isinstance(result, Failure):
            return Failure(CTraderDemoMarketDataError(str(result.error)))
        return Success(None)

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, ExternalPortError]:
        del metadata
        ready = self._ready()
        if isinstance(ready, Failure):
            return Success(
                ExternalHealth(
                    descriptor=self._descriptor,
                    availability=PortAvailability.UNAVAILABLE,
                    checked_at=checked_at,
                    message="cTrader DEMO session is unavailable",
                )
            )
        return Success(
            ExternalHealth(
                descriptor=self._descriptor,
                availability=PortAvailability.AVAILABLE,
                checked_at=checked_at,
            )
        )

    def _mapping(self, instrument: str) -> CTraderSymbolMapping | None:
        for mapping in self._configuration.symbol_mappings:
            if mapping.instrument.value == instrument:
                return mapping
        return None

    def validate_symbol_mappings(self) -> Result[None, ExternalPortError]:
        """Verify configured identity, precision and volume bounds against DEMO."""
        ready = self._ready()
        if isinstance(ready, Failure):
            return ready
        listed = self._client.request(
            "ProtoOASymbolsListReq",
            {
                "ctidTraderAccountId": self._client.account_id,
                "includeArchivedSymbols": False,
            },
            client_msg_id="qore-symbol-list-validation",
            timeout_seconds=self._configuration.rest_timeout.milliseconds / 1000,
        )
        if isinstance(listed, Failure):
            return Failure(CTraderDemoMarketDataError(str(listed.error)))
        if getattr(listed.value, "ctidTraderAccountId", None) != self._client.account_id:
            return Failure(CTraderDemoMarketDataValidationError("symbol-list account mismatch"))
        native_light_symbols = getattr(listed.value, "symbol", None)
        if native_light_symbols is None:
            return Failure(CTraderDemoMarketDataValidationError("symbol list is missing"))
        try:
            light_by_id = {_int_field(item, "symbolId"): item for item in native_light_symbols}
        except (AttributeError, TypeError, ValueError):
            return Failure(CTraderDemoMarketDataValidationError("invalid native symbol list"))
        for mapping in self._configuration.symbol_mappings:
            light = light_by_id.get(mapping.symbol_id)
            if (
                light is None
                or getattr(light, "symbolName", None) != mapping.symbol_name
                or getattr(light, "enabled", None) is not True
            ):
                return Failure(
                    CTraderDemoMarketDataValidationError(
                        "configured cTrader symbol identity is absent or disabled"
                    )
                )

        details = self._client.request(
            "ProtoOASymbolByIdReq",
            {
                "ctidTraderAccountId": self._client.account_id,
                "symbolId": [item.symbol_id for item in self._configuration.symbol_mappings],
            },
            client_msg_id="qore-symbol-details-validation",
            timeout_seconds=self._configuration.rest_timeout.milliseconds / 1000,
        )
        if isinstance(details, Failure):
            return Failure(CTraderDemoMarketDataError(str(details.error)))
        if getattr(details.value, "ctidTraderAccountId", None) != self._client.account_id:
            return Failure(CTraderDemoMarketDataValidationError("symbol-details account mismatch"))
        native_symbols = getattr(details.value, "symbol", None)
        if native_symbols is None:
            return Failure(CTraderDemoMarketDataValidationError("symbol details are missing"))
        try:
            detail_by_id = {_int_field(item, "symbolId"): item for item in native_symbols}
            for mapping in self._configuration.symbol_mappings:
                native = detail_by_id[mapping.symbol_id]
                expected = (
                    mapping.digits,
                    mapping.min_volume_units,
                    mapping.max_volume_units,
                    mapping.step_volume_units,
                )
                observed = (
                    _int_field(native, "digits"),
                    _int_field(native, "minVolume"),
                    _int_field(native, "maxVolume"),
                    _int_field(native, "stepVolume"),
                )
                if observed != expected:
                    raise ValueError("symbol constraints mismatch")
        except (AttributeError, KeyError, TypeError, ValueError):
            return Failure(
                CTraderDemoMarketDataValidationError(
                    "configured symbol precision or volume constraints mismatch DEMO"
                )
            )
        return Success(None)

    def read_trendbars(
        self,
        request: OhlcRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderTrendbarReadResult, ExternalPortError]:
        del metadata
        ready = self._ready()
        if isinstance(ready, Failure):
            return ready
        mapping = self._mapping(request.instrument.symbol)
        if mapping is None:
            return Failure(
                CTraderDemoMarketDataValidationError(
                    "requested instrument is not mapped for cTrader DEMO"
                )
            )
        period = next(
            (item for item in CTraderTrendbarPeriod if item.seconds == request.timeframe.seconds),
            None,
        )
        if period is None or period not in _PERIOD_VALUES:
            return Failure(
                CTraderDemoMarketDataValidationError(
                    "requested timeframe is not admitted by cTrader runtime"
                )
            )
        response = self._client.request(
            "ProtoOAGetTrendbarsReq",
            {
                "ctidTraderAccountId": self._client.account_id,
                "fromTimestamp": int(request.opened_at.timestamp() * 1000),
                "period": _PERIOD_VALUES[period],
                "symbolId": mapping.symbol_id,
                "toTimestamp": int(request.closed_at.timestamp() * 1000),
            },
            client_msg_id=(
                f"trendbars:{mapping.symbol_id}:{period.value}:{int(request.closed_at.timestamp())}"
            ),
            timeout_seconds=self._configuration.rest_timeout.milliseconds / 1000,
        )
        if isinstance(response, Failure):
            return Failure(CTraderDemoMarketDataError(str(response.error)))
        if getattr(response.value, "ctidTraderAccountId", None) != self._client.account_id:
            return Failure(CTraderDemoMarketDataValidationError("trendbar account mismatch"))
        if getattr(response.value, "symbolId", mapping.symbol_id) != mapping.symbol_id:
            return Failure(CTraderDemoMarketDataValidationError("trendbar symbol mismatch"))
        native_bars = getattr(response.value, "trendbar", None)
        if native_bars is None:
            return Failure(CTraderDemoMarketDataValidationError("trendbar response missing bars"))
        try:
            bars = tuple(
                CTraderTrendbar(
                    low_relative=_int_field(item, "low"),
                    delta_open=_int_field(item, "deltaOpen"),
                    delta_high=_int_field(item, "deltaHigh"),
                    delta_close=_int_field(item, "deltaClose"),
                    utc_timestamp_in_minutes=_int_field(item, "utcTimestampInMinutes"),
                )
                for item in native_bars
            )
        except (AttributeError, TypeError, ValueError) as error:
            return Failure(
                CTraderDemoMarketDataValidationError(
                    f"invalid native trendbar response: {type(error).__name__}"
                )
            )
        return Success(
            CTraderTrendbarReadResult(
                instrument=request.instrument.symbol,
                symbol_id=mapping.symbol_id,
                digits=mapping.digits,
                period=period,
                trendbars=bars,
            )
        )

    def read_quote(
        self,
        request: QuoteRequest,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalQuotePayload, ExternalPortError]:
        del metadata
        ready = self._ready()
        if isinstance(ready, Failure):
            return ready
        mapping = self._mapping(request.instrument.symbol)
        if mapping is None:
            return Failure(
                CTraderDemoMarketDataValidationError(
                    "requested quote instrument is not mapped for cTrader DEMO"
                )
            )
        subscribed = self._client.request(
            "ProtoOASubscribeSpotsReq",
            {
                "ctidTraderAccountId": self._client.account_id,
                "subscribeToSpotTimestamp": True,
                "symbolId": [mapping.symbol_id],
            },
            client_msg_id=f"spots:{mapping.symbol_id}",
            timeout_seconds=self._configuration.rest_timeout.milliseconds / 1000,
        )
        if isinstance(subscribed, Failure):
            return Failure(CTraderDemoMarketDataError(str(subscribed.error)))
        event = self._client.wait_for_event(
            "ProtoOASpotEvent",
            timeout_seconds=self._configuration.rest_timeout.milliseconds / 1000,
            predicate=lambda item: getattr(item, "symbolId", None) == mapping.symbol_id,
        )
        if isinstance(event, Failure):
            return Failure(CTraderDemoMarketDataError(str(event.error)))
        bid_relative = getattr(event.value, "bid", None)
        ask_relative = getattr(event.value, "ask", None)
        if type(bid_relative) is not int or type(ask_relative) is not int:
            return Failure(CTraderDemoMarketDataValidationError("spot bid/ask missing"))
        bid = Decimal(bid_relative) / _RELATIVE_PRICE_SCALE
        ask = Decimal(ask_relative) / _RELATIVE_PRICE_SCALE
        if bid <= 0 or ask <= 0 or ask < bid:
            return Failure(CTraderDemoMarketDataValidationError("invalid spot bid/ask"))
        timestamp = getattr(event.value, "timestamp", None)
        observed_at = self._clock()
        if type(timestamp) is int and timestamp > 0:
            try:
                observed_at = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
            except (OverflowError, OSError, ValueError):
                return Failure(CTraderDemoMarketDataValidationError("invalid spot timestamp"))
        return Success(
            ExternalQuotePayload(
                source=self._descriptor,
                instrument=request.instrument.symbol,
                observed_at=observed_at,
                bid=format(bid, f".{mapping.digits}f"),
                ask=format(ask, f".{mapping.digits}f"),
            )
        )
