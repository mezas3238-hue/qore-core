from __future__ import annotations

import pytest

from qore.infrastructure.adapter_configuration import AdapterSecretRequirements
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.oanda_practice_configuration import (
    OandaPracticeCapability,
    OandaPracticeConfigurationError,
    OandaPracticeConfigurationValidationError,
    OandaPracticeOperationalLimits,
    OandaPracticeRuntimeConfiguration,
    oanda_practice_secret_requirements,
)
from qore.infrastructure.ports import ExternalPortError
from qore.infrastructure.transport import ExternalTransportTimeout


def _account(
    *,
    provider_key: str = "oanda-v20",
    environment: MarketRuntimeEnvironment = MarketRuntimeEnvironment.DEMO,
) -> MarketTestAccountIdentity:
    return MarketTestAccountIdentity(
        provider_key=provider_key,
        account_ref="practice-001",
        environment=environment,
    )


def _limits(
    *,
    rest_requests_per_second: int = 60,
    active_streams: int = 2,
    new_connections_per_second: int = 1,
) -> OandaPracticeOperationalLimits:
    return OandaPracticeOperationalLimits(
        rest_requests_per_second=rest_requests_per_second,
        active_streams=active_streams,
        new_connections_per_second=new_connections_per_second,
    )


def _configuration(
    *,
    provider_key: str = "oanda-v20",
    environment: MarketRuntimeEnvironment = MarketRuntimeEnvironment.DEMO,
    rest_endpoint: ProviderEndpoint | None = None,
    streaming_endpoint: ProviderEndpoint | None = None,
    account: MarketTestAccountIdentity | None = None,
    symbols: tuple[str, ...] = ("EUR_USD", "GBP_USD"),
    capabilities: tuple[OandaPracticeCapability, ...] = (
        OandaPracticeCapability.ACCOUNT,
        OandaPracticeCapability.ORDERS,
        OandaPracticeCapability.PRICING,
        OandaPracticeCapability.TRANSACTIONS,
    ),
    rest_timeout: ExternalTransportTimeout | None = None,
    stream_connect_timeout: ExternalTransportTimeout | None = None,
    limits: OandaPracticeOperationalLimits | None = None,
    secret_requirements: AdapterSecretRequirements | None = None,
) -> OandaPracticeRuntimeConfiguration:
    return OandaPracticeRuntimeConfiguration(
        provider_key=provider_key,
        environment=environment,
        rest_endpoint=rest_endpoint
        or ProviderEndpoint(host="api-fxpractice.oanda.com"),
        streaming_endpoint=streaming_endpoint
        or ProviderEndpoint(host="stream-fxpractice.oanda.com"),
        account=account or _account(environment=environment),
        symbols=symbols,
        capabilities=capabilities,
        rest_timeout=rest_timeout or ExternalTransportTimeout(milliseconds=3000),
        stream_connect_timeout=stream_connect_timeout
        or ExternalTransportTimeout(milliseconds=5000),
        limits=limits or _limits(),
        secret_requirements=secret_requirements
        or oanda_practice_secret_requirements(),
    )


def test_oanda_practice_configuration_is_canonical_and_secret_free() -> None:
    configuration = _configuration()

    assert configuration.provider_key == "oanda-v20"
    assert configuration.environment is MarketRuntimeEnvironment.DEMO
    assert configuration.rest_endpoint.origin == "https://api-fxpractice.oanda.com"
    assert (
        configuration.streaming_endpoint.origin
        == "https://stream-fxpractice.oanda.com"
    )
    assert configuration.symbols == ("EUR_USD", "GBP_USD")
    assert configuration.secret_requirements.logical_values() == (
        ("oanda-personal-access-token", True),
    )
    assert configuration.logical_values() == configuration.logical_values()
    assert "Bearer " not in repr(configuration)


def test_configuration_errors_remain_typed_external_port_errors() -> None:
    assert issubclass(OandaPracticeConfigurationError, ExternalPortError)
    assert issubclass(
        OandaPracticeConfigurationValidationError,
        OandaPracticeConfigurationError,
    )


def test_configuration_rejects_production_rest_endpoint() -> None:
    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="approved OANDA fxTrade Practice host",
    ):
        _configuration(
            rest_endpoint=ProviderEndpoint(host="api-fxtrade.oanda.com")
        )


def test_configuration_rejects_production_streaming_endpoint() -> None:
    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="approved OANDA fxTrade Practice host",
    ):
        _configuration(
            streaming_endpoint=ProviderEndpoint(host="stream-fxtrade.oanda.com")
        )


def test_configuration_rejects_non_demo_environment() -> None:
    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="map exclusively to DEMO",
    ):
        _configuration(environment=MarketRuntimeEnvironment.TEST)


def test_configuration_rejects_account_provider_mismatch() -> None:
    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="account provider_key",
    ):
        _configuration(account=_account(provider_key="other-provider"))


def test_configuration_rejects_unsorted_duplicate_or_invalid_symbols() -> None:
    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="stable sorted order",
    ):
        _configuration(symbols=("GBP_USD", "EUR_USD"))

    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="duplicates",
    ):
        _configuration(symbols=("EUR_USD", "EUR_USD"))

    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="currency-pair syntax",
    ):
        _configuration(symbols=("EURUSD",))


def test_configuration_requires_mission_capabilities_in_stable_order() -> None:
    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="account, orders, pricing and transactions",
    ):
        _configuration(
            capabilities=(
                OandaPracticeCapability.ACCOUNT,
                OandaPracticeCapability.PRICING,
            )
        )

    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="stable sorted order",
    ):
        _configuration(
            capabilities=(
                OandaPracticeCapability.PRICING,
                OandaPracticeCapability.ACCOUNT,
                OandaPracticeCapability.ORDERS,
                OandaPracticeCapability.TRANSACTIONS,
            )
        )


def test_configuration_rejects_missing_or_extra_secret_requirements() -> None:
    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="exactly one personal access token reference",
    ):
        _configuration(secret_requirements=AdapterSecretRequirements())


def test_operational_limits_are_strict_and_provider_bounded() -> None:
    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="rest_requests_per_second must be an int",
    ):
        OandaPracticeOperationalLimits(
            rest_requests_per_second=True,
            active_streams=1,
            new_connections_per_second=1,
        )

    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="OANDA ceiling",
    ):
        _limits(rest_requests_per_second=121)

    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="OANDA ceiling",
    ):
        _limits(active_streams=21)

    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="OANDA ceiling",
    ):
        _limits(new_connections_per_second=3)


def test_pricing_stream_capability_requires_nonzero_stream_budget() -> None:
    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="requires at least one active stream",
    ):
        _configuration(
            capabilities=(
                OandaPracticeCapability.ACCOUNT,
                OandaPracticeCapability.ORDERS,
                OandaPracticeCapability.PRICING,
                OandaPracticeCapability.PRICING_STREAM,
                OandaPracticeCapability.TRANSACTIONS,
            ),
            limits=_limits(active_streams=0),
        )


def test_configuration_rejects_noncanonical_endpoint_shape() -> None:
    with pytest.raises(
        OandaPracticeConfigurationValidationError,
        match="HTTPS port 443 and root base path",
    ):
        _configuration(
            rest_endpoint=ProviderEndpoint(
                host="api-fxpractice.oanda.com",
                port=8443,
            )
        )
