from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite
from uuid import UUID

from qore.infrastructure.futures_adapter_contracts import (
    FuturesAdapterCapability,
    FuturesAdapterProfile,
    FuturesAdapterValidationError,
    FuturesBarObservation,
    FuturesContractMapping,
    FuturesExecutionEnvironment,
    FuturesExecutionRequest,
    FuturesOrderSide,
    FuturesOrderType,
    FuturesProviderName,
    FuturesQuoteObservation,
    FuturesTimeInForce,
    FuturesTradeObservation,
)
from qore.infrastructure.market_data import Timeframe
from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

TRADOVATE_PROVIDER = FuturesProviderName("tradovate")


class TradovateCandidateError(InfrastructureError):
    """Base error for the non-production Tradovate candidate boundary."""

    __slots__ = ()


class TradovateCandidateValidationError(TradovateCandidateError):
    """Violation of deterministic Tradovate candidate invariants."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise TradovateCandidateValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise TradovateCandidateValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise TradovateCandidateValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_price(value: float, *, field_name: str) -> None:
    if type(value) is not float or not isfinite(value) or value <= 0.0:
        raise TradovateCandidateValidationError(
            f"{field_name} must be a positive finite float"
        )


def _validate_optional_price(value: float | None, *, field_name: str) -> None:
    if value is not None:
        _validate_price(value, field_name=field_name)


class TradovateCandidateStatus(StrEnum):
    OFFLINE_ELIGIBLE = "offline_eligible"
    OPERATIONAL_EVIDENCE_REQUIRED = "operational_evidence_required"


@dataclass(frozen=True, slots=True)
class TradovateCandidateAssessment:
    """Candidate evidence only; never an operational or Production certificate."""

    provider: FuturesProviderName
    status: TradovateCandidateStatus
    demo_simulation_supported: bool
    market_data_websocket_supported: bool
    authenticated_operational_evidence: bool
    network_io_performed: bool
    production_authorized: bool

    def __post_init__(self) -> None:
        if self.provider != TRADOVATE_PROVIDER:
            raise TradovateCandidateValidationError(
                "candidate assessment provider must be tradovate"
            )
        if not isinstance(self.status, TradovateCandidateStatus):
            raise TradovateCandidateValidationError(
                "candidate status must be TradovateCandidateStatus"
            )
        for field_name, value in (
            ("demo_simulation_supported", self.demo_simulation_supported),
            ("market_data_websocket_supported", self.market_data_websocket_supported),
            (
                "authenticated_operational_evidence",
                self.authenticated_operational_evidence,
            ),
            ("network_io_performed", self.network_io_performed),
            ("production_authorized", self.production_authorized),
        ):
            if type(value) is not bool:
                raise TradovateCandidateValidationError(
                    f"{field_name} must be bool"
                )
        if self.authenticated_operational_evidence or self.network_io_performed:
            raise TradovateCandidateValidationError(
                "offline candidate assessment cannot claim operational evidence"
            )
        if self.production_authorized:
            raise TradovateCandidateValidationError(
                "Tradovate candidate assessment cannot authorize Production"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.provider.logical_values(),
            self.status.value,
            self.demo_simulation_supported,
            self.market_data_websocket_supported,
            self.authenticated_operational_evidence,
            self.network_io_performed,
            self.production_authorized,
        )


def evaluate_tradovate_candidate() -> TradovateCandidateAssessment:
    """Return the repository-scoped offline candidate verdict."""

    return TradovateCandidateAssessment(
        provider=TRADOVATE_PROVIDER,
        status=TradovateCandidateStatus.OPERATIONAL_EVIDENCE_REQUIRED,
        demo_simulation_supported=True,
        market_data_websocket_supported=True,
        authenticated_operational_evidence=False,
        network_io_performed=False,
        production_authorized=False,
    )


@dataclass(frozen=True, slots=True)
class TradovateDemoAccountReference:
    """Opaque QORE-side reference; never a real Tradovate account identifier."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="Tradovate DEMO account reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class TradovateSymbol:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise TradovateCandidateValidationError(
                "Tradovate symbol must be non-empty"
            )
        if self.value != self.value.strip():
            raise TradovateCandidateValidationError(
                "Tradovate symbol must not contain surrounding whitespace"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class TradovateQuotePayload:
    symbol: TradovateSymbol
    provider_timestamp: datetime
    received_at: datetime
    bid: float
    ask: float

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, TradovateSymbol):
            raise TradovateCandidateValidationError(
                "quote symbol must be TradovateSymbol"
            )
        _validate_timestamp(
            self.provider_timestamp,
            field_name="Tradovate quote provider_timestamp",
        )
        _validate_timestamp(
            self.received_at,
            field_name="Tradovate quote received_at",
        )
        if self.received_at < self.provider_timestamp:
            raise TradovateCandidateValidationError(
                "Tradovate quote receipt cannot predate provider timestamp"
            )
        _validate_price(self.bid, field_name="Tradovate quote bid")
        _validate_price(self.ask, field_name="Tradovate quote ask")
        if self.bid > self.ask:
            raise TradovateCandidateValidationError(
                "Tradovate quote bid must not exceed ask"
            )


@dataclass(frozen=True, slots=True)
class TradovateTradePayload:
    symbol: TradovateSymbol
    provider_timestamp: datetime
    received_at: datetime
    price: float
    quantity: int

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, TradovateSymbol):
            raise TradovateCandidateValidationError(
                "trade symbol must be TradovateSymbol"
            )
        _validate_timestamp(
            self.provider_timestamp,
            field_name="Tradovate trade provider_timestamp",
        )
        _validate_timestamp(
            self.received_at,
            field_name="Tradovate trade received_at",
        )
        if self.received_at < self.provider_timestamp:
            raise TradovateCandidateValidationError(
                "Tradovate trade receipt cannot predate provider timestamp"
            )
        _validate_price(self.price, field_name="Tradovate trade price")
        if type(self.quantity) is not int or self.quantity <= 0:
            raise TradovateCandidateValidationError(
                "Tradovate trade quantity must be a positive integer"
            )


@dataclass(frozen=True, slots=True)
class TradovateBarPayload:
    symbol: TradovateSymbol
    opened_at: datetime
    closed_at: datetime
    received_at: datetime
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, TradovateSymbol):
            raise TradovateCandidateValidationError(
                "bar symbol must be TradovateSymbol"
            )
        _validate_timestamp(self.opened_at, field_name="Tradovate bar opened_at")
        _validate_timestamp(self.closed_at, field_name="Tradovate bar closed_at")
        _validate_timestamp(self.received_at, field_name="Tradovate bar received_at")
        if self.closed_at <= self.opened_at:
            raise TradovateCandidateValidationError(
                "Tradovate bar closed_at must be after opened_at"
            )
        if self.received_at < self.closed_at:
            raise TradovateCandidateValidationError(
                "Tradovate closed bar cannot arrive before close"
            )
        _validate_price(self.open, field_name="Tradovate bar open")
        _validate_price(self.high, field_name="Tradovate bar high")
        _validate_price(self.low, field_name="Tradovate bar low")
        _validate_price(self.close, field_name="Tradovate bar close")
        if self.low > self.high:
            raise TradovateCandidateValidationError(
                "Tradovate bar low must not exceed high"
            )
        if not self.low <= self.open <= self.high:
            raise TradovateCandidateValidationError(
                "Tradovate bar open must be within low/high"
            )
        if not self.low <= self.close <= self.high:
            raise TradovateCandidateValidationError(
                "Tradovate bar close must be within low/high"
            )


class TradovateOrderAction(StrEnum):
    BUY = "Buy"
    SELL = "Sell"


class TradovateOrderType(StrEnum):
    MARKET = "Market"
    LIMIT = "Limit"
    STOP = "Stop"


class TradovateTimeInForce(StrEnum):
    DAY = "Day"
    GTC = "GTC"


@dataclass(frozen=True, slots=True)
class TradovateDemoOrderIntent:
    """Deterministic DEMO translation; this object performs no API call."""

    request_id: object
    account_ref: TradovateDemoAccountReference
    symbol: TradovateSymbol
    action: TradovateOrderAction
    quantity: int
    order_type: TradovateOrderType
    time_in_force: TradovateTimeInForce
    limit_price: float | None
    stop_price: float | None
    client_order_id: UUID
    is_automated: bool
    requested_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.account_ref, TradovateDemoAccountReference):
            raise TradovateCandidateValidationError(
                "account_ref must be TradovateDemoAccountReference"
            )
        if not isinstance(self.symbol, TradovateSymbol):
            raise TradovateCandidateValidationError(
                "order symbol must be TradovateSymbol"
            )
        if not isinstance(self.action, TradovateOrderAction):
            raise TradovateCandidateValidationError(
                "order action must be TradovateOrderAction"
            )
        if type(self.quantity) is not int or self.quantity <= 0:
            raise TradovateCandidateValidationError(
                "order quantity must be a positive integer"
            )
        if not isinstance(self.order_type, TradovateOrderType):
            raise TradovateCandidateValidationError(
                "order_type must be TradovateOrderType"
            )
        if not isinstance(self.time_in_force, TradovateTimeInForce):
            raise TradovateCandidateValidationError(
                "time_in_force must be TradovateTimeInForce"
            )
        _validate_optional_price(self.limit_price, field_name="limit_price")
        _validate_optional_price(self.stop_price, field_name="stop_price")
        if self.order_type is TradovateOrderType.MARKET:
            if self.limit_price is not None or self.stop_price is not None:
                raise TradovateCandidateValidationError(
                    "Market order cannot carry limit/stop price"
                )
        elif self.order_type is TradovateOrderType.LIMIT:
            if self.limit_price is None or self.stop_price is not None:
                raise TradovateCandidateValidationError(
                    "Limit order requires only limit_price"
                )
        elif self.stop_price is None or self.limit_price is not None:
            raise TradovateCandidateValidationError(
                "Stop order requires only stop_price"
            )
        _validate_uuid(self.client_order_id, field_name="Tradovate client_order_id")
        if self.is_automated is not True:
            raise TradovateCandidateValidationError(
                "Tradovate automated candidate order must set is_automated true"
            )
        _validate_timestamp(self.requested_at, field_name="Tradovate requested_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.request_id,
            self.account_ref.logical_values(),
            self.symbol.logical_values(),
            self.action.value,
            self.quantity,
            self.order_type.value,
            self.time_in_force.value,
            self.limit_price,
            self.stop_price,
            str(self.client_order_id),
            self.is_automated,
            self.requested_at.isoformat(),
        )


def validate_tradovate_profile(
    profile: FuturesAdapterProfile,
) -> Result[FuturesAdapterProfile, TradovateCandidateError]:
    """Validate candidate profile without resolving secret values."""

    if not isinstance(profile, FuturesAdapterProfile):
        return Failure(
            TradovateCandidateValidationError(
                "profile must be FuturesAdapterProfile"
            )
        )
    if profile.provider != TRADOVATE_PROVIDER:
        return Failure(
            TradovateCandidateValidationError(
                "profile provider must be tradovate"
            )
        )
    required = {
        FuturesAdapterCapability.MARKET_DATA,
        FuturesAdapterCapability.EXECUTION,
    }
    if not required.issubset(set(profile.capabilities)):
        return Failure(
            TradovateCandidateValidationError(
                "Tradovate candidate requires market-data and execution capabilities"
            )
        )
    if not profile.secret_refs:
        return Failure(
            TradovateCandidateValidationError(
                "Tradovate candidate requires opaque authentication SecretRef"
            )
        )
    return Success(profile)


def _validate_mapping_symbol(
    mapping: FuturesContractMapping,
    symbol: TradovateSymbol,
) -> None:
    if not isinstance(mapping, FuturesContractMapping):
        raise TradovateCandidateValidationError(
            "mapping must be FuturesContractMapping"
        )
    if mapping.provider != TRADOVATE_PROVIDER:
        raise TradovateCandidateValidationError(
            "mapping provider must be tradovate"
        )
    if mapping.provider_contract_id.value != symbol.value:
        raise TradovateCandidateValidationError(
            "Tradovate payload symbol must match mapping provider contract id"
        )


def normalize_tradovate_quote(
    payload: TradovateQuotePayload,
    mapping: FuturesContractMapping,
    source: ExternalSourceDescriptor,
) -> Result[FuturesQuoteObservation, TradovateCandidateError]:
    if not isinstance(payload, TradovateQuotePayload):
        return Failure(
            TradovateCandidateValidationError(
                "payload must be TradovateQuotePayload"
            )
        )
    try:
        _validate_mapping_symbol(mapping, payload.symbol)
        observation = FuturesQuoteObservation(
            mapping=mapping,
            source=source,
            provider_timestamp=payload.provider_timestamp,
            received_at=payload.received_at,
            bid=payload.bid,
            ask=payload.ask,
        )
    except (TradovateCandidateValidationError, FuturesAdapterValidationError) as error:
        return Failure(TradovateCandidateValidationError(str(error)))
    return Success(observation)


def normalize_tradovate_trade(
    payload: TradovateTradePayload,
    mapping: FuturesContractMapping,
    source: ExternalSourceDescriptor,
) -> Result[FuturesTradeObservation, TradovateCandidateError]:
    if not isinstance(payload, TradovateTradePayload):
        return Failure(
            TradovateCandidateValidationError(
                "payload must be TradovateTradePayload"
            )
        )
    try:
        _validate_mapping_symbol(mapping, payload.symbol)
        observation = FuturesTradeObservation(
            mapping=mapping,
            source=source,
            provider_timestamp=payload.provider_timestamp,
            received_at=payload.received_at,
            price=payload.price,
            quantity=payload.quantity,
        )
    except (TradovateCandidateValidationError, FuturesAdapterValidationError) as error:
        return Failure(TradovateCandidateValidationError(str(error)))
    return Success(observation)


def normalize_tradovate_bar(
    payload: TradovateBarPayload,
    mapping: FuturesContractMapping,
    source: ExternalSourceDescriptor,
    *,
    timeframe: Timeframe,
) -> Result[FuturesBarObservation, TradovateCandidateError]:
    if not isinstance(payload, TradovateBarPayload):
        return Failure(
            TradovateCandidateValidationError(
                "payload must be TradovateBarPayload"
            )
        )
    try:
        _validate_mapping_symbol(mapping, payload.symbol)
        observation = FuturesBarObservation(
            mapping=mapping,
            source=source,
            timeframe=timeframe,
            opened_at=payload.opened_at,
            closed_at=payload.closed_at,
            received_at=payload.received_at,
            open=payload.open,
            high=payload.high,
            low=payload.low,
            close=payload.close,
        )
    except (TradovateCandidateValidationError, FuturesAdapterValidationError) as error:
        return Failure(TradovateCandidateValidationError(str(error)))
    return Success(observation)


def translate_tradovate_demo_order(
    request: FuturesExecutionRequest,
    *,
    account_ref: TradovateDemoAccountReference,
) -> Result[TradovateDemoOrderIntent, TradovateCandidateError]:
    """Translate an authorized request into DEMO intent without sending it."""

    if not isinstance(request, FuturesExecutionRequest):
        return Failure(
            TradovateCandidateValidationError(
                "request must be FuturesExecutionRequest"
            )
        )
    if request.mapping.provider != TRADOVATE_PROVIDER:
        return Failure(
            TradovateCandidateValidationError(
                "request mapping provider must be tradovate"
            )
        )
    if request.environment is not FuturesExecutionEnvironment.SIMULATION:
        return Failure(
            TradovateCandidateValidationError(
                "Tradovate candidate execution requires SIMULATION environment"
            )
        )
    action = (
        TradovateOrderAction.BUY
        if request.side is FuturesOrderSide.BUY
        else TradovateOrderAction.SELL
    )
    order_type = {
        FuturesOrderType.MARKET: TradovateOrderType.MARKET,
        FuturesOrderType.LIMIT: TradovateOrderType.LIMIT,
        FuturesOrderType.STOP: TradovateOrderType.STOP,
    }[request.order_type]
    time_in_force = (
        TradovateTimeInForce.DAY
        if request.time_in_force is FuturesTimeInForce.DAY
        else TradovateTimeInForce.GTC
    )
    try:
        intent = TradovateDemoOrderIntent(
            request_id=request.request_id.logical_values(),
            account_ref=account_ref,
            symbol=TradovateSymbol(request.mapping.provider_contract_id.value),
            action=action,
            quantity=request.quantity,
            order_type=order_type,
            time_in_force=time_in_force,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            client_order_id=request.idempotency_key.value,
            is_automated=True,
            requested_at=request.requested_at,
        )
    except TradovateCandidateValidationError as error:
        return Failure(error)
    return Success(intent)
