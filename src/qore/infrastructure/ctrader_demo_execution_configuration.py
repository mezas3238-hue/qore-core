from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
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
from qore.infrastructure.order_intent import ExecutionInstrument
from qore.infrastructure.ports import ExternalPortError
from qore.infrastructure.transport import ExternalTransportTimeout

_CTRADER_DEMO_PROVIDER_KEY = "ctrader-demo"
_CTRADER_DEMO_HOST = "demo.ctraderapi.com"
_CTRADER_DEMO_PORT = 5035
_CTRADER_DEMO_SECRET_NAMES = (
    "ctrader-demo-access-token",
    "ctrader-demo-client-id",
    "ctrader-demo-client-secret",
    "ctrader-demo-refresh-token",
)
_CTRADER_MAX_ORDER_REQUESTS_PER_SECOND = 5


class CTraderDemoConfigurationError(ExternalPortError):
    """Base error for the cTrader DEMO execution configuration boundary."""

    __slots__ = ()


class CTraderDemoConfigurationValidationError(CTraderDemoConfigurationError):
    """Violation of a cTrader DEMO execution configuration invariant."""

    __slots__ = ()


class CTraderDemoCapability(StrEnum):
    """Provider-specific capabilities selected for cTrader DEMO composition."""

    ACCOUNT = "account"
    CANDLES = "candles"
    ORDERS = "orders"
    POSITIONS = "positions"


class CTraderDemoWireProtocol(StrEnum):
    """Closed wire protocol admitted by the cTrader DEMO runtime."""

    PROTOBUF_TCP_TLS = "protobuf_tcp_tls"


_REQUIRED_CAPABILITIES = frozenset(
    {
        CTraderDemoCapability.ACCOUNT,
        CTraderDemoCapability.ORDERS,
    }
)


def ctrader_demo_secret_requirements() -> AdapterSecretRequirements:
    """Declare required Open API secret names without resolving secret material."""
    return AdapterSecretRequirements(
        tuple(
            AdapterSecretRequirement(
                name=AdapterSecretName(name),
                required=True,
            )
            for name in _CTRADER_DEMO_SECRET_NAMES
        )
    )


def _validate_demo_endpoint(endpoint: ProviderEndpoint, *, field_name: str) -> None:
    if not isinstance(endpoint, ProviderEndpoint):
        raise CTraderDemoConfigurationValidationError(f"{field_name} must be ProviderEndpoint")
    if endpoint.host != _CTRADER_DEMO_HOST:
        raise CTraderDemoConfigurationValidationError(
            f"{field_name} must use the approved cTrader DEMO host"
        )
    if endpoint.port != _CTRADER_DEMO_PORT or endpoint.base_path != "/":
        raise CTraderDemoConfigurationValidationError(
            f"{field_name} must use cTrader Protobuf port 5035 and root base path"
        )


@dataclass(frozen=True, slots=True)
class CTraderSymbolMapping:
    """Exact binding of one canonical QORE instrument to a cTrader DEMO symbol."""

    instrument: ExecutionInstrument
    symbol_id: int
    symbol_name: str
    digits: int
    volume_step: Decimal
    min_volume_units: int
    max_volume_units: int
    step_volume_units: int

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, ExecutionInstrument):
            raise CTraderDemoConfigurationValidationError(
                "symbol mapping instrument must be ExecutionInstrument"
            )
        if type(self.symbol_id) is not int or self.symbol_id <= 0:
            raise CTraderDemoConfigurationValidationError(
                "symbol mapping symbol_id must be a positive int"
            )
        if (
            not isinstance(self.symbol_name, str)
            or fullmatch(r"[A-Z0-9][A-Z0-9]{1,31}", self.symbol_name) is None
        ):
            raise CTraderDemoConfigurationValidationError(
                "symbol mapping symbol_name must use canonical uppercase syntax"
            )
        if type(self.digits) is not int or self.digits < 0:
            raise CTraderDemoConfigurationValidationError(
                "symbol mapping digits must be a non-negative int"
            )
        if not isinstance(self.volume_step, Decimal):
            raise CTraderDemoConfigurationValidationError(
                "symbol mapping volume_step must be Decimal"
            )
        if not self.volume_step.is_finite() or self.volume_step <= Decimal("0"):
            raise CTraderDemoConfigurationValidationError(
                "symbol mapping volume_step must be finite and positive"
            )
        for field_name, value in (
            ("min_volume_units", self.min_volume_units),
            ("max_volume_units", self.max_volume_units),
            ("step_volume_units", self.step_volume_units),
        ):
            if type(value) is not int or value <= 0:
                raise CTraderDemoConfigurationValidationError(
                    f"symbol mapping {field_name} must be a positive int"
                )
        if self.min_volume_units > self.max_volume_units:
            raise CTraderDemoConfigurationValidationError(
                "symbol mapping min_volume_units must not exceed max_volume_units"
            )
        if self.min_volume_units % self.step_volume_units != 0:
            raise CTraderDemoConfigurationValidationError(
                "symbol mapping min_volume_units must align to step_volume_units"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.instrument.value,
            self.symbol_id,
            self.symbol_name,
            self.digits,
            format(self.volume_step, "f"),
            self.min_volume_units,
            self.max_volume_units,
            self.step_volume_units,
        )


@dataclass(frozen=True, slots=True)
class CTraderDemoOperationalLimits:
    """Explicit QORE limits bounded by the documented cTrader DEMO ceiling."""

    order_requests_per_second: int

    def __post_init__(self) -> None:
        if type(self.order_requests_per_second) is not int:
            raise CTraderDemoConfigurationValidationError(
                "order_requests_per_second must be an int"
            )
        if not (1 <= self.order_requests_per_second <= _CTRADER_MAX_ORDER_REQUESTS_PER_SECOND):
            raise CTraderDemoConfigurationValidationError(
                "order_requests_per_second must be between 1 and the cTrader ceiling"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.order_requests_per_second,)


@dataclass(frozen=True, slots=True)
class CTraderDemoRuntimeConfiguration:
    """Immutable DEMO-only provider configuration for the cTrader execution gateway."""

    provider_key: str
    environment: MarketRuntimeEnvironment
    endpoint: ProviderEndpoint
    account: MarketTestAccountIdentity
    symbol_mappings: tuple[CTraderSymbolMapping, ...]
    capabilities: tuple[CTraderDemoCapability, ...]
    rest_timeout: ExternalTransportTimeout
    limits: CTraderDemoOperationalLimits
    secret_requirements: AdapterSecretRequirements
    wire_protocol: CTraderDemoWireProtocol = CTraderDemoWireProtocol.PROTOBUF_TCP_TLS

    def __post_init__(self) -> None:
        if self.provider_key != _CTRADER_DEMO_PROVIDER_KEY:
            raise CTraderDemoConfigurationValidationError(
                "provider_key must identify the approved cTrader DEMO provider"
            )
        if not isinstance(self.environment, MarketRuntimeEnvironment):
            raise CTraderDemoConfigurationValidationError(
                "environment must be MarketRuntimeEnvironment"
            )
        if self.environment is not MarketRuntimeEnvironment.DEMO:
            raise CTraderDemoConfigurationValidationError(
                "cTrader execution must map exclusively to DEMO"
            )
        _validate_demo_endpoint(self.endpoint, field_name="endpoint")
        if self.wire_protocol is not CTraderDemoWireProtocol.PROTOBUF_TCP_TLS:
            raise CTraderDemoConfigurationValidationError(
                "cTrader DEMO requires Protobuf over TCP/TLS"
            )
        if not isinstance(self.account, MarketTestAccountIdentity):
            raise CTraderDemoConfigurationValidationError(
                "account must be MarketTestAccountIdentity"
            )
        if self.account.provider_key != self.provider_key:
            raise CTraderDemoConfigurationValidationError(
                "account provider_key must match runtime provider_key"
            )
        if self.account.environment is not self.environment:
            raise CTraderDemoConfigurationValidationError(
                "account environment must match cTrader DEMO environment"
            )
        if not isinstance(self.symbol_mappings, tuple) or not self.symbol_mappings:
            raise CTraderDemoConfigurationValidationError(
                "symbol_mappings must be a non-empty tuple"
            )
        if any(not isinstance(mapping, CTraderSymbolMapping) for mapping in self.symbol_mappings):
            raise CTraderDemoConfigurationValidationError(
                "symbol_mappings entries must be CTraderSymbolMapping"
            )
        instruments = tuple(mapping.instrument for mapping in self.symbol_mappings)
        if len(set(instruments)) != len(instruments):
            raise CTraderDemoConfigurationValidationError(
                "symbol_mappings must not contain duplicate instruments"
            )
        symbol_ids = tuple(mapping.symbol_id for mapping in self.symbol_mappings)
        if len(set(symbol_ids)) != len(symbol_ids):
            raise CTraderDemoConfigurationValidationError(
                "symbol_mappings must not contain duplicate symbol_id values"
            )
        if (
            tuple(sorted(self.symbol_mappings, key=lambda mapping: mapping.instrument.value))
            != self.symbol_mappings
        ):
            raise CTraderDemoConfigurationValidationError(
                "symbol_mappings must use stable sorted order by instrument"
            )
        if not isinstance(self.capabilities, tuple):
            raise CTraderDemoConfigurationValidationError("capabilities must be a tuple")
        if any(
            not isinstance(capability, CTraderDemoCapability) for capability in self.capabilities
        ):
            raise CTraderDemoConfigurationValidationError(
                "capabilities entries must be CTraderDemoCapability"
            )
        if len(set(self.capabilities)) != len(self.capabilities):
            raise CTraderDemoConfigurationValidationError(
                "capabilities must not contain duplicates"
            )
        if tuple(sorted(self.capabilities, key=lambda item: item.value)) != self.capabilities:
            raise CTraderDemoConfigurationValidationError(
                "capabilities must use stable sorted order"
            )
        if not _REQUIRED_CAPABILITIES.issubset(self.capabilities):
            raise CTraderDemoConfigurationValidationError(
                "capabilities must include account and orders"
            )
        if not isinstance(self.rest_timeout, ExternalTransportTimeout):
            raise CTraderDemoConfigurationValidationError(
                "rest_timeout must be ExternalTransportTimeout"
            )
        if not isinstance(self.limits, CTraderDemoOperationalLimits):
            raise CTraderDemoConfigurationValidationError(
                "limits must be CTraderDemoOperationalLimits"
            )
        if not isinstance(self.secret_requirements, AdapterSecretRequirements):
            raise CTraderDemoConfigurationValidationError(
                "secret_requirements must be AdapterSecretRequirements"
            )
        if self.secret_requirements != ctrader_demo_secret_requirements():
            raise CTraderDemoConfigurationValidationError(
                "cTrader DEMO requires app credentials plus access and refresh tokens"
            )

    def symbol_mapping(
        self,
        instrument: ExecutionInstrument,
    ) -> CTraderSymbolMapping | None:
        """Return the exact mapping for one canonical instrument, if configured."""
        if not isinstance(instrument, ExecutionInstrument):
            return None
        for mapping in self.symbol_mappings:
            if mapping.instrument == instrument:
                return mapping
        return None

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.provider_key,
            self.environment.value,
            self.endpoint.logical_values(),
            self.wire_protocol.value,
            self.account.logical_values(),
            tuple(mapping.logical_values() for mapping in self.symbol_mappings),
            tuple(capability.value for capability in self.capabilities),
            self.rest_timeout.logical_values(),
            self.limits.logical_values(),
            self.secret_requirements.logical_values(),
        )
