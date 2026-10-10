"""Bounded one-shot runner for QORE's first protected cTrader DEMO LIMIT."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol, runtime_checkable

from qore.infrastructure.account_policy import AccountPolicyVersion
from qore.infrastructure.ctrader_demo_execution_configuration import (
    CTraderDemoRuntimeConfiguration,
)
from qore.infrastructure.ctrader_demo_risk_operational_runtime import (
    RiskCTraderDemoReconciliationResult,
    RiskCTraderDemoSubmissionResult,
)
from qore.infrastructure.demo_first_execution_intent import build_first_demo_execution_intent
from qore.infrastructure.execution_boundary import ExecutionReceiptId, ExecutionRequestId
from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.order_intent import ExecutionIdempotencyKey, OrderIntent, OrderIntentId
from qore.infrastructure.ports import ExternalHealth, ExternalRequestMetadata, PortAvailability
from qore.infrastructure.risk_authority import (
    RiskDecision,
    RiskFingerprint,
    RiskOutcome,
    RiskScopeSnapshot,
)
from qore.infrastructure.trader_lab.first_execution_phase import (
    FirstDemoExecutionPhaseReadiness,
    FirstDemoExecutionPhaseStatus,
)
from qore.infrastructure.traders.first_cohort_runtime import (
    FirstCohortOperationalEvaluation,
    evaluate_first_demo_cohort,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class FirstDemoRunnerStatus(StrEnum):
    NO_ORDER = "no_order"
    EXECUTED = "executed"
    CONTAINED = "contained"


class FirstDemoExecutionRunnerError(InfrastructureError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class FirstDemoRiskApproval:
    decision: RiskDecision
    scope: RiskScopeSnapshot
    account_policy_version: AccountPolicyVersion
    authorization_fingerprint: RiskFingerprint
    request_id: ExecutionRequestId
    receipt_id: ExecutionReceiptId
    authorized_at: datetime
    submitted_at: datetime


@runtime_checkable
class FirstDemoRiskAuthorizer(Protocol):
    def authorize(
        self, intent: OrderIntent, *, evaluated_at: datetime
    ) -> Result[FirstDemoRiskApproval, InfrastructureError]: ...


@runtime_checkable
class FirstDemoRiskExecutionBoundary(Protocol):
    @property
    def configuration(self) -> CTraderDemoRuntimeConfiguration: ...

    @property
    def has_unresolved_mutations(self) -> bool: ...

    def connect(
        self,
        *,
        checked_at: datetime,
        metadata: ExternalRequestMetadata,
    ) -> Result[ExternalHealth, InfrastructureError]: ...

    def submit_risk_authorized(
        self,
        decision: RiskDecision,
        intent: OrderIntent,
        *,
        scope: RiskScopeSnapshot,
        account_policy_version: AccountPolicyVersion,
        expected_authorization_fingerprint: RiskFingerprint,
        request_id: ExecutionRequestId,
        receipt_id: ExecutionReceiptId,
        authorized_at: datetime,
        submitted_at: datetime,
    ) -> Result[RiskCTraderDemoSubmissionResult, InfrastructureError]: ...

    def poll_and_reconcile(
        self,
        submitted: RiskCTraderDemoSubmissionResult,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[RiskCTraderDemoReconciliationResult, InfrastructureError]: ...


@dataclass(frozen=True, slots=True)
class FirstDemoExecutionRunResult:
    status: FirstDemoRunnerStatus
    reason: str
    cohort: FirstCohortOperationalEvaluation | None = None
    preflight: ExternalHealth | None = None
    intent: OrderIntent | None = None
    submission: RiskCTraderDemoSubmissionResult | None = None
    reconciliation: RiskCTraderDemoReconciliationResult | None = None
    mutation_count: int = 0

    def __post_init__(self) -> None:
        if self.mutation_count not in {0, 1}:
            raise FirstDemoExecutionRunnerError("runner mutation_count must be zero or one")
        if self.status is FirstDemoRunnerStatus.EXECUTED:
            if (
                self.mutation_count != 1
                or self.intent is None
                or self.submission is None
                or self.reconciliation is None
            ):
                raise FirstDemoExecutionRunnerError(
                    "executed result requires one mutation and reconciled evidence"
                )
        elif self.status is FirstDemoRunnerStatus.NO_ORDER and self.mutation_count != 0:
            raise FirstDemoExecutionRunnerError("NO_ORDER cannot follow a broker mutation")


def _no_order(
    reason: str,
    *,
    cohort: FirstCohortOperationalEvaluation | None = None,
    preflight: ExternalHealth | None = None,
    intent: OrderIntent | None = None,
) -> Success[FirstDemoExecutionRunResult]:
    return Success(
        FirstDemoExecutionRunResult(
            status=FirstDemoRunnerStatus.NO_ORDER,
            reason=reason,
            cohort=cohort,
            preflight=preflight,
            intent=intent,
        )
    )


def run_first_demo_execution_once(
    readiness: FirstDemoExecutionPhaseReadiness,
    *,
    snapshots: tuple[OhlcSnapshot, ...],
    runtime: FirstDemoRiskExecutionBoundary,
    risk_authorizer: FirstDemoRiskAuthorizer,
    intent_id: OrderIntentId,
    idempotency_key: ExecutionIdempotencyKey,
    metadata: ExternalRequestMetadata,
    operation_at: datetime,
    max_risk_age: timedelta,
) -> Result[FirstDemoExecutionRunResult, FirstDemoExecutionRunnerError]:
    """Evaluate five Traders and cross the irreversible boundary at most once."""
    try:
        if not isinstance(readiness, FirstDemoExecutionPhaseReadiness):
            raise FirstDemoExecutionRunnerError("readiness must be canonical")
        readiness.__post_init__()
        if readiness.status is not FirstDemoExecutionPhaseStatus.READY_FOR_FIRST_EXECUTION:
            return _no_order("first DEMO phase is blocked")
        if not isinstance(runtime, FirstDemoRiskExecutionBoundary):
            raise FirstDemoExecutionRunnerError("runtime does not satisfy DEMO Risk boundary")
        if runtime.configuration != readiness.configuration:
            return _no_order("runtime configuration differs from certified readiness")
        if runtime.has_unresolved_mutations:
            return _no_order("durable ledger contains unresolved mutation")
        if not isinstance(risk_authorizer, FirstDemoRiskAuthorizer):
            raise FirstDemoExecutionRunnerError("risk authorizer boundary is missing")
        if operation_at.tzinfo is None or operation_at.utcoffset() is None:
            raise FirstDemoExecutionRunnerError("operation_at must be timezone-aware")
        if max_risk_age <= timedelta(0):
            raise FirstDemoExecutionRunnerError("max_risk_age must be positive")

        health = runtime.connect(checked_at=operation_at, metadata=metadata)
        if (
            isinstance(health, Failure)
            or health.value.availability is not PortAvailability.AVAILABLE
        ):
            return _no_order("fresh cTrader DEMO preflight is unavailable")
        cohort_result = evaluate_first_demo_cohort(
            readiness.selection,
            snapshots=snapshots,
            evaluated_at=operation_at,
        )
        if isinstance(cohort_result, Failure):
            return _no_order("five-Trader operational evaluation failed", preflight=health.value)
        cohort = cohort_result.value
        if cohort.selected_output is None:
            return _no_order(
                "no DEMO_ELIGIBLE Trader selected",
                cohort=cohort,
                preflight=health.value,
            )
        built = build_first_demo_execution_intent(
            readiness.selection,
            cohort.selected_output,
            configuration=readiness.configuration,
            intent_id=intent_id,
            idempotency_key=idempotency_key,
            created_at=operation_at,
            metadata=metadata,
        )
        if isinstance(built, Failure):
            return _no_order(
                "selected Trader has no admissible current SETUP",
                cohort=cohort,
                preflight=health.value,
            )
        intent = built.value
        approval_result = risk_authorizer.authorize(intent, evaluated_at=operation_at)
        if isinstance(approval_result, Failure):
            return _no_order(
                "fresh Risk denied or failed",
                cohort=cohort,
                preflight=health.value,
                intent=intent,
            )
        approval = approval_result.value
        authorization = approval.decision.authorization
        if (
            approval.decision.outcome not in {RiskOutcome.ALLOW, RiskOutcome.REDUCE}
            or authorization is None
            or authorization.valid_until <= approval.submitted_at
            or authorization.issued_at > operation_at
            or operation_at - authorization.issued_at > max_risk_age
        ):
            return _no_order(
                "Risk authorization is invalid or stale",
                cohort=cohort,
                preflight=health.value,
                intent=intent,
            )

        mutation_count = 1
        submitted = runtime.submit_risk_authorized(
            approval.decision,
            intent,
            scope=approval.scope,
            account_policy_version=approval.account_policy_version,
            expected_authorization_fingerprint=approval.authorization_fingerprint,
            request_id=approval.request_id,
            receipt_id=approval.receipt_id,
            authorized_at=approval.authorized_at,
            submitted_at=approval.submitted_at,
        )
        if isinstance(submitted, Failure):
            return Success(
                FirstDemoExecutionRunResult(
                    status=FirstDemoRunnerStatus.CONTAINED,
                    reason="single broker mutation did not produce definitive evidence",
                    cohort=cohort,
                    preflight=health.value,
                    intent=intent,
                    mutation_count=mutation_count,
                )
            )
        reconciled = runtime.poll_and_reconcile(submitted.value, metadata=metadata)
        if isinstance(reconciled, Failure):
            return Success(
                FirstDemoExecutionRunResult(
                    status=FirstDemoRunnerStatus.CONTAINED,
                    reason="broker order exists but reconciliation is ambiguous",
                    cohort=cohort,
                    preflight=health.value,
                    intent=intent,
                    submission=submitted.value,
                    mutation_count=mutation_count,
                )
            )
        return Success(
            FirstDemoExecutionRunResult(
                status=FirstDemoRunnerStatus.EXECUTED,
                reason="one protected DEMO LIMIT reconciled",
                cohort=cohort,
                preflight=health.value,
                intent=intent,
                submission=submitted.value,
                reconciliation=reconciled.value,
                mutation_count=mutation_count,
            )
        )
    except (FirstDemoExecutionRunnerError, ValueError) as error:
        return Failure(FirstDemoExecutionRunnerError(str(error)))
