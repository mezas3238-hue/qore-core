from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.adapter_resilience import (
    AdapterRateLimitPolicy,
    AdapterRetryDelay,
    AdapterRetryPolicy,
    AdapterRetryableFailure,
    AdapterTimeoutPolicy,
)
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.mission03_resilience_policy import (
    Mission03OperationResiliencePolicy,
    Mission03ResilienceOperation,
    Mission03ResiliencePolicyPack,
    Mission03ResiliencePolicyValidationError,
    build_mission03_resilience_policy_pack,
)
from qore.infrastructure.oanda_practice_configuration import (
    OandaPracticeCapability,
    OandaPracticeOperationalLimits,
    OandaPracticeRuntimeConfiguration,
    oanda_practice_secret_requirements,
)
from qore.infrastructure.transport import ExternalTransportTimeout
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 9, 1, 0, tzinfo=UTC)


def _configuration(
    *,
    capabilities: tuple[OandaPracticeCapability, ...] | None = None,
) -> OandaPracticeRuntimeConfiguration:
    return OandaPracticeRuntimeConfiguration(
        provider_key="oanda-v20",
        environment=MarketRuntimeEnvironment.DEMO,
        rest_endpoint=ProviderEndpoint(host="api-fxpractice.oanda.com"),
        streaming_endpoint=ProviderEndpoint(host="stream-fxpractice.oanda.com"),
        account=MarketTestAccountIdentity(
            provider_key="oanda-v20",
            account_ref="practice-001",
            environment=MarketRuntimeEnvironment.DEMO,
        ),
        symbols=("EUR_USD", "GBP_USD"),
        capabilities=(
            capabilities
            if capabilities is not None
            else (
                OandaPracticeCapability.ACCOUNT,
                OandaPracticeCapability.ORDERS,
                OandaPracticeCapability.PRICING,
                OandaPracticeCapability.TRANSACTIONS,
            )
        ),
        rest_timeout=ExternalTransportTimeout(milliseconds=3000),
        stream_connect_timeout=ExternalTransportTimeout(milliseconds=5000),
        limits=OandaPracticeOperationalLimits(
            rest_requests_per_second=1,
            active_streams=0,
            new_connections_per_second=1,
        ),
        secret_requirements=oanda_practice_secret_requirements(),
    )


def test_pack_contains_every_operation_once_with_explicit_limits() -> None:
    result = build_mission03_resilience_policy_pack(_configuration())

    assert isinstance(result, Success)
    pack = result.value
    assert tuple(item.operation for item in pack.operations) == (
        Mission03ResilienceOperation.MARKET_READ,
        Mission03ResilienceOperation.ACCOUNT_READ,
        Mission03ResilienceOperation.ORDER_CREATE,
        Mission03ResilienceOperation.ORDER_CANCEL,
    )
    assert pack.provider_key == "oanda-v20"
    assert pack.environment == "demo"
    assert pack.automatic_retries_enabled is False
    assert pack.operationally_resilient is False
    assert pack.logical_values() == pack.logical_values()
    for policy in pack.operations:
        assert policy.timeout.operation_timeout.milliseconds == 3000
        assert policy.retry.max_attempts == 1
        assert policy.retry.retries_enabled is False
        assert policy.retry.delay_schedule == ()
        assert policy.retry.retryable_failures == ()
        assert policy.rate_limit.request_limit == 1
        assert policy.rate_limit.window.milliseconds == 1000
        assert policy.rate_limit.burst_capacity == 1


def test_execution_operations_are_explicitly_side_effecting_and_non_retrying() -> None:
    result = build_mission03_resilience_policy_pack(_configuration())
    assert isinstance(result, Success)

    create = result.value.policy_for(Mission03ResilienceOperation.ORDER_CREATE)
    cancel = result.value.policy_for(Mission03ResilienceOperation.ORDER_CANCEL)
    market = result.value.policy_for(Mission03ResilienceOperation.MARKET_READ)

    assert create.side_effecting is True
    assert cancel.side_effecting is True
    assert market.side_effecting is False
    assert create.retry.retries_enabled is False
    assert cancel.retry.retries_enabled is False


def test_side_effecting_policy_rejects_automatic_retry() -> None:
    with pytest.raises(Mission03ResiliencePolicyValidationError):
        Mission03OperationResiliencePolicy(
            operation=Mission03ResilienceOperation.ORDER_CREATE,
            timeout=AdapterTimeoutPolicy(
                operation_timeout=AdapterRetryDelay(milliseconds=3000)
            ),
            retry=AdapterRetryPolicy(
                max_attempts=2,
                delay_schedule=(AdapterRetryDelay(milliseconds=100),),
                retryable_failures=(AdapterRetryableFailure.TIMEOUT,),
            ),
            rate_limit=AdapterRateLimitPolicy(
                request_limit=1,
                window=AdapterRetryDelay(milliseconds=1000),
                burst_capacity=1,
            ),
        )


def test_pack_rejects_retry_even_for_reads_during_current_preparation() -> None:
    timeout = AdapterTimeoutPolicy(
        operation_timeout=AdapterRetryDelay(milliseconds=3000)
    )
    rate_limit = AdapterRateLimitPolicy(
        request_limit=1,
        window=AdapterRetryDelay(milliseconds=1000),
        burst_capacity=1,
    )
    read_retry = AdapterRetryPolicy(
        max_attempts=2,
        delay_schedule=(AdapterRetryDelay(milliseconds=100),),
        retryable_failures=(AdapterRetryableFailure.UNAVAILABLE,),
    )
    no_retry = AdapterRetryPolicy(max_attempts=1)

    with pytest.raises(Mission03ResiliencePolicyValidationError):
        Mission03ResiliencePolicyPack(
            provider_key="oanda-v20",
            environment="demo",
            operations=(
                Mission03OperationResiliencePolicy(
                    operation=Mission03ResilienceOperation.MARKET_READ,
                    timeout=timeout,
                    retry=read_retry,
                    rate_limit=rate_limit,
                ),
                Mission03OperationResiliencePolicy(
                    operation=Mission03ResilienceOperation.ACCOUNT_READ,
                    timeout=timeout,
                    retry=no_retry,
                    rate_limit=rate_limit,
                ),
                Mission03OperationResiliencePolicy(
                    operation=Mission03ResilienceOperation.ORDER_CREATE,
                    timeout=timeout,
                    retry=no_retry,
                    rate_limit=rate_limit,
                ),
                Mission03OperationResiliencePolicy(
                    operation=Mission03ResilienceOperation.ORDER_CANCEL,
                    timeout=timeout,
                    retry=no_retry,
                    rate_limit=rate_limit,
                ),
            ),
        )


def test_pack_requires_account_pricing_and_orders_capabilities() -> None:
    result = build_mission03_resilience_policy_pack(
        _configuration(
            capabilities=(
                OandaPracticeCapability.ACCOUNT,
                OandaPracticeCapability.PRICING,
            )
        )
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, Mission03ResiliencePolicyValidationError)


def test_pack_is_demo_only_and_lookup_is_typed() -> None:
    result = build_mission03_resilience_policy_pack(_configuration())
    assert isinstance(result, Success)

    with pytest.raises(Mission03ResiliencePolicyValidationError):
        Mission03ResiliencePolicyPack(
            provider_key="oanda-v20",
            environment="production",
            operations=result.value.operations,
        )

    with pytest.raises(Mission03ResiliencePolicyValidationError):
        result.value.policy_for("order-create")


def test_no_runtime_clock_or_sleep_is_embedded_in_policy_values() -> None:
    result = build_mission03_resilience_policy_pack(_configuration())
    assert isinstance(result, Success)

    values = repr(result.value.logical_values()).lower()
    assert "sleep" not in values
    assert "token" not in values
    assert "practice-001" not in values
    assert _NOW.tzinfo is UTC
