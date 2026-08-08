from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.ingestion import ExternalOhlcPayload, ExternalQuotePayload
from qore.infrastructure.live_market_data import (
    ControlledLiveMarketDataFlow,
    LiveMarketDataPayloadAdapter,
)
from qore.infrastructure.market_data import OhlcRequest, QuoteRequest
from qore.infrastructure.ports import ExternalPortError, ExternalSourceDescriptor
from qore.infrastructure.read_only_provider_adapter import ReadOnlyExternalProviderAdapter
from qore.infrastructure.transport import (
    ExternalTransportMethod,
    ExternalTransportRequest,
    ExternalTransportResponse,
    ExternalTransportTimeout,
)
from qore.kernel.result import Failure, Result, Success


class RealMarketDataProviderError(ExternalPortError):
    """Base error for the concrete JSON real-market data adapter."""

    __slots__ = ()


class RealMarketDataProviderValidationError(RealMarketDataProviderError):
    """Provider payload or configuration violates the concrete adapter contract."""

    __slots__ = ()


def _json_object(payload: bytes) -> Result[Mapping[str, object], ExternalPortError]:
    try:
        decoded: object = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return Failure(
            RealMarketDataProviderValidationError(
                "market-data response must be a UTF-8 JSON object"
            )
        )
    if not isinstance(decoded, dict):
        return Failure(
            RealMarketDataProviderValidationError(
                "market-data response root must be a JSON object"
            )
        )
    if any(not isinstance(key, str) for key in decoded):
        return Failure(
            RealMarketDataProviderValidationError(
                "market-data response keys must be strings"
            )
        )
    return Success(decoded)


def _string_field(data: Mapping[str, object], field_name: str) -> Result[str, ExternalPortError]:
    value = data.get(field_name)
    if not isinstance(value, str) or not value.strip():
        return Failure(
            RealMarketDataProviderValidationError(
                f"market-data field {field_name} must be a non-empty string"
            )
        )
    return Success(value)


def _decimal_field(
    data: Mapping[str, object],
    field_name: str,
) -> Result[str | float, ExternalPortError]:
    value = data.get(field_name)
    if isinstance(value, bool):
        return Failure(
            RealMarketDataProviderValidationError(
                f"market-data field {field_name} must be decimal-compatible"
            )
        )
    if isinstance(value, str):
        return Success(value)
    if isinstance(value, (int, float)):
        return Success(float(value))
    return Failure(
        RealMarketDataProviderValidationError(
            f"market-data field {field_name} must be decimal-compatible"
        )
    )


def _whole_number_field(
    data: Mapping[str, object],
    field_name: str,
) -> Result[str | int, ExternalPortError]:
    value = data.get(field_name)
    if isinstance(value, bool):
        return Failure(
            RealMarketDataProviderValidationError(
                f"market-data field {field_name} must be a whole number"
            )
        )
    if isinstance(value, str):
        return Success(value)
    if isinstance(value, int):
        return Success(value)
    return Failure(
        RealMarketDataProviderValidationError(
            f"market-data field {field_name} must be a whole number"
        )
    )


def _timestamp_field(
    data: Mapping[str, object],
    field_name: str,
) -> Result[datetime, ExternalPortError]:
    value_result = _string_field(data, field_name)
    if isinstance(value_result, Failure):
        return value_result
    try:
        value = datetime.fromisoformat(value_result.value)
    except ValueError:
        return Failure(
            RealMarketDataProviderValidationError(
                f"market-data field {field_name} must be ISO-8601"
            )
        )
    if value.tzinfo is None or value.utcoffset() is None:
        return Failure(
            RealMarketDataProviderValidationError(
                f"market-data field {field_name} must be timezone-aware"
            )
        )
    return Success(value)


@dataclass(frozen=True, slots=True)
class ConcreteJsonMarketDataRequestFactory:
    """Concrete request mapping for a canonical JSON market-data HTTP surface."""

    endpoint: ProviderEndpoint
    timeout: ExternalTransportTimeout
    quote_path: str = "/quote"
    ohlc_path: str = "/ohlc"

    def __post_init__(self) -> None:
        if not isinstance(self.endpoint, ProviderEndpoint):
            raise RealMarketDataProviderValidationError(
                "market-data endpoint must be ProviderEndpoint"
            )
        if not isinstance(self.timeout, ExternalTransportTimeout):
            raise RealMarketDataProviderValidationError(
                "market-data timeout must be ExternalTransportTimeout"
            )
        for field_name, value in (
            ("quote_path", self.quote_path),
            ("ohlc_path", self.ohlc_path),
        ):
            if not isinstance(value, str) or not value.startswith("/"):
                raise RealMarketDataProviderValidationError(
                    f"{field_name} must be an absolute relative-path"
                )

    def quote_request(self, request: QuoteRequest) -> ExternalTransportRequest:
        if not isinstance(request, QuoteRequest):
            raise RealMarketDataProviderValidationError(
                "quote request factory requires QuoteRequest"
            )
        return ExternalTransportRequest(
            endpoint=self.endpoint,
            method=ExternalTransportMethod.GET,
            path=self.quote_path,
            timeout=self.timeout,
            query=(("instrument", request.instrument.symbol),),
            headers={"accept": "application/json"},
        )

    def ohlc_request(self, request: OhlcRequest) -> ExternalTransportRequest:
        if not isinstance(request, OhlcRequest):
            raise RealMarketDataProviderValidationError(
                "OHLC request factory requires OhlcRequest"
            )
        return ExternalTransportRequest(
            endpoint=self.endpoint,
            method=ExternalTransportMethod.GET,
            path=self.ohlc_path,
            timeout=self.timeout,
            query=(
                ("closed_at", request.closed_at.isoformat()),
                ("instrument", request.instrument.symbol),
                ("opened_at", request.opened_at.isoformat()),
                ("timeframe_seconds", str(request.timeframe.seconds)),
            ),
            headers={"accept": "application/json"},
        )


class ConcreteJsonMarketDataDecoder:
    """Decode a concrete JSON wire format into existing provider-neutral payloads."""

    __slots__ = ()

    def decode_quote(
        self,
        response: ExternalTransportResponse,
        *,
        source: ExternalSourceDescriptor,
        request: QuoteRequest,
    ) -> Result[ExternalQuotePayload, ExternalPortError]:
        if not isinstance(response, ExternalTransportResponse):
            return Failure(
                RealMarketDataProviderValidationError(
                    "quote decoder requires ExternalTransportResponse"
                )
            )
        if not isinstance(source, ExternalSourceDescriptor):
            return Failure(
                RealMarketDataProviderValidationError(
                    "quote decoder requires ExternalSourceDescriptor"
                )
            )
        if not isinstance(request, QuoteRequest):
            return Failure(
                RealMarketDataProviderValidationError(
                    "quote decoder requires QuoteRequest"
                )
            )
        data_result = _json_object(response.payload)
        if isinstance(data_result, Failure):
            return data_result
        data = data_result.value
        instrument = _string_field(data, "instrument")
        observed_at = _timestamp_field(data, "observed_at")
        bid = _decimal_field(data, "bid")
        ask = _decimal_field(data, "ask")
        for result in (instrument, observed_at, bid, ask):
            if isinstance(result, Failure):
                return Failure(result.error)
        assert isinstance(instrument, Success)
        assert isinstance(observed_at, Success)
        assert isinstance(bid, Success)
        assert isinstance(ask, Success)
        return Success(
            ExternalQuotePayload(
                source=source,
                instrument=instrument.value,
                observed_at=observed_at.value,
                bid=bid.value,
                ask=ask.value,
            )
        )

    def decode_ohlc(
        self,
        response: ExternalTransportResponse,
        *,
        source: ExternalSourceDescriptor,
        request: OhlcRequest,
    ) -> Result[ExternalOhlcPayload, ExternalPortError]:
        if not isinstance(response, ExternalTransportResponse):
            return Failure(
                RealMarketDataProviderValidationError(
                    "OHLC decoder requires ExternalTransportResponse"
                )
            )
        if not isinstance(source, ExternalSourceDescriptor):
            return Failure(
                RealMarketDataProviderValidationError(
                    "OHLC decoder requires ExternalSourceDescriptor"
                )
            )
        if not isinstance(request, OhlcRequest):
            return Failure(
                RealMarketDataProviderValidationError(
                    "OHLC decoder requires OhlcRequest"
                )
            )
        data_result = _json_object(response.payload)
        if isinstance(data_result, Failure):
            return data_result
        data = data_result.value
        instrument = _string_field(data, "instrument")
        timeframe = _whole_number_field(data, "timeframe_seconds")
        opened_at = _timestamp_field(data, "opened_at")
        closed_at = _timestamp_field(data, "closed_at")
        open_value = _decimal_field(data, "open")
        high = _decimal_field(data, "high")
        low = _decimal_field(data, "low")
        close = _decimal_field(data, "close")
        for result in (
            instrument,
            timeframe,
            opened_at,
            closed_at,
            open_value,
            high,
            low,
            close,
        ):
            if isinstance(result, Failure):
                return Failure(result.error)
        assert isinstance(instrument, Success)
        assert isinstance(timeframe, Success)
        assert isinstance(opened_at, Success)
        assert isinstance(closed_at, Success)
        assert isinstance(open_value, Success)
        assert isinstance(high, Success)
        assert isinstance(low, Success)
        assert isinstance(close, Success)
        return Success(
            ExternalOhlcPayload(
                source=source,
                instrument=instrument.value,
                timeframe_seconds=timeframe.value,
                opened_at=opened_at.value,
                closed_at=closed_at.value,
                open=open_value.value,
                high=high.value,
                low=low.value,
                close=close.value,
            )
        )


def build_concrete_json_market_data_flow(
    *,
    provider: ReadOnlyExternalProviderAdapter,
    endpoint: ProviderEndpoint,
    timeout: ExternalTransportTimeout,
    resolved_at: datetime,
) -> ControlledLiveMarketDataFlow:
    """Compose concrete wire mapping into the canonical existing ingestion flow."""
    return ControlledLiveMarketDataFlow(
        LiveMarketDataPayloadAdapter(
            provider=provider,
            request_factory=ConcreteJsonMarketDataRequestFactory(
                endpoint=endpoint,
                timeout=timeout,
            ),
            decoder=ConcreteJsonMarketDataDecoder(),
            resolved_at=resolved_at,
        )
    )
