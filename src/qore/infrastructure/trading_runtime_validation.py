from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.core.application import CoreApplication
from qore.infrastructure.controlled_execution import (
    ControlledExecutionRuntime,
    compose_controlled_execution_runtime,
)
from qore.infrastructure.execution_boundary import (
    ExecutionReceipt,
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionStatus,
    SandboxExecutionBoundary,
)
from qore.infrastructure.execution_failure_containment import (
    ExecutionContainmentSnapshot,
    ExecutionFailureKind,
    ExecutionFailureSignal,
    ExecutionFailureStage,
    contain_execution_failure,
    evaluate_reconciliation_containment,
)
from qore.infrastructure.execution_orchestration import (
    ExecutionOrchestrationId,
    GovernedExecutionReason,
    GovernedExecutionSnapshot,
    GovernedExecutionState,
    GovernedExecutionTransitionRequest,
    declare_governed_execution,
    transition_governed_execution,
)
from qore.infrastructure.execution_reconciliation import (
    ExecutionObservation,
    ExecutionReconciliationSnapshot,
    ExecutionReconciliationStatus,
    observe_execution_receipt,
)
from qore.infrastructure.order_intent import OrderIntent
from qore.infrastructure.ports import ExternalPortError
from qore.infrastructure.pretrade_safety import (
    ExecutionSafetySwitchSnapshot,
    PreTradeAuthorization,
    authorize_order_intent,
)
from qore.infrastructure.trading_safety_evidence import (
    TradingSafetyCheck,
    TradingSafetyCheckStatus,
    TradingSafetyEvidenceBundle,
    TradingSafetyEvidenceRecord,
    aggregate_trading_safety_evidence,
)
from qore.kernel.result import Failure, Result, Success


class TradingRuntimeValidationError(ExternalPortError):
    """Base error for PHASE-12 trading runtime validation."""

    __slots__ = ()


class TradingRuntimeValidationInvariantError(TradingRuntimeValidationError):
    """Violation of deterministic validation-harness invariants."""

    __slots__ = ()


class TradingRuntimeObservationMode(StrEnum):
    MATCHED = "matched"
    MISSING = "missing"
    DIVERGED = "diverged"


@dataclass(frozen=True, slots=True)
class TradingRuntimeValidationResult:
    orchestration: GovernedExecutionSnapshot
    containment: ExecutionContainmentSnapshot
    evidence: TradingSafetyEvidenceBundle
    receipts_before: int
    receipts_after: int
    receipt: ExecutionReceipt | None = None
    reconciliation: ExecutionReconciliationSnapshot | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.orchestration, GovernedExecutionSnapshot):
            raise TradingRuntimeValidationInvariantError(
                "validation result requires GovernedExecutionSnapshot"
            )
        if not isinstance(self.containment, ExecutionContainmentSnapshot):
            raise TradingRuntimeValidationInvariantError(
                "validation result requires ExecutionContainmentSnapshot"
            )
        if not isinstance(self.evidence, TradingSafetyEvidenceBundle):
            raise TradingRuntimeValidationInvariantError(
                "validation result requires TradingSafetyEvidenceBundle"
            )
        for field_name, value in (
            ("receipts_before", self.receipts_before),
            ("receipts_after", self.receipts_after),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise TradingRuntimeValidationInvariantError(
                    f"{field_name} must be a non-negative int"
                )
        if self.receipts_after < self.receipts_before:
            raise TradingRuntimeValidationInvariantError(
                "validation must not reduce sandbox receipt count"
            )
        if self.receipt is not None and not isinstance(self.receipt, ExecutionReceipt):
            raise TradingRuntimeValidationInvariantError(
                "receipt must be ExecutionReceipt or None"
            )
        if self.reconciliation is not None and not isinstance(
            self.reconciliation, ExecutionReconciliationSnapshot
        ):
            raise TradingRuntimeValidationInvariantError(
                "reconciliation must be ExecutionReconciliationSnapshot or None"
            )
        if self.evidence.passed:
            if self.orchestration.state is not GovernedExecutionState.RECONCILED:
                raise TradingRuntimeValidationInvariantError(
                    "passing validation requires RECONCILED orchestration"
                )
            if self.receipt is None or self.reconciliation is None:
                raise TradingRuntimeValidationInvariantError(
                    "passing validation requires receipt and reconciliation"
                )
            if self.containment.contained:
                raise TradingRuntimeValidationInvariantError(
                    "passing validation must not be contained"
                )
        else:
            if self.orchestration.state not in {
                GovernedExecutionState.BLOCKED,
                GovernedExecutionState.CONTAINED,
            }:
                raise TradingRuntimeValidationInvariantError(
                    "failed validation must terminate BLOCKED or CONTAINED"
                )
            if not self.containment.contained:
                raise TradingRuntimeValidationInvariantError(
                    "failed validation must be contained"
                )

    @property
    def passed(self) -> bool:
        return self.evidence.passed

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.orchestration.logical_values(),
            self.containment.logical_values(),
            self.evidence.logical_values(),
            self.receipts_before,
            self.receipts_after,
            self.receipt.logical_values() if self.receipt is not None else None,
            (
                self.reconciliation.logical_values()
                if self.reconciliation is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class TradingRuntimeValidationHarness:
    core: CoreApplication
    sandbox: SandboxExecutionBoundary
    runtime: ControlledExecutionRuntime

    def __post_init__(self) -> None:
        if not isinstance(self.core, CoreApplication):
            raise TradingRuntimeValidationInvariantError(
                "validation harness core must be CoreApplication"
            )
        if not isinstance(self.sandbox, SandboxExecutionBoundary):
            raise TradingRuntimeValidationInvariantError(
                "validation harness requires SandboxExecutionBoundary"
            )
        if not isinstance(self.runtime, ControlledExecutionRuntime):
            raise TradingRuntimeValidationInvariantError(
                "validation harness runtime must be ControlledExecutionRuntime"
            )
        if self.runtime.core is not self.core:
            raise TradingRuntimeValidationInvariantError(
                "validation harness runtime must preserve exact Core identity"
            )
        if self.runtime.execution is not self.sandbox:
            raise TradingRuntimeValidationInvariantError(
                "validation harness runtime must use exact sandbox identity"
            )

    def validate(
        self,
        orchestration_id: ExecutionOrchestrationId,
        intent: OrderIntent,
        authorization: PreTradeAuthorization,
        switch: ExecutionSafetySwitchSnapshot,
        *,
        request_id: ExecutionRequestId,
        receipt_id: ExecutionReceiptId,
        authorized_at: datetime,
        submitted_at: datetime,
        observed_at: datetime,
        reconciled_at: datetime,
        evaluated_at: datetime,
        observation_mode: TradingRuntimeObservationMode = (
            TradingRuntimeObservationMode.MATCHED
        ),
    ) -> Result[TradingRuntimeValidationResult, ExternalPortError]:
        if not isinstance(orchestration_id, ExecutionOrchestrationId):
            return Failure(
                TradingRuntimeValidationInvariantError(
                    "orchestration_id must be ExecutionOrchestrationId"
                )
            )
        if not isinstance(observation_mode, TradingRuntimeObservationMode):
            return Failure(
                TradingRuntimeValidationInvariantError(
                    "observation_mode must be TradingRuntimeObservationMode"
                )
            )

        event_bus = self.core.event_bus
        runtime_plan = self.core.runtime_plan
        runtime_snapshot = self.core.runtime_snapshot()
        runtime_health = self.core.runtime_health()
        receipts_before = len(self.sandbox.receipts)

        declared = declare_governed_execution(
            orchestration_id,
            intent.intent_id,
            requested_at=intent.created_at,
        )
        if isinstance(declared, Failure):
            return Failure(declared.error)

        authorized = authorize_order_intent(
            intent,
            authorization,
            switch,
            authorized_at=authorized_at,
        )
        if isinstance(authorized, Failure):
            result = self._blocked_result(
                declared.value,
                intent,
                switch,
                receipts_before=receipts_before,
                authorized_at=authorized_at,
                evaluated_at=evaluated_at,
            )
            return self._return_if_core_preserved(
                result,
                event_bus=event_bus,
                runtime_plan=runtime_plan,
                runtime_snapshot=runtime_snapshot,
                runtime_health=runtime_health,
            )

        orchestration_authorized = transition_governed_execution(
            declared.value,
            GovernedExecutionTransitionRequest(
                state=GovernedExecutionState.AUTHORIZED,
                transitioned_at=authorized_at,
                reason=GovernedExecutionReason.AUTHORIZATION_APPROVED,
                authorization_id=authorization.authorization_id,
            ),
        )
        if isinstance(orchestration_authorized, Failure):
            return Failure(orchestration_authorized.error)

        submitted = self.runtime.authorize_and_submit(
            intent,
            authorization,
            switch,
            request_id=request_id,
            receipt_id=receipt_id,
            authorized_at=authorized_at,
            submitted_at=submitted_at,
        )
        if isinstance(submitted, Failure):
            result = self._submission_failure_result(
                orchestration_authorized.value,
                intent,
                receipts_before=receipts_before,
                submitted_at=submitted_at,
                evaluated_at=evaluated_at,
            )
            return self._return_if_core_preserved(
                result,
                event_bus=event_bus,
                runtime_plan=runtime_plan,
                runtime_snapshot=runtime_snapshot,
                runtime_health=runtime_health,
            )

        orchestration_submitted = transition_governed_execution(
            orchestration_authorized.value,
            GovernedExecutionTransitionRequest(
                state=GovernedExecutionState.SUBMITTED,
                transitioned_at=submitted_at,
                reason=GovernedExecutionReason.SUBMISSION_ACCEPTED,
                receipt_id=submitted.value.receipt_id,
            ),
        )
        if isinstance(orchestration_submitted, Failure):
            return Failure(orchestration_submitted.error)

        observation = self._observation(
            submitted.value,
            mode=observation_mode,
            observed_at=observed_at,
        )
        if isinstance(observation, Failure):
            return Failure(observation.error)

        reconciliation = self.runtime.reconcile(
            submitted.value,
            observation.value,
            reconciled_at=reconciled_at,
        )
        if isinstance(reconciliation, Failure):
            return Failure(reconciliation.error)

        containment = evaluate_reconciliation_containment(
            reconciliation.value,
            evaluated_at=evaluated_at,
        )
        if isinstance(containment, Failure):
            return Failure(containment.error)

        result = self._reconciled_result(
            orchestration_submitted.value,
            intent,
            submitted.value,
            reconciliation.value,
            containment.value,
            receipts_before=receipts_before,
            evaluated_at=evaluated_at,
        )
        return self._return_if_core_preserved(
            result,
            event_bus=event_bus,
            runtime_plan=runtime_plan,
            runtime_snapshot=runtime_snapshot,
            runtime_health=runtime_health,
        )

    def _blocked_result(
        self,
        orchestration: GovernedExecutionSnapshot,
        intent: OrderIntent,
        switch: ExecutionSafetySwitchSnapshot,
        *,
        receipts_before: int,
        authorized_at: datetime,
        evaluated_at: datetime,
    ) -> Result[TradingRuntimeValidationResult, ExternalPortError]:
        blocked = transition_governed_execution(
            orchestration,
            GovernedExecutionTransitionRequest(
                state=GovernedExecutionState.BLOCKED,
                transitioned_at=authorized_at,
                reason=GovernedExecutionReason.SAFETY_BLOCKED,
            ),
        )
        if isinstance(blocked, Failure):
            return Failure(blocked.error)
        signal = ExecutionFailureSignal(
            stage=ExecutionFailureStage.PRE_TRADE,
            kind=ExecutionFailureKind.SAFETY_BLOCKED,
            observed_at=authorized_at,
            code="pretrade.safety.blocked",
        )
        containment = contain_execution_failure(
            signal,
            evaluated_at=evaluated_at,
        )
        if isinstance(containment, Failure):
            return Failure(containment.error)
        evidence = self._evidence(
            orchestration.orchestration_id,
            intent,
            evaluated_at=evaluated_at,
            authorization=TradingSafetyCheckStatus.FAIL,
            switch=(
                TradingSafetyCheckStatus.PASS
                if switch.allows_execution
                else TradingSafetyCheckStatus.FAIL
            ),
            idempotency=TradingSafetyCheckStatus.FAIL,
            reconciliation=TradingSafetyCheckStatus.FAIL,
            containment=TradingSafetyCheckStatus.PASS,
        )
        if isinstance(evidence, Failure):
            return Failure(evidence.error)
        return self._make_result(
            orchestration=blocked.value,
            containment=containment.value,
            evidence=evidence.value,
            receipts_before=receipts_before,
        )

    def _submission_failure_result(
        self,
        orchestration: GovernedExecutionSnapshot,
        intent: OrderIntent,
        *,
        receipts_before: int,
        submitted_at: datetime,
        evaluated_at: datetime,
    ) -> Result[TradingRuntimeValidationResult, ExternalPortError]:
        signal = ExecutionFailureSignal(
            stage=ExecutionFailureStage.SUBMIT,
            kind=ExecutionFailureKind.SUBMISSION_FAILURE,
            observed_at=submitted_at,
            code="submit.failed",
        )
        containment = contain_execution_failure(
            signal,
            evaluated_at=evaluated_at,
        )
        if isinstance(containment, Failure):
            return Failure(containment.error)
        contained = transition_governed_execution(
            orchestration,
            GovernedExecutionTransitionRequest(
                state=GovernedExecutionState.CONTAINED,
                transitioned_at=evaluated_at,
                reason=GovernedExecutionReason.FAILURE_CONTAINED,
            ),
        )
        if isinstance(contained, Failure):
            return Failure(contained.error)
        evidence = self._evidence(
            orchestration.orchestration_id,
            intent,
            evaluated_at=evaluated_at,
            authorization=TradingSafetyCheckStatus.PASS,
            switch=TradingSafetyCheckStatus.PASS,
            idempotency=TradingSafetyCheckStatus.FAIL,
            reconciliation=TradingSafetyCheckStatus.FAIL,
            containment=TradingSafetyCheckStatus.PASS,
        )
        if isinstance(evidence, Failure):
            return Failure(evidence.error)
        return self._make_result(
            orchestration=contained.value,
            containment=containment.value,
            evidence=evidence.value,
            receipts_before=receipts_before,
        )

    def _reconciled_result(
        self,
        orchestration: GovernedExecutionSnapshot,
        intent: OrderIntent,
        receipt: ExecutionReceipt,
        reconciliation: ExecutionReconciliationSnapshot,
        containment: ExecutionContainmentSnapshot,
        *,
        receipts_before: int,
        evaluated_at: datetime,
    ) -> Result[TradingRuntimeValidationResult, ExternalPortError]:
        if reconciliation.status is ExecutionReconciliationStatus.MATCHED:
            terminal = transition_governed_execution(
                orchestration,
                GovernedExecutionTransitionRequest(
                    state=GovernedExecutionState.RECONCILED,
                    transitioned_at=reconciliation.reconciled_at,
                    reason=GovernedExecutionReason.RECONCILIATION_MATCHED,
                    reconciliation_status=ExecutionReconciliationStatus.MATCHED,
                ),
            )
            reconciliation_check = TradingSafetyCheckStatus.PASS
        else:
            terminal = transition_governed_execution(
                orchestration,
                GovernedExecutionTransitionRequest(
                    state=GovernedExecutionState.CONTAINED,
                    transitioned_at=evaluated_at,
                    reason=GovernedExecutionReason.FAILURE_CONTAINED,
                    reconciliation_status=reconciliation.status,
                ),
            )
            reconciliation_check = TradingSafetyCheckStatus.FAIL
        if isinstance(terminal, Failure):
            return Failure(terminal.error)
        evidence = self._evidence(
            orchestration.orchestration_id,
            intent,
            evaluated_at=evaluated_at,
            authorization=TradingSafetyCheckStatus.PASS,
            switch=TradingSafetyCheckStatus.PASS,
            idempotency=TradingSafetyCheckStatus.PASS,
            reconciliation=reconciliation_check,
            containment=TradingSafetyCheckStatus.PASS,
        )
        if isinstance(evidence, Failure):
            return Failure(evidence.error)
        return self._make_result(
            orchestration=terminal.value,
            containment=containment,
            evidence=evidence.value,
            receipts_before=receipts_before,
            receipt=receipt,
            reconciliation=reconciliation,
        )

    def _observation(
        self,
        receipt: ExecutionReceipt,
        *,
        mode: TradingRuntimeObservationMode,
        observed_at: datetime,
    ) -> Result[ExecutionObservation | None, ExternalPortError]:
        if mode is TradingRuntimeObservationMode.MISSING:
            return Success(None)
        if mode is TradingRuntimeObservationMode.DIVERGED:
            try:
                return Success(
                    ExecutionObservation(
                        receipt_id=receipt.receipt_id,
                        request_id=receipt.request_id,
                        idempotency_key=receipt.idempotency_key,
                        status=ExecutionStatus.CANCELLED,
                        observed_at=observed_at,
                    )
                )
            except ExternalPortError as error:
                return Failure(error)
        observed = observe_execution_receipt(
            receipt,
            observed_at=observed_at,
        )
        if isinstance(observed, Failure):
            return Failure(observed.error)
        return Success(observed.value)

    def _evidence(
        self,
        orchestration_id: ExecutionOrchestrationId,
        intent: OrderIntent,
        *,
        evaluated_at: datetime,
        authorization: TradingSafetyCheckStatus,
        switch: TradingSafetyCheckStatus,
        idempotency: TradingSafetyCheckStatus,
        reconciliation: TradingSafetyCheckStatus,
        containment: TradingSafetyCheckStatus,
    ) -> Result[TradingSafetyEvidenceBundle, ExternalPortError]:
        statuses = (
            (TradingSafetyCheck.AUTHORIZATION, authorization),
            (TradingSafetyCheck.SWITCH, switch),
            (TradingSafetyCheck.IDEMPOTENCY, idempotency),
            (TradingSafetyCheck.RECONCILIATION, reconciliation),
            (TradingSafetyCheck.CONTAINMENT, containment),
        )
        try:
            records = tuple(
                TradingSafetyEvidenceRecord(
                    check=check,
                    status=status,
                    observed_at=evaluated_at,
                    code=f"{check.value}.{status.value}",
                )
                for check, status in statuses
            )
        except ExternalPortError as error:
            return Failure(error)
        aggregated = aggregate_trading_safety_evidence(
            orchestration_id,
            intent.intent_id,
            records,
            evaluated_at=evaluated_at,
        )
        if isinstance(aggregated, Failure):
            return Failure(aggregated.error)
        return Success(aggregated.value)

    def _make_result(
        self,
        *,
        orchestration: GovernedExecutionSnapshot,
        containment: ExecutionContainmentSnapshot,
        evidence: TradingSafetyEvidenceBundle,
        receipts_before: int,
        receipt: ExecutionReceipt | None = None,
        reconciliation: ExecutionReconciliationSnapshot | None = None,
    ) -> Result[TradingRuntimeValidationResult, ExternalPortError]:
        try:
            return Success(
                TradingRuntimeValidationResult(
                    orchestration=orchestration,
                    containment=containment,
                    evidence=evidence,
                    receipts_before=receipts_before,
                    receipts_after=len(self.sandbox.receipts),
                    receipt=receipt,
                    reconciliation=reconciliation,
                )
            )
        except ExternalPortError as error:
            return Failure(error)

    def _return_if_core_preserved(
        self,
        result: Result[TradingRuntimeValidationResult, ExternalPortError],
        *,
        event_bus: object,
        runtime_plan: object,
        runtime_snapshot: object,
        runtime_health: object,
    ) -> Result[TradingRuntimeValidationResult, ExternalPortError]:
        if isinstance(result, Failure):
            return result
        if self.core.event_bus is not event_bus:
            return Failure(
                TradingRuntimeValidationInvariantError(
                    "validation must preserve Core EventBus"
                )
            )
        if self.core.runtime_plan != runtime_plan:
            return Failure(
                TradingRuntimeValidationInvariantError(
                    "validation must preserve Core RuntimePlan"
                )
            )
        if self.core.runtime_snapshot() != runtime_snapshot:
            return Failure(
                TradingRuntimeValidationInvariantError(
                    "validation must preserve Core RuntimeSnapshot"
                )
            )
        if self.core.runtime_health() != runtime_health:
            return Failure(
                TradingRuntimeValidationInvariantError(
                    "validation must preserve Core RuntimeHealth"
                )
            )
        return result


def compose_trading_runtime_validation_harness(
    core: CoreApplication,
    sandbox: SandboxExecutionBoundary,
) -> Result[TradingRuntimeValidationHarness, ExternalPortError]:
    if not isinstance(core, CoreApplication):
        return Failure(
            TradingRuntimeValidationInvariantError(
                "validation harness core must be CoreApplication"
            )
        )
    if not isinstance(sandbox, SandboxExecutionBoundary):
        return Failure(
            TradingRuntimeValidationInvariantError(
                "validation harness requires SandboxExecutionBoundary"
            )
        )

    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    runtime = compose_controlled_execution_runtime(core, sandbox)
    if isinstance(runtime, Failure):
        return Failure(runtime.error)
    try:
        harness = TradingRuntimeValidationHarness(
            core=core,
            sandbox=sandbox,
            runtime=runtime.value,
        )
    except ExternalPortError as error:
        return Failure(error)

    if core.event_bus is not event_bus:
        return Failure(
            TradingRuntimeValidationInvariantError(
                "validation composition must preserve Core EventBus"
            )
        )
    if core.runtime_plan != runtime_plan:
        return Failure(
            TradingRuntimeValidationInvariantError(
                "validation composition must preserve Core RuntimePlan"
            )
        )
    if core.runtime_snapshot() != runtime_snapshot:
        return Failure(
            TradingRuntimeValidationInvariantError(
                "validation composition must preserve Core RuntimeSnapshot"
            )
        )
    if core.runtime_health() != runtime_health:
        return Failure(
            TradingRuntimeValidationInvariantError(
                "validation composition must preserve Core RuntimeHealth"
            )
        )
    return Success(harness)
