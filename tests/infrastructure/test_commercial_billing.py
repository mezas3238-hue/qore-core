from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.client_performance_ledger as performance
import qore.infrastructure.client_trial_licensing as licensing
import qore.infrastructure.commercial_billing as billing
import qore.infrastructure.commercial_products as products
import qore.infrastructure.proprietary_accounts as money
import qore.kernel.result as result

_NOW = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
_USD = money.CurrencyCode("USD")


def _uuid(suffix: int) -> UUID:
    return UUID(f"39000000-0000-0000-0000-{suffix:012d}")


def _amount(value: str) -> money.MoneyAmount:
    return money.MoneyAmount(currency=_USD, amount=Decimal(value))


def _ea_plan() -> products.CommercialPlan:
    product = products.CommercialProduct(
        product_id=products.CommercialProductId(_uuid(1)),
        kind=products.CommercialProductKind.CLIENT_EXECUTION_AGENT,
        availability=products.CommercialProductAvailability.CONFIRMED,
    )
    return products.CommercialPlan(
        plan_id=products.CommercialPlanId(_uuid(2)),
        version=products.CommercialPlanVersion(1),
        product=product,
        billing_unit=products.CommercialBillingUnit.ACCOUNT,
        cadence=products.CommercialBillingCadence.MONTHLY,
        price=_amount("29"),
    )


def _invoice(*, suffix: int = 10) -> billing.CommercialInvoice:
    return billing.CommercialInvoice.from_plan(
        invoice_id=billing.CommercialInvoiceId(_uuid(suffix)),
        client_id=accounts.ClientId(_uuid(20)),
        account_id=accounts.TradingAccountId(_uuid(21)),
        plan=_ea_plan(),
        period_started_at=_NOW,
        period_ended_at=_NOW + timedelta(days=30),
        issued_at=_NOW,
        due_at=_NOW + timedelta(days=7),
    )


def _payment(
    *,
    suffix: int = 30,
    amount: str = "29",
    verification: billing.CommercialPaymentVerification = (
        billing.CommercialPaymentVerification.VERIFIED
    ),
) -> billing.VerifiedCommercialPayment:
    return billing.VerifiedCommercialPayment(
        payment_id=billing.CommercialPaymentId(_uuid(suffix)),
        client_id=accounts.ClientId(_uuid(20)),
        amount=_amount(amount),
        paid_at=_NOW + timedelta(days=1),
        verification=verification,
        evidence_ref=billing.CommercialPaymentEvidenceReference(_uuid(suffix + 1)),
    )


def _ledger_with_invoice() -> billing.CommercialBillingLedger:
    appended = billing.append_invoice(billing.CommercialBillingLedger(), _invoice())
    assert isinstance(appended, result.Success)
    return appended.value


def _ledger_with_payment(
    *,
    amount: str = "29",
) -> billing.CommercialBillingLedger:
    ledger = _ledger_with_invoice()
    appended = billing.append_verified_payment(ledger, _payment(amount=amount))
    assert isinstance(appended, result.Success)
    return appended.value


def _allocation(
    *,
    suffix: int,
    amount: str,
    invoice_id: billing.CommercialInvoiceId | None = None,
    payment_id: billing.CommercialPaymentId | None = None,
) -> billing.CommercialPaymentAllocation:
    return billing.CommercialPaymentAllocation(
        allocation_id=billing.CommercialPaymentAllocationId(_uuid(suffix)),
        invoice_id=invoice_id or billing.CommercialInvoiceId(_uuid(10)),
        payment_id=payment_id or billing.CommercialPaymentId(_uuid(30)),
        amount=_amount(amount),
        allocated_at=_NOW + timedelta(days=1, seconds=1),
        evidence_ref=billing.CommercialBillingEvidenceReference(_uuid(suffix + 1)),
    )


def test_invoice_starts_due_and_due_is_not_paid() -> None:
    ledger = _ledger_with_invoice()
    invoice = ledger.invoices[0]

    assert ledger.invoice_status(invoice.invoice_id) is billing.CommercialInvoiceStatus.DUE
    assert ledger.outstanding(invoice.invoice_id) == _amount("29")
    assert not hasattr(invoice, "mark_paid")
    assert not hasattr(invoice, "paid")


def test_only_verified_payment_enters_billing_ledger() -> None:
    ledger = _ledger_with_invoice()
    rejected = _payment(
        verification=billing.CommercialPaymentVerification.REJECTED,
    )

    appended = billing.append_verified_payment(ledger, rejected)

    assert isinstance(appended, result.Failure)
    assert "only VERIFIED payment" in str(appended.error)
    assert ledger.payments == ()


def test_partial_and_full_payment_status_derive_from_verified_allocations() -> None:
    ledger = _ledger_with_payment()
    invoice_id = ledger.invoices[0].invoice_id

    partial = billing.allocate_verified_payment(
        ledger,
        _allocation(suffix=40, amount="10"),
    )
    assert isinstance(partial, result.Success)
    assert partial.value.invoice_status(invoice_id) is (
        billing.CommercialInvoiceStatus.PARTIALLY_PAID
    )
    assert partial.value.outstanding(invoice_id) == _amount("19")

    final = billing.allocate_verified_payment(
        partial.value,
        _allocation(suffix=42, amount="19"),
    )
    assert isinstance(final, result.Success)
    assert final.value.invoice_status(invoice_id) is billing.CommercialInvoiceStatus.PAID
    assert final.value.outstanding(invoice_id) == _amount("0")


def test_invoice_cannot_be_overallocated() -> None:
    ledger = _ledger_with_payment(amount="100")

    allocated = billing.allocate_verified_payment(
        ledger,
        _allocation(suffix=50, amount="30"),
    )

    assert isinstance(allocated, result.Failure)
    assert "cannot exceed amount due" in str(allocated.error)


def test_one_verified_payment_cannot_be_overallocated_across_invoices() -> None:
    first = _invoice(suffix=10)
    second = _invoice(suffix=11)
    ledger = billing.CommercialBillingLedger(invoices=(first, second))
    payment_result = billing.append_verified_payment(ledger, _payment(amount="40"))
    assert isinstance(payment_result, result.Success)
    first_allocation = billing.allocate_verified_payment(
        payment_result.value,
        _allocation(suffix=60, amount="20", invoice_id=first.invoice_id),
    )
    assert isinstance(first_allocation, result.Success)

    second_allocation = billing.allocate_verified_payment(
        first_allocation.value,
        _allocation(suffix=62, amount="21", invoice_id=second.invoice_id),
    )

    assert isinstance(second_allocation, result.Failure)
    assert "cannot exceed verified payment amount" in str(second_allocation.error)


def test_invoice_scope_is_derived_from_plan_billing_unit() -> None:
    ea = _ea_plan()
    with pytest.raises(billing.CommercialBillingValidationError):
        billing.CommercialInvoice.from_plan(
            invoice_id=billing.CommercialInvoiceId(_uuid(70)),
            client_id=accounts.ClientId(_uuid(20)),
            account_id=None,
            plan=ea,
            period_started_at=_NOW,
            period_ended_at=_NOW + timedelta(days=30),
            issued_at=_NOW,
            due_at=_NOW + timedelta(days=7),
        )


def test_core_performance_fee_is_20_percent_of_eligible_client_paid_profit() -> None:
    eligible = performance.EligibleClientPaidProfitRecord(
        record_id=performance.ClientPerformanceRecordId(_uuid(80)),
        account_id=accounts.TradingAccountId(_uuid(21)),
        paid_profit_record_id=performance.ClientPerformanceRecordId(_uuid(81)),
        amount=_amount("8000"),
        payout_policy_ref=performance.ClientPayoutPolicyReference(_uuid(82)),
        evaluated_at=_NOW,
        evidence_ref=performance.ClientPerformanceEvidenceReference(_uuid(83)),
    )
    policy = billing.PerformanceFeePolicy(
        policy_id=billing.PerformanceFeePolicyId(_uuid(84)),
        version=billing.PerformanceFeePolicyVersion(1),
    )

    assessment = billing.calculate_performance_fee(policy, eligible)

    assert assessment.eligible_paid_profit == _amount("8000")
    assert assessment.fee_amount == _amount("1600")
    assert assessment.eligible_paid_profit_record_id == eligible.record_id


def test_performance_fee_policy_cannot_silently_change_from_20_percent() -> None:
    with pytest.raises(billing.CommercialBillingValidationError):
        billing.PerformanceFeePolicy(
            policy_id=billing.PerformanceFeePolicyId(_uuid(90)),
            version=billing.PerformanceFeePolicyVersion(2),
            fee_bps=2500,
        )


def test_payment_failure_projects_to_licensing_without_close_authority() -> None:
    standing = billing.CommercialBillingStanding(
        client_id=accounts.ClientId(_uuid(20)),
        account_id=accounts.TradingAccountId(_uuid(21)),
        state=billing.CommercialBillingStandingState.PAYMENT_FAILED,
        evaluated_at=_NOW,
        evidence_ref=billing.CommercialBillingEvidenceReference(_uuid(91)),
    )

    projected = billing.project_license_payment_standing(standing)

    assert projected is licensing.CommercialPaymentStanding.PAYMENT_FAILED
    assert not hasattr(standing, "close_trade")
    assert not hasattr(standing, "liquidate")
    assert not hasattr(standing, "submit_order")


def test_billing_has_no_broker_or_trade_authority() -> None:
    assert not hasattr(billing.CommercialBillingLedger, "submit_order")
    assert not hasattr(billing.VerifiedCommercialPayment, "execute")
    assert not hasattr(billing.CommercialInvoice, "close_position")
    assert not hasattr(billing.PerformanceFeeAssessment, "mark_cash_received")
