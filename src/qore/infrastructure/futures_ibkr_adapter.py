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

IBKR_PROVIDER = FuturesProviderName("ibkr")


class IBKRFuturesAdapterError(InfrastructureError):
    """Base error for the non-production IBKR Futures adapter."""

    __slots__ = ()


class IBKRFuturesValidationError(IBKRFuturesAdapterError):
    """Violation of deterministic IBKR adapter invariants."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise IBKRFuturesValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise IBKRFuturesValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise IBKRFuturesValidationError(f"{field_name} must be timezone-aware")


def _validate_price(value: float, *, field_name: str) -> None:
    if type(value) is not float or not isfinite(value) or value <= 0.0:
        raise IBKRFuturesValidationError(
            f"{field_name} must be a positive finite float"
        )


def _validate_optional_price(value: float | None, *, field_name: str) -> None:
    if value is not None:
        _validate_price(value, field_name=field_name)


@dataclass(frozen=True, slots=True)
class IBKRPaperAccountReference:
    """Opaque QORE-side reference; never an IBKR account code or username."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="IBKR paper account reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True, order=True)
class IBKRContractId:
    """Provider-side conid retained outside canonical QORE instrument identity."""

    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value <= 0:
            raise IBKRFuturesValidationError(
                "IBKR contract id must be a positive integer"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


class IBKRMarketDataMode(StrEnum):
    REALTIME = "realtime"
    DELAYED = "delayed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class IBKRQuotePayload:
    contract_id: IBKRContractId
    data_mode: IBKRMarketDataMode
    provider_timestamp: datetime
    received_at: datetime
    bid: float
    ask: float

    def __post_init__(self) -> None:
        if not isinstance(self.contract_id, IBKRContractId):
            raise IBKRFuturesValidationError(
                "quote contract_id must be IBKRContractId"
            )
        if not isinstance(self.data_mode, IBKRMarketDataMode):
            raise IBKRFuturesValidationError(
                "quote data_mode must be IBKRMarketDataMode"
            )
        _validate_timestamp(self.provider_timestamp, field_name="IBKR quote provider_timestamp")
        _validate_timestamp(self.received_at, field_name="IBKR quote received_at")
        if self.received_at < self.provider_timestamp:
            raise IBKRFuturesValidationError(
                "IBKR quote receipt cannot predate provider timestamp"
            )
        _validate_price(self.bid, field_name="IBKR quote bid")
        _validate_price(self.ask, field_name="IBKR quote ask")
        if self.bid > self.ask:
            raise IBKRFuturesValidationError("IBKR quote bid must not exceed ask")


@dataclass(frozen=True, slots=True)
class IBKRTradePayload:
    contract_id: IBKRContractId
    data_mode: IBKRMarketDataMode
    provider_timestamp: datetime
    received_at: datetime
    price: float
    quantity: int

    def __post_init__(self) -> None:
        if not isinstance(self.contract_id, IBKRContractId):
            raise IBKRFuturesValidationError(
                "trade contract_id must be IBKRContractId"
            )
        if not isinstance(self.data_mode, IBKRMarketDataMode):
            raise IBKRFuturesValidationError(
                "trade data_mode must be IBKRMarketDataMode"
            )
        _validate_timestamp(self.provider_timestamp, field_name="IBKR trade provider_timestamp")
        _validate_timestamp(self.received_at, field_name="IBKR trade received_at")
        if self.received_at < self.provider_timestamp:
            raise IBKRFuturesValidationError(
                "IBKR trade receipt cannot predate provider timestamp"
            )
        _validate_price(self.price, field_name="IBKR trade price")
        if type(self.quantity) is not int or self.quantity <= 0:
            raise IBKRFuturesValidationError(
                "IBKR trade quantity must be a positive integer"
            )


@dataclass(frozen=True, slots=True)
class IBKRBarPayload:
    contract_id: IBKRContractId
    data_mode: IBKRMarketDataMode
    opened_at: datetime
    closed_at: datetime
    received_at: datetime
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        if not isinstance(self.contract_id, IBKRContractId):
            raise IBKRFuturesValidationError(
                "bar contract_id must be IBKRContractId"
            )
        if not isinstance(self.data_mode, IBKRMarketDataMode):
            raise IBKRFuturesValidationError(
                "bar data_mode must be IBKRMarketDataMode"
            )
        _validate_timestamp(self.opened_at, field_name="IBKR bar opened_at")
        _validate_timestamp(self.closed_at, field_name="IBKR bar closed_at")
        _validate_timestamp(self.received_at, field_name="IBKR bar received_at")
        if self.closed_at <= self.opened_at:
            raise IBKRFuturesValidationError("IBKR bar closed_at must be after opened_at")
        if self.received_at < self.closed_at:
            raise IBKRFuturesValidationError(
                "IBKR closed bar cannot arrive before close"
            )
        _validate_price(self.open, field_name="IBKR bar open")
        _validate_price(self.high, field_name="IBKR bar high")
        _validate_price(self.low, field_name="IBKR bar low")
        _validate_price(self.close, field_name="IBKR bar close")
        if self.low > self.high:
            raise IBKRFuturesValidationError("IBKR bar low must not exceed high")
        if not self.low <= self.open <= self.high:
            raise IBKRFuturesValidationError("IBKR bar open must be within low/high")
        if not self.low <= self.close <= self.high:
            raise IBKRFuturesValidationError("IBKR bar close must be within low/high")


@dataclass(frozen=True, slots=True)
class IBKRNormalizedQuote:
    observation: FuturesQuoteObservation
    data_mode: IBKRMarketDataMode

    def __post_init__(self) -> None:
        if not isinstance(self.observation, FuturesQuoteObservation):
            raise IBKRFuturesValidationError(
                "normalized quote observation must be FuturesQuoteObservation"
            )
        if not isinstance(self.data_mode, IBKRMarketDataMode):
            raise IBKRFuturesValidationError(
                "normalized quote data_mode must be IBKRMarketDataMode"
            )

    @property
    def is_realtime_certifiable(self) -> bool:
        return self.data_mode is IBKRMarketDataMode.REALTIME


@dataclass(frozen=True, slots=True)
class IBKRNormalizedTrade:
    observation: FuturesTradeObservation
    data_mode: IBKRMarketDataMode

    def __post_init__(self) -> None:
        if not isinstance(self.observation, FuturesTradeObservation):
            raise IBKRFuturesValidationError(
                "normalized trade observation must be FuturesTradeObservation"
            )
        if not isinstance(self.data_mode, IBKRMarketDataMode):
            raise IBKRFuturesValidationError(
                "normalized trade data_mode must be IBKRMarketDataMode"
            )

    @property
    def is_realtime_certifiable(self) -> bool:
        return self.data_mode is IBKRMarketDataMode.REALTIME


@dataclass(frozen=True, slots=True)
class IBKRNormalizedBar:
    observation: FuturesBarObservation
    data_mode: IBKRMarketDataMode

    def __post_init__(self) -> None:
        if not isinstance(self.observation, FuturesBarObservation):
            raise IBKRFuturesValidationError(
                "normalized bar observation must be FuturesBarObservation"
            )
        if not isinstance(self.data_mode, IBKRMarketDataMode):
            raise IBKRFuturesValidationError(
                "normalized bar data_mode must be IBKRMarketDataMode"
            )

    @property
    def is_realtime_certifiable(self) -> bool:
        return self.data_mode is IBKRMarketDataMode.REALTIME


class IBKRMarketDataContinuityState(StrEnum):
    ACTIVE = "active"
    RESUBSCRIPTION_REQUIRED = "resubscription_required"
    BLOCKED = "blocked"


class IBKRMarketDataSessionObservation(StrEnum):
    ACTIVE = "active"
    PROVIDER_STREAM_ENDED = "provider_stream_ended"
    SESSION_UNAUTHORIZED = "session_unauthorized"
    UNKNOWN = "unknown"


def classify_ibkr_market_data_continuity(
    observation: IBKRMarketDataSessionObservation,
) -> IBKRMarketDataContinuityState:
    """Classify feed continuity only; never retries or redispatches an order."""

    if not isinstance(observation, IBKRMarketDataSessionObservation):
        raise IBKRFuturesValidationError(
            "observation must be IBKRMarketDataSessionObservation"
        )
    if observation is IBKRMarketDataSessionObservation.ACTIVE:
        return IBKRMarketDataContinuityState.ACTIVE
    if observation is IBKRMarketDataSessionObservation.PROVIDER_STREAM_ENDED:
        return IBKRMarketDataContinuityState.RESUBSCRIPTION_REQUIRED
    return IBKRMarketDataContinuityState.BLOCKED


class IBKROrderAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class IBKROrderType(StrEnum):
    MARKET = "MKT"
    LIMIT = "LMT"
    STOP = "STP"


class IBKRTimeInForce(StrEnum):
    DAY = "DAY"
    GTC = "GTC"


@dataclass(frozen=True, slots=True)
class IBKRPaperOrderIntent:
    """Deterministic paper translation; this object performs no API call."""

    request_id: FuturesExecutionRequestId
    account_ref: IBKRPaperAccountReference
    contract_id: IBKRContractId
    action: IBKROrderAction
    quantity: int
    order_type: IBKROrderType
    time_in_force: IBKRTimeInForce
    limit_price: float | None
    stop_price: float | None
    order_ref: UUID
    requested_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, FuturesExecutionRequestId):
            raise IBKRFuturesValidationError(
                "order request_id must be FuturesExecutionRequestId"
            )
        if not isinstance(self.account_ref, IBKRPaperAccountReference):
            raise IBKRFuturesValidationError(
                "account_ref must be IBKRPaperAccountReference"
            )
        if not isinstance(self.contract_id, IBKRContractId):
            raise IBKRFuturesValidationError(
                "order contract_id must be IBKRContractId"
            )
        if not isinstance(self.action, IBKROrderAction):
            raise IBKRFuturesValidationError("action must be IBKROrderAction")
        if type(self.quantity) is not int or self.quantity <= 0:
            raise IBKRFuturesValidationError(
                "order quantity must be a positive integer"
            )
        if not isinstance(self.order_type, IBKROrderType):
            raise IBKRFuturesValidationError("order_type must be IBKROrderType")
        if not isinstance(self.time_in_force, IBKRTimeInForce):
            raise IBKRFuturesValidationError(
                "time_in_force must be IBKRTimeInForce"
            )
        _validate_optional_price(self.limit_price, field_name="limit_price")
        _validate_optional_price(self.stop_price, field_name="stop_price")
        if self.order_type is IBKROrderType.MARKET:
            if self.limit_price is not None or self.stop_price is not None:
                raise IBKRFuturesValidationError(
                    "MKT order cannot carry limit/stop price"
                )
        elif self.order_type is IBKROrderType.LIMIT:
            if self.limit_price is None or self.stop_price is not None:
                raise IBKRFuturesValidationError(
                    "LMT order requires only limit_price"
                )
        elif self.stop_price is None or self.limit_price is not None:
            raise IBKRFuturesValidationError(
                "STP order requires only stop_price"
            )
        _validate_uuid(self.order_ref, field_name="IBKR order_ref")
        _validate_timestamp(self.requested_at, field_name="IBKR requested_at")


class IBKRExecutionEventType(StrEnum):
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    PARTIAL_FILL = "partial_fill"
    FILL = "fill"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class IBKRExecutionEventPayload:
    request_id: FuturesExecutionRequestId
    event_type: IBKRExecutionEventType
    provider_order_id: str | None
    cumulative_filled_quantity: int
    observed_at: datetime
    evidence_ref: FuturesExecutionEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, FuturesExecutionRequestId):
            raise IBKRFuturesValidationError(
                "event request_id must be FuturesExecutionRequestId"
            )
        if not isinstance(self.event_type, IBKRExecutionEventType):
            raise IBKRFuturesValidationError(
                "event_type must be IBKRExecutionEventType"
            )
        if self.provider_order_id is not None:
            if not isinstance(self.provider_order_id, str) or not self.provider_order_id.strip():
                raise IBKRFuturesValidationError(
                    "provider_order_id must be non-empty or None"
                )
            if self.provider_order_id != self.provider_order_id.strip():
                raise IBKRFuturesValidationError(
                    "provider_order_id must not contain surrounding whitespace"
                )
        if (
            type(self.cumulative_filled_quantity) is not int
            or self.cumulative_filled_quantity < 0
        ):
            raise IBKRFuturesValidationError(
                "cumulative_filled_quantity must be non-negative integer"
            )
        _validate_timestamp(self.observed_at, field_name="IBKR event observed_at")
        if not isinstance(self.evidence_ref, FuturesExecutionEvidenceReference):
            raise IBKRFuturesValidationError(
                "evidence_ref must be FuturesExecutionEvidenceReference"
            )


class IBKRReconciliationStatus(StrEnum):
    MATCHED = "matched"
    DIVERGED = "diverged"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class IBKRReconciliationPayload:
    request_id: FuturesExecutionRequestId
    status: IBKRReconciliationStatus
    reconciled_at: datetime
    evidence_refs: tuple[FuturesExecutionEvidenceReference, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, FuturesExecutionRequestId):
            raise IBKRFuturesValidationError(
                "reconciliation request_id must be FuturesExecutionRequestId"
            )
        if not isinstance(self.status, IBKRReconciliationStatus):
            raise IBKRFuturesValidationError(
                "status must be IBKRReconciliationStatus"
            )
        _validate_timestamp(self.reconciled_at, field_name="IBKR reconciled_at")
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs or any(
            not isinstance(ref, FuturesExecutionEvidenceReference)
            for ref in self.evidence_refs
        ):
            raise IBKRFuturesValidationError(
                "reconciliation requires immutable non-empty evidence refs"
            )
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise IBKRFuturesValidationError(
                "reconciliation evidence refs must be unique"
            )


def validate_ibkr_profile(
    profile: FuturesAdapterProfile,
) -> Result[FuturesAdapterProfile, IBKRFuturesAdapterError]:
    """Validate IBKR certification profile without resolving secrets or entitlements."""

    if not isinstance(profile, FuturesAdapterProfile):
        return Failure(IBKRFuturesValidationError("profile must be FuturesAdapterProfile"))
    if profile.provider != IBKR_PROVIDER:
        return Failure(IBKRFuturesValidationError("profile provider must be ibkr"))
    required = {
        FuturesAdapterCapability.MARKET_DATA,
        FuturesAdapterCapability.EXECUTION,
    }
    if not required.issubset(set(profile.capabilities)):
        return Failure(
            IBKRFuturesValidationError(
                "IBKR profile requires market-data and execution capabilities"
            )
        )
    if not profile.secret_refs:
        return Failure(
            IBKRFuturesValidationError(
                "IBKR profile requires opaque authentication SecretRef"
            )
        )
    return Success(profile)


def _validate_mapping_contract(
    mapping: FuturesContractMapping,
    contract_id: IBKRContractId,
) -> None:
    if not isinstance(mapping, FuturesContractMapping):
        raise IBKRFuturesValidationError("mapping must be FuturesContractMapping")
    if mapping.provider != IBKR_PROVIDER:
        raise IBKRFuturesValidationError("mapping provider must be ibkr")
    if mapping.provider_contract_id.value != str(contract_id.value):
        raise IBKRFuturesValidationError(
            "IBKR payload contract id must match mapping provider contract id"
        )


def normalize_ibkr_quote(
    payload: IBKRQuotePayload,
    mapping: FuturesContractMapping,
    source: ExternalSourceDescriptor,
) -> Result[IBKRNormalizedQuote, IBKRFuturesAdapterError]:
    if not isinstance(payload, IBKRQuotePayload):
        return Failure(IBKRFuturesValidationError("payload must be IBKRQuotePayload"))
    try:
        _validate_mapping_contract(mapping, payload.contract_id)
        observation = FuturesQuoteObservation(
            mapping=mapping,
            source=source,
            provider_timestamp=payload.provider_timestamp,
            received_at=payload.received_at,
            bid=payload.bid,
            ask=payload.ask,
        )
        normalized = IBKRNormalizedQuote(observation=observation, data_mode=payload.data_mode)
    except (IBKRFuturesValidationError, FuturesAdapterValidationError) as construction_error:
        return Failure(IBKRFuturesValidationError(str(construction_error)))
    return Success(normalized)


def normalize_ibkr_trade(
    payload: IBKRTradePayload,
    mapping: FuturesContractMapping,
    source: ExternalSourceDescriptor,
) -> Result[IBKRNormalizedTrade, IBKRFuturesAdapterError]:
    if not isinstance(payload, IBKRTradePayload):
        return Failure(IBKRFuturesValidationError("payload must be IBKRTradePayload"))
    try:
        _validate_mapping_contract(mapping, payload.contract_id)
        observation = FuturesTradeObservation(
            mapping=mapping,
            source=source,
            provider_timestamp=payload.provider_timestamp,
            received_at=payload.received_at,
            price=payload.price,
            quantity=payload.quantity,
        )
        normalized = IBKRNormalizedTrade(observation=observation, data_mode=payload.data_mode)
    except (IBKRFuturesValidationError, FuturesAdapterValidationError) as construction_error:
        return Failure(IBKRFuturesValidationError(str(construction_error)))
    return Success(normalized)


def normalize_ibkr_bar(
    payload: IBKRBarPayload,
    mapping: FuturesContractMapping,
    source: ExternalSourceDescriptor,
    *,
    timeframe: Timeframe,
) -> Result[IBKRNormalizedBar, IBKRFuturesAdapterError]:
    if not isinstance(payload, IBKRBarPayload):
        return Failure(IBKRFuturesValidationError("payload must be IBKRBarPayload"))
    try:
        _validate_mapping_contract(mapping, payload.contract_id)
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
        normalized = IBKRNormalizedBar(observation=observation, data_mode=payload.data_mode)
    except (IBKRFuturesValidationError, FuturesAdapterValidationError) as construction_error:
        return Failure(IBKRFuturesValidationError(str(construction_error)))
    return Success(normalized)


def translate_ibkr_paper_order(
    request: FuturesExecutionRequest,
    *,
    account_ref: IBKRPaperAccountReference,
) -> Result[IBKRPaperOrderIntent, IBKRFuturesAdapterError]:
    """Translate an authorized request into an IBKR paper intent without sending it."""

    if not isinstance(request, FuturesExecutionRequest):
        return Failure(IBKRFuturesValidationError("request must be FuturesExecutionRequest"))
    if request.mapping.provider != IBKR_PROVIDER:
        return Failure(IBKRFuturesValidationError("request mapping provider must be ibkr"))
    if request.environment is not FuturesExecutionEnvironment.PAPER:
        return Failure(
            IBKRFuturesValidationError(
                "IBKR execution certification requires PAPER environment"
            )
        )
    try:
        contract_id = IBKRContractId(int(request.mapping.provider_contract_id.value))
    except (ValueError, IBKRFuturesValidationError) as conversion_error:
        return Failure(IBKRFuturesValidationError(str(conversion_error)))
    action = (
        IBKROrderAction.BUY
        if request.side is FuturesOrderSide.BUY
        else IBKROrderAction.SELL
    )
    order_type = {
        FuturesOrderType.MARKET: IBKROrderType.MARKET,
        FuturesOrderType.LIMIT: IBKROrderType.LIMIT,
        FuturesOrderType.STOP: IBKROrderType.STOP,
    }[request.order_type]
    time_in_force = (
        IBKRTimeInForce.DAY
        if request.time_in_force is FuturesTimeInForce.DAY
        else IBKRTimeInForce.GTC
    )
    try:
        intent = IBKRPaperOrderIntent(
            request_id=request.request_id,
            account_ref=account_ref,
            contract_id=contract_id,
            action=action,
            quantity=request.quantity,
            order_type=order_type,
            time_in_force=time_in_force,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            order_ref=request.idempotency_key.value,
            requested_at=request.requested_at,
        )
    except IBKRFuturesValidationError as construction_error:
        return Failure(construction_error)
    return Success(intent)


def normalize_ibkr_execution_event(
    request: FuturesExecutionRequest,
    payload: IBKRExecutionEventPayload,
    *,
    observation_id: FuturesExecutionObservationId,
) -> Result[FuturesExecutionObservation, IBKRFuturesAdapterError]:
    """Normalize IBKR paper evidence; UNKNOWN becomes canonical AMBIGUOUS."""

    if not isinstance(payload, IBKRExecutionEventPayload):
        return Failure(
            IBKRFuturesValidationError("payload must be IBKRExecutionEventPayload")
        )
    state = {
        IBKRExecutionEventType.ACKNOWLEDGED: FuturesExecutionState.ACKNOWLEDGED,
        IBKRExecutionEventType.REJECTED: FuturesExecutionState.REJECTED,
        IBKRExecutionEventType.PARTIAL_FILL: FuturesExecutionState.PARTIALLY_FILLED,
        IBKRExecutionEventType.FILL: FuturesExecutionState.FILLED,
        IBKRExecutionEventType.UNKNOWN: FuturesExecutionState.AMBIGUOUS,
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
        return Failure(IBKRFuturesValidationError(str(construction_error)))
    validated = validate_futures_execution_observation(request, observation)
    if isinstance(validated, Failure):
        validation_error: FuturesAdapterContractError = validated.error
        return Failure(IBKRFuturesValidationError(str(validation_error)))
    return Success(validated.value)


def normalize_ibkr_reconciliation(
    payload: IBKRReconciliationPayload,
) -> Result[FuturesExecutionReconciliation, IBKRFuturesAdapterError]:
    if not isinstance(payload, IBKRReconciliationPayload):
        return Failure(
            IBKRFuturesValidationError("payload must be IBKRReconciliationPayload")
        )
    status = {
        IBKRReconciliationStatus.MATCHED: FuturesExecutionReconciliationStatus.MATCHED,
        IBKRReconciliationStatus.DIVERGED: FuturesExecutionReconciliationStatus.DIVERGED,
        IBKRReconciliationStatus.UNKNOWN: FuturesExecutionReconciliationStatus.AMBIGUOUS,
    }[payload.status]
    try:
        reconciliation = FuturesExecutionReconciliation(
            request_id=payload.request_id,
            status=status,
            reconciled_at=payload.reconciled_at,
            evidence_refs=payload.evidence_refs,
        )
    except FuturesAdapterValidationError as construction_error:
        return Failure(IBKRFuturesValidationError(str(construction_error)))
    return Success(reconciliation)
