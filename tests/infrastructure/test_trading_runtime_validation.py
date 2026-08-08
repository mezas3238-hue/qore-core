from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.execution_boundary import (
    ExecutionReceiptId,
    ExecutionRequestId,
    ExecutionStatus,
    SandboxExecutionBoundary,
)
from qore.infrastructure.execution_orchestration import (
    ExecutionOrchestrationId,
    GovernedExecutionState,
)
from qore.infrastructure.execution_reconciliation import ExecutionReconciliationStatus
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderIntent,
    OrderIntentId,
    OrderQuantity,
    OrderSide,
    OrderType,
)
from qore.infrastructure.ports import ExternalRequestMetadata
from qore.infrastructure.pretrade_safety import (
    ExecutionSafetySwitchSnapshot,
    ExecutionSwitchState,
    PreTradeAuthorization,
    PreTradeAuthorizationId,
    PreTradeDecision,
    PreTradePolicyId,
)
from qore.infrastructure.trading_runtime_validation import (
    TradingRuntimeObservationMode,
    compose_trading_runtime_validation_harness,
)
from qore.infrastructure.trading_safety_evidence import TradingSafetyVerdict
from qore.kernel.result import Success

_NOW = datetime(2026, 8, 8, 10, 0, tzinfo=UTC)
_INTENT_ID = OrderIntentId(UUID("b3000000-0000-0000-0000-000000000001"))
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("b3000000-0000-0000-0000-000000000002")),
    causation_id=CausationId(UUID("b3000000-0000-0000-0000-000000000003")),
)
_REQUEST_ID = ExecutionRequestId(UUID("b3000000-0000-0000-0000-000000000006"))
_RECEIPT_ID = ExecutionReceiptId(UUID("b3000000-0000-0000-0000-000000000007"))


def _core() -> CoreApplication:
    result = bootstrap(Configuration(application_name="qore-trading-validation"))
    assert isinstance(result, Success)
    return result.value


def _intent() -> OrderIntent:
    return OrderIntent(
        intent_id=_INTENT_ID,
        idempotency_key=ExecutionIdempotencyKey(
            UUID("b3000000-0000-0000-0000-000000000004")
        ),
        instrument=ExecutionInstrument("EURUSD"),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=OrderQuantity(Decimal("1")),
        created_at=_NOW,
        metadata=_METADATA,
    )


def _authorization(
    decision: PreTradeDecision = PreTradeDecision.APPROVED,
) -> PreTradeAuthorization:
    return PreTradeAuthorization(
        authorization_id=PreTradeAuthorizationId(
            UUID("b3000000-0000-0000-0000-000000000005")
        ),
        policy_id=PreTradePolicyId("risk.pretrade.v1"),
        intent_id=_INTENT_ID,
        decision=decision,
        evaluated_at=_NOW + timedelta(seconds=1),
        expires_at=_NOW + timedelta(seconds=20),
        reason="trading runtime validation policy",
    )


def _switch(
    state: ExecutionSwitchState = ExecutionSwitchState.ENABLED,
) -> ExecutionSafetySwitchSnapshot:
    return ExecutionSafetySwitchSnapshot(
        state=state,
        observed_at=_NOW + timedelta(seconds=2),
        reason="trading runtime validation switch",
    )


def _validate(
    sandbox: SandboxExecutionBoundary,
    *,
    orchestration_value: int = 8,
    decision: PreTradeDecision = PreTradeDecision.APPROVED,
    switch_state: ExecutionSwitchState = ExecutionSwitchState.ENABLED,
    mode: TradingRuntimeObservationMode = TradingRuntimeObservationMode.MATCHED,
):
    harness = compose_trading_runtime_validation_harness(_core(), sandbox)
    assert isinstance(harness, Success)
    orchestration_id = ExecutionOrchestrationId(
        UUID(f"b3000000-0000-0000-0000-{orchestration_value:012d}")
    )
    return harness.value.validate(
        orchestration_id,
        _intent(),
        _authorization(decision),
        _switch(switch_state),
        request_id=_REQUEST_ID,
        receipt_id=_RECEIPT_ID,
        authorized_at=_NOW + timedelta(seconds=3),
        submitted_at=_NOW + timedelta(seconds=4),
        observed_at=_NOW + timedelta(seconds=5),
        reconciled_at=_NOW + timedelta(seconds=6),
        evaluated_at=_NOW + timedelta(seconds=7),
        observation_mode=mode,
    )


def test_nominal_sandbox_scenario_passes_full_safety_validation() -> None:
    sandbox = SandboxExecutionBoundary()
    result = _validate(sandbox)

    assert isinstance(result, Success)
    assert result.value.passed is True
    assert result.value.evidence.verdict is TradingSafetyVerdict.PASS
    assert result.value.orchestration.state is GovernedExecutionState.RECONCILED
    assert result.value.reconciliation is not None
    assert result.value.reconciliation.status is ExecutionReconciliationStatus.MATCHED
    assert result.value.containment.contained is False
    assert result.value.receipts_before == 0
    assert result.value.receipts_after == 1


def test_blocked_switch_contains_before_sandbox_receipt() -> None:
    sandbox = SandboxExecutionBoundary()
    result = _validate(
        sandbox,
        switch_state=ExecutionSwitchState.BLOCKED,
    )

    assert isinstance(result, Success)
    assert result.value.passed is False
    assert result.value.orchestration.state is GovernedExecutionState.BLOCKED
    assert result.value.containment.contained is True
    assert result.value.receipts_before == 0
    assert result.value.receipts_after == 0
    assert sandbox.receipts == ()


def test_blocked_pretrade_contains_before_sandbox_receipt() -> None:
    sandbox = SandboxExecutionBoundary()
    result = _validate(
        sandbox,
        decision=PreTradeDecision.BLOCKED,
    )

    assert isinstance(result, Success)
    assert result.value.passed is False
    assert result.value.orchestration.state is GovernedExecutionState.BLOCKED
    assert result.value.receipts_after == 0
    assert sandbox.receipts == ()


def test_diverged_observation_is_contained_without_corrective_execution() -> None:
    sandbox = SandboxExecutionBoundary()
    result = _validate(
        sandbox,
        mode=TradingRuntimeObservationMode.DIVERGED,
    )

    assert isinstance(result, Success)
    assert result.value.passed is False
    assert result.value.orchestration.state is GovernedExecutionState.CONTAINED
    assert result.value.reconciliation is not None
    assert result.value.reconciliation.status is ExecutionReconciliationStatus.DIVERGED
    assert result.value.containment.contained is True
    assert result.value.receipts_after == 1
    assert sandbox.receipts[0].status is ExecutionStatus.ACCEPTED


def test_missing_observation_is_contained_and_requires_no_retry() -> None:
    sandbox = SandboxExecutionBoundary()
    result = _validate(
        sandbox,
        mode=TradingRuntimeObservationMode.MISSING,
    )

    assert isinstance(result, Success)
    assert result.value.passed is False
    assert result.value.reconciliation is not None
    assert result.value.reconciliation.status is ExecutionReconciliationStatus.MISSING
    assert result.value.orchestration.state is GovernedExecutionState.CONTAINED
    assert result.value.receipts_after == 1
    assert not hasattr(result.value, "retry")
    assert not hasattr(result.value, "resubmit")


def test_exact_replay_reuses_receipt_without_duplicate_execution() -> None:
    sandbox = SandboxExecutionBoundary()
    first = _validate(sandbox, orchestration_value=8)
    second = _validate(sandbox, orchestration_value=9)

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.passed is True
    assert second.value.passed is True
    assert first.value.receipt == second.value.receipt
    assert first.value.receipts_after == 1
    assert second.value.receipts_before == 1
    assert second.value.receipts_after == 1


def test_validation_harness_preserves_core_and_exposes_no_broker_surface() -> None:
    core = _core()
    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()
    sandbox = SandboxExecutionBoundary()
    harness = compose_trading_runtime_validation_harness(core, sandbox)

    assert isinstance(harness, Success)
    result = harness.value.validate(
        ExecutionOrchestrationId(UUID("b3000000-0000-0000-0000-000000000010")),
        _intent(),
        _authorization(),
        _switch(),
        request_id=_REQUEST_ID,
        receipt_id=_RECEIPT_ID,
        authorized_at=_NOW + timedelta(seconds=3),
        submitted_at=_NOW + timedelta(seconds=4),
        observed_at=_NOW + timedelta(seconds=5),
        reconciled_at=_NOW + timedelta(seconds=6),
        evaluated_at=_NOW + timedelta(seconds=7),
    )

    assert isinstance(result, Success)
    assert core.event_bus is event_bus
    assert core.runtime_plan == runtime_plan
    assert core.runtime_snapshot() == runtime_snapshot
    assert core.runtime_health() == runtime_health
    assert not hasattr(harness.value, "connect_broker")
    assert not hasattr(harness.value, "account_credentials")
