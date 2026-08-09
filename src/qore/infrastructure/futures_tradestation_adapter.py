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

TRADESTATION_PROVIDER = FuturesProviderName("tradestation")


class TradeStationFuturesAdapterError(InfrastructureError):
    """Base error for the non-production TradeStation Futures adapter."""

    __slots__ = ()


class TradeStationFuturesValidationError(TradeStationFuturesAdapterError):
    """Violation of deterministic TradeStation adapter invariants."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise TradeStationFuturesValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise TradeStationFuturesValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise TradeStationFuturesValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_price(value: float, *, field_name: str) -> None:
    if type(value) is not float or not isfinite(value) or value <= 0.0:
        raise TradeStationFuturesValidationError(
            f"{field_name} must be a positive finite float"
        )


def _validate_optional_price(value: float | None, *, field_name: str) -> None:
    if value is not None:
        _validate_price(value, field_name=field_name)


@dataclass(frozen=True, slots=True)
class TradeStationSimAccountReference:
    """Opaque QORE-side reference; never a real TradeStation account identifier."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="TradeStation SIM account reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class TradeStationSymbol:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise TradeStationFuturesValidationError(
                "TradeStation symbol must be non-empty"
            )
        if self.value != self.value.strip():
            raise TradeStationFuturesValidationError(
                "TradeStation symbol must not contain surrounding whitespace"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class TradeStationQuotePayload:
    symbol: TradeStationSymbol
    provider_timestamp: datetime
    received_at: datetime
    bid: float
    ask: float

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, TradeStationSymbol):
            raise TradeStationFuturesValidationError(
                "quote symbol must be TradeStationSymbol"
            )
        _validate_timestamp(
            self.provider_timestamp,
            field_name="TradeStation quote provider_timestamp",
        )
        _validate_timestamp(
            self.received_at,
            field_name="TradeStation quote received_at",
        )
        if self.received_at < self.provider_timestamp:
            raise TradeStationFuturesValidationError(
                "TradeStation quote receipt cannot predate provider timestamp"
            )
        _validate_price(self.bid, field_name="TradeStation quote bid")
        _validate_price(self.ask, field_name="TradeStation quote ask")
        if self.bid > self.ask:
            raise TradeStationFuturesValidationError(
                "TradeStation quote bid must not exceed ask"
            )


@dataclass(frozen=True, slots=True)
class TradeStationTradePayload:
    symbol: TradeStationSymbol
    provider_timestamp: datetime
    received_at: datetime
    price: float
    quantity: int

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, TradeStationSymbol):
            raise TradeStationFuturesValidationError(
                "trade symbol must be TradeStationSymbol"
            )
        _validate_timestamp(
            self.provider_timestamp,
            field_name="TradeStation trade provider_timestamp",
        )
        _validate_timestamp(
            self.received_at,
            field_name="TradeStation trade received_at",
        )
        if self.received_at < self.provider_timestamp:
            raise TradeStationFuturesValidationError(
                "TradeStation trade receipt cannot predate provider timestamp"
            )
        _validate_price(self.price, field_name="TradeStation trade price")
        if type(self.quantity) is not int or self.quantity <= 0:
            raise TradeStationFuturesValidationError(
                "TradeStation trade quantity must be a positive integer"
            )


@dataclass(frozen=True, slots=True)
class TradeStationBarPayload:
    symbol: TradeStationSymbol
    opened_at: datetime
    closed_at: datetime
    received_at: datetime
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, TradeStationSymbol):
            raise TradeStationFuturesValidationError(
                "bar symbol must be TradeStationSymbol"
            )
        _validate_timestamp(self.opened_at, field_name="TradeStation bar opened_at")
        _validate_timestamp(self.closed_at, field_name="TradeStation bar closed_at")
        _validate_timestamp(self.received_at, field_name="TradeStation bar received_at")
        if self.closed_at <= self.opened_at:
            raise TradeStationFuturesValidationError(
                "TradeStation bar closed_at must be after opened_at"
            )
        if self.received_at < self.closed_at:
            raise TradeStationFuturesValidationError(
                "TradeStation closed bar cannot arrive before close"
            )
        _validate_price(self.open, field_name="TradeStation bar open")
        _validate_price(self.high, field_name="TradeStation bar high")
        _validate_price(self.low, field_name="TradeStation bar low")
        _validate_price(self.close, field_name="TradeStation bar close")
        if self.low > self.high:
            raise TradeStationFuturesValidationError(
                "TradeStation bar low must not exceed high"
            )
        if not self.low <= self.open <= self.high:
            raise TradeStationFuturesValidationError(
                "TradeStation bar open must be within low/high"
            )
        if not self.low <= self.close <= self.high:
            raise TradeStationFuturesValidationError(
                "TradeStation bar close must be within low/high"
            )


class TradeStationOrderAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class TradeStationOrderType(StrEnum):
    MARKET = "Market"
    LIMIT = "Limit"
    STOP_MARKET = "StopMarket"


class TradeStationDuration(StrEnum):
    DAY = "DAY"
    GTC = "GTC"


@dataclass(frozen=True, slots=True)
class TradeStationSimOrderIntent:
    """Deterministic SIM translation; this object performs no API call."""

    request_id: FuturesExecutionRequestId
    account_ref: TradeStationSimAccountReference
    symbol: TradeStationSymbol
    action: TradeStationOrderAction
    quantity: int
    order_type: TradeStationOrderType
    duration: TradeStationDuration
    limit_price: float | None
    stop_price: float | None
    client_order_id: UUID
    requested_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, FuturesExecutionRequestId):
            raise TradeStationFuturesValidationError(
                "order request_id must be FuturesExecutionRequestId"
            )
        if not isinstance(self.account_ref, TradeStationSimAccountReference):
            raise TradeStationFuturesValidationError(
                "account_ref must be TradeStationSimAccountReference"
            )
        if not isinstance(self.symbol, TradeStationSymbol):
            raise TradeStationFuturesValidationError(
                "order symbol must be TradeStationSymbol"
            )
        if not isinstance(self.action, TradeStationOrderAction):
            raise TradeStationFuturesValidationError(
                "order action must be TradeStationOrderAction"
            )
        if type(self.quantity) is not int or self.quantity <= 0:
            raise TradeStationFuturesValidationError(
                "order quantity must be a positive integer"
            )
        if not isinstance(self.order_type, TradeStationOrderType):
            raise TradeStationFuturesValidationError(
                "order_type must be TradeStationOrderType"
            )
        if not isinstance(self.duration, TradeStationDuration):
            raise TradeStationFuturesValidationError(
                "duration must be TradeStationDuration"
            )
        _validate_optional_price(self.limit_price, field_name="limit_price")
        _validate_optional_price(self.stop_price, field_name="stop_price")
        if self.order_type is TradeStationOrderType.MARKET:
            if self.limit_price is not None or self.stop_price is not None:
                raise TradeStationFuturesValidationError(
                    "Market order cannot carry limit/stop price"
                )
        elif self.order_type is TradeStationOrderType.LIMIT:
            if self.limit_price is None or self.stop_price is not None:
                raise TradeStationFuturesValidationError(
                    "Limit order requires only limit_price"
                )
        elif self.stop_price is None or self.limit_price is not None:
            raise TradeStationFuturesValidationError(
                "StopMarket order requires only stop_price"
            )
        _validate_uuid(self.client_order_id, field_name="TradeStation client_order_id")
        _validate_timestamp(self.requested_at, field_name="TradeStation requested_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.request_id.logical_values(),
            self.account_ref.logical_values(),
            self.symbol.logical_values(),
            self.action.value,
            self.quantity,
            self.order_type.value,
            self.duration.value,
            self.limit_price,
            self.stop_price,
            str(self.client_order_id),
            self.requested_at.isoformat(),
        )


class TradeStationExecutionEventType(StrEnum):
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    PARTIAL_FILL = "partial_fill"
    FILL = "fill"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TradeStationExecutionEventPayload:
    request_id: FuturesExecutionRequestId
    event_type: TradeStationExecutionEventType
    provider_order_id: str | None
    cumulative_filled_quantity: int
    observed_at: datetime
    evidence_ref: FuturesExecutionEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, FuturesExecutionRequestId):
            raise TradeStationFuturesValidationError(
                "event request_id must be FuturesExecutionRequestId"
            )
        if not isinstance(self.event_type, TradeStationExecutionEventType):
            raise TradeStationFuturesValidationError(
                "event_type must be TradeStationExecutionEventType"
            )
        if self.provider_order_id is not None:
            if not isinstance(self.provider_order_id, str) or not self.provider_order_id.strip():
                raise TradeStationFuturesValidationError(
                    "provider_order_id must be non-empty or None"
                )
            if self.provider_order_id != self.provider_order_id.strip():
                raise TradeStationFuturesValidationError(
                    "provider_order_id must not contain surrounding whitespace"
                )
        if (
            type(self.cumulative_filled_quantity) is not int
            or self.cumulative_filled_quantity < 0
        ):
            raise TradeStationFuturesValidationError(
                "cumulative_filled_quantity must be non-negative integer"
            )
        _validate_timestamp(self.observed_at, field_name="TradeStation event observed_at")
        if not isinstance(self.evidence_ref, FuturesExecutionEvidenceReference):
            raise TradeStationFuturesValidationError(
                "evidence_ref must be FuturesExecutionEvidenceReference"
            )


class TradeStationReconciliationStatus(StrEnum):
    MATCHED = "matched"
    DIVERGED = "diverged"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class TradeStationReconciliationPayload:
    request_id: FuturesExecutionRequestId
    status: TradeStationReconciliationStatus
    reconciled_at: datetime
    evidence_refs: tuple[FuturesExecutionEvidenceReference, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, FuturesExecutionRequestId):
            raise TradeStationFuturesValidationError(
                "reconciliation request_id must be FuturesExecutionRequestId"
            )
        if not isinstance(self.status, TradeStationReconciliationStatus):
            raise TradeStationFuturesValidationError(
                "status must be TradeStationReconciliationStatus"
            )
        _validate_timestamp(self.reconciled_at, field_name="TradeStation reconciled_at")
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs or any(
            not isinstance(ref, FuturesExecutionEvidenceReference)
            for ref in self.evidence_refs
        ):
            raise TradeStationFuturesValidationError(
                "reconciliation requires immutable non-empty evidence refs"
            )
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise TradeStationFuturesValidationError(
                "reconciliation evidence refs must be unique"
            )


def validate_tradestation_profile(
    profile: FuturesAdapterProfile,
) -> Result[FuturesAdapterProfile, TradeStationFuturesAdapterError]:
    """Validate TradeStation certification profile without resolving secrets."""

    if not isinstance(profile, FuturesAdapterProfile):
        return Failure(
            TradeStationFuturesValidationError(
                "profile must be FuturesAdapterProfile"
            )
        )
    if profile.provider != TRADESTATION_PROVIDER:
        return Failure(
            TradeStationFuturesValidationError(
                "profile provider must be tradestation"
            )
        )
    required = {
        FuturesAdapterCapability.MARKET_DATA,
        FuturesAdapterCapability.EXECUTION,
    }
    if not required.issubset(set(profile.capabilities)):
        return Failure(
            TradeStationFuturesValidationError(
                "TradeStation profile requires market-data and execution capabilities"
            )
        )
    if not profile.secret_refs:
        return Failure(
            TradeStationFuturesValidationError(
                "TradeStation profile requires opaque authentication SecretRef"
            )
        )
    return Success(profile)


def _validate_mapping_symbol(
    mapping: FuturesContractMapping,
    symbol: TradeStationSymbol,
) -> None:
    if not isinstance(mapping, FuturesContractMapping):
        raise TradeStationFuturesValidationError(
            "mapping must be FuturesContractMapping"
        )
    if mapping.provider != TRADESTATION_PROVIDER:
        raise TradeStationFuturesValidationError(
            "mapping provider must be tradestation"
        )
    if mapping.provider_contract_id.value != symbol.value:
        raise TradeStationFuturesValidationError(
            "TradeStation payload symbol must match mapping provider contract id"
        )


def normalize_tradestation_quote(
    payload: TradeStationQuotePayload,
    mapping: FuturesContractMapping,
    source: ExternalSourceDescriptor,
) -> Result[FuturesQuoteObservation, TradeStationFuturesAdapterError]:
    if not isinstance(payload, TradeStationQuotePayload):
        return Failure(
            TradeStationFuturesValidationError(
                "payload must be TradeStationQuotePayload"
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
    except (TradeStationFuturesValidationError, FuturesAdapterValidationError) as error:
        return Failure(TradeStationFuturesValidationError(str(error)))
    return Success(observation)


def normalize_tradestation_trade(
    payload: TradeStationTradePayload,
    mapping: FuturesContractMapping,
    source: ExternalSourceDescriptor,
) -> Result[FuturesTradeObservation, TradeStationFuturesAdapterError]:
    if not isinstance(payload, TradeStationTradePayload):
        return Failure(
            TradeStationFuturesValidationError(
                "payload must be TradeStationTradePayload"
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
    except (TradeStationFuturesValidationError, FuturesAdapterValidationError) as error:
        return Failure(TradeStationFuturesValidationError(str(error)))
    return Success(observation)


def normalize_tradestation_bar(
    payload: TradeStationBarPayload,
    mapping: FuturesContractMapping,
    source: ExternalSourceDescriptor,
    *,
    timeframe: Timeframe,
) -> Result[FuturesBarObservation, TradeStationFuturesAdapterError]:
    if not isinstance(payload, TradeStationBarPayload):
        return Failure(
            TradeStationFuturesValidationError(
                "payload must be TradeStationBarPayload"
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
    except (TradeStationFuturesValidationError, FuturesAdapterValidationError) as error:
        return Failure(TradeStationFuturesValidationError(str(error)))
    return Success(observation)


def translate_tradestation_sim_order(
    request: FuturesExecutionRequest,
    *,
    account_ref: TradeStationSimAccountReference,
) -> Result[TradeStationSimOrderIntent, TradeStationFuturesAdapterError]:
    """Translate an authorized request into a SIM intent without sending it."""

    if not isinstance(request, FuturesExecutionRequest):
        return Failure(
            TradeStationFuturesValidationError(
                "request must be FuturesExecutionRequest"
            )
        )
    if request.mapping.provider != TRADESTATION_PROVIDER:
        return Failure(
            TradeStationFuturesValidationError(
                "request mapping provider must be tradestation"
            )
        )
    if request.environment is not FuturesExecutionEnvironment.SIMULATION:
        return Failure(
            TradeStationFuturesValidationError(
                "TradeStation execution certification requires SIMULATION environment"
            )
        )
    action = (
        TradeStationOrderAction.BUY
        if request.side is FuturesOrderSide.BUY
        else TradeStationOrderAction.SELL
    )
    order_type = {
        FuturesOrderType.MARKET: TradeStationOrderType.MARKET,
        FuturesOrderType.LIMIT: TradeStationOrderType.LIMIT,
        FuturesOrderType.STOP: TradeStationOrderType.STOP_MARKET,
    }[request.order_type]
    duration = (
        TradeStationDuration.DAY
        if request.time_in_force is FuturesTimeInForce.DAY
        else TradeStationDuration.GTC
    )
    try:
        intent = TradeStationSimOrderIntent(
            request_id=request.request_id,
            account_ref=account_ref,
            symbol=TradeStationSymbol(request.mapping.provider_contract_id.value),
            action=action,
            quantity=request.quantity,
            order_type=order_type,
            duration=duration,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            client_order_id=request.idempotency_key.value,
            requested_at=request.requested_at,
        )
    except TradeStationFuturesValidationError as error:
        return Failure(error)
    return Success(intent)


def normalize_tradestation_execution_event(
    request: FuturesExecutionRequest,
    payload: TradeStationExecutionEventPayload,
    *,
    observation_id: FuturesExecutionObservationId,
) -> Result[FuturesExecutionObservation, TradeStationFuturesAdapterError]:
    """Normalize TradeStation order evidence; UNKNOWN becomes AMBIGUOUS."""

    if not isinstance(payload, TradeStationExecutionEventPayload):
        return Failure(
            TradeStationFuturesValidationError(
                "payload must be TradeStationExecutionEventPayload"
            )
        )
    state = {
        TradeStationExecutionEventType.ACKNOWLEDGED: FuturesExecutionState.ACKNOWLEDGED,
        TradeStationExecutionEventType.REJECTED: FuturesExecutionState.REJECTED,
        TradeStationExecutionEventType.PARTIAL_FILL: FuturesExecutionState.PARTIALLY_FILLED,
        TradeStationExecutionEventType.FILL: FuturesExecutionState.FILLED,
        TradeStationExecutionEventType.UNKNOWN: FuturesExecutionState.AMBIGUOUS,
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
        return Failure(TradeStationFuturesValidationError(str(construction_error)))
    validated = validate_futures_execution_observation(request, observation)
    if isinstance(validated, Failure):
        validation_error: FuturesAdapterContractError = validated.error
        return Failure(TradeStationFuturesValidationError(str(validation_error)))
    return Success(validated.value)


def normalize_tradestation_reconciliation(
    payload: TradeStationReconciliationPayload,
) -> Result[FuturesExecutionReconciliation, TradeStationFuturesAdapterError]:
    if not isinstance(payload, TradeStationReconciliationPayload):
        return Failure(
            TradeStationFuturesValidationError(
                "payload must be TradeStationReconciliationPayload"
            )
        )
    status = {
        TradeStationReconciliationStatus.MATCHED: FuturesExecutionReconciliationStatus.MATCHED,
        TradeStationReconciliationStatus.DIVERGED: FuturesExecutionReconciliationStatus.DIVERGED,
        TradeStationReconciliationStatus.UNKNOWN: FuturesExecutionReconciliationStatus.AMBIGUOUS,
    }[payload.status]
    try:
        reconciliation = FuturesExecutionReconciliation(
            request_id=payload.request_id,
            status=status,
            reconciled_at=payload.reconciled_at,
            evidence_refs=payload.evidence_refs,
        )
    except FuturesAdapterValidationError as error:
        return Failure(TradeStationFuturesValidationError(str(error)))
    return Success(reconciliation)
