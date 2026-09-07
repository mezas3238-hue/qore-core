from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.execution_boundary import (
    ExecutionBoundaryError,
    ExecutionReceiptId,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderSide,
)
from qore.kernel.result import Failure, Result, Success

_PROVIDER_ORDER_REF_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._-]*"
_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password",
    "secret",
    "token",
)


class CTraderDemoExecutionError(ExecutionBoundaryError):
    """Base error for the cTrader DEMO execution boundary."""

    __slots__ = ()


class CTraderDemoExecutionValidationError(CTraderDemoExecutionError):
    """Violation of a cTrader DEMO execution contract invariant."""

    __slots__ = ()


class CTraderDemoExecutionConflictError(CTraderDemoExecutionError):
    """Typed idempotency or provider-state conflict."""

    __slots__ = ()


class CTraderDemoExecutionUnknownOutcomeError(CTraderDemoExecutionError):
    """A mutating attempt reached an indeterminate external outcome."""

    __slots__ = ()


class CTraderDemoExecutionNotAcceptedError(CTraderDemoExecutionError):
    """Provider acknowledged a request but did not leave an accepted execution."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise CTraderDemoExecutionValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CTraderDemoExecutionValidationError(f"{field_name} must be timezone-aware")


def _validate_provider_ref(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or fullmatch(_PROVIDER_ORDER_REF_PATTERN, value) is None:
        raise CTraderDemoExecutionValidationError(
            f"{field_name} must be a stable non-secret provider reference"
        )


def _validate_reason(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CTraderDemoExecutionValidationError("cTrader DEMO reason must be a non-empty string")
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise CTraderDemoExecutionValidationError(
            "cTrader DEMO reason must not contain sensitive material"
        )


def ctrader_demo_account_fingerprint(account_ref: str) -> str:
    """Return a deterministic non-secret fingerprint for a cTrader account ref."""
    if not isinstance(account_ref, str) or not account_ref:
        raise CTraderDemoExecutionValidationError(
            "account fingerprint requires a non-empty account ref"
        )
    digest = hashlib.sha256(account_ref.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:24]}"


class CTraderDemoOrderDisposition(StrEnum):
    """Provider-observable definitive outcome of one submitted order."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class CTraderDemoOrderState(StrEnum):
    """Closed QORE-facing lifecycle for one cTrader DEMO execution."""

    REQUESTED = "requested"
    LOCALLY_BLOCKED = "locally_blocked"
    ATTEMPT_STARTED = "attempt_started"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    OUTCOME_UNKNOWN = "outcome_unknown"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    RESOLVED = "resolved"
    CONTAINED = "contained"


_DEFINITIVE_DISPOSITIONS = frozenset(
    {
        CTraderDemoOrderDisposition.ACCEPTED,
        CTraderDemoOrderDisposition.REJECTED,
        CTraderDemoOrderDisposition.PARTIALLY_FILLED,
        CTraderDemoOrderDisposition.FILLED,
        CTraderDemoOrderDisposition.CANCELLED,
        CTraderDemoOrderDisposition.EXPIRED,
    }
)

_DISPOSITION_ORDER_STATE = {
    CTraderDemoOrderDisposition.ACCEPTED: CTraderDemoOrderState.ACCEPTED,
    CTraderDemoOrderDisposition.REJECTED: CTraderDemoOrderState.REJECTED,
    CTraderDemoOrderDisposition.PARTIALLY_FILLED: CTraderDemoOrderState.PARTIALLY_FILLED,
    CTraderDemoOrderDisposition.FILLED: CTraderDemoOrderState.FILLED,
    CTraderDemoOrderDisposition.CANCELLED: CTraderDemoOrderState.CANCELLED,
    CTraderDemoOrderDisposition.EXPIRED: CTraderDemoOrderState.EXPIRED,
}


def order_state_for_disposition(
    disposition: CTraderDemoOrderDisposition,
) -> CTraderDemoOrderState:
    """Project a definitive provider disposition into its QORE order state."""
    if not isinstance(disposition, CTraderDemoOrderDisposition):
        raise CTraderDemoExecutionValidationError(
            "order state projection requires CTraderDemoOrderDisposition"
        )
    return _DISPOSITION_ORDER_STATE[disposition]


class CTraderDemoAttemptState(StrEnum):
    """Deterministic mutation-attempt lifecycle (PHASE E)."""

    NOT_ATTEMPTED = "not_attempted"
    ATTEMPT_STARTED = "attempt_started"
    DEFINITIVE_OUTCOME = "definitive_outcome"
    OUTCOME_UNKNOWN = "outcome_unknown"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    RESOLVED = "resolved"
    CONTAINED = "contained"


_ATTEMPT_TRANSITIONS: dict[CTraderDemoAttemptState, frozenset[CTraderDemoAttemptState]] = {
    CTraderDemoAttemptState.NOT_ATTEMPTED: frozenset({CTraderDemoAttemptState.ATTEMPT_STARTED}),
    CTraderDemoAttemptState.ATTEMPT_STARTED: frozenset(
        {
            CTraderDemoAttemptState.DEFINITIVE_OUTCOME,
            CTraderDemoAttemptState.OUTCOME_UNKNOWN,
        }
    ),
    CTraderDemoAttemptState.DEFINITIVE_OUTCOME: frozenset(),
    CTraderDemoAttemptState.OUTCOME_UNKNOWN: frozenset(
        {CTraderDemoAttemptState.RECONCILIATION_REQUIRED}
    ),
    CTraderDemoAttemptState.RECONCILIATION_REQUIRED: frozenset(
        {
            CTraderDemoAttemptState.RESOLVED,
            CTraderDemoAttemptState.CONTAINED,
        }
    ),
    CTraderDemoAttemptState.RESOLVED: frozenset(),
    CTraderDemoAttemptState.CONTAINED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class CTraderDemoMutationAttempt:
    """Immutable in-memory attempt record for one exact execution intent."""

    idempotency_key: ExecutionIdempotencyKey
    receipt_id: ExecutionReceiptId
    submission_logical: tuple[object, ...]
    state: CTraderDemoAttemptState
    transitioned_at: datetime
    provider_order_ref: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.idempotency_key, ExecutionIdempotencyKey):
            raise CTraderDemoExecutionValidationError(
                "attempt idempotency_key must be ExecutionIdempotencyKey"
            )
        if not isinstance(self.receipt_id, ExecutionReceiptId):
            raise CTraderDemoExecutionValidationError(
                "attempt receipt_id must be ExecutionReceiptId"
            )
        if not isinstance(self.submission_logical, tuple):
            raise CTraderDemoExecutionValidationError("attempt submission_logical must be a tuple")
        if not isinstance(self.state, CTraderDemoAttemptState):
            raise CTraderDemoExecutionValidationError(
                "attempt state must be CTraderDemoAttemptState"
            )
        _validate_timestamp(self.transitioned_at, field_name="attempt transitioned_at")
        if self.provider_order_ref is not None:
            _validate_provider_ref(self.provider_order_ref, field_name="attempt provider_order_ref")
        if self.reason is not None:
            _validate_reason(self.reason)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.idempotency_key.logical_values(),
            self.receipt_id.logical_values(),
            self.submission_logical,
            self.state.value,
            self.transitioned_at.isoformat(),
            self.provider_order_ref,
            self.reason,
        )


def transition_ctrader_demo_attempt(
    attempt: CTraderDemoMutationAttempt,
    to_state: CTraderDemoAttemptState,
    *,
    transitioned_at: datetime,
    provider_order_ref: str | None = None,
    reason: str | None = None,
) -> Result[CTraderDemoMutationAttempt, CTraderDemoExecutionError]:
    """Transition an attempt through the closed fail-closed lifecycle."""
    if not isinstance(attempt, CTraderDemoMutationAttempt):
        return Failure(
            CTraderDemoExecutionValidationError(
                "attempt transition requires CTraderDemoMutationAttempt"
            )
        )
    if not isinstance(to_state, CTraderDemoAttemptState):
        return Failure(
            CTraderDemoExecutionValidationError(
                "attempt transition requires CTraderDemoAttemptState"
            )
        )
    try:
        _validate_timestamp(transitioned_at, field_name="attempt transitioned_at")
    except CTraderDemoExecutionError as error:
        return Failure(error)
    if transitioned_at <= attempt.transitioned_at:
        return Failure(
            CTraderDemoExecutionValidationError(
                "attempt transition must be after the current attempt state"
            )
        )
    if to_state not in _ATTEMPT_TRANSITIONS[attempt.state]:
        return Failure(
            CTraderDemoExecutionConflictError(
                f"invalid attempt transition: {attempt.state.value} -> {to_state.value}"
            )
        )
    if provider_order_ref is not None:
        try:
            _validate_provider_ref(provider_order_ref, field_name="attempt provider_order_ref")
        except CTraderDemoExecutionError as error:
            return Failure(error)
    if reason is not None:
        try:
            _validate_reason(reason)
        except CTraderDemoExecutionError as error:
            return Failure(error)
    try:
        next_attempt = CTraderDemoMutationAttempt(
            idempotency_key=attempt.idempotency_key,
            receipt_id=attempt.receipt_id,
            submission_logical=attempt.submission_logical,
            state=to_state,
            transitioned_at=transitioned_at,
            provider_order_ref=(
                provider_order_ref if provider_order_ref is not None else attempt.provider_order_ref
            ),
            reason=reason if reason is not None else attempt.reason,
        )
    except CTraderDemoExecutionError as error:
        return Failure(error)
    return Success(next_attempt)


@dataclass(frozen=True, slots=True)
class CTraderDemoExecutionOutcome:
    """Sanitized definitive provider evidence for one submitted execution."""

    account: MarketTestAccountIdentity
    provider_order_ref: str
    disposition: CTraderDemoOrderDisposition
    created_at: datetime
    recorded_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.account, MarketTestAccountIdentity):
            raise CTraderDemoExecutionValidationError(
                "execution outcome requires MarketTestAccountIdentity"
            )
        if self.account.provider_key != "ctrader-demo":
            raise CTraderDemoExecutionValidationError(
                "execution outcome provider must be ctrader-demo"
            )
        if self.account.environment is not MarketRuntimeEnvironment.DEMO:
            raise CTraderDemoExecutionValidationError("execution outcome environment must be demo")
        _validate_provider_ref(
            self.provider_order_ref, field_name="execution outcome provider_order_ref"
        )
        if not isinstance(self.disposition, CTraderDemoOrderDisposition):
            raise CTraderDemoExecutionValidationError(
                "execution outcome requires explicit disposition"
            )
        _validate_timestamp(self.created_at, field_name="execution outcome created_at")
        _validate_timestamp(self.recorded_at, field_name="execution outcome recorded_at")
        if self.recorded_at < self.created_at:
            raise CTraderDemoExecutionValidationError(
                "execution outcome recorded_at must not predate creation"
            )

    @property
    def account_fingerprint(self) -> str:
        return ctrader_demo_account_fingerprint(self.account.account_ref)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account.logical_values(),
            self.provider_order_ref,
            self.disposition.value,
            self.created_at.isoformat(),
            self.recorded_at.isoformat(),
        )

    def sanitized_values(self) -> tuple[object, ...]:
        return (
            self.account.provider_key,
            self.account.environment.value,
            self.account_fingerprint,
            self.provider_order_ref,
            self.disposition.value,
            self.created_at.isoformat(),
            self.recorded_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class CTraderDemoFillObservation:
    """Trustworthy provider fill evidence correlated to one exact execution."""

    receipt_id: ExecutionReceiptId
    idempotency_key: ExecutionIdempotencyKey
    account: MarketTestAccountIdentity
    instrument: ExecutionInstrument
    side: OrderSide
    provider_order_ref: str
    fill_ref: str
    fill_quantity: Decimal
    cumulative_quantity: Decimal
    fill_price: Decimal
    provider_timestamp: datetime
    received_at: datetime
    is_complete: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.receipt_id, ExecutionReceiptId):
            raise CTraderDemoExecutionValidationError("fill receipt_id must be ExecutionReceiptId")
        if not isinstance(self.idempotency_key, ExecutionIdempotencyKey):
            raise CTraderDemoExecutionValidationError(
                "fill idempotency_key must be ExecutionIdempotencyKey"
            )
        if not isinstance(self.account, MarketTestAccountIdentity):
            raise CTraderDemoExecutionValidationError(
                "fill account must be MarketTestAccountIdentity"
            )
        if self.account.provider_key != "ctrader-demo":
            raise CTraderDemoExecutionValidationError("fill provider must be ctrader-demo")
        if self.account.environment is not MarketRuntimeEnvironment.DEMO:
            raise CTraderDemoExecutionValidationError("fill environment must be demo")
        if not isinstance(self.instrument, ExecutionInstrument):
            raise CTraderDemoExecutionValidationError("fill instrument must be ExecutionInstrument")
        if not isinstance(self.side, OrderSide):
            raise CTraderDemoExecutionValidationError("fill side must be OrderSide")
        _validate_provider_ref(self.provider_order_ref, field_name="fill provider_order_ref")
        _validate_provider_ref(self.fill_ref, field_name="fill fill_ref")
        if self.fill_ref == self.provider_order_ref:
            raise CTraderDemoExecutionValidationError(
                "fill fill_ref must not equal provider_order_ref"
            )
        for field_name, value in (
            ("fill fill_quantity", self.fill_quantity),
            ("fill cumulative_quantity", self.cumulative_quantity),
            ("fill fill_price", self.fill_price),
        ):
            if not isinstance(value, Decimal):
                raise CTraderDemoExecutionValidationError(f"{field_name} must be Decimal")
        if not self.fill_quantity.is_finite() or self.fill_quantity <= Decimal("0"):
            raise CTraderDemoExecutionValidationError(
                "fill fill_quantity must be finite and positive"
            )
        if not self.cumulative_quantity.is_finite() or self.cumulative_quantity < Decimal("0"):
            raise CTraderDemoExecutionValidationError(
                "fill cumulative_quantity must be finite and non-negative"
            )
        if self.cumulative_quantity < self.fill_quantity:
            raise CTraderDemoExecutionValidationError(
                "fill cumulative_quantity must not be below fill_quantity"
            )
        if not self.fill_price.is_finite() or self.fill_price <= Decimal("0"):
            raise CTraderDemoExecutionValidationError("fill fill_price must be finite and positive")
        _validate_timestamp(self.provider_timestamp, field_name="fill provider_timestamp")
        _validate_timestamp(self.received_at, field_name="fill received_at")
        if self.received_at < self.provider_timestamp:
            raise CTraderDemoExecutionValidationError(
                "fill received_at must not predate provider_timestamp"
            )
        if type(self.is_complete) is not bool:
            raise CTraderDemoExecutionValidationError("fill is_complete must be a strict bool")

    @property
    def account_fingerprint(self) -> str:
        return ctrader_demo_account_fingerprint(self.account.account_ref)

    def provider_identity(self) -> tuple[object, ...]:
        """Provider-relative identity of one fill, excluding local receive time."""
        return (
            self.receipt_id.logical_values(),
            self.idempotency_key.logical_values(),
            self.account.logical_values(),
            self.instrument.value,
            self.side.value,
            self.provider_order_ref,
            self.fill_ref,
            format(self.fill_quantity, "f"),
            format(self.cumulative_quantity, "f"),
            format(self.fill_price, "f"),
            self.provider_timestamp.isoformat(),
            self.is_complete,
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.receipt_id.logical_values(),
            self.idempotency_key.logical_values(),
            self.account.logical_values(),
            self.instrument.value,
            self.side.value,
            self.provider_order_ref,
            self.fill_ref,
            format(self.fill_quantity, "f"),
            format(self.cumulative_quantity, "f"),
            format(self.fill_price, "f"),
            self.provider_timestamp.isoformat(),
            self.received_at.isoformat(),
            self.is_complete,
        )

    def sanitized_values(self) -> tuple[object, ...]:
        return (
            self.receipt_id.logical_values(),
            self.idempotency_key.logical_values(),
            self.account.provider_key,
            self.account.environment.value,
            self.account_fingerprint,
            self.instrument.value,
            self.side.value,
            self.provider_order_ref,
            self.fill_ref,
            format(self.fill_quantity, "f"),
            format(self.cumulative_quantity, "f"),
            format(self.fill_price, "f"),
            self.provider_timestamp.isoformat(),
            self.received_at.isoformat(),
            self.is_complete,
        )


class CTraderDemoFillReconciliationStatus(StrEnum):
    MATCHED = "matched"
    PARTIAL = "partial"
    DIVERGED = "diverged"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class CTraderDemoFillReconciliation:
    """Pure fill-vs-intent comparison. It never performs corrective execution."""

    status: CTraderDemoFillReconciliationStatus
    reconciled_at: datetime
    requested_quantity: Decimal
    filled_quantity: Decimal
    issues: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, CTraderDemoFillReconciliationStatus):
            raise CTraderDemoExecutionValidationError("fill reconciliation status must be valid")
        _validate_timestamp(self.reconciled_at, field_name="fill reconciled_at")
        if not isinstance(self.requested_quantity, Decimal):
            raise CTraderDemoExecutionValidationError(
                "fill reconciliation requested_quantity must be Decimal"
            )
        if not self.requested_quantity.is_finite() or self.requested_quantity <= Decimal("0"):
            raise CTraderDemoExecutionValidationError(
                "fill reconciliation requested_quantity must be finite and positive"
            )
        if not isinstance(self.filled_quantity, Decimal):
            raise CTraderDemoExecutionValidationError(
                "fill reconciliation filled_quantity must be Decimal"
            )
        if not self.filled_quantity.is_finite() or self.filled_quantity < Decimal("0"):
            raise CTraderDemoExecutionValidationError(
                "fill reconciliation filled_quantity must be finite and non-negative"
            )
        if not isinstance(self.issues, tuple) or any(
            not isinstance(issue, str) or not issue for issue in self.issues
        ):
            raise CTraderDemoExecutionValidationError(
                "fill reconciliation issues must be non-empty strings in a tuple"
            )
        if self.status is CTraderDemoFillReconciliationStatus.MATCHED and self.issues:
            raise CTraderDemoExecutionValidationError(
                "matched fill reconciliation must not carry issues"
            )
        if self.status is not CTraderDemoFillReconciliationStatus.MATCHED and not self.issues:
            raise CTraderDemoExecutionValidationError(
                "non-matched fill reconciliation requires at least one issue"
            )

    @property
    def requires_manual_action(self) -> bool:
        return self.status is not CTraderDemoFillReconciliationStatus.MATCHED

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.status.value,
            self.reconciled_at.isoformat(),
            format(self.requested_quantity, "f"),
            format(self.filled_quantity, "f"),
            self.issues,
        )


def reconcile_ctrader_demo_fills(
    requested_quantity: Decimal,
    filled_quantity: Decimal,
    *,
    is_complete: bool,
    reconciled_at: datetime,
) -> Result[CTraderDemoFillReconciliation, CTraderDemoExecutionError]:
    """Reconcile cumulative fill quantity against exact requested quantity."""
    if not isinstance(requested_quantity, Decimal):
        return Failure(
            CTraderDemoExecutionValidationError(
                "fill reconciliation requires requested_quantity Decimal"
            )
        )
    if not requested_quantity.is_finite() or requested_quantity <= Decimal("0"):
        return Failure(
            CTraderDemoExecutionValidationError("requested_quantity must be finite and positive")
        )
    if not isinstance(filled_quantity, Decimal):
        return Failure(
            CTraderDemoExecutionValidationError(
                "fill reconciliation requires filled_quantity Decimal"
            )
        )
    if not filled_quantity.is_finite() or filled_quantity < Decimal("0"):
        return Failure(
            CTraderDemoExecutionValidationError("filled_quantity must be finite and non-negative")
        )
    if type(is_complete) is not bool:
        return Failure(CTraderDemoExecutionValidationError("is_complete must be a strict bool"))
    try:
        _validate_timestamp(reconciled_at, field_name="fill reconciled_at")
    except CTraderDemoExecutionError as error:
        return Failure(error)

    if filled_quantity > requested_quantity:
        return Success(
            CTraderDemoFillReconciliation(
                status=CTraderDemoFillReconciliationStatus.DIVERGED,
                reconciled_at=reconciled_at,
                requested_quantity=requested_quantity,
                filled_quantity=filled_quantity,
                issues=("fill_quantity_exceeds_requested_quantity",),
            )
        )
    if is_complete:
        if filled_quantity == requested_quantity:
            return Success(
                CTraderDemoFillReconciliation(
                    status=CTraderDemoFillReconciliationStatus.MATCHED,
                    reconciled_at=reconciled_at,
                    requested_quantity=requested_quantity,
                    filled_quantity=filled_quantity,
                )
            )
        return Success(
            CTraderDemoFillReconciliation(
                status=CTraderDemoFillReconciliationStatus.DIVERGED,
                reconciled_at=reconciled_at,
                requested_quantity=requested_quantity,
                filled_quantity=filled_quantity,
                issues=("complete_fill_below_requested_quantity",),
            )
        )
    if filled_quantity == Decimal("0"):
        return Success(
            CTraderDemoFillReconciliation(
                status=CTraderDemoFillReconciliationStatus.MISSING,
                reconciled_at=reconciled_at,
                requested_quantity=requested_quantity,
                filled_quantity=filled_quantity,
                issues=("no_fill_evidence",),
            )
        )
    return Success(
        CTraderDemoFillReconciliation(
            status=CTraderDemoFillReconciliationStatus.PARTIAL,
            reconciled_at=reconciled_at,
            requested_quantity=requested_quantity,
            filled_quantity=filled_quantity,
            issues=("partial_fill_remaining",),
        )
    )
