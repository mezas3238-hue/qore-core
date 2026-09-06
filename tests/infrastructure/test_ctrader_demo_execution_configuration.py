from __future__ import annotations

from decimal import Decimal

import pytest

from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoCapability,
    CTraderDemoConfigurationValidationError,
    CTraderDemoOperationalLimits,
    CTraderDemoRuntimeConfiguration,
    CTraderSymbolMapping,
    ctrader_demo_secret_requirements,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import ExecutionInstrument
from qore.infrastructure.transport import ExternalTransportTimeout


def _account(
    *,
    environment: MarketRuntimeEnvironment = MarketRuntimeEnvironment.DEMO,
    account_ref: str = "demo-001",
) -> MarketTestAccountIdentity:
    return MarketTestAccountIdentity(
        provider_key="ctrader-demo",
        account_ref=account_ref,
        environment=environment,
    )


def _mapping(*, instrument: str = "EURUSD") -> CTraderSymbolMapping:
    return CTraderSymbolMapping(
        instrument=ExecutionInstrument(instrument),
        symbol_id=1234,
        symbol_name=instrument,
        digits=5,
        volume_step=Decimal("1"),
        min_volume_units=1,
        max_volume_units=1_000_000,
        step_volume_units=1,
    )


def _configuration(
    *,
    account: MarketTestAccountIdentity | None = None,
    environment: MarketRuntimeEnvironment = MarketRuntimeEnvironment.DEMO,
    endpoint: ProviderEndpoint | None = None,
    mappings: tuple[CTraderSymbolMapping, ...] | None = None,
    capabilities: tuple[CTraderDemoCapability, ...] | None = None,
) -> CTraderDemoRuntimeConfiguration:
    return CTraderDemoRuntimeConfiguration(
        provider_key="ctrader-demo",
        environment=environment,
        endpoint=endpoint or ProviderEndpoint(host="demo.ctraderapi.com", port=5035),
        account=account or _account(),
        symbol_mappings=mappings or (_mapping(),),
        capabilities=capabilities or (CTraderDemoCapability.ACCOUNT, CTraderDemoCapability.ORDERS),
        rest_timeout=ExternalTransportTimeout(milliseconds=3000),
        limits=CTraderDemoOperationalLimits(order_requests_per_second=1),
        secret_requirements=ctrader_demo_secret_requirements(),
    )


def test_valid_demo_configuration_is_accepted() -> None:
    configuration = _configuration()
    assert configuration.symbol_mapping(ExecutionInstrument("EURUSD")) == _mapping()
    assert configuration.logical_values() == configuration.logical_values()


def test_live_environment_fails_closed() -> None:
    with pytest.raises(CTraderDemoConfigurationValidationError):
        _configuration(environment=MarketRuntimeEnvironment.PRODUCTION)


def test_test_environment_is_rejected_for_execution() -> None:
    with pytest.raises(CTraderDemoConfigurationValidationError):
        _configuration(environment=MarketRuntimeEnvironment.TEST)


def test_wrong_provider_key_is_rejected() -> None:
    with pytest.raises(CTraderDemoConfigurationValidationError):
        CTraderDemoRuntimeConfiguration(
            provider_key="ctrader-live",
            environment=MarketRuntimeEnvironment.DEMO,
            endpoint=ProviderEndpoint(host="demo.ctraderapi.com", port=5035),
            account=_account(),
            symbol_mappings=(_mapping(),),
            capabilities=(
                CTraderDemoCapability.ACCOUNT,
                CTraderDemoCapability.ORDERS,
            ),
            rest_timeout=ExternalTransportTimeout(milliseconds=3000),
            limits=CTraderDemoOperationalLimits(order_requests_per_second=1),
            secret_requirements=ctrader_demo_secret_requirements(),
        )


def test_wrong_endpoint_host_is_rejected() -> None:
    with pytest.raises(CTraderDemoConfigurationValidationError):
        _configuration(endpoint=ProviderEndpoint(host="live.ctrader.com"))


def test_account_must_match_provider_and_environment() -> None:
    mismatched = MarketTestAccountIdentity(
        provider_key="oanda-v20",
        account_ref="demo-001",
        environment=MarketRuntimeEnvironment.DEMO,
    )
    with pytest.raises(CTraderDemoConfigurationValidationError):
        _configuration(account=mismatched)


def test_duplicate_symbol_ids_are_rejected() -> None:
    mappings = (
        CTraderSymbolMapping(
            instrument=ExecutionInstrument("EURUSD"),
            symbol_id=1234,
            symbol_name="EURUSD",
            digits=5,
            volume_step=Decimal("1"),
            min_volume_units=1,
            max_volume_units=1_000_000,
            step_volume_units=1,
        ),
        CTraderSymbolMapping(
            instrument=ExecutionInstrument("GBPUSD"),
            symbol_id=1234,
            symbol_name="GBPUSD",
            digits=5,
            volume_step=Decimal("1"),
            min_volume_units=1,
            max_volume_units=1_000_000,
            step_volume_units=1,
        ),
    )
    with pytest.raises(CTraderDemoConfigurationValidationError):
        _configuration(mappings=mappings)


def test_missing_orders_capability_is_rejected() -> None:
    with pytest.raises(CTraderDemoConfigurationValidationError):
        _configuration(capabilities=(CTraderDemoCapability.ACCOUNT,))


def test_duplicate_capabilities_are_rejected() -> None:
    with pytest.raises(CTraderDemoConfigurationValidationError):
        _configuration(
            capabilities=(
                CTraderDemoCapability.ACCOUNT,
                CTraderDemoCapability.ACCOUNT,
                CTraderDemoCapability.ORDERS,
            )
        )


def test_symbol_mapping_rejects_invalid_volume_step() -> None:
    with pytest.raises(CTraderDemoConfigurationValidationError):
        CTraderSymbolMapping(
            instrument=ExecutionInstrument("EURUSD"),
            symbol_id=1234,
            symbol_name="EURUSD",
            digits=5,
            volume_step=Decimal("0"),
            min_volume_units=1,
            max_volume_units=1_000_000,
            step_volume_units=1,
        )


def test_secret_requirements_are_non_secret_and_stable() -> None:
    first = ctrader_demo_secret_requirements()
    second = ctrader_demo_secret_requirements()
    assert first == second
    assert first.requirements[0].name.value == "ctrader-demo-access-token"
    assert first.requirements[0].required is True
    assert first.logical_values() == (
        ("ctrader-demo-access-token", True),
        ("ctrader-demo-client-id", True),
        ("ctrader-demo-client-secret", True),
        ("ctrader-demo-refresh-token", True),
    )
