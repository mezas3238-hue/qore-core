from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite
from re import fullmatch
from uuid import UUID

from qore.functional.decisions import DecisionId
from qore.infrastructure.client_accounts import (
    ExecutionRuntimeReference,
    TradingAccountId,
)
from qore.infrastructure.hosting_execution_lease import (
    HostingExecutionAuthorityAttestation,
)
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataError,
    MarketDataSnapshotId,
    OhlcSnapshot,
    QuoteSnapshot,
    Timeframe,
)
from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor
from qore.infrastructure.secrets import SecretRef
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class FuturesAdapterContractError(InfrastructureError):
    """Base error for provider-neutral Futures adapter contracts."""

    __slots__ = ()


class FuturesAdapterValidationError(FuturesAdapterContractError):
    """Violation of a Futures adapter contract invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise FuturesAdapterValidationError(f"{field_name} must be UUID")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise FuturesAdapterValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise FuturesAdapterValidationError(f"{field_name} must be timezone-aware")


def _validate_price(value: float, *, field_name: str) -> None:
    if type(value) is not float or not isfinite(value) or value <= 0.0:
        raise FuturesAdapterValidationError(
            f"{field_name} must be a positive finite float"
        )


def _validate_optional_price(value: float | None, *, field_name: str) -> None:
    if value is not None:
        _validate_price(value, field_name=field_name)


@dataclass(frozen=True, slots=True)
class FuturesProviderName:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9.-]*", self.value
        ) is None:
            raise FuturesAdapterValidationError(
                "provider name must use canonical lowercase syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class FuturesProviderContractId:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise FuturesAdapterValidationError(
                "provider contract id must be a non-empty string"
            )
        if self.value != self.value.strip():
            raise FuturesAdapterValidationError(
                "provider contract id must not contain surrounding whitespace"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class FuturesExecutionRequestId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="futures execution request id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FuturesExecutionObservationId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="futures execution observation id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FuturesExecutionEvidenceReference:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="futures execution evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FuturesIdempotencyKey:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="futures idempotency key")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FuturesProviderOrderReference:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise FuturesAdapterValidationError(
                "provider order reference must be non-empty"
            )
        if self.value != self.value.strip():
            raise FuturesAdapterValidationError(
                "provider order reference must not contain surrounding whitespace"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class FuturesAdapterCapability(StrEnum):
    MARKET_DATA = "market_data"
    EXECUTION = "execution"


@dataclass(frozen=True, slots=True)
class FuturesAdapterProfile:
    """Provider-neutral adapter identity/configuration without secret values."""

    adapter_id: AdapterId
    provider: FuturesProviderName
    market_data_source: ExternalSourceDescriptor
    execution_source: ExternalSourceDescriptor
    capabilities: tuple[FuturesAdapterCapability, ...]
    secret_refs: tuple[SecretRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.adapter_id, AdapterId):
            raise FuturesAdapterValidationError("adapter_id must be AdapterId")
        if not isinstance(self.provider, FuturesProviderName):
            raise FuturesAdapterValidationError(
                "provider must be FuturesProviderName"
            )
        if not isinstance(self.market_data_source, ExternalSourceDescriptor):
            raise FuturesAdapterValidationError(
                "market_data_source must be ExternalSourceDescriptor"
            )
        if not self.market_data_source.port_name.value.startswith("market-data"):
            raise FuturesAdapterValidationError(
                "market_data_source must use market-data namespace"
            )
        if not isinstance(self.execution_source, ExternalSourceDescriptor):
            raise FuturesAdapterValidationError(
                "execution_source must be ExternalSourceDescriptor"
            )
        if not self.execution_source.port_name.value.startswith("execution"):
            raise FuturesAdapterValidationError(
                "execution_source must use execution namespace"
            )
        if self.market_data_source.adapter_id != self.adapter_id:
            raise FuturesAdapterValidationError(
                "market-data source must bind adapter profile id"
            )
        if self.execution_source.adapter_id != self.adapter_id:
            raise FuturesAdapterValidationError(
                "execution source must bind adapter profile id"
            )
        if not isinstance(self.capabilities, tuple) or not self.capabilities or any(
            not isinstance(item, FuturesAdapterCapability) for item in self.capabilities
        ):
            raise FuturesAdapterValidationError(
                "capabilities must be a non-empty immutable capability tuple"
            )
        if len(self.capabilities) != len(set(self.capabilities)):
            raise FuturesAdapterValidationError("capabilities must be unique")
        if not isinstance(self.secret_refs, tuple) or any(
            not isinstance(ref, SecretRef) for ref in self.secret_refs
        ):
            raise FuturesAdapterValidationError(
                "secret_refs must contain only canonical SecretRef values"
            )
        if len(self.secret_refs) != len(set(self.secret_refs)):
            raise FuturesAdapterValidationError("secret_refs must be unique")

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.adapter_id.value),
            self.provider.logical_values(),
            self.market_data_source.logical_values(),
            self.execution_source.logical_values(),
            tuple(item.value for item in self.capabilities),
            tuple(ref.logical_values() for ref in self.secret_refs),
        )


@dataclass(frozen=True, slots=True)
class FuturesContractMapping:
    """Provider contract identity mapped to one canonical QORE instrument."""

    provider: FuturesProviderName
    provider_contract_id: FuturesProviderContractId
    instrument: Instrument

    def __post_init__(self) -> None:
        if not isinstance(self.provider, FuturesProviderName):
            raise FuturesAdapterValidationError(
                "mapping provider must be FuturesProviderName"
            )
        if not isinstance(self.provider_contract_id, FuturesProviderContractId):
            raise FuturesAdapterValidationError(
                "provider_contract_id must be FuturesProviderContractId"
            )
        if not isinstance(self.instrument, Instrument):
            raise FuturesAdapterValidationError(
                "mapping instrument must be canonical Instrument"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.provider.logical_values(),
            self.provider_contract_id.logical_values(),
            self.instrument.symbol,
        )


@dataclass(frozen=True, slots=True)
class FuturesQuoteObservation:
    mapping: FuturesContractMapping
    source: ExternalSourceDescriptor
    provider_timestamp: datetime
    received_at: datetime
    bid: float
    ask: float

    def __post_init__(self) -> None:
        if not isinstance(self.mapping, FuturesContractMapping):
            raise FuturesAdapterValidationError(
                "quote mapping must be FuturesContractMapping"
            )
        if not isinstance(self.source, ExternalSourceDescriptor):
            raise FuturesAdapterValidationError(
                "quote source must be ExternalSourceDescriptor"
            )
        if not self.source.port_name.value.startswith("market-data"):
            raise FuturesAdapterValidationError(
                "quote source must use market-data namespace"
            )
        _validate_timestamp(
            self.provider_timestamp,
            field_name="quote provider_timestamp",
        )
        _validate_timestamp(self.received_at, field_name="quote received_at")
        if self.received_at < self.provider_timestamp:
            raise FuturesAdapterValidationError(
                "quote received_at cannot predate provider_timestamp"
            )
        _validate_price(self.bid, field_name="quote bid")
        _validate_price(self.ask, field_name="quote ask")
        if self.bid > self.ask:
            raise FuturesAdapterValidationError("quote bid must not exceed ask")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mapping.logical_values(),
            self.source.logical_values(),
            self.provider_timestamp.isoformat(),
            self.received_at.isoformat(),
            self.bid,
            self.ask,
        )


@dataclass(frozen=True, slots=True)
class FuturesTradeObservation:
    mapping: FuturesContractMapping
    source: ExternalSourceDescriptor
    provider_timestamp: datetime
    received_at: datetime
    price: float
    quantity: int

    def __post_init__(self) -> None:
        if not isinstance(self.mapping, FuturesContractMapping):
            raise FuturesAdapterValidationError(
                "trade mapping must be FuturesContractMapping"
            )
        if not isinstance(self.source, ExternalSourceDescriptor):
            raise FuturesAdapterValidationError(
                "trade source must be ExternalSourceDescriptor"
            )
        if not self.source.port_name.value.startswith("market-data"):
            raise FuturesAdapterValidationError(
                "trade source must use market-data namespace"
            )
        _validate_timestamp(
            self.provider_timestamp,
            field_name="trade provider_timestamp",
        )
        _validate_timestamp(self.received_at, field_name="trade received_at")
        if self.received_at < self.provider_timestamp:
            raise FuturesAdapterValidationError(
                "trade received_at cannot predate provider_timestamp"
            )
        _validate_price(self.price, field_name="trade price")
        if type(self.quantity) is not int or self.quantity <= 0:
            raise FuturesAdapterValidationError(
                "trade quantity must be a positive integer"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mapping.logical_values(),
            self.source.logical_values(),
            self.provider_timestamp.isoformat(),
            self.received_at.isoformat(),
            self.price,
            self.quantity,
        )


@dataclass(frozen=True, slots=True)
class FuturesBarObservation:
    mapping: FuturesContractMapping
    source: ExternalSourceDescriptor
    timeframe: Timeframe
    opened_at: datetime
    closed_at: datetime
    received_at: datetime
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        if not isinstance(self.mapping, FuturesContractMapping):
            raise FuturesAdapterValidationError(
                "bar mapping must be FuturesContractMapping"
            )
        if not isinstance(self.source, ExternalSourceDescriptor):
            raise FuturesAdapterValidationError(
                "bar source must be ExternalSourceDescriptor"
            )
        if not self.source.port_name.value.startswith("market-data"):
            raise FuturesAdapterValidationError(
                "bar source must use market-data namespace"
            )
        if not isinstance(self.timeframe, Timeframe):
            raise FuturesAdapterValidationError("bar timeframe must be Timeframe")
        _validate_timestamp(self.opened_at, field_name="bar opened_at")
        _validate_timestamp(self.closed_at, field_name="bar closed_at")
        _validate_timestamp(self.received_at, field_name="bar received_at")
        if self.closed_at <= self.opened_at:
            raise FuturesAdapterValidationError(
                "bar closed_at must be after opened_at"
            )
        if (self.closed_at - self.opened_at).total_seconds() != self.timeframe.seconds:
            raise FuturesAdapterValidationError(
                "bar interval must exactly match timeframe"
            )
        if self.received_at < self.closed_at:
            raise FuturesAdapterValidationError(
                "closed bar received_at cannot predate closed_at"
            )
        _validate_price(self.open, field_name="bar open")
        _validate_price(self.high, field_name="bar high")
        _validate_price(self.low, field_name="bar low")
        _validate_price(self.close, field_name="bar close")
        if self.low > self.high:
            raise FuturesAdapterValidationError("bar low must not exceed high")
        if not self.low <= self.open <= self.high:
            raise FuturesAdapterValidationError(
                "bar open must be within low/high"
            )
        if not self.low <= self.close <= self.high:
            raise FuturesAdapterValidationError(
                "bar close must be within low/high"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mapping.logical_values(),
            self.source.logical_values(),
            self.timeframe.seconds,
            self.opened_at.isoformat(),
            self.closed_at.isoformat(),
            self.received_at.isoformat(),
            self.open,
            self.high,
            self.low,
            self.close,
        )


class FuturesExecutionEnvironment(StrEnum):
    PAPER = "paper"
    SIMULATION = "simulation"


class FuturesOrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class FuturesOrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class FuturesTimeInForce(StrEnum):
    DAY = "day"
    GTC = "gtc"


@dataclass(frozen=True, slots=True)
class FuturesExecutionRequest:
    """Translation input for an already-authorized Core trading action."""

    request_id: FuturesExecutionRequestId
    account_id: TradingAccountId
    runtime_ref: ExecutionRuntimeReference
    decision_id: DecisionId
    authority: HostingExecutionAuthorityAttestation
    environment: FuturesExecutionEnvironment
    mapping: FuturesContractMapping
    side: FuturesOrderSide
    quantity: int
    order_type: FuturesOrderType
    time_in_force: FuturesTimeInForce
    limit_price: float | None
    stop_price: float | None
    idempotency_key: FuturesIdempotencyKey
    requested_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, FuturesExecutionRequestId):
            raise FuturesAdapterValidationError(
                "request_id must be FuturesExecutionRequestId"
            )
        if not isinstance(self.account_id, TradingAccountId):
            raise FuturesAdapterValidationError(
                "account_id must be TradingAccountId"
            )
        if not isinstance(self.runtime_ref, ExecutionRuntimeReference):
            raise FuturesAdapterValidationError(
                "runtime_ref must be ExecutionRuntimeReference"
            )
        if not isinstance(self.decision_id, DecisionId):
            raise FuturesAdapterValidationError(
                "decision_id must be canonical DecisionId"
            )
        if not isinstance(self.authority, HostingExecutionAuthorityAttestation):
            raise FuturesAdapterValidationError(
                "authority must be HostingExecutionAuthorityAttestation"
            )
        if (
            self.authority.account_id != self.account_id
            or self.authority.runtime_ref != self.runtime_ref
        ):
            raise FuturesAdapterValidationError(
                "execution authority scope must match request account/runtime"
            )
        if not isinstance(self.environment, FuturesExecutionEnvironment):
            raise FuturesAdapterValidationError(
                "environment must be FuturesExecutionEnvironment"
            )
        if not isinstance(self.mapping, FuturesContractMapping):
            raise FuturesAdapterValidationError(
                "mapping must be FuturesContractMapping"
            )
        if not isinstance(self.side, FuturesOrderSide):
            raise FuturesAdapterValidationError("side must be FuturesOrderSide")
        if type(self.quantity) is not int or self.quantity <= 0:
            raise FuturesAdapterValidationError(
                "execution quantity must be a positive integer"
            )
        if not isinstance(self.order_type, FuturesOrderType):
            raise FuturesAdapterValidationError(
                "order_type must be FuturesOrderType"
            )
        if not isinstance(self.time_in_force, FuturesTimeInForce):
            raise FuturesAdapterValidationError(
                "time_in_force must be FuturesTimeInForce"
            )
        _validate_optional_price(self.limit_price, field_name="limit_price")
        _validate_optional_price(self.stop_price, field_name="stop_price")
        if self.order_type is FuturesOrderType.MARKET:
            if self.limit_price is not None or self.stop_price is not None:
                raise FuturesAdapterValidationError(
                    "MARKET request cannot carry limit/stop price"
                )
        elif self.order_type is FuturesOrderType.LIMIT:
            if self.limit_price is None or self.stop_price is not None:
                raise FuturesAdapterValidationError(
                    "LIMIT request requires only limit_price"
                )
        elif self.stop_price is None or self.limit_price is not None:
            raise FuturesAdapterValidationError(
                "STOP request requires only stop_price"
            )
        if not isinstance(self.idempotency_key, FuturesIdempotencyKey):
            raise FuturesAdapterValidationError(
                "idempotency_key must be FuturesIdempotencyKey"
            )
        _validate_timestamp(self.requested_at, field_name="request requested_at")
        if self.requested_at < self.authority.evaluated_at:
            raise FuturesAdapterValidationError(
                "request cannot predate authority attestation"
            )

    def payload_fingerprint(self) -> tuple[object, ...]:
        return (
            self.account_id.logical_values(),
            self.runtime_ref.logical_values(),
            str(self.decision_id.value),
            self.authority.logical_values(),
            self.environment.value,
            self.mapping.logical_values(),
            self.side.value,
            self.quantity,
            self.order_type.value,
            self.time_in_force.value,
            self.limit_price,
            self.stop_price,
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.request_id.logical_values(),
            self.payload_fingerprint(),
            self.idempotency_key.logical_values(),
            self.requested_at.isoformat(),
        )


class FuturesExecutionState(StrEnum):
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class FuturesExecutionObservation:
    observation_id: FuturesExecutionObservationId
    request_id: FuturesExecutionRequestId
    state: FuturesExecutionState
    provider_order_ref: FuturesProviderOrderReference | None
    cumulative_filled_quantity: int
    observed_at: datetime
    evidence_ref: FuturesExecutionEvidenceReference

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, FuturesExecutionObservationId):
            raise FuturesAdapterValidationError(
                "observation_id must be FuturesExecutionObservationId"
            )
        if not isinstance(self.request_id, FuturesExecutionRequestId):
            raise FuturesAdapterValidationError(
                "observation request_id must be FuturesExecutionRequestId"
            )
        if not isinstance(self.state, FuturesExecutionState):
            raise FuturesAdapterValidationError(
                "state must be FuturesExecutionState"
            )
        if self.provider_order_ref is not None and not isinstance(
            self.provider_order_ref,
            FuturesProviderOrderReference,
        ):
            raise FuturesAdapterValidationError(
                "provider_order_ref must be FuturesProviderOrderReference or None"
            )
        if (
            type(self.cumulative_filled_quantity) is not int
            or self.cumulative_filled_quantity < 0
        ):
            raise FuturesAdapterValidationError(
                "cumulative_filled_quantity must be a non-negative integer"
            )
        if self.state is FuturesExecutionState.ACKNOWLEDGED:
            if self.provider_order_ref is None or self.cumulative_filled_quantity != 0:
                raise FuturesAdapterValidationError(
                    "ACKNOWLEDGED requires provider order ref and zero fill"
                )
        elif self.state is FuturesExecutionState.REJECTED:
            if self.cumulative_filled_quantity != 0:
                raise FuturesAdapterValidationError(
                    "REJECTED observation cannot carry fills"
                )
        elif self.state in {
            FuturesExecutionState.PARTIALLY_FILLED,
            FuturesExecutionState.FILLED,
        }:
            if self.provider_order_ref is None or self.cumulative_filled_quantity <= 0:
                raise FuturesAdapterValidationError(
                    "fill observation requires provider order ref and positive fill"
                )
        _validate_timestamp(self.observed_at, field_name="execution observed_at")
        if not isinstance(self.evidence_ref, FuturesExecutionEvidenceReference):
            raise FuturesAdapterValidationError(
                "evidence_ref must be FuturesExecutionEvidenceReference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.observation_id.logical_values(),
            self.request_id.logical_values(),
            self.state.value,
            (
                self.provider_order_ref.logical_values()
                if self.provider_order_ref is not None
                else None
            ),
            self.cumulative_filled_quantity,
            self.observed_at.isoformat(),
            self.evidence_ref.logical_values(),
        )


class FuturesExecutionReconciliationStatus(StrEnum):
    MATCHED = "matched"
    DIVERGED = "diverged"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class FuturesExecutionReconciliation:
    request_id: FuturesExecutionRequestId
    status: FuturesExecutionReconciliationStatus
    reconciled_at: datetime
    evidence_refs: tuple[FuturesExecutionEvidenceReference, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, FuturesExecutionRequestId):
            raise FuturesAdapterValidationError(
                "reconciliation request_id must be FuturesExecutionRequestId"
            )
        if not isinstance(self.status, FuturesExecutionReconciliationStatus):
            raise FuturesAdapterValidationError(
                "status must be FuturesExecutionReconciliationStatus"
            )
        _validate_timestamp(self.reconciled_at, field_name="reconciled_at")
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs or any(
            not isinstance(ref, FuturesExecutionEvidenceReference)
            for ref in self.evidence_refs
        ):
            raise FuturesAdapterValidationError(
                "reconciliation requires immutable non-empty evidence refs"
            )
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise FuturesAdapterValidationError(
                "reconciliation evidence refs must be unique"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.request_id.logical_values(),
            self.status.value,
            self.reconciled_at.isoformat(),
            tuple(ref.logical_values() for ref in self.evidence_refs),
        )


class FuturesReplayDisposition(StrEnum):
    NEW_REQUEST_UNSEEN = "new_request_unseen"
    DUPLICATE_ALREADY_KNOWN = "duplicate_already_known"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"


def classify_futures_request_replay(
    request: FuturesExecutionRequest,
    known_request: FuturesExecutionRequest | None,
) -> FuturesReplayDisposition:
    """Classify replay evidence only; never retries or redispatches an order."""

    if not isinstance(request, FuturesExecutionRequest):
        raise FuturesAdapterValidationError(
            "request must be FuturesExecutionRequest"
        )
    if known_request is None:
        return FuturesReplayDisposition.NEW_REQUEST_UNSEEN
    if not isinstance(known_request, FuturesExecutionRequest):
        raise FuturesAdapterValidationError(
            "known_request must be FuturesExecutionRequest or None"
        )
    if request.idempotency_key != known_request.idempotency_key:
        return FuturesReplayDisposition.NEW_REQUEST_UNSEEN
    if request.payload_fingerprint() == known_request.payload_fingerprint():
        return FuturesReplayDisposition.DUPLICATE_ALREADY_KNOWN
    return FuturesReplayDisposition.IDEMPOTENCY_CONFLICT


def validate_futures_execution_observation(
    request: FuturesExecutionRequest,
    observation: FuturesExecutionObservation,
) -> Result[FuturesExecutionObservation, FuturesAdapterContractError]:
    """Validate provider execution evidence without retry or redispatch semantics."""

    if not isinstance(request, FuturesExecutionRequest):
        return Failure(
            FuturesAdapterValidationError(
                "request must be FuturesExecutionRequest"
            )
        )
    if not isinstance(observation, FuturesExecutionObservation):
        return Failure(
            FuturesAdapterValidationError(
                "observation must be FuturesExecutionObservation"
            )
        )
    if observation.request_id != request.request_id:
        return Failure(
            FuturesAdapterValidationError(
                "execution observation must bind exact request id"
            )
        )
    if observation.observed_at < request.requested_at:
        return Failure(
            FuturesAdapterValidationError(
                "execution observation cannot predate request"
            )
        )
    if observation.cumulative_filled_quantity > request.quantity:
        return Failure(
            FuturesAdapterValidationError(
                "cumulative fill cannot exceed requested quantity"
            )
        )
    if observation.state is FuturesExecutionState.FILLED:
        if observation.cumulative_filled_quantity != request.quantity:
            return Failure(
                FuturesAdapterValidationError(
                    "FILLED observation must equal requested quantity"
                )
            )
    if observation.state is FuturesExecutionState.PARTIALLY_FILLED:
        if observation.cumulative_filled_quantity >= request.quantity:
            return Failure(
                FuturesAdapterValidationError(
                    "PARTIALLY_FILLED must remain below requested quantity"
                )
            )
    return Success(observation)


def normalize_futures_quote(
    observation: FuturesQuoteObservation,
    *,
    snapshot_id: MarketDataSnapshotId,
) -> Result[QuoteSnapshot, FuturesAdapterContractError]:
    """Translate provider-neutral Futures quote evidence into canonical QORE market data."""

    if not isinstance(observation, FuturesQuoteObservation):
        return Failure(
            FuturesAdapterValidationError(
                "observation must be FuturesQuoteObservation"
            )
        )
    try:
        snapshot = QuoteSnapshot(
            snapshot_id=snapshot_id,
            instrument=observation.mapping.instrument,
            source=observation.source,
            observed_at=observation.provider_timestamp,
            bid=observation.bid,
            ask=observation.ask,
        )
    except MarketDataError as error:
        return Failure(FuturesAdapterValidationError(str(error)))
    return Success(snapshot)


def normalize_futures_bar(
    observation: FuturesBarObservation,
    *,
    snapshot_id: MarketDataSnapshotId,
) -> Result[OhlcSnapshot, FuturesAdapterContractError]:
    """Translate provider-neutral Futures bar evidence into canonical QORE OHLC."""

    if not isinstance(observation, FuturesBarObservation):
        return Failure(
            FuturesAdapterValidationError(
                "observation must be FuturesBarObservation"
            )
        )
    try:
        snapshot = OhlcSnapshot(
            snapshot_id=snapshot_id,
            instrument=observation.mapping.instrument,
            source=observation.source,
            timeframe=observation.timeframe,
            opened_at=observation.opened_at,
            closed_at=observation.closed_at,
            open=observation.open,
            high=observation.high,
            low=observation.low,
            close=observation.close,
        )
    except MarketDataError as error:
        return Failure(FuturesAdapterValidationError(str(error)))
    return Success(snapshot)
