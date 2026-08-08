from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.adapter_configuration import (
    AdapterSecretName,
    AdapterSecretRequirement,
    AdapterSecretRequirements,
)
from qore.infrastructure.connectivity import ProviderEndpoint
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.ports import ExternalPortError
from qore.infrastructure.transport import ExternalTransportTimeout

_OANDA_PROVIDER_KEY = "oanda-v20"
_OANDA_PRACTICE_REST_HOST = "api-fxpractice.oanda.com"
_OANDA_PRACTICE_STREAM_HOST = "stream-fxpractice.oanda.com"
_OANDA_PERSONAL_ACCESS_TOKEN_NAME = "oanda-personal-access-token"
_OANDA_MAX_REST_REQUESTS_PER_SECOND = 120
_OANDA_MAX_ACTIVE_STREAMS = 20
_OANDA_MAX_NEW_CONNECTIONS_PER_SECOND = 2


class OandaPracticeConfigurationError(ExternalPortError):
    """Base error for OANDA v20 Practice runtime configuration."""

    __slots__ = ()


class OandaPracticeConfigurationValidationError(OandaPracticeConfigurationError):
    """Violation of an OANDA Practice configuration invariant."""

    __slots__ = ()


class OandaPracticeCapability(StrEnum):
    """Provider-specific capabilities selected for OANDA Practice composition."""

    ACCOUNT = "account"
    CANDLES = "candles"
    ORDERS = "orders"
    PRICING = "pricing"
    PRICING_STREAM = "pricing_stream"
    TRANSACTIONS = "transactions"


_REQUIRED_CAPABILITIES = frozenset(
    {
        OandaPracticeCapability.ACCOUNT,
        OandaPracticeCapability.ORDERS,
        OandaPracticeCapability.PRICING,
        OandaPracticeCapability.TRANSACTIONS,
    }
)


def oanda_practice_secret_requirements() -> AdapterSecretRequirements:
    """Declare the required credential name without resolving secret material."""
    return AdapterSecretRequirements(
        (
            AdapterSecretRequirement(
                name=AdapterSecretName(_OANDA_PERSONAL_ACCESS_TOKEN_NAME),
                required=True,
            ),
        )
    )


def _validate_practice_endpoint(
    endpoint: ProviderEndpoint,
    *,
    expected_host: str,
    field_name: str,
) -> None:
    if not isinstance(endpoint, ProviderEndpoint):
        raise OandaPracticeConfigurationValidationError(
            f"{field_name} must be ProviderEndpoint"
        )
    if endpoint.host != expected_host:
        raise OandaPracticeConfigurationValidationError(
            f"{field_name} must use the approved OANDA fxTrade Practice host"
        )
    if endpoint.port != 443 or endpoint.base_path != "/":
        raise OandaPracticeConfigurationValidationError(
            f"{field_name} must use HTTPS port 443 and root base path"
        )


@dataclass(frozen=True, slots=True)
class OandaPracticeOperationalLimits:
    """Explicit QORE limits bounded by documented OANDA provider ceilings."""

    rest_requests_per_second: int
    active_streams: int
    new_connections_per_second: int

    def __post_init__(self) -> None:
        if type(self.rest_requests_per_second) is not int:
            raise OandaPracticeConfigurationValidationError(
                "rest_requests_per_second must be an int"
            )
        if type(self.active_streams) is not int:
            raise OandaPracticeConfigurationValidationError(
                "active_streams must be an int"
            )
        if type(self.new_connections_per_second) is not int:
            raise OandaPracticeConfigurationValidationError(
                "new_connections_per_second must be an int"
            )
        if not 1 <= self.rest_requests_per_second <= _OANDA_MAX_REST_REQUESTS_PER_SECOND:
            raise OandaPracticeConfigurationValidationError(
                "rest_requests_per_second must be between 1 and the OANDA ceiling"
            )
        if not 0 <= self.active_streams <= _OANDA_MAX_ACTIVE_STREAMS:
            raise OandaPracticeConfigurationValidationError(
                "active_streams must be between 0 and the OANDA ceiling"
            )
        if not (
            1
            <= self.new_connections_per_second
            <= _OANDA_MAX_NEW_CONNECTIONS_PER_SECOND
        ):
            raise OandaPracticeConfigurationValidationError(
                "new_connections_per_second must be between 1 and the OANDA ceiling"
            )

    def logical_values(self) -> tuple[int, int, int]:
        return (
            self.rest_requests_per_second,
            self.active_streams,
            self.new_connections_per_second,
        )


@dataclass(frozen=True, slots=True)
class OandaPracticeRuntimeConfiguration:
    """Immutable provider-specific configuration for OANDA v20 fxTrade Practice."""

    provider_key: str
    environment: MarketRuntimeEnvironment
    rest_endpoint: ProviderEndpoint
    streaming_endpoint: ProviderEndpoint
    account: MarketTestAccountIdentity
    symbols: tuple[str, ...]
    capabilities: tuple[OandaPracticeCapability, ...]
    rest_timeout: ExternalTransportTimeout
    stream_connect_timeout: ExternalTransportTimeout
    limits: OandaPracticeOperationalLimits
    secret_requirements: AdapterSecretRequirements

    def __post_init__(self) -> None:
        if self.provider_key != _OANDA_PROVIDER_KEY:
            raise OandaPracticeConfigurationValidationError(
                "provider_key must identify the approved OANDA v20 provider"
            )
        if not isinstance(self.environment, MarketRuntimeEnvironment):
            raise OandaPracticeConfigurationValidationError(
                "environment must be MarketRuntimeEnvironment"
            )
        if self.environment is not MarketRuntimeEnvironment.DEMO:
            raise OandaPracticeConfigurationValidationError(
                "OANDA fxTrade Practice must map exclusively to DEMO"
            )
        _validate_practice_endpoint(
            self.rest_endpoint,
            expected_host=_OANDA_PRACTICE_REST_HOST,
            field_name="rest_endpoint",
        )
        _validate_practice_endpoint(
            self.streaming_endpoint,
            expected_host=_OANDA_PRACTICE_STREAM_HOST,
            field_name="streaming_endpoint",
        )
        if not isinstance(self.account, MarketTestAccountIdentity):
            raise OandaPracticeConfigurationValidationError(
                "account must be MarketTestAccountIdentity"
            )
        if self.account.provider_key != self.provider_key:
            raise OandaPracticeConfigurationValidationError(
                "account provider_key must match runtime provider_key"
            )
        if self.account.environment is not self.environment:
            raise OandaPracticeConfigurationValidationError(
                "account environment must match OANDA Practice DEMO environment"
            )
        if not isinstance(self.symbols, tuple) or not self.symbols:
            raise OandaPracticeConfigurationValidationError(
                "symbols must be a non-empty tuple"
            )
        if any(
            not isinstance(symbol, str)
            or fullmatch(r"[A-Z]{3}_[A-Z]{3}", symbol) is None
            for symbol in self.symbols
        ):
            raise OandaPracticeConfigurationValidationError(
                "symbols must use canonical OANDA currency-pair syntax"
            )
        if len(set(self.symbols)) != len(self.symbols):
            raise OandaPracticeConfigurationValidationError(
                "symbols must not contain duplicates"
            )
        if tuple(sorted(self.symbols)) != self.symbols:
            raise OandaPracticeConfigurationValidationError(
                "symbols must use stable sorted order"
            )
        if not isinstance(self.capabilities, tuple):
            raise OandaPracticeConfigurationValidationError(
                "capabilities must be a tuple"
            )
        if any(
            not isinstance(capability, OandaPracticeCapability)
            for capability in self.capabilities
        ):
            raise OandaPracticeConfigurationValidationError(
                "capabilities entries must be OandaPracticeCapability"
            )
        if len(set(self.capabilities)) != len(self.capabilities):
            raise OandaPracticeConfigurationValidationError(
                "capabilities must not contain duplicates"
            )
        if tuple(sorted(self.capabilities, key=lambda item: item.value)) != self.capabilities:
            raise OandaPracticeConfigurationValidationError(
                "capabilities must use stable sorted order"
            )
        if not _REQUIRED_CAPABILITIES.issubset(self.capabilities):
            raise OandaPracticeConfigurationValidationError(
                "capabilities must include account, orders, pricing and transactions"
            )
        if not isinstance(self.rest_timeout, ExternalTransportTimeout):
            raise OandaPracticeConfigurationValidationError(
                "rest_timeout must be ExternalTransportTimeout"
            )
        if not isinstance(self.stream_connect_timeout, ExternalTransportTimeout):
            raise OandaPracticeConfigurationValidationError(
                "stream_connect_timeout must be ExternalTransportTimeout"
            )
        if not isinstance(self.limits, OandaPracticeOperationalLimits):
            raise OandaPracticeConfigurationValidationError(
                "limits must be OandaPracticeOperationalLimits"
            )
        if (
            OandaPracticeCapability.PRICING_STREAM in self.capabilities
            and self.limits.active_streams == 0
        ):
            raise OandaPracticeConfigurationValidationError(
                "pricing_stream capability requires at least one active stream"
            )
        if not isinstance(self.secret_requirements, AdapterSecretRequirements):
            raise OandaPracticeConfigurationValidationError(
                "secret_requirements must be AdapterSecretRequirements"
            )
        if self.secret_requirements != oanda_practice_secret_requirements():
            raise OandaPracticeConfigurationValidationError(
                "OANDA Practice requires exactly one personal access token reference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.provider_key,
            self.environment.value,
            self.rest_endpoint.logical_values(),
            self.streaming_endpoint.logical_values(),
            self.account.logical_values(),
            self.symbols,
            tuple(capability.value for capability in self.capabilities),
            self.rest_timeout.logical_values(),
            self.stream_connect_timeout.logical_values(),
            self.limits.logical_values(),
            self.secret_requirements.logical_values(),
        )
