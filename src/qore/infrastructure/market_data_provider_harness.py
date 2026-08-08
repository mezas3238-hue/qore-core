from __future__ import annotations

import dataclasses
from datetime import datetime
from enum import StrEnum

import qore.infrastructure.adapter_configuration as adapter_configuration
import qore.infrastructure.adapter_resilience as adapter_resilience
import qore.infrastructure.ingestion as ingestion
import qore.infrastructure.market_data as market_data
import qore.infrastructure.ports as ports
import qore.infrastructure.providers as providers
import qore.infrastructure.reference_adapters as reference_adapters
import qore.kernel.result as result_contract


class MarketDataProviderHarnessError(ports.ExternalPortError):
    """Base error for read-only market-data provider harness contracts."""

    __slots__ = ()


class MarketDataProviderHarnessValidationError(MarketDataProviderHarnessError):
    """Violation of a read-only market-data provider harness invariant."""

    __slots__ = ()


class MarketDataProviderHarnessState(StrEnum):
    """Closed deterministic provider harness state for read-only tests."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    THROTTLED = "throttled"


@dataclasses.dataclass(frozen=True, slots=True)
class MarketDataProviderQuoteIngestion:
    """Explicit quote ingestion request for the market-data provider harness."""

    request: market_data.QuoteRequest
    snapshot_id: market_data.MarketDataSnapshotId

    def __post_init__(self) -> None:
        if not isinstance(self.request, market_data.QuoteRequest):
            raise MarketDataProviderHarnessValidationError(
                "provider quote ingestion request must be QuoteRequest"
            )
        if not isinstance(self.snapshot_id, market_data.MarketDataSnapshotId):
            raise MarketDataProviderHarnessValidationError(
                "provider quote ingestion snapshot_id must be MarketDataSnapshotId"
            )


@dataclasses.dataclass(frozen=True, slots=True)
class MarketDataProviderOhlcIngestion:
    """Explicit OHLC ingestion request for the market-data provider harness."""

    request: market_data.OhlcRequest
    snapshot_id: market_data.MarketDataSnapshotId

    def __post_init__(self) -> None:
        if not isinstance(self.request, market_data.OhlcRequest):
            raise MarketDataProviderHarnessValidationError(
                "provider OHLC ingestion request must be OhlcRequest"
            )
        if not isinstance(self.snapshot_id, market_data.MarketDataSnapshotId):
            raise MarketDataProviderHarnessValidationError(
                "provider OHLC ingestion snapshot_id must be MarketDataSnapshotId"
            )


@dataclasses.dataclass(frozen=True, slots=True)
class ReadOnlyMarketDataProviderHarnessConfiguration:
    """Explicit deterministic inputs for a read-only market-data provider harness."""

    adapter_configuration: adapter_configuration.ExternalAdapterConfiguration
    metadata: ports.ExternalRequestMetadata
    resilience_policy: adapter_resilience.AdapterResiliencePolicy
    quote_payloads: tuple[ingestion.ExternalQuotePayload, ...] = ()
    ohlc_payloads: tuple[ingestion.ExternalOhlcPayload, ...] = ()
    quote_ingestions: tuple[MarketDataProviderQuoteIngestion, ...] = ()
    ohlc_ingestions: tuple[MarketDataProviderOhlcIngestion, ...] = ()
    state: MarketDataProviderHarnessState = MarketDataProviderHarnessState.AVAILABLE
    retry_after: adapter_resilience.AdapterRetryDelay | None = None
    circuit_breaker: adapter_resilience.AdapterCircuitBreakerSnapshot | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.adapter_configuration,
            adapter_configuration.ExternalAdapterConfiguration,
        ):
            raise MarketDataProviderHarnessValidationError(
                "provider harness adapter_configuration must be "
                "ExternalAdapterConfiguration"
            )
        if not isinstance(self.metadata, ports.ExternalRequestMetadata):
            raise MarketDataProviderHarnessValidationError(
                "provider harness metadata must be ExternalRequestMetadata"
            )
        if not isinstance(
            self.resilience_policy,
            adapter_resilience.AdapterResiliencePolicy,
        ):
            raise MarketDataProviderHarnessValidationError(
                "provider harness resilience_policy must be AdapterResiliencePolicy"
            )
        if not isinstance(self.state, MarketDataProviderHarnessState):
            raise MarketDataProviderHarnessValidationError(
                "provider harness state must be MarketDataProviderHarnessState"
            )
        if self.retry_after is not None and not isinstance(
            self.retry_after,
            adapter_resilience.AdapterRetryDelay,
        ):
            raise MarketDataProviderHarnessValidationError(
                "provider harness retry_after must be AdapterRetryDelay or None"
            )
        if self.circuit_breaker is not None and not isinstance(
            self.circuit_breaker,
            adapter_resilience.AdapterCircuitBreakerSnapshot,
        ):
            raise MarketDataProviderHarnessValidationError(
                "provider harness circuit_breaker must be "
                "AdapterCircuitBreakerSnapshot or None"
            )
        if not self.adapter_configuration.is_enabled:
            raise MarketDataProviderHarnessValidationError(
                "provider harness adapter configuration must be enabled"
            )
        if (
            self.adapter_configuration.provider
            != self.resilience_policy.provider
        ):
            raise MarketDataProviderHarnessValidationError(
                "provider harness resilience provider must match adapter configuration"
            )
        if self.adapter_configuration.source != self.resilience_policy.source:
            raise MarketDataProviderHarnessValidationError(
                "provider harness resilience source must match adapter configuration"
            )
        source_name = self.adapter_configuration.source.port_name.value
        if source_name != "market-data" and not source_name.startswith(
            "market-data."
        ):
            raise MarketDataProviderHarnessValidationError(
                "provider harness source must use the market-data namespace"
            )
        if not self.adapter_configuration.provider.capabilities.supports(
            providers.ProviderCapability.MARKET_DATA_READ
        ):
            raise MarketDataProviderHarnessValidationError(
                "provider harness requires market-data read capability"
            )
        if (
            self.adapter_configuration.mode
            is adapter_configuration.AdapterConfigurationMode.DISABLED
        ):
            raise MarketDataProviderHarnessValidationError(
                "provider harness adapter mode must not be disabled"
            )
        if (
            self.state is MarketDataProviderHarnessState.THROTTLED
            and self.resilience_policy.rate_limit is None
        ):
            raise MarketDataProviderHarnessValidationError(
                "throttled provider harness requires a rate-limit policy"
            )
        _validate_tuple(
            self.quote_payloads,
            item_type=ingestion.ExternalQuotePayload,
            field_name="provider harness quote_payloads",
        )
        _validate_tuple(
            self.ohlc_payloads,
            item_type=ingestion.ExternalOhlcPayload,
            field_name="provider harness ohlc_payloads",
        )
        _validate_tuple(
            self.quote_ingestions,
            item_type=MarketDataProviderQuoteIngestion,
            field_name="provider harness quote_ingestions",
        )
        _validate_tuple(
            self.ohlc_ingestions,
            item_type=MarketDataProviderOhlcIngestion,
            field_name="provider harness ohlc_ingestions",
        )

    @property
    def provider(self) -> providers.ProviderDescriptor:
        """Expose provider governance from the explicit adapter configuration."""
        return self.adapter_configuration.provider

    @property
    def source(self) -> ports.ExternalSourceDescriptor:
        """Expose the market-data source from the explicit adapter configuration."""
        return self.adapter_configuration.source

    def logical_values(self) -> tuple[object, ...]:
        """Return deterministic harness inputs without payload-sensitive values."""
        return (
            self.adapter_configuration.logical_values(),
            self.metadata.logical_values(),
            self.resilience_policy.logical_values(),
            tuple(payload.instrument for payload in self.quote_payloads),
            tuple(
                (
                    payload.instrument,
                    payload.timeframe_seconds,
                    payload.opened_at.isoformat(),
                    payload.closed_at.isoformat(),
                )
                for payload in self.ohlc_payloads
            ),
            tuple(request.snapshot_id.value for request in self.quote_ingestions),
            tuple(request.snapshot_id.value for request in self.ohlc_ingestions),
            self.state.value,
            self.retry_after.logical_values()
            if self.retry_after is not None
            else None,
            self.circuit_breaker.logical_values()
            if self.circuit_breaker is not None
            else None,
        )


class ReadOnlyMarketDataProviderPayloadHarness:
    """Deterministic provider-like payload port for read-only market data."""

    __slots__ = ("_configuration", "_ohlc", "_quotes")

    def __init__(
        self,
        configuration: ReadOnlyMarketDataProviderHarnessConfiguration,
    ) -> None:
        if not isinstance(configuration, ReadOnlyMarketDataProviderHarnessConfiguration):
            raise MarketDataProviderHarnessValidationError(
                "payload harness configuration must be "
                "ReadOnlyMarketDataProviderHarnessConfiguration"
            )
        self._configuration = configuration
        self._quotes = _build_quote_map(configuration.quote_payloads)
        self._ohlc = _build_ohlc_map(configuration.ohlc_payloads)

    @property
    def provider_descriptor(self) -> providers.ProviderDescriptor:
        """Expose provider governance without concrete provider dependencies."""
        return self._configuration.provider

    @property
    def provider_capabilities(self) -> providers.ProviderCapabilitySet:
        """Expose provider-neutral capabilities."""
        return self.provider_descriptor.capabilities

    @property
    def adapter_configuration(
        self,
    ) -> adapter_configuration.ExternalAdapterConfiguration:
        """Expose immutable adapter configuration without secret values."""
        return self._configuration.adapter_configuration

    @property
    def policy(self) -> adapter_resilience.AdapterResiliencePolicy:
        """Expose declarative resilience policy without executing it."""
        return self._configuration.resilience_policy

    @property
    def descriptor(self) -> ports.ExternalSourceDescriptor:
        """Expose the explicit market-data source descriptor."""
        return self._configuration.source

    def resilience_snapshot(
        self,
        *,
        observed_at: datetime,
        metadata: ports.ExternalRequestMetadata,
    ) -> result_contract.Result[
        adapter_resilience.AdapterResilienceSnapshot,
        adapter_resilience.AdapterResilienceError,
    ]:
        metadata_result = _validate_metadata(metadata)
        if isinstance(metadata_result, result_contract.Failure):
            return result_contract.Failure(
                adapter_resilience.AdapterResilienceValidationError(
                    str(metadata_result.error)
                )
            )
        try:
            snapshot = adapter_resilience.AdapterResilienceSnapshot(
                policy=self.policy,
                observed_at=observed_at,
                circuit_breaker=self._configuration.circuit_breaker,
                metadata={"harness_state": self._configuration.state.value},
            )
        except adapter_resilience.AdapterResilienceError as error:
            return result_contract.Failure(error)
        return result_contract.Success(snapshot)

    def health(
        self,
        *,
        checked_at: datetime,
        metadata: ports.ExternalRequestMetadata,
    ) -> result_contract.Result[ports.ExternalHealth, ports.ExternalPortError]:
        metadata_result = _validate_metadata(metadata)
        if isinstance(metadata_result, result_contract.Failure):
            return metadata_result
        try:
            health = ports.ExternalHealth(
                descriptor=self.descriptor,
                availability=_availability_for_state(self._configuration.state),
                checked_at=checked_at,
                message=_message_for_state(self._configuration.state),
                details={
                    "provider_name": self.provider_descriptor.provider_name.value,
                    "state": self._configuration.state.value,
                },
            )
        except ports.ExternalPortError as error:
            return result_contract.Failure(error)
        return result_contract.Success(health)

    def read_external_quote(
        self,
        request: market_data.QuoteRequest,
        *,
        metadata: ports.ExternalRequestMetadata,
    ) -> result_contract.Result[ingestion.ExternalQuotePayload, ports.ExternalPortError]:
        preflight = self._preflight_read(request, metadata=metadata)
        if isinstance(preflight, result_contract.Failure):
            return preflight
        payload = self._quotes.get(request.instrument.symbol)
        if payload is None:
            return result_contract.Failure(
                MarketDataProviderHarnessValidationError(
                    f"provider quote payload is not configured for {request.instrument.symbol}"
                )
            )
        return result_contract.Success(payload)

    def read_external_ohlc(
        self,
        request: market_data.OhlcRequest,
        *,
        metadata: ports.ExternalRequestMetadata,
    ) -> result_contract.Result[ingestion.ExternalOhlcPayload, ports.ExternalPortError]:
        preflight = self._preflight_read(request, metadata=metadata)
        if isinstance(preflight, result_contract.Failure):
            return preflight
        key = (
            request.instrument.symbol,
            request.timeframe.seconds,
            request.opened_at,
            request.closed_at,
        )
        payload = self._ohlc.get(key)
        if payload is None:
            return result_contract.Failure(
                MarketDataProviderHarnessValidationError(
                    "provider OHLC payload is not configured for request interval"
                )
            )
        return result_contract.Success(payload)

    def _preflight_read(
        self,
        request: object,
        *,
        metadata: ports.ExternalRequestMetadata,
    ) -> result_contract.Result[None, ports.ExternalPortError]:
        metadata_result = _validate_metadata(metadata)
        if isinstance(metadata_result, result_contract.Failure):
            return metadata_result
        if not isinstance(request, (market_data.QuoteRequest, market_data.OhlcRequest)):
            return result_contract.Failure(
                MarketDataProviderHarnessValidationError(
                    "provider harness read request must be QuoteRequest or OhlcRequest"
                )
            )
        state_error = _error_for_state(self._configuration)
        if state_error is not None:
            return result_contract.Failure(state_error)
        return result_contract.Success(None)


@dataclasses.dataclass(frozen=True, slots=True)
class ReadOnlyMarketDataProviderHarness:
    """Composed read-only provider harness exposing canonical MarketDataPort."""

    configuration: ReadOnlyMarketDataProviderHarnessConfiguration
    provider_payload: ReadOnlyMarketDataProviderPayloadHarness
    ingestion_flow: ingestion.MarketDataIngestionFlow
    market_data: reference_adapters.ReferenceMarketDataAdapter

    def __post_init__(self) -> None:
        if not isinstance(
            self.configuration,
            ReadOnlyMarketDataProviderHarnessConfiguration,
        ):
            raise MarketDataProviderHarnessValidationError(
                "market-data provider harness configuration must be "
                "ReadOnlyMarketDataProviderHarnessConfiguration"
            )
        if not isinstance(
            self.provider_payload,
            ReadOnlyMarketDataProviderPayloadHarness,
        ):
            raise MarketDataProviderHarnessValidationError(
                "provider_payload must be ReadOnlyMarketDataProviderPayloadHarness"
            )
        if not isinstance(self.ingestion_flow, ingestion.MarketDataIngestionFlow):
            raise MarketDataProviderHarnessValidationError(
                "ingestion_flow must be MarketDataIngestionFlow"
            )
        if not isinstance(
            self.market_data,
            reference_adapters.ReferenceMarketDataAdapter,
        ):
            raise MarketDataProviderHarnessValidationError(
                "market_data must be ReferenceMarketDataAdapter"
            )
        if self.ingestion_flow.port is not self.provider_payload:
            raise MarketDataProviderHarnessValidationError(
                "ingestion flow must use the composed provider payload harness"
            )
        if self.market_data.descriptor != self.configuration.source:
            raise MarketDataProviderHarnessValidationError(
                "canonical market-data adapter descriptor must match configuration"
            )

    @property
    def provider(self) -> providers.ProviderDescriptor:
        """Expose provider governance from configuration."""
        return self.configuration.provider

    @property
    def adapter_configuration(
        self,
    ) -> adapter_configuration.ExternalAdapterConfiguration:
        """Expose immutable adapter configuration."""
        return self.configuration.adapter_configuration

    @property
    def ports(self) -> market_data.MarketDataPort:
        """Expose canonical market data through the approved port contract."""
        return self.market_data


def compose_read_only_market_data_provider_harness(
    configuration: ReadOnlyMarketDataProviderHarnessConfiguration,
) -> result_contract.Result[
    ReadOnlyMarketDataProviderHarness,
    ports.ExternalPortError,
]:
    """Compose provider-like payloads, ingestion, and canonical MarketDataPort."""
    if not isinstance(configuration, ReadOnlyMarketDataProviderHarnessConfiguration):
        return result_contract.Failure(
            MarketDataProviderHarnessValidationError(
                "configuration must be ReadOnlyMarketDataProviderHarnessConfiguration"
            )
        )
    try:
        provider_payload = ReadOnlyMarketDataProviderPayloadHarness(configuration)
        flow = ingestion.MarketDataIngestionFlow(provider_payload)
    except ports.ExternalPortError as error:
        return result_contract.Failure(error)

    quote_result = _ingest_quotes(flow, configuration)
    if isinstance(quote_result, result_contract.Failure):
        return quote_result
    ohlc_result = _ingest_ohlc(flow, configuration)
    if isinstance(ohlc_result, result_contract.Failure):
        return ohlc_result

    try:
        canonical_market_data = reference_adapters.ReferenceMarketDataAdapter(
            configuration.source,
            quotes=quote_result.value,
            ohlc=ohlc_result.value,
        )
        harness = ReadOnlyMarketDataProviderHarness(
            configuration=configuration,
            provider_payload=provider_payload,
            ingestion_flow=flow,
            market_data=canonical_market_data,
        )
    except ports.ExternalPortError as error:
        return result_contract.Failure(error)
    return result_contract.Success(harness)


def _validate_tuple(
    value: object,
    *,
    item_type: type[object],
    field_name: str,
) -> tuple[object, ...]:
    if not isinstance(value, tuple):
        raise MarketDataProviderHarnessValidationError(f"{field_name} must be a tuple")
    for item in value:
        if not isinstance(item, item_type):
            raise MarketDataProviderHarnessValidationError(
                f"{field_name} entries must be {item_type.__name__}"
            )
    return value


def _validate_metadata(
    metadata: ports.ExternalRequestMetadata,
) -> result_contract.Result[None, ports.ExternalPortError]:
    if not isinstance(metadata, ports.ExternalRequestMetadata):
        return result_contract.Failure(
            MarketDataProviderHarnessValidationError(
                "provider harness metadata must be ExternalRequestMetadata"
            )
        )
    return result_contract.Success(None)


def _build_quote_map(
    payloads: tuple[ingestion.ExternalQuotePayload, ...],
) -> dict[str, ingestion.ExternalQuotePayload]:
    quote_map: dict[str, ingestion.ExternalQuotePayload] = {}
    for payload in payloads:
        if not isinstance(payload.instrument, str):
            raise MarketDataProviderHarnessValidationError(
                "provider quote payload instrument must be a string"
            )
        key = payload.instrument.strip().upper()
        if not key:
            raise MarketDataProviderHarnessValidationError(
                "provider quote payload instrument must not normalize to empty"
            )
        if key in quote_map:
            raise MarketDataProviderHarnessValidationError(
                "provider quote payloads must contain at most one payload per instrument"
            )
        quote_map[key] = payload
    return quote_map


def _build_ohlc_map(
    payloads: tuple[ingestion.ExternalOhlcPayload, ...],
) -> dict[tuple[str, int, datetime, datetime], ingestion.ExternalOhlcPayload]:
    ohlc_map: dict[tuple[str, int, datetime, datetime], ingestion.ExternalOhlcPayload] = {}
    for payload in payloads:
        if not isinstance(payload.instrument, str):
            raise MarketDataProviderHarnessValidationError(
                "provider OHLC payload instrument must be a string"
            )
        key = (
            payload.instrument.strip().upper(),
            _normalize_timeframe_key(payload.timeframe_seconds),
            payload.opened_at,
            payload.closed_at,
        )
        if not key[0]:
            raise MarketDataProviderHarnessValidationError(
                "provider OHLC payload instrument must not normalize to empty"
            )
        if key in ohlc_map:
            raise MarketDataProviderHarnessValidationError(
                "provider OHLC payloads must not contain duplicate intervals"
            )
        ohlc_map[key] = payload
    return ohlc_map


def _normalize_timeframe_key(value: ingestion.ExternalWholeNumberValue) -> int:
    if type(value) is int and value > 0:
        return value
    if isinstance(value, str):
        candidate = value.strip()
        if candidate.isascii() and candidate.isdecimal():
            normalized = int(candidate)
            if normalized > 0:
                return normalized
    raise MarketDataProviderHarnessValidationError(
        "provider OHLC timeframe must normalize to a positive int"
    )


def _availability_for_state(
    state: MarketDataProviderHarnessState,
) -> ports.PortAvailability:
    if state is MarketDataProviderHarnessState.AVAILABLE:
        return ports.PortAvailability.AVAILABLE
    if state is MarketDataProviderHarnessState.THROTTLED:
        return ports.PortAvailability.DEGRADED
    return ports.PortAvailability.UNAVAILABLE


def _message_for_state(state: MarketDataProviderHarnessState) -> str | None:
    if state is MarketDataProviderHarnessState.AVAILABLE:
        return None
    if state is MarketDataProviderHarnessState.THROTTLED:
        return "market-data provider harness is throttled"
    return "market-data provider harness is unavailable"


def _error_for_state(
    configuration: ReadOnlyMarketDataProviderHarnessConfiguration,
) -> ports.ExternalPortError | None:
    if configuration.state is MarketDataProviderHarnessState.AVAILABLE:
        return None
    if configuration.state is MarketDataProviderHarnessState.THROTTLED:
        if configuration.resilience_policy.rate_limit is None:
            return MarketDataProviderHarnessValidationError(
                "throttled provider harness requires a rate-limit policy"
            )
        return adapter_resilience.AdapterThrottledError(
            source=configuration.source,
            policy=configuration.resilience_policy.rate_limit,
            retry_after=configuration.retry_after,
        )
    return adapter_resilience.AdapterResilienceUnavailableError(
        source=configuration.source,
        circuit_breaker=configuration.circuit_breaker,
    )


def _ingest_quotes(
    flow: ingestion.MarketDataIngestionFlow,
    configuration: ReadOnlyMarketDataProviderHarnessConfiguration,
) -> result_contract.Result[
    tuple[market_data.QuoteSnapshot, ...],
    ports.ExternalPortError,
]:
    snapshots: list[market_data.QuoteSnapshot] = []
    for request in configuration.quote_ingestions:
        result = flow.ingest_quote(
            request.request,
            snapshot_id=request.snapshot_id,
            metadata=configuration.metadata,
        )
        if isinstance(result, result_contract.Failure):
            return result
        snapshots.append(result.value)
    return result_contract.Success(tuple(snapshots))


def _ingest_ohlc(
    flow: ingestion.MarketDataIngestionFlow,
    configuration: ReadOnlyMarketDataProviderHarnessConfiguration,
) -> result_contract.Result[
    tuple[market_data.OhlcSnapshot, ...],
    ports.ExternalPortError,
]:
    snapshots: list[market_data.OhlcSnapshot] = []
    for request in configuration.ohlc_ingestions:
        result = flow.ingest_ohlc(
            request.request,
            snapshot_id=request.snapshot_id,
            metadata=configuration.metadata,
        )
        if isinstance(result, result_contract.Failure):
            return result
        snapshots.append(result.value)
    return result_contract.Success(tuple(snapshots))
