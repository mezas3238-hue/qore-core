from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.events import CorrelationId
from qore.governance.composition import compose_functional_governance
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
    AdapterRetryDelay,
    AdapterRetryPolicy,
    AdapterRetryableFailure,
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
    MarketDataProviderOhlcIngestion,
    MarketDataProviderQuoteIngestion,
    ReadOnlyMarketDataProviderHarnessConfiguration,
)
from qore.infrastructure.persistence import (
    LoadPersistenceRequest,
    PersistenceKey,
    PersistenceVersion,
    SavePersistenceRequest,
    StoredRecord,
)
from qore.infrastructure.persistence_backend_harness import (
    PersistenceBackendHarnessConfiguration,
    PersistenceBackendHarnessState,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.provider_readiness import (
    ProviderReadinessEndToEndComposition,
    ProviderReadinessEndToEndConfiguration,
    ProviderReadinessEndToEndError,
    ProviderReadinessEndToEndValidationError,
    compose_provider_readiness_end_to_end,
)
from qore.infrastructure.providers import (
    ProviderCapability,
    ProviderCapabilitySet,
    ProviderDescriptor,
    ProviderEnablement,
    ProviderId,
    ProviderName,
)
from qore.kernel.result import Failure, Result, Success
from qore.specialized_governance.composition import compose_specialized_governance

Payload = dict[str, int]

_NOW = datetime(2026, 8, 8, 1, 30, tzinfo=UTC)
_OPENED_AT = datetime(2026, 8, 8, 1, 0, tzinfo=UTC)
_CLOSED_AT = _OPENED_AT + timedelta(minutes=15)
_MARKET_PROVIDER_ID = ProviderId(UUID("f8000000-0000-0000-0000-000000000001"))
_MARKET_ADAPTER_ID = AdapterId(UUID("f8000000-0000-0000-0000-000000000002"))
_MARKET_SOURCE_ID = SourceId(UUID("f8000000-0000-0000-0000-000000000003"))
_PERSISTENCE_PROVIDER_ID = ProviderId(UUID("f8000000-0000-0000-0000-000000000004"))
_PERSISTENCE_ADAPTER_ID = AdapterId(UUID("f8000000-0000-0000-0000-000000000005"))
_PERSISTENCE_SOURCE_ID = SourceId(UUID("f8000000-0000-0000-0000-000000000006"))
_CORRELATION_ID = CorrelationId(UUID("f8000000-0000-0000-0000-000000000007"))
_QUOTE_ID = MarketDataSnapshotId(UUID("f8000000-0000-0000-0000-000000000008"))
_OHLC_ID = MarketDataSnapshotId(UUID("f8000000-0000-0000-0000-000000000009"))
_KEY = PersistenceKey("provider.e2e", "state/seed")
_NEW_KEY = PersistenceKey("provider.e2e", "state/new")
_VERSION_ZERO = PersistenceVersion(0)


def _core(name: str = "qore-provider-readiness-e2e-test") -> CoreApplication:
    boot = bootstrap(Configuration(application_name=name))
    assert isinstance(boot, Success)
    return boot.value


def _metadata() -> ExternalRequestMetadata:
    return ExternalRequestMetadata(correlation_id=_CORRELATION_ID)


def _market_source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_MARKET_ADAPTER_ID,
        source_id=_MARKET_SOURCE_ID,
        port_name=PortName("market-data.provider-readiness"),
    )


def _persistence_source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=_PERSISTENCE_ADAPTER_ID,
        source_id=_PERSISTENCE_SOURCE_ID,
        port_name=PortName("persistence.provider-readiness"),
    )


def _market_provider() -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=_MARKET_PROVIDER_ID,
        provider_name=ProviderName("provider-readiness-market-data"),
        enablement=ProviderEnablement.READ_ONLY,
        capabilities=ProviderCapabilitySet(
            (
                ProviderCapability.HEALTH,
                ProviderCapability.MARKET_DATA_READ,
            )
        ),
    )


def _persistence_provider() -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=_PERSISTENCE_PROVIDER_ID,
        provider_name=ProviderName("provider-readiness-persistence"),
        enablement=ProviderEnablement.READ_ONLY,
        capabilities=ProviderCapabilitySet(
            (
                ProviderCapability.HEALTH,
                ProviderCapability.PERSISTENCE_READ,
                ProviderCapability.PERSISTENCE_WRITE,
            )
        ),
    )


def _market_adapter_configuration() -> ExternalAdapterConfiguration:
    return ExternalAdapterConfiguration(
        provider=_market_provider(),
        source=_market_source(),
        mode=AdapterConfigurationMode.READ_ONLY,
    )


def _persistence_adapter_configuration() -> ExternalAdapterConfiguration:
    return ExternalAdapterConfiguration(
        provider=_persistence_provider(),
        source=_persistence_source(),
        mode=AdapterConfigurationMode.READ_ONLY,
    )


def _resilience_policy(
    provider: ProviderDescriptor,
    source: ExternalSourceDescriptor,
    *,
    rate_limit: AdapterRateLimitPolicy | None = None,
) -> AdapterResiliencePolicy:
    return AdapterResiliencePolicy(
        provider=provider,
        source=source,
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


def _market_resilience_policy() -> AdapterResiliencePolicy:
    return _resilience_policy(_market_provider(), _market_source())


def _persistence_resilience_policy(
    *,
    rate_limit: AdapterRateLimitPolicy | None = None,
) -> AdapterResiliencePolicy:
    return _resilience_policy(
        _persistence_provider(),
        _persistence_source(),
        rate_limit=rate_limit,
    )


def _instrument() -> Instrument:
    return Instrument("EURUSD")


def _quote_request() -> QuoteRequest:
    return QuoteRequest(_instrument())


def _ohlc_request() -> OhlcRequest:
    return OhlcRequest(
        instrument=_instrument(),
        timeframe=Timeframe(900),
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
    )


def _quote_payload(*, bid: str = "1.2000") -> ExternalQuotePayload:
    return ExternalQuotePayload(
        source=_market_source(),
        instrument=" eurusd ",
        observed_at=_NOW,
        bid=bid,
        ask="1.2002",
    )


def _ohlc_payload() -> ExternalOhlcPayload:
    return ExternalOhlcPayload(
        source=_market_source(),
        instrument="eurusd",
        timeframe_seconds="900",
        opened_at=_OPENED_AT,
        closed_at=_CLOSED_AT,
        open="1.1980",
        high="1.2010",
        low="1.1970",
        close="1.2000",
    )


def _record(value: Payload | None = None) -> StoredRecord[Payload]:
    return StoredRecord(
        key=_KEY,
        version=_VERSION_ZERO,
        value=value or {"seed": 1},
        source=_persistence_source(),
        stored_at=_NOW,
    )


def _market_configuration(
    *,
    quote_payloads: tuple[ExternalQuotePayload, ...] | None = None,
) -> ReadOnlyMarketDataProviderHarnessConfiguration:
    return ReadOnlyMarketDataProviderHarnessConfiguration(
        adapter_configuration=_market_adapter_configuration(),
        metadata=_metadata(),
        resilience_policy=_market_resilience_policy(),
        quote_payloads=quote_payloads or (_quote_payload(),),
        ohlc_payloads=(_ohlc_payload(),),
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
    )


def _persistence_configuration(
    *,
    state: PersistenceBackendHarnessState = PersistenceBackendHarnessState.AVAILABLE,
    rate_limit: AdapterRateLimitPolicy | None = None,
    retry_after: AdapterRetryDelay | None = None,
    circuit_breaker: AdapterCircuitBreakerSnapshot | None = None,
) -> PersistenceBackendHarnessConfiguration[Payload]:
    return PersistenceBackendHarnessConfiguration(
        adapter_configuration=_persistence_adapter_configuration(),
        metadata=_metadata(),
        resilience_policy=_persistence_resilience_policy(rate_limit=rate_limit),
        initial_records=(_record(),),
        state=state,
        retry_after=retry_after,
        circuit_breaker=circuit_breaker,
    )


def _configuration(
    *,
    market_data: ReadOnlyMarketDataProviderHarnessConfiguration | None = None,
    persistence: PersistenceBackendHarnessConfiguration[Payload] | None = None,
) -> ProviderReadinessEndToEndConfiguration[Payload]:
    return ProviderReadinessEndToEndConfiguration(
        market_data=market_data or _market_configuration(),
        persistence=persistence or _persistence_configuration(),
    )


def test_provider_readiness_e2e_composes_harnesses_above_one_core() -> None:
    core = _core()
    event_bus = core.event_bus
    before_snapshot = core.runtime_snapshot()
    before_health = core.runtime_health()
    before_plan = core.runtime_plan
    result: Result[
        ProviderReadinessEndToEndComposition[Payload],
        ExternalPortError,
    ] = compose_provider_readiness_end_to_end(core, _configuration())

    assert isinstance(result, Success)
    composition = result.value
    assert composition.core is core
    assert composition.infrastructure.core is core
    assert composition.core.event_bus is event_bus
    assert composition.infrastructure.adapters.market_data is composition.market_data.market_data
    assert composition.infrastructure.adapters.persistence is composition.persistence.persistence
    assert composition.ports.market_data is composition.market_data.market_data
    assert composition.ports.persistence is composition.persistence.persistence
    assert core.runtime_snapshot() == before_snapshot
    assert core.runtime_health() == before_health
    assert core.runtime_plan == before_plan
    assert len(core.runtime_plan.components) == 1
    assert core.runtime_plan.components[0].component is core.engine


def test_provider_readiness_e2e_supports_application_level_consumption() -> None:
    core = _core("qore-provider-readiness-consumption")
    result: Result[
        ProviderReadinessEndToEndComposition[Payload],
        ExternalPortError,
    ] = compose_provider_readiness_end_to_end(core, _configuration())

    assert isinstance(result, Success)
    quote_result = result.value.ports.market_data.read_quote(
        _quote_request(),
        metadata=_metadata(),
    )
    ohlc_result = result.value.ports.market_data.read_ohlc(
        _ohlc_request(),
        metadata=_metadata(),
    )
    load_result = result.value.ports.persistence.load(
        LoadPersistenceRequest(_KEY),
        metadata=_metadata(),
    )
    save_result = result.value.ports.persistence.save(
        SavePersistenceRequest(
            key=_NEW_KEY,
            version=_VERSION_ZERO,
            value={"saved": 2},
            stored_at=_NOW,
        ),
        metadata=_metadata(),
    )

    assert isinstance(quote_result, Success)
    assert quote_result.value.snapshot_id == _QUOTE_ID
    assert quote_result.value.source == _market_source()
    assert isinstance(ohlc_result, Success)
    assert ohlc_result.value.snapshot_id == _OHLC_ID
    assert isinstance(load_result, Success)
    assert load_result.value is not None
    assert load_result.value.value == {"seed": 1}
    assert isinstance(save_result, Success)
    assert save_result.value.source == _persistence_source()


def test_provider_readiness_e2e_compositions_are_isolated_by_instance() -> None:
    core = _core("qore-provider-readiness-isolation")
    first = compose_provider_readiness_end_to_end(core, _configuration())
    second = compose_provider_readiness_end_to_end(core, _configuration())

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    save_result = first.value.ports.persistence.save(
        SavePersistenceRequest(
            key=_NEW_KEY,
            version=_VERSION_ZERO,
            value={"first": 1},
            stored_at=_NOW,
        ),
        metadata=_metadata(),
    )
    second_load = second.value.ports.persistence.load(
        LoadPersistenceRequest(_NEW_KEY),
        metadata=_metadata(),
    )

    assert isinstance(save_result, Success)
    assert first.value.core is core
    assert second.value.core is core
    assert first.value.adapters.market_data is not second.value.adapters.market_data
    assert first.value.adapters.persistence is not second.value.adapters.persistence
    assert isinstance(second_load, Success)
    assert second_load.value is None


def test_provider_readiness_e2e_propagates_market_data_failure() -> None:
    configuration = _configuration(
        market_data=_market_configuration(
            quote_payloads=(_quote_payload(bid="not-a-number"),)
        )
    )
    result: Result[
        ProviderReadinessEndToEndComposition[Payload],
        ExternalPortError,
    ] = compose_provider_readiness_end_to_end(_core(), configuration)

    assert isinstance(result, Failure)
    assert isinstance(result.error, IngestionValidationError)
    assert "bid" in str(result.error)


def test_provider_readiness_e2e_propagates_persistence_failure() -> None:
    circuit_breaker = AdapterCircuitBreakerSnapshot(
        state=AdapterCircuitBreakerState.OPEN,
        observed_at=_NOW,
        failure_count=2,
        recovery_delay=AdapterRetryDelay(500),
        message="backend temporarily unavailable",
    )
    configuration = _configuration(
        persistence=_persistence_configuration(
            state=PersistenceBackendHarnessState.UNAVAILABLE,
            circuit_breaker=circuit_breaker,
        )
    )
    result: Result[
        ProviderReadinessEndToEndComposition[Payload],
        ExternalPortError,
    ] = compose_provider_readiness_end_to_end(_core(), configuration)

    assert isinstance(result, Failure)
    assert isinstance(result.error, AdapterResilienceUnavailableError)
    assert "circuit_breaker=open" in str(result.error)


def test_provider_readiness_e2e_propagates_throttling_failure() -> None:
    rate_limit = AdapterRateLimitPolicy(
        request_limit=1,
        window=AdapterRetryDelay(1000),
    )
    configuration = _configuration(
        persistence=_persistence_configuration(
            state=PersistenceBackendHarnessState.THROTTLED,
            rate_limit=rate_limit,
            retry_after=AdapterRetryDelay(750),
        )
    )
    result: Result[
        ProviderReadinessEndToEndComposition[Payload],
        ExternalPortError,
    ] = compose_provider_readiness_end_to_end(_core(), configuration)

    assert isinstance(result, Failure)
    assert isinstance(result.error, AdapterThrottledError)
    assert "retry_after_ms=750" in str(result.error)


def test_provider_readiness_e2e_rejects_runtime_bypasses() -> None:
    with_result: Result[
        ProviderReadinessEndToEndComposition[Payload],
        ExternalPortError,
    ] = compose_provider_readiness_end_to_end(
        cast(CoreApplication, object()),
        _configuration(),
    )
    invalid_configuration: Result[
        ProviderReadinessEndToEndComposition[Payload],
        ExternalPortError,
    ] = compose_provider_readiness_end_to_end(
        _core(),
        cast(ProviderReadinessEndToEndConfiguration[Payload], object()),
    )

    assert isinstance(with_result, Failure)
    assert isinstance(with_result.error, ProviderReadinessEndToEndValidationError)
    assert isinstance(invalid_configuration, Failure)
    assert isinstance(
        invalid_configuration.error,
        ProviderReadinessEndToEndValidationError,
    )


def test_functional_and_specialized_governance_still_compose_without_provider_config() -> None:
    functional = compose_functional_governance(
        Configuration(application_name="qore-functional-after-provider-readiness")
    )
    specialized = compose_specialized_governance(
        Configuration(application_name="qore-specialized-after-provider-readiness")
    )

    assert isinstance(functional, Success)
    assert isinstance(specialized, Success)
    assert len(functional.value.core.runtime_plan.components) == 1
    assert len(specialized.value.core.runtime_plan.components) == 1


def test_provider_readiness_public_exports() -> None:
    import qore.infrastructure as infrastructure

    assert (
        infrastructure.ProviderReadinessEndToEndConfiguration
        is ProviderReadinessEndToEndConfiguration
    )
    assert (
        infrastructure.ProviderReadinessEndToEndComposition
        is ProviderReadinessEndToEndComposition
    )
    assert infrastructure.ProviderReadinessEndToEndError is ProviderReadinessEndToEndError
    assert issubclass(ProviderReadinessEndToEndError, ExternalPortError)
    assert (
        infrastructure.ProviderReadinessEndToEndValidationError
        is ProviderReadinessEndToEndValidationError
    )
    assert (
        infrastructure.compose_provider_readiness_end_to_end
        is compose_provider_readiness_end_to_end
    )
