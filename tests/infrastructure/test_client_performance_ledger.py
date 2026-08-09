from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import qore.functional.decisions as decisions
import qore.infrastructure.account_policy as account_policy
import qore.infrastructure.client_accounts as client_accounts
import qore.infrastructure.client_execution_agent as client_agent
import qore.infrastructure.client_performance_ledger as performance
import qore.infrastructure.client_position_lifecycle as lifecycle
import qore.infrastructure.execution_boundary as execution_boundary
import qore.infrastructure.execution_reconciliation as reconciliation
import qore.infrastructure.order_intent as order_intent
import qore.infrastructure.proprietary_accounts as money
import qore.kernel.result as result

_NOW = datetime(2026, 8, 9, 10, 0, tzinfo=UTC)
_USD = money.CurrencyCode("USD")


def _uuid(suffix: int) -> UUID:
    return UUID(f"36000000-0000-0000-0000-{suffix:012d}")


def _amount(value: str) -> money.MoneyAmount:
    return money.MoneyAmount(currency=_USD, amount=Decimal(value))


def _plan(*, account_suffix: int = 2, decision_suffix: int = 3) -> client_agent.ClientExecutionPlan:
    return client_agent.ClientExecutionPlan(
        client_id=client_accounts.ClientId(_uuid(1)),
        account_id=client_accounts.TradingAccountId(_uuid(account_suffix)),
        decision_id=decisions.DecisionId(_uuid(decision_suffix)),
        instrument=order_intent.ExecutionInstrument("EUR_USD"),
        side=order_intent.OrderSide.BUY,
        order_type=order_intent.OrderType.MARKET,
        quantity=order_intent.OrderQuantity(Decimal("0.25")),
        entry_reference_price=order_intent.OrderPrice(Decimal("1.1000")),
        limit_price=None,
        stop_loss=order_intent.OrderPrice(Decimal("1.0950")),
        take_profit=order_intent.OrderPrice(Decimal("1.1100")),
        trailing_policy_ref=client_agent.TrailingPolicyReference(_uuid(4)),
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


def _receipt(suffix: int, at: datetime) -> execution_boundary.ExecutionReceipt:
    return execution_boundary.ExecutionReceipt(
        receipt_id=execution_boundary.ExecutionReceiptId(_uuid(100 + suffix)),
        request_id=execution_boundary.ExecutionRequestId(_uuid(200 + suffix)),
        idempotency_key=order_intent.ExecutionIdempotencyKey(_uuid(300 + suffix)),
        status=execution_boundary.ExecutionStatus.ACCEPTED,
        recorded_at=at,
    )


def _matched(
    receipt: execution_boundary.ExecutionReceipt,
    at: datetime,
) -> reconciliation.ExecutionReconciliationSnapshot:
    observed = reconciliation.ExecutionObservation(
        receipt_id=receipt.receipt_id,
        request_id=receipt.request_id,
        idempotency_key=receipt.idempotency_key,
        status=receipt.status,
        observed_at=at,
    )
    return reconciliation.ExecutionReconciliationSnapshot(
        status=reconciliation.ExecutionReconciliationStatus.MATCHED,
        reconciled_at=at,
        expected=receipt,
        observed=observed,
        issues=(),
    )


def _closed_position(
    *,
    account_suffix: int = 2,
    decision_suffix: int = 3,
    position_suffix: int = 500,
) -> lifecycle.ClientPositionLifecycle:
    plan = _plan(account_suffix=account_suffix, decision_suffix=decision_suffix)
    entry_receipt = _receipt(position_suffix, _NOW + timedelta(seconds=1))
    confirmation = lifecycle.ClientExecutionConfirmation(
        plan=plan,
        receipt=entry_receipt,
        reconciliation=_matched(entry_receipt, _NOW + timedelta(seconds=2)),
        fill_price=plan.entry_reference_price,
        confirmed_at=_NOW + timedelta(seconds=3),
        evidence_ref=lifecycle.ClientPositionEvidenceReference(_uuid(position_suffix + 1)),
    )
    opened = lifecycle.open_client_position(
        confirmation,
        position_id=lifecycle.ClientPositionId(_uuid(position_suffix + 2)),
        action_id=lifecycle.ClientPositionActionId(_uuid(position_suffix + 3)),
        rationale_code=lifecycle.ClientPositionRationaleCode("execution.confirmed"),
        opened_at=_NOW + timedelta(seconds=4),
    )
    assert isinstance(opened, result.Success)
    exit_receipt = _receipt(position_suffix + 10, _NOW + timedelta(seconds=5))
    closed = lifecycle.close_client_position(
        opened.value,
        exit_receipt,
        _matched(exit_receipt, _NOW + timedelta(seconds=6)),
        action_id=lifecycle.ClientPositionActionId(_uuid(position_suffix + 4)),
        exit_price=order_intent.OrderPrice(Decimal("1.1080")),
        exit_reason=lifecycle.ClientPositionExitReason.TAKE_PROFIT,
        evidence_ref=lifecycle.ClientPositionEvidenceReference(_uuid(position_suffix + 5)),
        rationale_code=lifecycle.ClientPositionRationaleCode("exit.take_profit"),
        closed_at=_NOW + timedelta(seconds=7),
    )
    assert isinstance(closed, result.Success)
    return closed.value


def _ledger(*, account_suffix: int = 2) -> performance.ClientPerformanceLedger:
    return performance.ClientPerformanceLedger(
        account_id=client_accounts.TradingAccountId(_uuid(account_suffix)),
        currency=_USD,
    )


def _append_realized(
    ledger: performance.ClientPerformanceLedger,
    position: lifecycle.ClientPositionLifecycle,
    *,
    suffix: int,
    pnl: str,
) -> performance.ClientPerformanceLedger:
    appended = performance.append_realized_performance(
        ledger,
        position,
        record_id=performance.ClientPerformanceRecordId(_uuid(suffix)),
        realized_pnl=_amount(pnl),
        evidence_ref=performance.ClientPerformanceEvidenceReference(_uuid(suffix + 1)),
        recorded_at=_NOW + timedelta(seconds=8),
    )
    assert isinstance(appended, result.Success)
    return appended.value


def test_realized_ledger_accepts_wins_and_losses_per_account() -> None:
    ledger = _ledger()
    first = _append_realized(ledger, _closed_position(), suffix=700, pnl="125.50")
    second_position = _closed_position(decision_suffix=33, position_suffix=600)
    second = _append_realized(first, second_position, suffix=710, pnl="-40.25")

    assert len(second.realized) == 2
    assert second.net_realized_pnl == _amount("85.25")
    assert second.realized[0].account_id == second.account_id
    assert second.realized[1].decision_id == second_position.plan.decision_id


def test_same_position_cannot_be_recorded_twice() -> None:
    position = _closed_position()
    first = _append_realized(_ledger(), position, suffix=720, pnl="100")

    duplicate = performance.append_realized_performance(
        first,
        position,
        record_id=performance.ClientPerformanceRecordId(_uuid(722)),
        realized_pnl=_amount("100"),
        evidence_ref=performance.ClientPerformanceEvidenceReference(_uuid(723)),
        recorded_at=_NOW + timedelta(seconds=9),
    )

    assert isinstance(duplicate, result.Failure)
    assert str(duplicate.error) == "position already has a realized performance record"


def test_correction_is_append_only_delta_with_lineage() -> None:
    ledger = _append_realized(
        _ledger(),
        _closed_position(),
        suffix=730,
        pnl="100",
    )
    correction = performance.ClientPerformanceCorrectionRecord(
        record_id=performance.ClientPerformanceRecordId(_uuid(732)),
        account_id=ledger.account_id,
        corrects_record_id=ledger.realized[0].record_id,
        adjustment=_amount("-10"),
        corrected_at=_NOW + timedelta(seconds=10),
        evidence_ref=performance.ClientPerformanceEvidenceReference(_uuid(733)),
    )

    corrected = performance.append_performance_correction(ledger, correction)

    assert isinstance(corrected, result.Success)
    assert corrected.value.realized == ledger.realized
    assert corrected.value.net_realized_pnl == _amount("90")
    assert corrected.value.corrections[0].corrects_record_id == ledger.realized[0].record_id


def test_paid_profit_requires_existing_entitlement_and_payout_evidence() -> None:
    ledger = _ledger()
    entitled = performance.ClientEntitledProfitRecord(
        record_id=performance.ClientPerformanceRecordId(_uuid(740)),
        account_id=ledger.account_id,
        amount=_amount("8000"),
        payout_policy_ref=performance.ClientPayoutPolicyReference(_uuid(741)),
        evaluated_at=_NOW,
        evidence_ref=performance.ClientPerformanceEvidenceReference(_uuid(742)),
    )
    with_entitlement = performance.append_entitled_profit(ledger, entitled)
    assert isinstance(with_entitlement, result.Success)
    paid = performance.ClientPaidProfitRecord(
        record_id=performance.ClientPerformanceRecordId(_uuid(743)),
        account_id=ledger.account_id,
        entitlement_record_id=entitled.record_id,
        amount=_amount("8000"),
        paid_at=_NOW + timedelta(days=1),
        payout_evidence_ref=performance.ClientPayoutEvidenceReference(_uuid(744)),
    )

    with_paid = performance.append_paid_profit(with_entitlement.value, paid)

    assert isinstance(with_paid, result.Success)
    assert with_paid.value.paid[0].payout_evidence_ref == paid.payout_evidence_ref
    assert with_paid.value.entitled[0].record_id == paid.entitlement_record_id


def test_paid_profit_cannot_be_inferred_without_entitlement_lineage() -> None:
    ledger = _ledger()
    paid = performance.ClientPaidProfitRecord(
        record_id=performance.ClientPerformanceRecordId(_uuid(750)),
        account_id=ledger.account_id,
        entitlement_record_id=performance.ClientPerformanceRecordId(_uuid(751)),
        amount=_amount("100"),
        paid_at=_NOW,
        payout_evidence_ref=performance.ClientPayoutEvidenceReference(_uuid(752)),
    )

    appended = performance.append_paid_profit(ledger, paid)

    assert isinstance(appended, result.Failure)
    assert "existing entitlement" in str(appended.error)


def test_eligible_paid_profit_is_capped_by_verified_client_payout() -> None:
    ledger = _ledger()
    entitled = performance.ClientEntitledProfitRecord(
        record_id=performance.ClientPerformanceRecordId(_uuid(760)),
        account_id=ledger.account_id,
        amount=_amount("8000"),
        payout_policy_ref=performance.ClientPayoutPolicyReference(_uuid(761)),
        evaluated_at=_NOW,
        evidence_ref=performance.ClientPerformanceEvidenceReference(_uuid(762)),
    )
    entitled_result = performance.append_entitled_profit(ledger, entitled)
    assert isinstance(entitled_result, result.Success)
    paid = performance.ClientPaidProfitRecord(
        record_id=performance.ClientPerformanceRecordId(_uuid(763)),
        account_id=ledger.account_id,
        entitlement_record_id=entitled.record_id,
        amount=_amount("8000"),
        paid_at=_NOW + timedelta(days=1),
        payout_evidence_ref=performance.ClientPayoutEvidenceReference(_uuid(764)),
    )
    paid_result = performance.append_paid_profit(entitled_result.value, paid)
    assert isinstance(paid_result, result.Success)
    eligible = performance.EligibleClientPaidProfitRecord(
        record_id=performance.ClientPerformanceRecordId(_uuid(765)),
        account_id=ledger.account_id,
        paid_profit_record_id=paid.record_id,
        amount=_amount("8000"),
        payout_policy_ref=performance.ClientPayoutPolicyReference(_uuid(766)),
        evaluated_at=_NOW + timedelta(days=1, seconds=1),
        evidence_ref=performance.ClientPerformanceEvidenceReference(_uuid(767)),
    )

    eligible_result = performance.append_eligible_paid_profit(paid_result.value, eligible)

    assert isinstance(eligible_result, result.Success)
    assert eligible_result.value.eligible_paid[0].amount == _amount("8000")

    excessive = performance.EligibleClientPaidProfitRecord(
        record_id=performance.ClientPerformanceRecordId(_uuid(768)),
        account_id=ledger.account_id,
        paid_profit_record_id=paid.record_id,
        amount=_amount("8001"),
        payout_policy_ref=performance.ClientPayoutPolicyReference(_uuid(769)),
        evaluated_at=_NOW + timedelta(days=1, seconds=2),
        evidence_ref=performance.ClientPerformanceEvidenceReference(_uuid(770)),
    )
    excessive_result = performance.append_eligible_paid_profit(
        paid_result.value,
        excessive,
    )
    assert isinstance(excessive_result, result.Failure)


def test_accounts_cannot_contaminate_each_others_performance() -> None:
    account_a = _ledger(account_suffix=2)
    account_b_position = _closed_position(
        account_suffix=22,
        decision_suffix=23,
        position_suffix=800,
    )

    appended = performance.append_realized_performance(
        account_a,
        account_b_position,
        record_id=performance.ClientPerformanceRecordId(_uuid(810)),
        realized_pnl=_amount("100"),
        evidence_ref=performance.ClientPerformanceEvidenceReference(_uuid(811)),
        recorded_at=_NOW + timedelta(seconds=8),
    )

    assert isinstance(appended, result.Failure)
    assert "does not match ledger" in str(appended.error)


def test_client_performance_has_no_corporate_or_billing_authority() -> None:
    assert not hasattr(performance.ClientPerformanceLedger, "mark_invoice_paid")
    assert not hasattr(performance.ClientPerformanceLedger, "corporate_revenue")
    assert not hasattr(performance.ClientPerformanceLedger, "charge")
    assert not hasattr(performance.ClientPerformanceLedger, "submit_order")
