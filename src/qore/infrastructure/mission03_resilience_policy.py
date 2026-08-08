from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.adapter_resilience import (
    AdapterRateLimitPolicy,
    AdapterRetryDelay,
    AdapterRetryPolicy,
    AdapterTimeoutPolicy,
)
from qore.infrastructure.oanda_practice_configuration import (
    OandaPracticeCapability,
    OandaPracticeRuntimeConfiguration,
)
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success


class Mission03ResiliencePolicyError(ExternalPortError):
    """Base error for MISSION-03 OANDA Practice resilience preparation."""

    __slots__ = ()


class Mission03ResiliencePolicyValidationError(Mission03ResiliencePolicyError):
    """A Practice resilience policy pack violates a fail-closed invariant."""

    __slots__ = ()


class Mission03ResilienceOperation(StrEnum):
    MARKET_READ = "market-read"
    ACCOUNT_READ = "account-read"
    ORDER_CREATE = "order-create"
    ORDER_CANCEL = "order-cancel"


_OPERATION_ORDER: tuple[Mission03ResilienceOperation, ...] = (
    Mission03ResilienceOperation.MARKET_READ,
    Mission03ResilienceOperation.ACCOUNT_READ,
    Mission03ResilienceOperation.ORDER_CREATE,
    Mission03ResilienceOperation.ORDER_CANCEL,
)

_SIDE_EFFECTING_OPERATIONS = frozenset(
    {
        Mission03ResilienceOperation.ORDER_CREATE,
        Mission03ResilienceOperation.ORDER_CANCEL,
    }
)


@dataclass(frozen=True, slots=True)
class Mission03OperationResiliencePolicy:
    """Explicit timeout/retry/rate-limit declaration for one Practice operation."""

    operation: Mission03ResilienceOperation
    timeout: AdapterTimeoutPolicy
    retry: AdapterRetryPolicy
    rate_limit: AdapterRateLimitPolicy

    def __post_init__(self) -> None:
        if not isinstance(self.operation, Mission03ResilienceOperation):
            raise Mission03ResiliencePolicyValidationError(
                "MISSION-03 resilience operation must be explicit"
            )
        if not isinstance(self.timeout, AdapterTimeoutPolicy):
            raise Mission03ResiliencePolicyValidationError(
                "MISSION-03 resilience operation requires AdapterTimeoutPolicy"
            )
        if not isinstance(self.retry, AdapterRetryPolicy):
            raise Mission03ResiliencePolicyValidationError(
                "MISSION-03 resilience operation requires AdapterRetryPolicy"
            )
        if not isinstance(self.rate_limit, AdapterRateLimitPolicy):
            raise Mission03ResiliencePolicyValidationError(
                "MISSION-03 resilience operation requires AdapterRateLimitPolicy"
            )
        if self.operation in _SIDE_EFFECTING_OPERATIONS and self.retry.retries_enabled:
            raise Mission03ResiliencePolicyValidationError(
                "side-effecting Practice execution operations must not retry automatically"
            )

    @property
    def side_effecting(self) -> bool:
        return self.operation in _SIDE_EFFECTING_OPERATIONS

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.operation.value,
            self.side_effecting,
            self.timeout.logical_values(),
            self.retry.logical_values(),
            self.rate_limit.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class Mission03ResiliencePolicyPack:
    """Complete deterministic resilience preparation for the selected Practice boundary."""

    provider_key: str
    environment: str
    operations: tuple[Mission03OperationResiliencePolicy, ...]

    def __post_init__(self) -> None:
        if self.provider_key != "oanda-v20":
            raise Mission03ResiliencePolicyValidationError(
                "MISSION-03 resilience provider must be oanda-v20"
            )
        if self.environment != "demo":
            raise Mission03ResiliencePolicyValidationError(
                "MISSION-03 resilience environment must be demo"
            )
        if not isinstance(self.operations, tuple):
            raise Mission03ResiliencePolicyValidationError(
                "MISSION-03 resilience operations must be immutable tuple"
            )
        if any(
            not isinstance(item, Mission03OperationResiliencePolicy)
            for item in self.operations
        ):
            raise Mission03ResiliencePolicyValidationError(
                "MISSION-03 resilience operations must use typed policies"
            )
        if tuple(item.operation for item in self.operations) != _OPERATION_ORDER:
            raise Mission03ResiliencePolicyValidationError(
                "MISSION-03 resilience pack must contain every operation exactly once"
            )
        if any(item.retry.retries_enabled for item in self.operations):
            raise Mission03ResiliencePolicyValidationError(
                "MISSION-03 preparation keeps automatic retries disabled for all operations"
            )

    @property
    def automatic_retries_enabled(self) -> bool:
        return False

    @property
    def operationally_resilient(self) -> bool:
        """Policy preparation cannot close Gate #12 by itself."""
        return False

    def policy_for(
        self,
        operation: Mission03ResilienceOperation,
    ) -> Mission03OperationResiliencePolicy:
        if not isinstance(operation, Mission03ResilienceOperation):
            raise Mission03ResiliencePolicyValidationError(
                "resilience policy lookup requires Mission03ResilienceOperation"
            )
        for policy in self.operations:
            if policy.operation is operation:
                return policy
        raise Mission03ResiliencePolicyValidationError(
            "required resilience operation policy is missing"
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.provider_key,
            self.environment,
            tuple(item.logical_values() for item in self.operations),
            self.automatic_retries_enabled,
            self.operationally_resilient,
        )


def build_mission03_resilience_policy_pack(
    configuration: OandaPracticeRuntimeConfiguration,
) -> Result[Mission03ResiliencePolicyPack, Mission03ResiliencePolicyError]:
    """Build the current conservative Practice policy pack without runtime behavior."""

    if not isinstance(configuration, OandaPracticeRuntimeConfiguration):
        return Failure(
            Mission03ResiliencePolicyValidationError(
                "MISSION-03 resilience requires OandaPracticeRuntimeConfiguration"
            )
        )
    required_capabilities = {
        OandaPracticeCapability.ACCOUNT,
        OandaPracticeCapability.ORDERS,
        OandaPracticeCapability.PRICING,
    }
    if not required_capabilities.issubset(set(configuration.capabilities)):
        return Failure(
            Mission03ResiliencePolicyValidationError(
                "Practice configuration lacks required read/execution capabilities"
            )
        )
    timeout = AdapterTimeoutPolicy(
        operation_timeout=AdapterRetryDelay(
            milliseconds=configuration.rest_timeout.milliseconds
        )
    )
    no_retry = AdapterRetryPolicy(max_attempts=1)
    rate_limit = AdapterRateLimitPolicy(
        request_limit=configuration.limits.rest_requests_per_second,
        window=AdapterRetryDelay(milliseconds=1000),
        burst_capacity=configuration.limits.rest_requests_per_second,
    )
    try:
        pack = Mission03ResiliencePolicyPack(
            provider_key=configuration.provider_key,
            environment=configuration.environment.value,
            operations=tuple(
                Mission03OperationResiliencePolicy(
                    operation=operation,
                    timeout=timeout,
                    retry=no_retry,
                    rate_limit=rate_limit,
                )
                for operation in _OPERATION_ORDER
            ),
        )
    except (Mission03ResiliencePolicyError, ExternalPortError) as error:
        if isinstance(error, Mission03ResiliencePolicyError):
            return Failure(error)
        return Failure(Mission03ResiliencePolicyValidationError(str(error)))
    return Success(pack)
