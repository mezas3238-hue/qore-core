from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoCapability,
    CTraderDemoOperationalLimits,
    CTraderDemoRuntimeConfiguration,
    CTraderSymbolMapping,
    ctrader_demo_secret_requirements,
)
from qore.infrastructure.ctrader_demo_risk_operational_runtime import (
    CTraderDemoRiskOperationalRuntimeError,
    validate_ctrader_authorized_quantity,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import (
    ExecutionInstrument,
    OrderQuantity,
)
from qore.infrastructure.risk_authority import RiskAuthorization
from qore.infrastructure.transport import ExternalTransportTimeout
from qore.kernel.result import Failure, Success

_ACCOUNT = MarketTestAccountIdentity(
    provider_key="ctrader-demo",
    account_ref="424242",
    environment=MarketRuntimeEnvironment.DEMO,
)


def _configuration() -> CTraderDemoRuntimeConfiguration:
    return CTraderDemoRuntimeConfiguration(
        provider_key="ctrader-demo",
        environment=MarketRuntimeEnvironment.DEMO,
        endpoint=ProviderEndpoint(host="demo.ctraderapi.com", port=5035),
        account=_ACCOUNT,
        symbol_mappings=(
            CTraderSymbolMapping(
                instrument=ExecutionInstrument("EURUSD"),
                symbol_id=1,
                symbol_name="EURUSD",
                digits=5,
                volume_step=Decimal("0.01"),
                min_volume_units=1000,
                max_volume_units=1_000_000,
                step_volume_units=1000,
            ),
        ),
        capabilities=(
            CTraderDemoCapability.ACCOUNT,
            CTraderDemoCapability.ORDERS,
        ),
        rest_timeout=ExternalTransportTimeout(milliseconds=3000),
        limits=CTraderDemoOperationalLimits(order_requests_per_second=1),
        secret_requirements=ctrader_demo_secret_requirements(),
    )


def _authorization(quantity: str) -> RiskAuthorization:
    authorization = object.__new__(RiskAuthorization)
    object.__setattr__(authorization, "instrument", ExecutionInstrument("EURUSD"))
    object.__setattr__(authorization, "authorized_quantity", OrderQuantity(Decimal(quantity)))
    return authorization


def test_exact_broker_minimum_is_accepted() -> None:
    result = validate_ctrader_authorized_quantity(
        _configuration(),
        _authorization("10.00"),
    )

    assert isinstance(result, Success)


def test_reduce_below_broker_minimum_is_rejected_before_execution() -> None:
    result = validate_ctrader_authorized_quantity(
        _configuration(),
        _authorization("9.99"),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoRiskOperationalRuntimeError)
    assert "volume bounds" in str(result.error)


def test_reduce_not_aligned_to_broker_step_is_rejected() -> None:
    result = validate_ctrader_authorized_quantity(
        _configuration(),
        _authorization("15.00"),
    )

    assert isinstance(result, Failure)
    assert "stepVolume" in str(result.error)


def test_unmapped_risk_instrument_is_rejected() -> None:
    authorization = _authorization("10.00")
    object.__setattr__(authorization, "instrument", ExecutionInstrument("GBPUSD"))

    result = validate_ctrader_authorized_quantity(_configuration(), authorization)

    assert isinstance(result, Failure)
    assert "not mapped" in str(result.error)
