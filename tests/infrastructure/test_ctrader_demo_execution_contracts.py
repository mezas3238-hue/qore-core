from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.ctrader_demo_execution_contracts import (
    CTraderDemoAttemptState,
    CTraderDemoExecutionConflictError,
    CTraderDemoExecutionValidationError,
    CTraderDemoFillObservation,
    CTraderDemoFillReconciliationStatus,
    CTraderDemoMutationAttempt,
    CTraderDemoOrderDisposition,
    CTraderDemoOrderState,
    ctrader_demo_account_fingerprint,
    order_state_for_disposition,
    reconcile_ctrader_demo_fills,
    transition_ctrader_demo_attempt,
)
from qore.infrastructure.execution_boundary import ExecutionReceiptId
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)
from qore.infrastructure.order_intent import (
    ExecutionIdempotencyKey,
    ExecutionInstrument,
    OrderSide,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 23, 30, tzinfo=UTC)
_ACCOUNT = MarketTestAccountIdentity(
    provider_key="ctrader-demo",
    account_ref="demo-001",
    environment=MarketRuntimeEnvironment.DEMO,
)


def _attempt(
    *,
    state: CTraderDemoAttemptState = CTraderDemoAttemptState.NOT_ATTEMPTED,
    transitioned_at: datetime = _NOW,
    receipt_suffix: int = 1,
    key_suffix: int = 1,
) -> CTraderDemoMutationAttempt:
    return CTraderDemoMutationAttempt(
        idempotency_key=ExecutionIdempotencyKey(UUID(f"32000000-0000-0000-1000-{key_suffix:012d}")),
        receipt_id=ExecutionReceiptId(UUID(f"32000000-0000-0000-4000-{receipt_suffix:012d}")),
        submission_logical=(("submission", key_suffix),),
        state=state,
        transitioned_at=transitioned_at,
    )


def test_account_fingerprint_is_deterministic_and_non_reversible() -> None:
    first = ctrader_demo_account_fingerprint("demo-001")
    second = ctrader_demo_account_fingerprint("demo-001")
    assert first == second
    assert first.startswith("sha256:")
    assert "demo-001" not in first


def test_order_state_for_disposition_covers_all_dispositions() -> None:
    assert (
        order_state_for_disposition(CTraderDemoOrderDisposition.ACCEPTED)
        is CTraderDemoOrderState.ACCEPTED
    )
    assert (
        order_state_for_disposition(CTraderDemoOrderDisposition.FILLED)
        is CTraderDemoOrderState.FILLED
    )
    assert (
        order_state_for_disposition(CTraderDemoOrderDisposition.REJECTED)
        is CTraderDemoOrderState.REJECTED
    )


def test_attempt_transition_requires_strictly_later_timestamp() -> None:
    attempt = _attempt(state=CTraderDemoAttemptState.NOT_ATTEMPTED)
    result = transition_ctrader_demo_attempt(
        attempt,
        CTraderDemoAttemptState.ATTEMPT_STARTED,
        transitioned_at=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoExecutionValidationError)


def test_attempt_transition_rejects_invalid_hop() -> None:
    attempt = _attempt(state=CTraderDemoAttemptState.NOT_ATTEMPTED)
    result = transition_ctrader_demo_attempt(
        attempt,
        CTraderDemoAttemptState.DEFINITIVE_OUTCOME,
        transitioned_at=_NOW + timedelta(seconds=1),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoExecutionConflictError)


def test_attempt_lifecycle_full_path() -> None:
    attempt = _attempt(state=CTraderDemoAttemptState.NOT_ATTEMPTED)
    started = transition_ctrader_demo_attempt(
        attempt,
        CTraderDemoAttemptState.ATTEMPT_STARTED,
        transitioned_at=_NOW + timedelta(seconds=1),
    )
    assert isinstance(started, Success)
    unknown = transition_ctrader_demo_attempt(
        started.value,
        CTraderDemoAttemptState.OUTCOME_UNKNOWN,
        transitioned_at=_NOW + timedelta(seconds=2),
        reason="transport failure",
    )
    assert isinstance(unknown, Success)
    reconciling = transition_ctrader_demo_attempt(
        unknown.value,
        CTraderDemoAttemptState.RECONCILIATION_REQUIRED,
        transitioned_at=_NOW + timedelta(seconds=3),
    )
    assert isinstance(reconciling, Success)
    resolved = transition_ctrader_demo_attempt(
        reconciling.value,
        CTraderDemoAttemptState.RESOLVED,
        transitioned_at=_NOW + timedelta(seconds=4),
        provider_order_ref="70001",
    )
    assert isinstance(resolved, Success)
    assert resolved.value.state is CTraderDemoAttemptState.RESOLVED
    assert resolved.value.provider_order_ref == "70001"


def test_fill_reconciliation_matched_complete() -> None:
    result = reconcile_ctrader_demo_fills(
        Decimal("10"),
        Decimal("10"),
        is_complete=True,
        reconciled_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.status is CTraderDemoFillReconciliationStatus.MATCHED
    assert result.value.issues == ()


def test_fill_reconciliation_overfill_diverges() -> None:
    result = reconcile_ctrader_demo_fills(
        Decimal("10"),
        Decimal("11"),
        is_complete=True,
        reconciled_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.status is CTraderDemoFillReconciliationStatus.DIVERGED


def test_fill_reconciliation_complete_underfill_diverges() -> None:
    result = reconcile_ctrader_demo_fills(
        Decimal("10"),
        Decimal("8"),
        is_complete=True,
        reconciled_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.status is CTraderDemoFillReconciliationStatus.DIVERGED


def test_fill_reconciliation_partial_is_preserved() -> None:
    result = reconcile_ctrader_demo_fills(
        Decimal("10"),
        Decimal("4"),
        is_complete=False,
        reconciled_at=_NOW,
    )
    assert isinstance(result, Success)
    assert result.value.status is CTraderDemoFillReconciliationStatus.PARTIAL


def test_fill_observation_requires_demo_account() -> None:
    live = MarketTestAccountIdentity(
        provider_key="ctrader-demo",
        account_ref="demo-001",
        environment=MarketRuntimeEnvironment.PRODUCTION,
    )
    with pytest.raises(CTraderDemoExecutionValidationError):
        CTraderDemoFillObservation(
            receipt_id=ExecutionReceiptId(UUID("32000000-0000-0000-4000-000000000001")),
            idempotency_key=ExecutionIdempotencyKey(UUID("32000000-0000-0000-1000-000000000001")),
            account=live,
            instrument=ExecutionInstrument("EURUSD"),
            side=OrderSide.BUY,
            provider_order_ref="70001",
            fill_ref="90001",
            fill_quantity=Decimal("4"),
            cumulative_quantity=Decimal("4"),
            fill_price=Decimal("1.23456"),
            provider_timestamp=_NOW,
            received_at=_NOW + timedelta(milliseconds=1),
        )


def test_fill_observation_cumulative_must_cover_fill_quantity() -> None:
    with pytest.raises(CTraderDemoExecutionValidationError):
        CTraderDemoFillObservation(
            receipt_id=ExecutionReceiptId(UUID("32000000-0000-0000-4000-000000000001")),
            idempotency_key=ExecutionIdempotencyKey(UUID("32000000-0000-0000-1000-000000000001")),
            account=_ACCOUNT,
            instrument=ExecutionInstrument("EURUSD"),
            side=OrderSide.BUY,
            provider_order_ref="70001",
            fill_ref="90001",
            fill_quantity=Decimal("5"),
            cumulative_quantity=Decimal("4"),
            fill_price=Decimal("1.23456"),
            provider_timestamp=_NOW,
            received_at=_NOW + timedelta(milliseconds=1),
        )
