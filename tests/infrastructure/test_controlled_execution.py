from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.core.application import CoreApplication
from qore.core.bootstrap import bootstrap
from qore.core.configuration import Configuration
from qore.domain.events import CausationId, CorrelationId
from qore.infrastructure.controlled_execution import compose_controlled_execution_runtime
from qore.infrastructure.execution_boundary import (
    ExecutionReceiptId,
    ExecutionRequestId,
    SandboxExecutionBoundary,
)
from qore.infrastructure.execution_reconciliation import (
    ExecutionReconciliationStatus,
    observe_execution_receipt,
)
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
    PreTradeSafetyBlockedError,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 7, 10, tzinfo=UTC)
_INTENT_ID = OrderIntentId(UUID("b2000000-0000-0000-0000-000000000001"))
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("b2000000-0000-0000-0000-000000000002")),
    causation_id=CausationId(UUID("b2000000-0000-0000-0000-000000000003")),
)
_REQUEST_ID = ExecutionRequestId(UUID("b2000000-0000-0000-0000-000000000006"))
_RECEIPT_ID = ExecutionReceiptId(UUID("b2000000-0000-0000-0000-000000000007"))


def _core() -> CoreApplication:
    result = bootstrap(Configuration(application_name="qore-controlled-execution"))
    assert isinstance(result, Success)
    return result.value


def _intent() -> OrderIntent:
    return OrderIntent(
        intent_id=_INTENT_ID,
        idempotency_key=ExecutionIdempotencyKey(
            UUID("b2000000-0000-0000-0000-000000000004")
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
            UUID("b2000000-0000-0000-0000-000000000005")
        ),
        policy_id=PreTradePolicyId("risk.pretrade.v1"),
        intent_id=_INTENT_ID,
        decision=decision,
        evaluated_at=_NOW + timedelta(seconds=1),
        expires_at=_NOW + timedelta(seconds=10),
        reason="controlled execution safety evaluation",
    )


def _switch(
    state: ExecutionSwitchState = ExecutionSwitchState.ENABLED,
) -> ExecutionSafetySwitchSnapshot:
    return ExecutionSafetySwitchSnapshot(
        state=state,
        observed_at=_NOW + timedelta(seconds=2),
        reason="controlled execution switch declared",
    )


def test_controlled_execution_e2e_submits_and_reconciles_matched() -> None:
    core = _core()
    sandbox = SandboxExecutionBoundary()
    composed = compose_controlled_execution_runtime(core, sandbox)
    assert isinstance(composed, Success)

    submitted = composed.value.authorize_and_submit(
        _intent(),
        _authorization(),
        _switch(),
        request_id=_REQUEST_ID,
        receipt_id=_RECEIPT_ID,
        authorized_at=_NOW + timedelta(seconds=3),
        submitted_at=_NOW + timedelta(seconds=4),
    )
    assert isinstance(submitted, Success)
    observed = observe_execution_receipt(
        submitted.value,
        observed_at=_NOW + timedelta(seconds=5),
    )
    assert isinstance(observed, Success)
    reconciled = composed.value.reconcile(
        submitted.value,
        observed.value,
        reconciled_at=_NOW + timedelta(seconds=6),
    )

    assert isinstance(reconciled, Success)
    assert reconciled.value.status is ExecutionReconciliationStatus.MATCHED
    assert reconciled.value.requires_manual_action is False


def test_blocked_kill_switch_prevents_sandbox_submit() -> None:
    sandbox = SandboxExecutionBoundary()
    composed = compose_controlled_execution_runtime(_core(), sandbox)
    assert isinstance(composed, Success)

    result = composed.value.authorize_and_submit(
        _intent(),
        _authorization(),
        _switch(ExecutionSwitchState.BLOCKED),
        request_id=_REQUEST_ID,
        receipt_id=_RECEIPT_ID,
        authorized_at=_NOW + timedelta(seconds=3),
        submitted_at=_NOW + timedelta(seconds=4),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, PreTradeSafetyBlockedError)
    assert sandbox.receipts == ()


def test_blocked_pretrade_decision_prevents_sandbox_submit() -> None:
    sandbox = SandboxExecutionBoundary()
    composed = compose_controlled_execution_runtime(_core(), sandbox)
    assert isinstance(composed, Success)

    result = composed.value.authorize_and_submit(
        _intent(),
        _authorization(PreTradeDecision.BLOCKED),
        _switch(),
        request_id=_REQUEST_ID,
        receipt_id=_RECEIPT_ID,
        authorized_at=_NOW + timedelta(seconds=3),
        submitted_at=_NOW + timedelta(seconds=4),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, PreTradeSafetyBlockedError)
    assert sandbox.receipts == ()


def test_controlled_execution_composition_preserves_core_state() -> None:
    core = _core()
    event_bus = core.event_bus
    runtime_plan = core.runtime_plan
    runtime_snapshot = core.runtime_snapshot()
    runtime_health = core.runtime_health()

    result = compose_controlled_execution_runtime(core, SandboxExecutionBoundary())

    assert isinstance(result, Success)
    assert result.value.core is core
    assert core.event_bus is event_bus
    assert core.runtime_plan == runtime_plan
    assert core.runtime_snapshot() == runtime_snapshot
    assert core.runtime_health() == runtime_health


def test_controlled_execution_runtime_exposes_no_real_broker_connection() -> None:
    result = compose_controlled_execution_runtime(_core(), SandboxExecutionBoundary())

    assert isinstance(result, Success)
    assert not hasattr(result.value, "connect_broker")
    assert not hasattr(result.value, "account_credentials")
