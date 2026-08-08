from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.domain.events import CorrelationId
from qore.infrastructure.adapter_configuration import (
    AdapterConfigurationMode,
    ExternalAdapterConfiguration,
)
from qore.infrastructure.adapter_resilience import (
    AdapterCircuitBreakerSnapshot,
    AdapterCircuitBreakerState,
    AdapterRateLimitPolicy,
    AdapterResiliencePolicy,
    AdapterResilienceUnavailableError,
    AdapterRetryableFailure,
    AdapterRetryDelay,
    AdapterRetryPolicy,
    AdapterThrottledError,
    AdapterTimeoutPolicy,
)
from qore.infrastructure.ingestion import (
    ExternalOhlcPayload,
    ExternalQuotePayload,
    IngestionValidationError,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcRequest,
    QuoteRequest,
    Timeframe,
)
from qore.infrastructure.market_data_provider_harness import (
    MarketDataProviderHarnessError,
    MarketDataProviderHarnessState,
    MarketDataProviderHarnessValidationError,
    MarketDataProviderOhlcIngestion,
    MarketDataProviderQuoteIngestion,
    ReadOnlyMarketDataProviderHarness,
    ReadOnlyMarketDataProviderHarnessConfiguration,
    ReadOnlyMarketDataProviderPayloadHarness,
    compose_read_only_market_data_provider_harness,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortAvailability,
    PortName,
    SourceId,
)
from qore.infrastructure.providers import (
    ProviderCapability,
    ProviderCapabilitySet,
    ProviderDescriptor,
    ProviderEnablement,
    ProviderId,
    ProviderName,
)
from qore.kernel.result import Failure, Success

_RAW_SECRET = "sk-provider-secret-value"
_PROVIDER_ID = ProviderId(UUID("f6000000-0000-0000-0000-000000000001"))
_ADAPTER_ID = AdapterId(UUID("f6000000-0000-0000-0000-000000000002"))
_SOURCE_ID = SourceId(UUID("f6000000-0000-0000-0000-000000000003"))
_CORRELATION_ID = CorrelationId(UUID("f6000000-0000-0000-0000-000000000004"))
_QUOTE_ID = MarketDataSnapshotId(UUID("f6000000-0000-0000-0000-000000000005"))
_OHLC_ID = MarketDataSnapshotId(UUID("f6000000-0000-0000-0000-000000000006"))
_OTHER_SOURCE_ID = SourceId(UUID("f6000000-0000-0000-0000-000000000007"))
_OPENED_AT = datetime(2026, 8, 7, 13, 0, tzinfo=UTC)
_CLOSED_AT = _OPENED_AT + timedelta(minutes=1)
_OBSERVED_AT = datetime(2026, 8, 7, 13, 1, tzinfo=UTC)


def _provider() -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=_PROVIDER_ID,
        provider_name=ProviderName("reference-marketdata-provider"),
        enablement=ProviderEnablement.READ_ONLY,
        capabilities=ProviderCapabilitySet(
            (
                ProviderCapability.HEALTH,
                ProviderCapability.MARKET_DATA_READ,
            )
        ),
    )


def _source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_ADAPTER_ID,
        source_id=_SOURCE_ID,
        port_name=PortName("market-data.provider-harness"),
    )


def _other_source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_ADAPTER_ID,
        source_id=_OTHER_SOURCE_ID,
        port_name=PortName("market-data.provider-harness"),
    )


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(correlation_id=_CORRELATION_ID)


def _adapter_configuration() -> ExternalAdapterConfiguration:
    return ExternalAdapterConfiguration(
        provider=_provider(),
        source=_source(),
        mode=AdapterConfigurationMode.READ_ONLY,
    )


def _resilience_policy(
    *,
    rate_limit: AdapterRateLimitPolicy | None = None,
) -> AdapterResiliencePolicy:
    return AdapterResiliencePolicy(
        provider=_provider(),
        source=_source(),
        timeout=AdapterTimeoutPolicy(AdapterRetryDelay(250)),
        retry=AdapterRetryPolicy(
            max_attempts=2,
            delay_schedule=(AdapterRetryDelay(10),),
            retryable_failures=(
                AdapterRetryableFailure.THROTTLED,
                AdapterRetryableFailure.UNAVAILABLE,
            ),
        ),
        rate_limit=rate_limit,
    )


def _quote_request() -> QuoteRequest:
    return QuoteRequest(Instrument("EURUSD"))


def _ohlc_request() -> OhlcRequest:
    return OhlcRequest(
        instrument=Instrument("EURUSD"),
        timeframe=Timeframe(60),
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
    )


def _quote_payload(
    *,
    source: ExternalSourceDescriptor | None = None,
    bid: str = "1.1000",
    ask: str = "1.1002",
) -> ExternalQuotePayload:
    return ExternalQuotePayload(
        source=source or _source(),
        instrument=" eurusd ",
        observed_at=_OBSERVED_AT,
        bid=bid,
        ask=ask,
    )


def _ohlc_payload() -> ExternalOhlcPayload:
    return ExternalOhlcPayload(
        source=_source(),
        instrument="eurusd",
        timeframe_seconds="60",
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
        open="1.1000",
        high="1.1010",
        low="1.0990",
        close="1.1005",
    )


def _configuration(
    *,
    quote_payloads: tuple[ExternalQuotePayload, ...] | None = None,
    ohlc_payloads: tuple[ExternalOhlcPayload, ...] | None = None,
    state: MarketDataProviderHarnessState = MarketDataProviderHarnessState.AVAILABLE,
    rate_limit: AdapterRateLimitPolicy | None = None,
    retry_after: AdapterRetryDelay | None = None,
    circuit_breaker: AdapterCircuitBreakerSnapshot | None = None,
) -> ReadOnlyMarketDataProviderHarnessConfiguration:
    return ReadOnlyMarketDataProviderHarnessConfiguration(
        adapter_configuration=_adapter_configuration(),
        metadata=_metadata(),
        resilience_policy=_resilience_policy(rate_limit=rate_limit),
        quote_payloads=quote_payloads or (_quote_payload(),),
        ohlc_payloads=ohlc_payloads or (_ohlc_payload(),),
        quote_ingestions=(
            MarketDataProviderQuoteIngestion(
                request=_quote_request(),
                snapshot_id=_QUOTE_ID,
            ),
        ),
        ohlc_ingestions=(
            MarketDataProviderOhlcIngestion(
                request=_ohlc_request(),
                snapshot_id=_OHLC_ID,
            ),
        ),
        state=state,
        retry_after=retry_after,
        circuit_breaker=circuit_breaker,
    )


def test_market_data_provider_harness_normalizes_payloads_to_canonical_port() -> None:
    result = compose_read_only_market_data_provider_harness(_configuration())

    assert isinstance(result, Success)
    harness = result.value
    assert isinstance(harness, ReadOnlyMarketDataProviderHarness)
    assert isinstance(harness.provider_payload, ReadOnlyMarketDataProviderPayloadHarness)
    assert harness.ingestion_flow.port is harness.provider_payload
    assert harness.provider == _provider()
    assert harness.adapter_configuration == _adapter_configuration()

    quote_result = harness.ports.read_quote(_quote_request(), metadata=_metadata())
    ohlc_result = harness.ports.read_ohlc(_ohlc_request(), metadata=_metadata())

    assert isinstance(quote_result, Success)
    assert quote_result.value.snapshot_id == _QUOTE_ID
    assert quote_result.value.instrument.symbol == "EURUSD"
    assert quote_result.value.bid == 1.1
    assert quote_result.value.ask == 1.1002
    assert quote_result.value.source == _source()
    assert isinstance(ohlc_result, Success)
    assert ohlc_result.value.snapshot_id == _OHLC_ID
    assert ohlc_result.value.close == 1.1005


def test_market_data_provider_harness_health_and_resilience_are_explicit() -> None:
    result = compose_read_only_market_data_provider_harness(_configuration())

    assert isinstance(result, Success)
    payload_harness = result.value.provider_payload
    health_result = payload_harness.health(
        checked_at=_OBSERVED_AT,
        metadata=_metadata(),
    )
    resilience_result = payload_harness.resilience_snapshot(
        observed_at=_OBSERVED_AT,
        metadata=_metadata(),
    )

    assert isinstance(health_result, Success)
    assert health_result.value.availability is PortAvailability.AVAILABLE
    assert health_result.value.message is None
    assert health_result.value.details["provider_name"] == "reference-marketdata-provider"
    assert isinstance(resilience_result, Success)
    assert resilience_result.value.policy == _resilience_policy()
    assert resilience_result.value.metadata["harness_state"] == "available"


def test_market_data_provider_harness_invalid_payload_fails_in_ingestion() -> None:
    result = compose_read_only_market_data_provider_harness(
        _configuration(quote_payloads=(_quote_payload(bid="not-a-decimal"),))
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "bid" in str(result.error)


def test_market_data_provider_harness_unavailable_returns_resilience_error() -> None:
    circuit_breaker = AdapterCircuitBreakerSnapshot(
        state=AdapterCircuitBreakerState.OPEN,
        observed_at=_OBSERVED_AT,
        failure_count=3,
        recovery_delay=AdapterRetryDelay(500),
        message="provider temporarily unavailable",
    )

    result = compose_read_only_market_data_provider_harness(
        _configuration(
            state=MarketDataProviderHarnessState.UNAVAILABLE,
            circuit_breaker=circuit_breaker,
        )
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, AdapterResilienceUnavailableError)
    assert _RAW_SECRET not in str(result.error)
    assert "circuit_breaker=open" in str(result.error)


def test_market_data_provider_harness_throttled_returns_typed_error() -> None:
    rate_limit = AdapterRateLimitPolicy(
        request_limit=1,
        window=AdapterRetryDelay(1000),
    )

    result = compose_read_only_market_data_provider_harness(
        _configuration(
            state=MarketDataProviderHarnessState.THROTTLED,
            rate_limit=rate_limit,
            retry_after=AdapterRetryDelay(750),
        )
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, AdapterThrottledError)
    assert "retry_after_ms=750" in str(result.error)
    assert _RAW_SECRET not in str(result.error)


def test_market_data_provider_harness_source_mismatch_fails_normalization() -> None:
    result = compose_read_only_market_data_provider_harness(
        _configuration(quote_payloads=(_quote_payload(source=_other_source()),))
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "source" in str(result.error)
    assert "match port descriptor" in str(result.error)


def test_market_data_provider_harness_contracts_reject_runtime_type_bypasses() -> None:
    with pytest.raises(MarketDataProviderHarnessValidationError, match="QuoteRequest"):
        MarketDataProviderQuoteIngestion(
            request=cast(QuoteRequest, object()),
            snapshot_id=_QUOTE_ID,
        )
    with pytest.raises(MarketDataProviderHarnessValidationError, match="snapshot_id"):
        MarketDataProviderOhlcIngestion(
            request=_ohlc_request(),
            snapshot_id=cast(MarketDataSnapshotId, object()),
        )
    with pytest.raises(MarketDataProviderHarnessValidationError, match="metadata"):
        ReadOnlyMarketDataProviderHarnessConfiguration(
            adapter_configuration=_adapter_configuration(),
            metadata=cast(ExternalRequestMetadata, object()),
            resilience_policy=_resilience_policy(),
        )
    with pytest.raises(MarketDataProviderHarnessValidationError, match="rate-limit"):
        _configuration(state=MarketDataProviderHarnessState.THROTTLED)
    with pytest.raises(MarketDataProviderHarnessValidationError, match="enabled"):
        ReadOnlyMarketDataProviderHarnessConfiguration(
            adapter_configuration=ExternalAdapterConfiguration(
                provider=ProviderDescriptor(
                    provider_id=_PROVIDER_ID,
                    provider_name=ProviderName("reference-marketdata-provider"),
                    enablement=ProviderEnablement.DISABLED,
                    capabilities=ProviderCapabilitySet(
                        (ProviderCapability.MARKET_DATA_READ,)
                    ),
                ),
                source=_source(),
                mode=AdapterConfigurationMode.DISABLED,
            ),
            metadata=_metadata(),
            resilience_policy=_resilience_policy(),
        )


def test_market_data_provider_harness_public_exports() -> None:
    import qore.infrastructure as infrastructure

    assert infrastructure.MarketDataProviderHarnessError is MarketDataProviderHarnessError
    assert issubclass(MarketDataProviderHarnessError, ExternalPortError)
    assert infrastructure.MarketDataProviderHarnessState is MarketDataProviderHarnessState
    assert (
        infrastructure.MarketDataProviderHarnessValidationError
        is MarketDataProviderHarnessValidationError
    )
    assert infrastructure.MarketDataProviderOhlcIngestion is MarketDataProviderOhlcIngestion
    assert infrastructure.MarketDataProviderQuoteIngestion is MarketDataProviderQuoteIngestion
    assert infrastructure.ReadOnlyMarketDataProviderHarness is ReadOnlyMarketDataProviderHarness
    assert (
        infrastructure.ReadOnlyMarketDataProviderHarnessConfiguration
        is ReadOnlyMarketDataProviderHarnessConfiguration
    )
    assert (
        infrastructure.ReadOnlyMarketDataProviderPayloadHarness
        is ReadOnlyMarketDataProviderPayloadHarness
    )
    assert (
        infrastructure.compose_read_only_market_data_provider_harness
        is compose_read_only_market_data_provider_harness
    )
