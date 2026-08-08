from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import cast

from qore.infrastructure.activation_policy import ProviderActivationDecisionSnapshot
from qore.infrastructure.connectivity import (
    ProviderConnectivityMode,
    ReadOnlyProviderConnectivityIntent,
)
from qore.infrastructure.ingestion import ExternalOhlcPayload, ExternalQuotePayload
from qore.infrastructure.live_market_data import (
    ControlledLiveMarketDataFlow,
    LiveMarketDataPayloadAdapter,
)
from qore.infrastructure.market_data import OhlcRequest, QuoteRequest
from qore.infrastructure.oanda_practice_configuration import (
    OandaPracticeRuntimeConfiguration,
)
from qore.infrastructure.oanda_practice_credentials import (
    OandaPracticeCredentialActivation,
)
from qore.infrastructure.ports import (
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
)
from qore.infrastructure.providers import ProviderCapability
from qore.infrastructure.read_only_provider_adapter import (
    ReadOnlyExternalProviderAdapter,
    ReadOnlyProviderAdapterConfiguration,
)
from qore.infrastructure.secret_resolution import (
    SecretAuthenticatedTransportBoundary,
    SecretMaterialResolution,
)
from qore.infrastructure.secrets import (
    SecretBoundaryError,
    SecretBoundaryValidationError,
    SecretRef,
)
from qore.infrastructure.transport import (
    ExternalTransportMethod,
    ExternalTransportRequest,
    ExternalTransportResponse,
)
from qore.kernel.result import Failure, Result, Success

_GRANULARITY_BY_SECONDS = {
    5: "S5",
    10: "S10",
    15: "S15",
    30: "S30",
    60: "M1",
    120: "M2",
    240: "M4",
    300: "M5",
    600: "M10",
    900: "M15",
    1800: "M30",
    3600: "H1",
    7200: "H2",
    10800: "H3",
    14400: "H4",
    21600: "H6",
    28800: "H8",
    43200: "H12",
    86400: "D",
    604800: "W",
}


class OandaPracticeMarketFeedError(ExternalPortError):
    """Base error for the OANDA Practice market-data activation boundary."""

    __slots__ = ()


class OandaPracticeMarketFeedValidationError(OandaPracticeMarketFeedError):
    """Provider payload or composition violates OANDA Practice invariants."""

    __slots__ = ()


def _json_object(payload: bytes) -> Result[Mapping[str, object], ExternalPortError]:
    try:
        decoded: object = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return Failure(
            OandaPracticeMarketFeedValidationError(
                "OANDA market-data response must be a UTF-8 JSON object"
            )
        )
    if not isinstance(decoded, dict) or any(not isinstance(key, str) for key in decoded):
        return Failure(
            OandaPracticeMarketFeedValidationError(
                "OANDA market-data response root must be a string-keyed object"
            )
        )
    return Success(cast(dict[str, object], decoded))


def _timestamp(value: object, *, field_name: str) -> Result[datetime, ExternalPortError]:
    if not isinstance(value, str) or not value:
        return Failure(
            OandaPracticeMarketFeedValidationError(
                f"OANDA {field_name} must be a non-empty RFC3339 string"
            )
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return Failure(
            OandaPracticeMarketFeedValidationError(
                f"OANDA {field_name} must be parseable RFC3339"
            )
        )
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return Failure(
            OandaPracticeMarketFeedValidationError(
                f"OANDA {field_name} must be timezone-aware"
            )
        )
    return Success(parsed)


def _positive_decimal_string(
    value: object,
    *,
    field_name: str,
) -> Result[tuple[Decimal, str], ExternalPortError]:
    if not isinstance(value, str) or not value:
        return Failure(
            OandaPracticeMarketFeedValidationError(
                f"OANDA {field_name} must be a decimal string"
            )
        )
    try:
        decimal_value = Decimal(value)
    except InvalidOperation:
        return Failure(
            OandaPracticeMarketFeedValidationError(
                f"OANDA {field_name} must be a decimal string"
            )
        )
    if not decimal_value.is_finite() or decimal_value <= 0:
        return Failure(
            OandaPracticeMarketFeedValidationError(
                f"OANDA {field_name} must be positive and finite"
            )
        )
    return Success((decimal_value, value))


def _best_bucket_price(
    value: object,
    *,
    field_name: str,
    highest: bool,
) -> Result[str, ExternalPortError]:
    if not isinstance(value, list) or not value:
        return Failure(
            OandaPracticeMarketFeedValidationError(
                f"OANDA {field_name} must contain at least one price bucket"
            )
        )
    parsed: list[tuple[Decimal, str]] = []
    for item in value:
        if not isinstance(item, dict):
            return Failure(
                OandaPracticeMarketFeedValidationError(
                    f"OANDA {field_name} entries must be objects"
                )
            )
        price = _positive_decimal_string(
            item.get("price"),
            field_name=f"{field_name}.price",
        )
        if isinstance(price, Failure):
            return price
        parsed.append(price.value)
    selected = (
        max(parsed, key=lambda item: item[0])
        if highest
        else min(parsed, key=lambda item: item[0])
    )
    return Success(selected[1])


def _granularity(seconds: int) -> Result[str, ExternalPortError]:
    value = _GRANULARITY_BY_SECONDS.get(seconds)
    if value is None:
        return Failure(
            OandaPracticeMarketFeedValidationError(
                "requested timeframe is not supported by the OANDA Practice mapping"
            )
        )
    return Success(value)


@dataclass(frozen=True, slots=True)
class OandaPracticeMarketDataRequestFactory:
    """Map canonical requests onto the approved OANDA v20 Practice REST surface."""

    configuration: OandaPracticeRuntimeConfiguration

    def __post_init__(self) -> None:
        if not isinstance(self.configuration, OandaPracticeRuntimeConfiguration):
            raise OandaPracticeMarketFeedValidationError(
                "OANDA request factory requires OandaPracticeRuntimeConfiguration"
            )

    def _validate_symbol(self, symbol: str) -> None:
        if symbol not in self.configuration.symbols:
            raise OandaPracticeMarketFeedValidationError(
                "requested instrument is not allowlisted in OANDA Practice configuration"
            )

    def quote_request(self, request: QuoteRequest) -> ExternalTransportRequest:
        if not isinstance(request, QuoteRequest):
            raise OandaPracticeMarketFeedValidationError(
                "OANDA quote request factory requires QuoteRequest"
            )
        symbol = request.instrument.symbol
        self._validate_symbol(symbol)
        account_ref = self.configuration.account.account_ref
        return ExternalTransportRequest(
            endpoint=self.configuration.rest_endpoint,
            method=ExternalTransportMethod.GET,
            path=f"/v3/accounts/{account_ref}/pricing",
            timeout=self.configuration.rest_timeout,
            query=(("instruments", symbol),),
            headers={
                "accept": "application/json",
                "accept-datetime-format": "RFC3339",
            },
        )

    def ohlc_request(self, request: OhlcRequest) -> ExternalTransportRequest:
        if not isinstance(request, OhlcRequest):
            raise OandaPracticeMarketFeedValidationError(
                "OANDA OHLC request factory requires OhlcRequest"
            )
        symbol = request.instrument.symbol
        self._validate_symbol(symbol)
        granularity = _granularity(request.timeframe.seconds)
        if isinstance(granularity, Failure):
            raise granularity.error
        account_ref = self.configuration.account.account_ref
        return ExternalTransportRequest(
            endpoint=self.configuration.rest_endpoint,
            method=ExternalTransportMethod.GET,
            path=f"/v3/accounts/{account_ref}/instruments/{symbol}/candles",
            timeout=self.configuration.rest_timeout,
            query=(
                ("from", request.opened_at.isoformat()),
                ("granularity", granularity.value),
                ("price", "M"),
                ("to", request.closed_at.isoformat()),
            ),
            headers={
                "accept": "application/json",
                "accept-datetime-format": "RFC3339",
            },
        )


class OandaPracticeMarketDataDecoder:
    """Decode OANDA v20 pricing/candles into existing provider-neutral payloads."""

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
                OandaPracticeMarketFeedValidationError(
                    "OANDA quote decoder requires ExternalTransportResponse"
                )
            )
        if not isinstance(source, ExternalSourceDescriptor) or not isinstance(
            request, QuoteRequest
        ):
            return Failure(
                OandaPracticeMarketFeedValidationError(
                    "OANDA quote decoder requires explicit source and QuoteRequest"
                )
            )
        root = _json_object(response.payload)
        if isinstance(root, Failure):
            return root
        prices = root.value.get("prices")
        if not isinstance(prices, list):
            return Failure(
                OandaPracticeMarketFeedValidationError(
                    "OANDA pricing response prices must be an array"
                )
            )
        matching: list[dict[str, object]] = []
        for item in prices:
            if not isinstance(item, dict):
                return Failure(
                    OandaPracticeMarketFeedValidationError(
                        "OANDA pricing entries must be objects"
                    )
                )
            if item.get("instrument") == request.instrument.symbol:
                matching.append(cast(dict[str, object], item))
        if len(matching) != 1:
            return Failure(
                OandaPracticeMarketFeedValidationError(
                    "OANDA pricing response must contain exactly one requested instrument"
                )
            )
        price = matching[0]
        if price.get("tradeable") is not True:
            return Failure(
                OandaPracticeMarketFeedValidationError(
                    "OANDA requested price must be explicitly tradeable"
                )
            )
        observed_at = _timestamp(price.get("time"), field_name="price.time")
        if isinstance(observed_at, Failure):
            return observed_at
        bid = _best_bucket_price(price.get("bids"), field_name="bids", highest=True)
        if isinstance(bid, Failure):
            return bid
        ask = _best_bucket_price(price.get("asks"), field_name="asks", highest=False)
        if isinstance(ask, Failure):
            return ask
        bid_decimal = _positive_decimal_string(bid.value, field_name="best_bid")
        ask_decimal = _positive_decimal_string(ask.value, field_name="best_ask")
        if isinstance(bid_decimal, Failure):
            return bid_decimal
        if isinstance(ask_decimal, Failure):
            return ask_decimal
        if bid_decimal.value[0] > ask_decimal.value[0]:
            return Failure(
                OandaPracticeMarketFeedValidationError(
                    "OANDA best bid must not exceed best ask"
                )
            )
        return Success(
            ExternalQuotePayload(
                source=source,
                instrument=request.instrument.symbol,
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
                OandaPracticeMarketFeedValidationError(
                    "OANDA OHLC decoder requires ExternalTransportResponse"
                )
            )
        if not isinstance(source, ExternalSourceDescriptor) or not isinstance(
            request, OhlcRequest
        ):
            return Failure(
                OandaPracticeMarketFeedValidationError(
                    "OANDA OHLC decoder requires explicit source and OhlcRequest"
                )
            )
        expected_granularity = _granularity(request.timeframe.seconds)
        if isinstance(expected_granularity, Failure):
            return expected_granularity
        root = _json_object(response.payload)
        if isinstance(root, Failure):
            return root
        if root.value.get("instrument") != request.instrument.symbol:
            return Failure(
                OandaPracticeMarketFeedValidationError(
                    "OANDA candle instrument must match the requested instrument"
                )
            )
        if root.value.get("granularity") != expected_granularity.value:
            return Failure(
                OandaPracticeMarketFeedValidationError(
                    "OANDA candle granularity must match the requested timeframe"
                )
            )
        candles = root.value.get("candles")
        if not isinstance(candles, list) or len(candles) != 1:
            return Failure(
                OandaPracticeMarketFeedValidationError(
                    "OANDA candle response must contain exactly one candle"
                )
            )
        candle = candles[0]
        if not isinstance(candle, dict) or candle.get("complete") is not True:
            return Failure(
                OandaPracticeMarketFeedValidationError(
                    "OANDA candle must be an explicitly complete object"
                )
            )
        opened_at = _timestamp(candle.get("time"), field_name="candle.time")
        if isinstance(opened_at, Failure):
            return opened_at
        if opened_at.value != request.opened_at:
            return Failure(
                OandaPracticeMarketFeedValidationError(
                    "OANDA candle start must match the requested interval"
                )
            )
        derived_closed_at = opened_at.value + timedelta(seconds=request.timeframe.seconds)
        if derived_closed_at != request.closed_at:
            return Failure(
                OandaPracticeMarketFeedValidationError(
                    "OANDA candle interval must match the requested close"
                )
            )
        mid = candle.get("mid")
        if not isinstance(mid, dict):
            return Failure(
                OandaPracticeMarketFeedValidationError(
                    "OANDA midpoint candle data must be an object"
                )
            )
        values: dict[str, str] = {}
        for wire_name, canonical_name in (
            ("o", "open"),
            ("h", "high"),
            ("l", "low"),
            ("c", "close"),
        ):
            parsed = _positive_decimal_string(
                mid.get(wire_name),
                field_name=f"mid.{wire_name}",
            )
            if isinstance(parsed, Failure):
                return parsed
            values[canonical_name] = parsed.value[1]
        return Success(
            ExternalOhlcPayload(
                source=source,
                instrument=request.instrument.symbol,
                timeframe_seconds=request.timeframe.seconds,
                opened_at=opened_at.value,
                closed_at=derived_closed_at,
                open=values["open"],
                high=values["high"],
                low=values["low"],
                close=values["close"],
            )
        )


@dataclass(frozen=True, slots=True)
class ActivatedOandaPracticeCredentialResolver:
    """Expose only one already-authorized Practice credential to the provider adapter."""

    activation: OandaPracticeCredentialActivation

    def __post_init__(self) -> None:
        if not isinstance(self.activation, OandaPracticeCredentialActivation):
            raise OandaPracticeMarketFeedValidationError(
                "activated resolver requires OandaPracticeCredentialActivation"
            )

    def resolve_material(
        self,
        ref: SecretRef,
        *,
        metadata: ExternalRequestMetadata,
        resolved_at: datetime,
    ) -> Result[SecretMaterialResolution, SecretBoundaryError]:
        if ref != self.activation.ref:
            return Failure(
                SecretBoundaryValidationError(
                    "OANDA market feed may resolve only the activated Practice credential"
                )
            )
        if not isinstance(metadata, ExternalRequestMetadata):
            return Failure(
                SecretBoundaryValidationError(
                    "OANDA market feed credential resolution requires explicit metadata"
                )
            )
        if (
            not isinstance(resolved_at, datetime)
            or resolved_at.tzinfo is None
            or resolved_at.utcoffset() is None
        ):
            return Failure(
                SecretBoundaryValidationError(
                    "OANDA market feed resolved_at must be timezone-aware"
                )
            )
        if resolved_at < self.activation.activated_at:
            return Failure(
                SecretBoundaryValidationError(
                    "OANDA market feed resolution must not predate credential activation"
                )
            )
        try:
            resolution = SecretMaterialResolution(
                ref=ref,
                material=self.activation.material,
                resolved_at=resolved_at,
            )
        except SecretBoundaryError as error:
            return Failure(error)
        return Success(resolution)


def compose_oanda_practice_read_only_provider(
    *,
    configuration: OandaPracticeRuntimeConfiguration,
    credential: OandaPracticeCredentialActivation,
    activation: ProviderActivationDecisionSnapshot,
    authenticated_transport: SecretAuthenticatedTransportBoundary,
) -> Result[ReadOnlyExternalProviderAdapter, ExternalPortError]:
    """Bind approved OANDA Practice configuration to existing supervised provider IO."""
    if not isinstance(configuration, OandaPracticeRuntimeConfiguration):
        return Failure(
            OandaPracticeMarketFeedValidationError(
                "OANDA provider composition requires runtime configuration"
            )
        )
    if not isinstance(credential, OandaPracticeCredentialActivation):
        return Failure(
            OandaPracticeMarketFeedValidationError(
                "OANDA provider composition requires activated Practice credentials"
            )
        )
    if credential.configuration != configuration:
        return Failure(
            OandaPracticeMarketFeedValidationError(
                "OANDA credential configuration must match provider configuration"
            )
        )
    if (
        not isinstance(activation, ProviderActivationDecisionSnapshot)
        or not activation.can_activate
    ):
        return Failure(
            OandaPracticeMarketFeedValidationError(
                "OANDA market feed requires an allowed provider activation decision"
            )
        )
    if activation.policy.provider.provider_name.value != configuration.provider_key:
        return Failure(
            OandaPracticeMarketFeedValidationError(
                "OANDA activation provider identity must match runtime configuration"
            )
        )
    if not activation.policy.source.port_name.value.startswith("market-data"):
        return Failure(
            OandaPracticeMarketFeedValidationError(
                "OANDA market feed activation source must use market-data namespace"
            )
        )
    try:
        connectivity = ReadOnlyProviderConnectivityIntent(
            provider=activation.policy.provider,
            endpoint=configuration.rest_endpoint,
            mode=ProviderConnectivityMode.NETWORK_READ_ONLY,
            capability=ProviderCapability.MARKET_DATA_READ,
        )
        adapter_configuration = ReadOnlyProviderAdapterConfiguration(
            connectivity=connectivity,
            activation=activation,
            secret_ref=credential.ref,
        )
        adapter = ReadOnlyExternalProviderAdapter(
            configuration=adapter_configuration,
            authenticated_transport=authenticated_transport,
            secret_resolver=ActivatedOandaPracticeCredentialResolver(credential),
        )
    except ExternalPortError as error:
        return Failure(error)
    return Success(adapter)


def build_oanda_practice_market_data_flow(
    *,
    provider: ReadOnlyExternalProviderAdapter,
    configuration: OandaPracticeRuntimeConfiguration,
    resolved_at: datetime,
) -> Result[ControlledLiveMarketDataFlow, ExternalPortError]:
    """Compose OANDA wire mapping into the existing canonical ingestion flow."""
    if not isinstance(provider, ReadOnlyExternalProviderAdapter):
        return Failure(
            OandaPracticeMarketFeedValidationError(
                "OANDA market feed requires ReadOnlyExternalProviderAdapter"
            )
        )
    if not isinstance(configuration, OandaPracticeRuntimeConfiguration):
        return Failure(
            OandaPracticeMarketFeedValidationError(
                "OANDA market feed requires runtime configuration"
            )
        )
    if provider.connectivity_intent.endpoint != configuration.rest_endpoint:
        return Failure(
            OandaPracticeMarketFeedValidationError(
                "OANDA provider endpoint must match Practice runtime configuration"
            )
        )
    try:
        flow = ControlledLiveMarketDataFlow(
            LiveMarketDataPayloadAdapter(
                provider=provider,
                request_factory=OandaPracticeMarketDataRequestFactory(configuration),
                decoder=OandaPracticeMarketDataDecoder(),
                resolved_at=resolved_at,
            )
        )
    except ExternalPortError as error:
        return Failure(error)
    return Success(flow)
