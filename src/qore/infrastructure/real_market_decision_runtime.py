from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from qore.core.application import CoreApplication
from qore.infrastructure.controlled_execution import (
    ControlledExecutionRuntime,
    compose_controlled_execution_runtime,
)
from qore.infrastructure.execution_boundary import (
    ExecutionReceipt,
    ExecutionReceiptId,
    ExecutionRequestId,
)
from qore.infrastructure.market_data import (
    MarketDataSnapshotId,
    QuoteRequest,
    QuoteSnapshot,
)
from qore.infrastructure.market_test_safety_guard import SafetyGuardedTestExecutionBoundary
from qore.infrastructure.order_intent import OrderIntent
from qore.infrastructure.ports import ExternalPortError, ExternalRequestMetadata
from qore.infrastructure.pretrade_safety import (
    ExecutionSafetySwitchSnapshot,
    PreTradeAuthorization,
)
from qore.kernel.result import Failure, Result, Success


class RealMarketDecisionRuntimeError(ExternalPortError):
    """Base error for supervised decisions over canonical real-market data."""

    __slots__ = ()


class RealMarketDecisionRuntimeValidationError(RealMarketDecisionRuntimeError):
    """Violation of real-market decision runtime invariants."""

    __slots__ = ()


class RealMarketDecisionStatus(StrEnum):
    NO_ACTION = "no_action"
    SUBMITTED = "submitted"


@dataclass(frozen=True, slots=True)
class RealMarketDecisionContext:
    """Canonical decision input derived only from an immutable quote snapshot."""

    quote: QuoteSnapshot
    decided_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.quote, QuoteSnapshot):
            raise RealMarketDecisionRuntimeValidationError(
                "decision context quote must be QuoteSnapshot"
            )
        if not isinstance(self.decided_at, datetime):
            raise RealMarketDecisionRuntimeValidationError(
                "decision context decided_at must be a datetime"
            )
        if self.decided_at.tzinfo is None or self.decided_at.utcoffset() is None:
            raise RealMarketDecisionRuntimeValidationError(
                "decision context decided_at must be timezone-aware"
            )
        if self.decided_at < self.quote.observed_at:
            raise RealMarketDecisionRuntimeValidationError(
                "decision context must not predate observed market data"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.quote.logical_values(), self.decided_at.isoformat())


class SnapshotMarketDataBoundary(Protocol):
    """Canonical snapshot-producing market-data surface used by MISSION-02."""

    def read_quote(
        self,
        request: QuoteRequest,
        *,
        snapshot_id: MarketDataSnapshotId,
        metadata: ExternalRequestMetadata,
    ) -> Result[QuoteSnapshot, ExternalPortError]: ...


class RealMarketDecisionBoundary(Protocol):
    """Injectable ecosystem decision boundary; MISSION-02 adds no strategy."""

    def decide(
        self,
        context: RealMarketDecisionContext,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[OrderIntent | None, ExternalPortError]: ...


@dataclass(frozen=True, slots=True)
class RealMarketDecisionOutcome:
    status: RealMarketDecisionStatus
    quote: QuoteSnapshot
    decided_at: datetime
    intent: OrderIntent | None = None
    receipt: ExecutionReceipt | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, RealMarketDecisionStatus):
            raise RealMarketDecisionRuntimeValidationError(
                "decision outcome status must be RealMarketDecisionStatus"
            )
        if not isinstance(self.quote, QuoteSnapshot):
            raise RealMarketDecisionRuntimeValidationError(
                "decision outcome quote must be QuoteSnapshot"
            )
        if not isinstance(self.decided_at, datetime):
            raise RealMarketDecisionRuntimeValidationError(
                "decision outcome decided_at must be datetime"
            )
        if self.decided_at.tzinfo is None or self.decided_at.utcoffset() is None:
            raise RealMarketDecisionRuntimeValidationError(
                "decision outcome decided_at must be timezone-aware"
            )
        if self.status is RealMarketDecisionStatus.NO_ACTION:
            if self.intent is not None or self.receipt is not None:
                raise RealMarketDecisionRuntimeValidationError(
                    "no-action decision must not contain intent or receipt"
                )
        else:
            if not isinstance(self.intent, OrderIntent):
                raise RealMarketDecisionRuntimeValidationError(
                    "submitted decision requires OrderIntent"
                )
            if not isinstance(self.receipt, ExecutionReceipt):
                raise RealMarketDecisionRuntimeValidationError(
                    "submitted decision requires ExecutionReceipt"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.status.value,
            self.quote.logical_values(),
            self.decided_at.isoformat(),
            self.intent.logical_values() if self.intent is not None else None,
            self.receipt.logical_values() if self.receipt is not None else None,
        )


@dataclass(frozen=True, slots=True)
class RealMarketDecisionRuntime:
    """Read canonical market data, request a decision, then use governed TEST execution."""

    core: CoreApplication
    market_data: SnapshotMarketDataBoundary
    decision: RealMarketDecisionBoundary
    execution: ControlledExecutionRuntime

    def __post_init__(self) -> None:
        if not isinstance(self.core, CoreApplication):
            raise RealMarketDecisionRuntimeValidationError(
                "real-market decision runtime core must be CoreApplication"
            )

    def decide_and_submit_quote(
        self,
        request: QuoteRequest,
        *,
        snapshot_id: MarketDataSnapshotId,
        metadata: ExternalRequestMetadata,
        decided_at: datetime,
        authorization: PreTradeAuthorization,
        switch: ExecutionSafetySwitchSnapshot,
        request_id: ExecutionRequestId,
        receipt_id: ExecutionReceiptId,
        authorized_at: datetime,
        submitted_at: datetime,
    ) -> Result[RealMarketDecisionOutcome, ExternalPortError]:
        quote_result = self.market_data.read_quote(
            request,
            snapshot_id=snapshot_id,
            metadata=metadata,
        )
        if isinstance(quote_result, Failure):
            return Failure(quote_result.error)
        quote = quote_result.value
        try:
            context = RealMarketDecisionContext(quote=quote, decided_at=decided_at)
        except RealMarketDecisionRuntimeError as error:
            return Failure(error)
        decision_result = self.decision.decide(context, metadata=metadata)
        if isinstance(decision_result, Failure):
            return Failure(decision_result.error)
        intent = decision_result.value
        if intent is None:
            return Success(
                RealMarketDecisionOutcome(
                    status=RealMarketDecisionStatus.NO_ACTION,
                    quote=quote,
                    decided_at=decided_at,
                )
            )
        if intent.instrument.value != quote.instrument.symbol:
            return Failure(
                RealMarketDecisionRuntimeValidationError(
                    "decision intent instrument must match observed quote"
                )
            )
        if intent.created_at < quote.observed_at or intent.created_at < decided_at:
            return Failure(
                RealMarketDecisionRuntimeValidationError(
                    "decision intent must not predate market data or decision time"
                )
            )
        receipt_result = self.execution.authorize_and_submit(
            intent,
            authorization,
            switch,
            request_id=request_id,
            receipt_id=receipt_id,
            authorized_at=authorized_at,
            submitted_at=submitted_at,
        )
        if isinstance(receipt_result, Failure):
            return Failure(receipt_result.error)
        return Success(
            RealMarketDecisionOutcome(
                status=RealMarketDecisionStatus.SUBMITTED,
                quote=quote,
                decided_at=decided_at,
                intent=intent,
                receipt=receipt_result.value,
            )
        )


def compose_real_market_decision_runtime(
    *,
    core: CoreApplication,
    market_data: SnapshotMarketDataBoundary,
    decision: RealMarketDecisionBoundary,
    execution: SafetyGuardedTestExecutionBoundary,
) -> Result[RealMarketDecisionRuntime, ExternalPortError]:
    """Compose real-market decision flow while proving Core state invariance."""
    if not isinstance(core, CoreApplication):
        return Failure(
            RealMarketDecisionRuntimeValidationError(
                "real-market decision composition requires CoreApplication"
            )
        )
    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    controlled = compose_controlled_execution_runtime(core, execution)
    if isinstance(controlled, Failure):
        return Failure(controlled.error)
    try:
        runtime = RealMarketDecisionRuntime(
            core=core,
            market_data=market_data,
            decision=decision,
            execution=controlled.value,
        )
    except ExternalPortError as error:
        return Failure(error)

    if core.event_bus is not event_bus:
        return Failure(
            RealMarketDecisionRuntimeValidationError(
                "real-market decision runtime must preserve Core EventBus"
            )
        )
    if core.runtime_plan != runtime_plan:
        return Failure(
            RealMarketDecisionRuntimeValidationError(
                "real-market decision runtime must preserve Core RuntimePlan"
            )
        )
    if core.runtime_snapshot() != runtime_snapshot:
        return Failure(
            RealMarketDecisionRuntimeValidationError(
                "real-market decision runtime must preserve Core RuntimeSnapshot"
            )
        )
    if core.runtime_health() != runtime_health:
        return Failure(
            RealMarketDecisionRuntimeValidationError(
                "real-market decision runtime must preserve Core RuntimeHealth"
            )
        )
    return Success(runtime)
