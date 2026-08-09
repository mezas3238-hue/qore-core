from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite
from uuid import UUID

from qore.infrastructure.futures_adapter_contracts import (
    FuturesAdapterCapability,
    FuturesAdapterContractError,
    FuturesAdapterProfile,
    FuturesAdapterValidationError,
    FuturesBarObservation,
    FuturesContractMapping,
    FuturesExecutionEnvironment,
    FuturesExecutionEvidenceReference,
    FuturesExecutionObservation,
    FuturesExecutionObservationId,
    FuturesExecutionReconciliation,
    FuturesExecutionReconciliationStatus,
    FuturesExecutionRequest,
    FuturesExecutionRequestId,
    FuturesExecutionState,
    FuturesOrderSide,
    FuturesOrderType,
    FuturesProviderName,
    FuturesProviderOrderReference,
    FuturesQuoteObservation,
    FuturesTimeInForce,
    FuturesTradeObservation,
    validate_futures_execution_observation,
)
from qore.infrastructure.market_data import Timeframe
from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

TASTYTRADE_PROVIDER = FuturesProviderName("tastytrade")
TASTYTRADE_SANDBOX_QUOTE_DELAY_MINUTES = 15


class TastytradeFuturesAdapterError(InfrastructureError):
    """Base error for the non-production tastytrade Futures adapter."""

    __slots__ = ()


class TastytradeFuturesValidationError(TastytradeFuturesAdapterError):
    """Violation of deterministic tastytrade adapter invariants."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise TastytradeFuturesValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise TastytradeFuturesValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise TastytradeFuturesValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_price(value: float, *, field_name: str) -> None:
    if type(value) is not float or not isfinite(value) or value <= 0.0:
        raise TastytradeFuturesValidationError(
            f"{field_name} must be a positive finite float"
        )


def _validate_optional_price(value: float | None, *, field_name: str) -> None:
    if value is not None:
        _validate_price(value, field_name=field_name)


@dataclass(frozen=True, slots=True)
class TastytradeSandboxAccountReference:
    """Opaque QORE-side reference; never a tastytrade account number."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="tastytrade sandbox account reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class TastytradeFuturesSymbol:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise TastytradeFuturesValidationError(
                "tastytrade Futures symbol must be non-empty"
            )
        if self.value != self.value.strip():
            raise TastytradeFuturesValidationError(
                "tastytrade Futures symbol must not contain surrounding whitespace"
            )
        if not self.value.startswith("/"):
            raise TastytradeFuturesValidationError(
                "tastytrade Futures symbol must use slash-prefixed symbology"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class TastytradeSandboxMarketDataMode(StrEnum):
    DELAYED_15_MINUTES = "delayed_15_minutes"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TastytradeQuotePayload:
    symbol: TastytradeFuturesSymbol
    data_mode: TastytradeSandboxMarketDataMode
    provider_timestamp: datetime
    received_at: datetime
    bid: float
    ask: float

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, TastytradeFuturesSymbol):
            raise TastytradeFuturesValidationError(
                "quote symbol must be TastytradeFuturesSymbol"
            )
        if not isinstance(self.data_mode, TastytradeSandboxMarketDataMode):
            raise TastytradeFuturesValidationError(
                "quote data_mode must be TastytradeSandboxMarketDataMode"
            )
        _validate_timestamp(
            self.provider_timestamp,
            field_name="tastytrade quote provider_timestamp",
        )
        _validate_timestamp(self.received_at, field_name="tastytrade quote received_at")
        if self.received_at < self.provider_timestamp:
            raise TastytradeFuturesValidationError(
                "tastytrade quote receipt cannot predate provider timestamp"
            )
        _validate_price(self.bid, field_name="tastytrade quote bid")
        _validate_price(self.ask, field_name="tastytrade quote ask")
        if self.bid > self.ask:
            raise TastytradeFuturesValidationError(
                "tastytrade quote bid must not exceed ask"
            )


@dataclass(frozen=True, slots=True)
class TastytradeTradePayload:
    symbol: TastytradeFuturesSymbol
    data_mode: TastytradeSandboxMarketDataMode
    provider_timestamp: datetime
    received_at: datetime
    price: float
    quantity: int

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, TastytradeFuturesSymbol):
            raise TastytradeFuturesValidationError(
                "trade symbol must be TastytradeFuturesSymbol"
            )
        if not isinstance(self.data_mode, TastytradeSandboxMarketDataMode):
            raise TastytradeFuturesValidationError(
                "trade data_mode must be TastytradeSandboxMarketDataMode"
            )
        _validate_timestamp(
            self.provider_timestamp,
            field_name="tastytrade trade provider_timestamp",
        )
        _validate_timestamp(self.received_at, field_name="tastytrade trade received_at")
        if self.received_at < self.provider_timestamp:
            raise TastytradeFuturesValidationError(
                "tastytrade trade receipt cannot predate provider timestamp"
            )
        _validate_price(self.price, field_name="tastytrade trade price")
        if type(self.quantity) is not int or self.quantity <= 0:
            raise TastytradeFuturesValidationError(
                "tastytrade trade quantity must be a positive integer"
            )


@dataclass(frozen=True, slots=True)
class TastytradeBarPayload:
    symbol: TastytradeFuturesSymbol
    data_mode: TastytradeSandboxMarketDataMode
    opened_at: datetime
    closed_at: datetime
    received_at: datetime
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, TastytradeFuturesSymbol):
            raise TastytradeFuturesValidationError(
                "bar symbol must be TastytradeFuturesSymbol"
            )
        if not isinstance(self.data_mode, TastytradeSandboxMarketDataMode):
            raise TastytradeFuturesValidationError(
                "bar data_mode must be TastytradeSandboxMarketDataMode"
            )
        _validate_timestamp(self.opened_at, field_name="tastytrade bar opened_at")
        _validate_timestamp(self.closed_at, field_name="tastytrade bar closed_at")
        _validate_timestamp(self.received_at, field_name="tastytrade bar received_at")
        if self.closed_at <= self.opened_at:
            raise TastytradeFuturesValidationError(
                "tastytrade bar closed_at must be after opened_at"
            )
        if self.received_at < self.closed_at:
            raise TastytradeFuturesValidationError(
                "tastytrade closed bar cannot arrive before close"
            )
        _validate_price(self.open, field_name="tastytrade bar open")
        _validate_price(self.high, field_name="tastytrade bar high")
        _validate_price(self.low, field_name="tastytrade bar low")
        _validate_price(self.close, field_name="tastytrade bar close")
        if self.low > self.high:
            raise TastytradeFuturesValidationError(
                "tastytrade bar low must not exceed high"
            )
        if not self.low <= self.open <= self.high:
            raise TastytradeFuturesValidationError(
                "tastytrade bar open must be within low/high"
            )
        if not self.low <= self.close <= self.high:
            raise TastytradeFuturesValidationError(
                "tastytrade bar close must be within low/high"
            )


@dataclass(frozen=True, slots=True)
class TastytradeNormalizedQuote:
    observation: FuturesQuoteObservation
    data_mode: TastytradeSandboxMarketDataMode

    @property
    def is_realtime_certifiable(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class TastytradeNormalizedTrade:
    observation: FuturesTradeObservation
    data_mode: TastytradeSandboxMarketDataMode

    @property
    def is_realtime_certifiable(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class TastytradeNormalizedBar:
    observation: FuturesBarObservation
    data_mode: TastytradeSandboxMarketDataMode

    @property
    def is_realtime_certifiable(self) -> bool:
        return False


class TastytradeSandboxLifecycleState(StrEnum):
    CURRENT = "current"
    RESET_DETECTED = "reset_detected"
    UNKNOWN = "unknown"


class TastytradeSandboxContinuityDisposition(StrEnum):
    CONTINUE = "continue"
    RECONCILE_SANDBOX_STATE = "reconcile_sandbox_state"
    BLOCK = "block"


def classify_tastytrade_sandbox_continuity(
    state: TastytradeSandboxLifecycleState,
) -> TastytradeSandboxContinuityDisposition:
    """Classify sandbox lifecycle only; never retries or redispatches an order."""

    if not isinstance(state, TastytradeSandboxLifecycleState):
        raise TastytradeFuturesValidationError(
            "state must be TastytradeSandboxLifecycleState"
        )
    if state is TastytradeSandboxLifecycleState.CURRENT:
        return TastytradeSandboxContinuityDisposition.CONTINUE
    if state is TastytradeSandboxLifecycleState.RESET_DETECTED:
        return TastytradeSandboxContinuityDisposition.RECONCILE_SANDBOX_STATE
    return TastytradeSandboxContinuityDisposition.BLOCK


class TastytradeOrderAction(StrEnum):
    BUY = "Buy"
    SELL = "Sell"


class TastytradeOrderType(StrEnum):
    MARKET = "Market"
    LIMIT = "Limit"
    STOP = "Stop"


class TastytradeTimeInForce(StrEnum):
    DAY = "Day"
    GTC = "GTC"


@dataclass(frozen=True, slots=True)
class TastytradeSandboxOrderIntent:
    """Deterministic sandbox translation; this object performs no API call."""

    request_id: FuturesExecutionRequestId
    account_ref: TastytradeSandboxAccountReference
    symbol: TastytradeFuturesSymbol
    action: TastytradeOrderAction
    quantity: int
    order_type: TastytradeOrderType
    time_in_force: TastytradeTimeInForce
    limit_price: float | None
    stop_price: float | None
    client_order_id: UUID
    requested_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, FuturesExecutionRequestId):
            raise TastytradeFuturesValidationError(
                "order request_id must be FuturesExecutionRequestId"
            )
        if not isinstance(self.account_ref, TastytradeSandboxAccountReference):
            raise TastytradeFuturesValidationError(
                "account_ref must be TastytradeSandboxAccountReference"
            )
        if not isinstance(self.symbol, TastytradeFuturesSymbol):
            raise TastytradeFuturesValidationError(
                "order symbol must be TastytradeFuturesSymbol"
            )
        if not isinstance(self.action, TastytradeOrderAction):
            raise TastytradeFuturesValidationError(
                "action must be TastytradeOrderAction"
            )
        if type(self.quantity) is not int or self.quantity <= 0:
            raise TastytradeFuturesValidationError(
                "order quantity must be a positive integer"
            )
        if not isinstance(self.order_type, TastytradeOrderType):
            raise TastytradeFuturesValidationError(
                "order_type must be TastytradeOrderType"
            )
        if not isinstance(self.time_in_force, TastytradeTimeInForce):
            raise TastytradeFuturesValidationError(
                "time_in_force must be TastytradeTimeInForce"
            )
        _validate_optional_price(self.limit_price, field_name="limit_price")
        _validate_optional_price(self.stop_price, field_name="stop_price")
        if self.order_type is TastytradeOrderType.MARKET:
            if self.limit_price is not None or self.stop_price is not None:
                raise TastytradeFuturesValidationError(
                    "Market order cannot carry limit/stop price"
                )
        elif self.order_type is TastytradeOrderType.LIMIT:
            if self.limit_price is None or self.stop_price is not None:
                raise TastytradeFuturesValidationError(
                    "Limit order requires only limit_price"
                )
        elif self.stop_price is None or self.limit_price is not None:
            raise TastytradeFuturesValidationError(
                "Stop order requires only stop_price"
            )
        _validate_uuid(self.client_order_id, field_name="tastytrade client_order_id")
        _validate_timestamp(self.requested_at, field_name="tastytrade requested_at")


class TastytradeExecutionEventType(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PARTIAL_FILL = "partial_fill"
    FILL = "fill"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TastytradeExecutionEventPayload:
    request_id: FuturesExecutionRequestId
    event_type: TastytradeExecutionEventType
    provider_order_id: str | None
    cumulative_filled_quantity: int
    observed_at: datetime
    evidence_ref: FuturesExecutionEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, FuturesExecutionRequestId):
            raise TastytradeFuturesValidationError(
                "event request_id must be FuturesExecutionRequestId"
            )
        if not isinstance(self.event_type, TastytradeExecutionEventType):
            raise TastytradeFuturesValidationError(
                "event_type must be TastytradeExecutionEventType"
            )
        if self.provider_order_id is not None:
            if not isinstance(self.provider_order_id, str) or not self.provider_order_id.strip():
                raise TastytradeFuturesValidationError(
                    "provider_order_id must be non-empty or None"
                )
            if self.provider_order_id != self.provider_order_id.strip():
                raise TastytradeFuturesValidationError(
                    "provider_order_id must not contain surrounding whitespace"
                )
        if (
            type(self.cumulative_filled_quantity) is not int
            or self.cumulative_filled_quantity < 0
        ):
            raise TastytradeFuturesValidationError(
                "cumulative_filled_quantity must be non-negative integer"
            )
        _validate_timestamp(
            self.observed_at,
            field_name="tastytrade execution observed_at",
        )
        if not isinstance(self.evidence_ref, FuturesExecutionEvidenceReference):
            raise TastytradeFuturesValidationError(
                "evidence_ref must be FuturesExecutionEvidenceReference"
            )


class TastytradeReconciliationStatus(StrEnum):
    MATCHED = "matched"
    DIVERGED = "diverged"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TastytradeReconciliationPayload:
    request_id: FuturesExecutionRequestId
    status: TastytradeReconciliationStatus
    reconciled_at: datetime
    evidence_refs: tuple[FuturesExecutionEvidenceReference, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, FuturesExecutionRequestId):
            raise TastytradeFuturesValidationError(
                "reconciliation request_id must be FuturesExecutionRequestId"
            )
        if not isinstance(self.status, TastytradeReconciliationStatus):
            raise TastytradeFuturesValidationError(
                "status must be TastytradeReconciliationStatus"
            )
        _validate_timestamp(self.reconciled_at, field_name="tastytrade reconciled_at")
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs or any(
            not isinstance(ref, FuturesExecutionEvidenceReference)
            for ref in self.evidence_refs
        ):
            raise TastytradeFuturesValidationError(
                "reconciliation requires immutable non-empty evidence refs"
            )
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise TastytradeFuturesValidationError(
                "reconciliation evidence refs must be unique"
            )


def validate_tastytrade_profile(
    profile: FuturesAdapterProfile,
) -> Result[FuturesAdapterProfile, TastytradeFuturesAdapterError]:
    """Validate sandbox certification profile without resolving credentials."""

    if not isinstance(profile, FuturesAdapterProfile):
        return Failure(
            TastytradeFuturesValidationError(
                "profile must be FuturesAdapterProfile"
            )
        )
    if profile.provider != TASTYTRADE_PROVIDER:
        return Failure(
            TastytradeFuturesValidationError(
                "profile provider must be tastytrade"
            )
        )
    required = {
        FuturesAdapterCapability.MARKET_DATA,
        FuturesAdapterCapability.EXECUTION,
    }
    if not required.issubset(set(profile.capabilities)):
        return Failure(
            TastytradeFuturesValidationError(
                "tastytrade profile requires market-data and execution capabilities"
            )
        )
    if not profile.secret_refs:
        return Failure(
            TastytradeFuturesValidationError(
                "tastytrade profile requires opaque authentication SecretRef"
            )
        )
    return Success(profile)


def _validate_mapping_symbol(
    mapping: FuturesContractMapping,
    symbol: TastytradeFuturesSymbol,
) -> None:
    if not isinstance(mapping, FuturesContractMapping):
        raise TastytradeFuturesValidationError(
            "mapping must be FuturesContractMapping"
        )
    if mapping.provider != TASTYTRADE_PROVIDER:
        raise TastytradeFuturesValidationError(
            "mapping provider must be tastytrade"
        )
    if mapping.provider_contract_id.value != symbol.value:
        raise TastytradeFuturesValidationError(
            "tastytrade payload symbol must match mapping provider contract id"
        )


def normalize_tastytrade_quote(
    payload: TastytradeQuotePayload,
    mapping: FuturesContractMapping,
    source: ExternalSourceDescriptor,
) -> Result[TastytradeNormalizedQuote, TastytradeFuturesAdapterError]:
    if not isinstance(payload, TastytradeQuotePayload):
        return Failure(
            TastytradeFuturesValidationError(
                "payload must be TastytradeQuotePayload"
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
        normalized = TastytradeNormalizedQuote(
            observation=observation,
            data_mode=payload.data_mode,
        )
    except (TastytradeFuturesValidationError, FuturesAdapterValidationError) as error:
        return Failure(TastytradeFuturesValidationError(str(error)))
    return Success(normalized)


def normalize_tastytrade_trade(
    payload: TastytradeTradePayload,
    mapping: FuturesContractMapping,
    source: ExternalSourceDescriptor,
) -> Result[TastytradeNormalizedTrade, TastytradeFuturesAdapterError]:
    if not isinstance(payload, TastytradeTradePayload):
        return Failure(
            TastytradeFuturesValidationError(
                "payload must be TastytradeTradePayload"
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
        normalized = TastytradeNormalizedTrade(
            observation=observation,
            data_mode=payload.data_mode,
        )
    except (TastytradeFuturesValidationError, FuturesAdapterValidationError) as error:
        return Failure(TastytradeFuturesValidationError(str(error)))
    return Success(normalized)


def normalize_tastytrade_bar(
    payload: TastytradeBarPayload,
    mapping: FuturesContractMapping,
    source: ExternalSourceDescriptor,
    *,
    timeframe: Timeframe,
) -> Result[TastytradeNormalizedBar, TastytradeFuturesAdapterError]:
    if not isinstance(payload, TastytradeBarPayload):
        return Failure(
            TastytradeFuturesValidationError(
                "payload must be TastytradeBarPayload"
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
        normalized = TastytradeNormalizedBar(
            observation=observation,
            data_mode=payload.data_mode,
        )
    except (TastytradeFuturesValidationError, FuturesAdapterValidationError) as error:
        return Failure(TastytradeFuturesValidationError(str(error)))
    return Success(normalized)


def translate_tastytrade_sandbox_order(
    request: FuturesExecutionRequest,
    *,
    account_ref: TastytradeSandboxAccountReference,
) -> Result[TastytradeSandboxOrderIntent, TastytradeFuturesAdapterError]:
    """Translate an authorized request into sandbox intent without sending it."""

    if not isinstance(request, FuturesExecutionRequest):
        return Failure(
            TastytradeFuturesValidationError(
                "request must be FuturesExecutionRequest"
            )
        )
    if request.mapping.provider != TASTYTRADE_PROVIDER:
        return Failure(
            TastytradeFuturesValidationError(
                "request mapping provider must be tastytrade"
            )
        )
    if request.environment is not FuturesExecutionEnvironment.SIMULATION:
        return Failure(
            TastytradeFuturesValidationError(
                "tastytrade sandbox certification requires SIMULATION environment"
            )
        )
    action = (
        TastytradeOrderAction.BUY
        if request.side is FuturesOrderSide.BUY
        else TastytradeOrderAction.SELL
    )
    order_type = {
        FuturesOrderType.MARKET: TastytradeOrderType.MARKET,
        FuturesOrderType.LIMIT: TastytradeOrderType.LIMIT,
        FuturesOrderType.STOP: TastytradeOrderType.STOP,
    }[request.order_type]
    time_in_force = (
        TastytradeTimeInForce.DAY
        if request.time_in_force is FuturesTimeInForce.DAY
        else TastytradeTimeInForce.GTC
    )
    try:
        intent = TastytradeSandboxOrderIntent(
            request_id=request.request_id,
            account_ref=account_ref,
            symbol=TastytradeFuturesSymbol(request.mapping.provider_contract_id.value),
            action=action,
            quantity=request.quantity,
            order_type=order_type,
            time_in_force=time_in_force,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            client_order_id=request.idempotency_key.value,
            requested_at=request.requested_at,
        )
    except TastytradeFuturesValidationError as error:
        return Failure(error)
    return Success(intent)


def normalize_tastytrade_execution_event(
    request: FuturesExecutionRequest,
    payload: TastytradeExecutionEventPayload,
    *,
    observation_id: FuturesExecutionObservationId,
) -> Result[FuturesExecutionObservation, TastytradeFuturesAdapterError]:
    """Normalize sandbox order evidence; UNKNOWN becomes canonical AMBIGUOUS."""

    if not isinstance(payload, TastytradeExecutionEventPayload):
        return Failure(
            TastytradeFuturesValidationError(
                "payload must be TastytradeExecutionEventPayload"
            )
        )
    state = {
        TastytradeExecutionEventType.ACCEPTED: FuturesExecutionState.ACKNOWLEDGED,
        TastytradeExecutionEventType.REJECTED: FuturesExecutionState.REJECTED,
        TastytradeExecutionEventType.PARTIAL_FILL: FuturesExecutionState.PARTIALLY_FILLED,
        TastytradeExecutionEventType.FILL: FuturesExecutionState.FILLED,
        TastytradeExecutionEventType.UNKNOWN: FuturesExecutionState.AMBIGUOUS,
    }[payload.event_type]
    provider_ref = (
        FuturesProviderOrderReference(payload.provider_order_id)
        if payload.provider_order_id is not None
        else None
    )
    try:
        observation = FuturesExecutionObservation(
            observation_id=observation_id,
            request_id=payload.request_id,
            state=state,
            provider_order_ref=provider_ref,
            cumulative_filled_quantity=payload.cumulative_filled_quantity,
            observed_at=payload.observed_at,
            evidence_ref=payload.evidence_ref,
        )
    except FuturesAdapterValidationError as construction_error:
        return Failure(TastytradeFuturesValidationError(str(construction_error)))
    validated = validate_futures_execution_observation(request, observation)
    if isinstance(validated, Failure):
        validation_error: FuturesAdapterContractError = validated.error
        return Failure(TastytradeFuturesValidationError(str(validation_error)))
    return Success(validated.value)


def normalize_tastytrade_reconciliation(
    payload: TastytradeReconciliationPayload,
) -> Result[FuturesExecutionReconciliation, TastytradeFuturesAdapterError]:
    if not isinstance(payload, TastytradeReconciliationPayload):
        return Failure(
            TastytradeFuturesValidationError(
                "payload must be TastytradeReconciliationPayload"
            )
        )
    status = {
        TastytradeReconciliationStatus.MATCHED: FuturesExecutionReconciliationStatus.MATCHED,
        TastytradeReconciliationStatus.DIVERGED: FuturesExecutionReconciliationStatus.DIVERGED,
        TastytradeReconciliationStatus.UNKNOWN: FuturesExecutionReconciliationStatus.AMBIGUOUS,
    }[payload.status]
    try:
        reconciliation = FuturesExecutionReconciliation(
            request_id=payload.request_id,
            status=status,
            reconciled_at=payload.reconciled_at,
            evidence_refs=payload.evidence_refs,
        )
    except FuturesAdapterValidationError as error:
        return Failure(TastytradeFuturesValidationError(str(error)))
    return Success(reconciliation)
