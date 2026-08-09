from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

import qore.functional.decisions as decisions
import qore.infrastructure.account_policy as account_policy
import qore.infrastructure.client_accounts as client_accounts
import qore.infrastructure.client_execution_agent as client_agent
import qore.infrastructure.client_position_lifecycle as lifecycle
import qore.infrastructure.execution_boundary as execution_boundary
import qore.infrastructure.execution_reconciliation as reconciliation
import qore.infrastructure.order_intent as order_intent
import qore.kernel.result as result

_NOW = datetime(2026, 8, 9, 9, 0, tzinfo=UTC)


def _uuid(suffix: int) -> UUID:
    return UUID(f"35000000-0000-0000-0000-{suffix:012d}")


def _plan(
    *,
    side: order_intent.OrderSide = order_intent.OrderSide.BUY,
    trailing: bool = True,
) -> client_agent.ClientExecutionPlan:
    if side is order_intent.OrderSide.BUY:
        entry = Decimal("1.1000")
        stop = Decimal("1.0950")
        target = Decimal("1.1100")
    else:
        entry = Decimal("1.1000")
        stop = Decimal("1.1050")
        target = Decimal("1.0900")
    return client_agent.ClientExecutionPlan(
        client_id=client_accounts.ClientId(_uuid(1)),
        account_id=client_accounts.TradingAccountId(_uuid(2)),
        decision_id=decisions.DecisionId(_uuid(3)),
        instrument=order_intent.ExecutionInstrument("EUR_USD"),
        side=side,
        order_type=order_intent.OrderType.MARKET,
        quantity=order_intent.OrderQuantity(Decimal("0.25")),
        entry_reference_price=order_intent.OrderPrice(entry),
        limit_price=None,
        stop_loss=order_intent.OrderPrice(stop),
        take_profit=order_intent.OrderPrice(target),
        trailing_policy_ref=(
            client_agent.TrailingPolicyReference(_uuid(4)) if trailing else None
        ),
        account_policy_ref=client_accounts.AccountPolicyReference(_uuid(5)),
        account_policy_snapshot_id=account_policy.AccountPolicySnapshotId(_uuid(6)),
        execution_policy_id=client_agent.ClientExecutionPolicyId(_uuid(7)),
        sizing_policy_ref=client_agent.SizingPolicyReference(_uuid(8)),
        protection_policy_ref=client_agent.ProtectionPolicyReference(_uuid(9)),
        entitlement_ref=client_accounts.ProductEntitlementReference(_uuid(10)),
        runtime_ref=client_accounts.ExecutionRuntimeReference(_uuid(11)),
        account_observation_id=client_agent.ClientAccountObservationId(_uuid(12)),
        security_evidence_ref=client_agent.DecisionSecurityEvidenceReference(_uuid(13)),
        created_at=_NOW,
    )


def _receipt(
    suffix: int,
    *,
    recorded_at: datetime,
) -> execution_boundary.ExecutionReceipt:
    return execution_boundary.ExecutionReceipt(
        receipt_id=execution_boundary.ExecutionReceiptId(_uuid(100 + suffix)),
        request_id=execution_boundary.ExecutionRequestId(_uuid(200 + suffix)),
        idempotency_key=order_intent.ExecutionIdempotencyKey(_uuid(300 + suffix)),
        status=execution_boundary.ExecutionStatus.ACCEPTED,
        recorded_at=recorded_at,
    )


def _reconciliation(
    receipt: execution_boundary.ExecutionReceipt,
    *,
    reconciled_at: datetime,
    status: reconciliation.ExecutionReconciliationStatus = (
        reconciliation.ExecutionReconciliationStatus.MATCHED
    ),
) -> reconciliation.ExecutionReconciliationSnapshot:
    observed = reconciliation.ExecutionObservation(
        receipt_id=receipt.receipt_id,
        request_id=receipt.request_id,
        idempotency_key=receipt.idempotency_key,
        status=receipt.status,
        observed_at=reconciled_at - timedelta(seconds=1),
    )
    issues = () if status is reconciliation.ExecutionReconciliationStatus.MATCHED else (
        "status_mismatch",
    )
    return reconciliation.ExecutionReconciliationSnapshot(
        status=status,
        reconciled_at=reconciled_at,
        expected=receipt,
        observed=observed,
        issues=issues,
    )


def _confirmation(
    plan: client_agent.ClientExecutionPlan,
    *,
    suffix: int = 1,
) -> lifecycle.ClientExecutionConfirmation:
    receipt = _receipt(suffix, recorded_at=_NOW + timedelta(seconds=1))
    matched = _reconciliation(
        receipt,
        reconciled_at=_NOW + timedelta(seconds=2),
    )
    return lifecycle.ClientExecutionConfirmation(
        plan=plan,
        receipt=receipt,
        reconciliation=matched,
        fill_price=plan.entry_reference_price,
        confirmed_at=_NOW + timedelta(seconds=3),
        evidence_ref=lifecycle.ClientPositionEvidenceReference(_uuid(400 + suffix)),
    )


def _open(
    plan: client_agent.ClientExecutionPlan | None = None,
) -> lifecycle.ClientPositionLifecycle:
    selected_plan = plan or _plan()
    opened = lifecycle.open_client_position(
        _confirmation(selected_plan),
        position_id=lifecycle.ClientPositionId(_uuid(500)),
        action_id=lifecycle.ClientPositionActionId(_uuid(501)),
        rationale_code=lifecycle.ClientPositionRationaleCode("execution.confirmed"),
        opened_at=_NOW + timedelta(seconds=4),
    )
    assert isinstance(opened, result.Success)
    return opened.value


def test_open_position_preserves_complete_causal_genealogy() -> None:
    plan = _plan()
    confirmation = _confirmation(plan)

    opened = lifecycle.open_client_position(
        confirmation,
        position_id=lifecycle.ClientPositionId(_uuid(500)),
        action_id=lifecycle.ClientPositionActionId(_uuid(501)),
        rationale_code=lifecycle.ClientPositionRationaleCode("execution.confirmed"),
        opened_at=_NOW + timedelta(seconds=4),
    )

    assert isinstance(opened, result.Success)
    position = opened.value
    action = position.actions[0]
    assert position.state is lifecycle.ClientPositionState.OPEN
    assert position.entry_price == confirmation.fill_price
    assert position.current_stop == plan.stop_loss
    assert action.kind is lifecycle.ClientPositionActionKind.OPEN
    assert action.position_id == position.position_id
    assert action.account_id == plan.account_id
    assert action.decision_id == plan.decision_id
    assert action.account_policy_ref == plan.account_policy_ref
    assert action.account_policy_snapshot_id == plan.account_policy_snapshot_id
    assert action.execution_policy_id == plan.execution_policy_id
    assert action.protection_policy_ref == plan.protection_policy_ref
    assert action.trailing_policy_ref == plan.trailing_policy_ref
    assert action.execution_receipt_id == confirmation.receipt.receipt_id
    assert action.evidence_ref == confirmation.evidence_ref


def test_open_position_rejects_ambiguous_execution_reconciliation() -> None:
    plan = _plan()
    receipt = _receipt(1, recorded_at=_NOW + timedelta(seconds=1))
    diverged = _reconciliation(
        receipt,
        reconciled_at=_NOW + timedelta(seconds=2),
        status=reconciliation.ExecutionReconciliationStatus.DIVERGED,
    )

    with pytest.raises(lifecycle.ClientPositionLifecycleValidationError):
        lifecycle.ClientExecutionConfirmation(
            plan=plan,
            receipt=receipt,
            reconciliation=diverged,
            fill_price=plan.entry_reference_price,
            confirmed_at=_NOW + timedelta(seconds=3),
            evidence_ref=lifecycle.ClientPositionEvidenceReference(_uuid(401)),
        )


def test_buy_trailing_stop_is_monotonic_and_auditable() -> None:
    position = _open(_plan(side=order_intent.OrderSide.BUY))
    prior_stop = position.current_stop
    evidence = lifecycle.ClientPositionEvidenceReference(_uuid(510))

    trailed = lifecycle.apply_client_trailing_stop(
        position,
        action_id=lifecycle.ClientPositionActionId(_uuid(511)),
        new_stop=order_intent.OrderPrice(Decimal("1.1005")),
        evidence_ref=evidence,
        rationale_code=lifecycle.ClientPositionRationaleCode("trailing.policy_trigger"),
        occurred_at=_NOW + timedelta(seconds=5),
    )

    assert isinstance(trailed, result.Success)
    updated = trailed.value
    action = updated.actions[-1]
    assert updated.current_stop == order_intent.OrderPrice(Decimal("1.1005"))
    assert action.kind is lifecycle.ClientPositionActionKind.TRAILING_STOP
    assert action.previous_stop == prior_stop
    assert action.new_stop == updated.current_stop
    assert action.evidence_ref == evidence
    assert action.decision_id == updated.plan.decision_id
    assert action.trailing_policy_ref == updated.plan.trailing_policy_ref


def test_sell_trailing_stop_moves_only_toward_profit() -> None:
    position = _open(_plan(side=order_intent.OrderSide.SELL))

    trailed = lifecycle.apply_client_trailing_stop(
        position,
        action_id=lifecycle.ClientPositionActionId(_uuid(512)),
        new_stop=order_intent.OrderPrice(Decimal("1.0995")),
        evidence_ref=lifecycle.ClientPositionEvidenceReference(_uuid(513)),
        rationale_code=lifecycle.ClientPositionRationaleCode("trailing.policy_trigger"),
        occurred_at=_NOW + timedelta(seconds=5),
    )

    assert isinstance(trailed, result.Success)
    assert trailed.value.current_stop == order_intent.OrderPrice(Decimal("1.0995"))


def test_trailing_stop_rejects_worsening_or_target_crossing() -> None:
    position = _open(_plan(side=order_intent.OrderSide.BUY))

    for invalid_stop in (Decimal("1.0940"), Decimal("1.1110")):
        trailed = lifecycle.apply_client_trailing_stop(
            position,
            action_id=lifecycle.ClientPositionActionId(_uuid(520)),
            new_stop=order_intent.OrderPrice(invalid_stop),
            evidence_ref=lifecycle.ClientPositionEvidenceReference(_uuid(521)),
            rationale_code=lifecycle.ClientPositionRationaleCode(
                "trailing.policy_trigger"
            ),
            occurred_at=_NOW + timedelta(seconds=5),
        )
        assert isinstance(trailed, result.Failure)
        assert "trailing stop must improve protection" in str(trailed.error)


def test_trailing_requires_authorized_trailing_policy() -> None:
    position = _open(_plan(trailing=False))

    trailed = lifecycle.apply_client_trailing_stop(
        position,
        action_id=lifecycle.ClientPositionActionId(_uuid(530)),
        new_stop=order_intent.OrderPrice(Decimal("1.1005")),
        evidence_ref=lifecycle.ClientPositionEvidenceReference(_uuid(531)),
        rationale_code=lifecycle.ClientPositionRationaleCode("trailing.policy_trigger"),
        occurred_at=_NOW + timedelta(seconds=5),
    )

    assert isinstance(trailed, result.Failure)
    assert str(trailed.error) == "position execution plan does not authorize trailing"


def test_close_position_requires_distinct_matched_execution_evidence() -> None:
    position = _open()
    exit_receipt = _receipt(2, recorded_at=_NOW + timedelta(seconds=6))
    matched = _reconciliation(
        exit_receipt,
        reconciled_at=_NOW + timedelta(seconds=7),
    )
    evidence = lifecycle.ClientPositionEvidenceReference(_uuid(540))

    closed = lifecycle.close_client_position(
        position,
        exit_receipt,
        matched,
        action_id=lifecycle.ClientPositionActionId(_uuid(541)),
        exit_price=order_intent.OrderPrice(Decimal("1.1080")),
        exit_reason=lifecycle.ClientPositionExitReason.TAKE_PROFIT,
        evidence_ref=evidence,
        rationale_code=lifecycle.ClientPositionRationaleCode("exit.take_profit"),
        closed_at=_NOW + timedelta(seconds=8),
    )

    assert isinstance(closed, result.Success)
    final = closed.value
    action = final.actions[-1]
    assert final.state is lifecycle.ClientPositionState.CLOSED
    assert final.closed_at == _NOW + timedelta(seconds=8)
    assert action.kind is lifecycle.ClientPositionActionKind.EXIT
    assert action.execution_receipt_id == exit_receipt.receipt_id
    assert action.exit_reason is lifecycle.ClientPositionExitReason.TAKE_PROFIT
    assert action.evidence_ref == evidence
    assert action.decision_id == final.plan.decision_id


def test_ambiguous_exit_does_not_mutate_or_redispatch_position() -> None:
    position = _open()
    exit_receipt = _receipt(2, recorded_at=_NOW + timedelta(seconds=6))
    diverged = _reconciliation(
        exit_receipt,
        reconciled_at=_NOW + timedelta(seconds=7),
        status=reconciliation.ExecutionReconciliationStatus.DIVERGED,
    )

    closed = lifecycle.close_client_position(
        position,
        exit_receipt,
        diverged,
        action_id=lifecycle.ClientPositionActionId(_uuid(550)),
        exit_price=order_intent.OrderPrice(Decimal("1.1080")),
        exit_reason=lifecycle.ClientPositionExitReason.CORE_POLICY,
        evidence_ref=lifecycle.ClientPositionEvidenceReference(_uuid(551)),
        rationale_code=lifecycle.ClientPositionRationaleCode("exit.core_policy"),
        closed_at=_NOW + timedelta(seconds=8),
    )

    assert isinstance(closed, result.Failure)
    assert position.state is lifecycle.ClientPositionState.OPEN
    assert len(position.actions) == 1
    assert not hasattr(lifecycle, "redispatch")
    assert not hasattr(lifecycle, "retry")


def test_closed_position_cannot_be_modified_again() -> None:
    position = _open()
    exit_receipt = _receipt(2, recorded_at=_NOW + timedelta(seconds=6))
    matched = _reconciliation(
        exit_receipt,
        reconciled_at=_NOW + timedelta(seconds=7),
    )
    closed = lifecycle.close_client_position(
        position,
        exit_receipt,
        matched,
        action_id=lifecycle.ClientPositionActionId(_uuid(560)),
        exit_price=order_intent.OrderPrice(Decimal("1.1080")),
        exit_reason=lifecycle.ClientPositionExitReason.CORE_POLICY,
        evidence_ref=lifecycle.ClientPositionEvidenceReference(_uuid(561)),
        rationale_code=lifecycle.ClientPositionRationaleCode("exit.core_policy"),
        closed_at=_NOW + timedelta(seconds=8),
    )
    assert isinstance(closed, result.Success)

    trailed = lifecycle.apply_client_trailing_stop(
        closed.value,
        action_id=lifecycle.ClientPositionActionId(_uuid(562)),
        new_stop=order_intent.OrderPrice(Decimal("1.1005")),
        evidence_ref=lifecycle.ClientPositionEvidenceReference(_uuid(563)),
        rationale_code=lifecycle.ClientPositionRationaleCode("trailing.policy_trigger"),
        occurred_at=_NOW + timedelta(seconds=9),
    )
    closed_again = lifecycle.close_client_position(
        closed.value,
        _receipt(3, recorded_at=_NOW + timedelta(seconds=9)),
        _reconciliation(
            _receipt(3, recorded_at=_NOW + timedelta(seconds=9)),
            reconciled_at=_NOW + timedelta(seconds=10),
        ),
        action_id=lifecycle.ClientPositionActionId(_uuid(564)),
        exit_price=order_intent.OrderPrice(Decimal("1.1070")),
        exit_reason=lifecycle.ClientPositionExitReason.AUTHORIZED_MANUAL,
        evidence_ref=lifecycle.ClientPositionEvidenceReference(_uuid(565)),
        rationale_code=lifecycle.ClientPositionRationaleCode("exit.authorized_manual"),
        closed_at=_NOW + timedelta(seconds=11),
    )

    assert isinstance(trailed, result.Failure)
    assert isinstance(closed_again, result.Failure)


def test_orphan_action_with_wrong_account_is_rejected() -> None:
    plan = _plan()
    confirmation = _confirmation(plan)
    position_id = lifecycle.ClientPositionId(_uuid(570))
    action = lifecycle.ClientPositionAction(
        action_id=lifecycle.ClientPositionActionId(_uuid(571)),
        kind=lifecycle.ClientPositionActionKind.OPEN,
        position_id=position_id,
        account_id=client_accounts.TradingAccountId(_uuid(999)),
        decision_id=plan.decision_id,
        occurred_at=_NOW + timedelta(seconds=4),
        evidence_ref=confirmation.evidence_ref,
        rationale_code=lifecycle.ClientPositionRationaleCode("execution.confirmed"),
        account_policy_ref=plan.account_policy_ref,
        account_policy_snapshot_id=plan.account_policy_snapshot_id,
        execution_policy_id=plan.execution_policy_id,
        protection_policy_ref=plan.protection_policy_ref,
        trailing_policy_ref=plan.trailing_policy_ref,
        execution_receipt_id=confirmation.receipt.receipt_id,
        new_stop=plan.stop_loss,
    )

    with pytest.raises(lifecycle.ClientPositionLifecycleValidationError):
        lifecycle.ClientPositionLifecycle(
            plan=plan,
            position_id=position_id,
            state=lifecycle.ClientPositionState.OPEN,
            entry_price=confirmation.fill_price,
            current_stop=plan.stop_loss,
            take_profit=plan.take_profit,
            opened_at=_NOW + timedelta(seconds=4),
            closed_at=None,
            actions=(action,),
        )


def test_lifecycle_has_no_broker_or_submission_authority() -> None:
    assert not hasattr(lifecycle.ClientPositionLifecycle, "submit_order")
    assert not hasattr(lifecycle.ClientPositionLifecycle, "broker")
    assert not hasattr(lifecycle.ClientPositionLifecycle, "redispatch")
    assert not hasattr(lifecycle.ClientPositionAction, "execute")
