from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.core.application import CoreApplication
from qore.infrastructure.execution_boundary import (
    ExecutionBoundary,
    ExecutionBoundaryError,
    ExecutionReceipt,
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionSubmission,
)
from qore.infrastructure.execution_reconciliation import (
    ExecutionObservation,
    ExecutionReconciliationError,
    ExecutionReconciliationSnapshot,
    reconcile_execution,
)
from qore.infrastructure.order_intent import OrderIntent
from qore.infrastructure.ports import ExternalPortError
from qore.infrastructure.pretrade_safety import (
    ExecutionSafetySwitchSnapshot,
    PreTradeAuthorization,
    authorize_order_intent,
)
from qore.kernel.result import Failure, Result, Success


class ControlledExecutionRuntimeError(ExternalPortError):
    """Base error for PHASE-11 controlled execution composition."""

    __slots__ = ()


class ControlledExecutionRuntimeValidationError(ControlledExecutionRuntimeError):
    """Violation of controlled execution runtime invariants."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ControlledExecutionRuntime:
    """Fail-closed sandbox execution facade above an unchanged Core."""

    core: CoreApplication
    execution: ExecutionBoundary

    def __post_init__(self) -> None:
        if not isinstance(self.core, CoreApplication):
            raise ControlledExecutionRuntimeValidationError(
                "controlled execution core must be CoreApplication"
            )

    def authorize_and_submit(
        self,
        intent: OrderIntent,
        authorization: PreTradeAuthorization,
        switch: ExecutionSafetySwitchSnapshot,
        *,
        request_id: ExecutionRequestId,
        receipt_id: ExecutionReceiptId,
        authorized_at: datetime,
        submitted_at: datetime,
    ) -> Result[ExecutionReceipt, ExternalPortError]:
        """Authorize first, then submit only an AuthorizedOrderIntent."""
        authorized = authorize_order_intent(
            intent,
            authorization,
            switch,
            authorized_at=authorized_at,
        )
        if isinstance(authorized, Failure):
            return Failure(authorized.error)
        try:
            submission = ExecutionSubmission(
                request_id=request_id,
                receipt_id=receipt_id,
                authorized_intent=authorized.value,
                submitted_at=submitted_at,
            )
        except ExecutionBoundaryError as error:
            return Failure(error)
        return self.execution.submit(submission)

    def reconcile(
        self,
        expected: ExecutionReceipt | None,
        observed: ExecutionObservation | None,
        *,
        reconciled_at: datetime,
    ) -> Result[ExecutionReconciliationSnapshot, ExecutionReconciliationError]:
        """Compare execution state without corrective trading side effects."""
        return reconcile_execution(
            expected,
            observed,
            reconciled_at=reconciled_at,
        )


def compose_controlled_execution_runtime(
    core: CoreApplication,
    execution: ExecutionBoundary,
) -> Result[ControlledExecutionRuntime, ExternalPortError]:
    """Compose controlled execution while proving Core state is unchanged."""
    if not isinstance(core, CoreApplication):
        return Failure(
            ControlledExecutionRuntimeValidationError(
                "controlled execution core must be CoreApplication"
            )
        )

    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    try:
        runtime = ControlledExecutionRuntime(core=core, execution=execution)
    except ExternalPortError as error:
        return Failure(error)

    if core.event_bus is not event_bus:
        return Failure(
            ControlledExecutionRuntimeValidationError(
                "controlled execution must preserve Core EventBus"
            )
        )
    if core.runtime_plan != runtime_plan:
        return Failure(
            ControlledExecutionRuntimeValidationError(
                "controlled execution must not mutate Core RuntimePlan"
            )
        )
    if core.runtime_snapshot() != runtime_snapshot:
        return Failure(
            ControlledExecutionRuntimeValidationError(
                "controlled execution must not mutate Core RuntimeSnapshot"
            )
        )
    if core.runtime_health() != runtime_health:
        return Failure(
            ControlledExecutionRuntimeValidationError(
                "controlled execution must not mutate Core RuntimeHealth"
            )
        )
    return Success(runtime)
