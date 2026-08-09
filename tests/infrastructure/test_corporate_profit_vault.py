from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.client_performance_ledger as performance
import qore.infrastructure.commercial_billing as billing
import qore.infrastructure.commercial_products as products
import qore.infrastructure.corporate_profit_vault as vault
import qore.infrastructure.proprietary_accounts as money
import qore.kernel.result as result

_NOW = datetime(2026, 8, 9, 13, 0, tzinfo=UTC)
_USD = money.CurrencyCode("USD")


def _uuid(suffix: int) -> UUID:
    return UUID(f"40000000-0000-0000-0000-{suffix:012d}")


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


def _invoice() -> billing.CommercialInvoice:
    return billing.CommercialInvoice.from_plan(
        invoice_id=billing.CommercialInvoiceId(_uuid(10)),
        client_id=accounts.ClientId(_uuid(20)),
        account_id=accounts.TradingAccountId(_uuid(21)),
        plan=_ea_plan(),
        period_started_at=_NOW,
        period_ended_at=_NOW + timedelta(days=30),
        issued_at=_NOW,
        due_at=_NOW + timedelta(days=7),
    )


def _billing_with_due_invoice() -> billing.CommercialBillingLedger:
    appended = billing.append_invoice(billing.CommercialBillingLedger(), _invoice())
    assert isinstance(appended, result.Success)
    return appended.value


def _billing_with_paid_allocation() -> billing.CommercialBillingLedger:
    ledger = _billing_with_due_invoice()
    payment = billing.VerifiedCommercialPayment(
        payment_id=billing.CommercialPaymentId(_uuid(30)),
        client_id=accounts.ClientId(_uuid(20)),
        amount=_amount("29"),
        paid_at=_NOW + timedelta(days=1),
        verification=billing.CommercialPaymentVerification.VERIFIED,
        evidence_ref=billing.CommercialPaymentEvidenceReference(_uuid(31)),
    )
    with_payment = billing.append_verified_payment(ledger, payment)
    assert isinstance(with_payment, result.Success)
    allocation = billing.CommercialPaymentAllocation(
        allocation_id=billing.CommercialPaymentAllocationId(_uuid(32)),
        invoice_id=ledger.invoices[0].invoice_id,
        payment_id=payment.payment_id,
        amount=_amount("29"),
        allocated_at=_NOW + timedelta(days=1, seconds=1),
        evidence_ref=billing.CommercialBillingEvidenceReference(_uuid(33)),
    )
    allocated = billing.allocate_verified_payment(with_payment.value, allocation)
    assert isinstance(allocated, result.Success)
    return allocated.value


def test_due_invoice_creates_revenue_and_receivable_but_not_cash() -> None:
    ledger = _billing_with_due_invoice()
    invoice = ledger.invoices[0]
    revenue = vault.attribute_invoice_revenue(
        invoice,
        record_id=vault.CorporateVaultRecordId(_uuid(100)),
        attributed_at=_NOW,
    )
    receivable = vault.snapshot_accounts_receivable(
        ledger,
        invoice.invoice_id,
        record_id=vault.CorporateVaultRecordId(_uuid(101)),
        recorded_at=_NOW,
    )
    corporate = vault.CorporateProfitVault(
        revenue_attributions=(revenue,),
        receivables=(receivable,),
    )

    assert revenue.source is vault.CorporateRevenueSource.EA_SUBSCRIPTION
    assert revenue.amount == _amount("29")
    assert receivable.state is vault.CorporateReceivableState.OPEN
    assert receivable.outstanding == _amount("29")
    assert corporate.cash_received == ()


def test_cash_received_requires_verified_payment_allocation_evidence() -> None:
    ledger = _billing_with_paid_allocation()
    allocation = ledger.allocations[0]
    payment = ledger.payments[0]

    cash = vault.cash_received_from_allocation(
        ledger,
        allocation.allocation_id,
        record_id=vault.CorporateVaultRecordId(_uuid(110)),
        recorded_at=_NOW + timedelta(days=1, seconds=2),
    )

    assert cash.amount == allocation.amount
    assert cash.payment_id == payment.payment_id
    assert cash.payment_evidence_ref == payment.evidence_ref
    assert cash.paid_at == payment.paid_at
    assert cash.source is vault.CorporateRevenueSource.EA_SUBSCRIPTION


def test_missing_payment_allocation_cannot_be_inferred_as_cash() -> None:
    ledger = _billing_with_due_invoice()

    with pytest.raises(vault.CorporateProfitVaultValidationError):
        vault.cash_received_from_allocation(
            ledger,
            billing.CommercialPaymentAllocationId(_uuid(999)),
            record_id=vault.CorporateVaultRecordId(_uuid(111)),
            recorded_at=_NOW + timedelta(days=1),
        )


def test_same_payment_allocation_cannot_create_cash_twice() -> None:
    ledger = _billing_with_paid_allocation()
    allocation = ledger.allocations[0]
    first = vault.cash_received_from_allocation(
        ledger,
        allocation.allocation_id,
        record_id=vault.CorporateVaultRecordId(_uuid(120)),
        recorded_at=_NOW + timedelta(days=1, seconds=2),
    )
    second = vault.cash_received_from_allocation(
        ledger,
        allocation.allocation_id,
        record_id=vault.CorporateVaultRecordId(_uuid(121)),
        recorded_at=_NOW + timedelta(days=1, seconds=3),
    )
    corporate = vault.CorporateProfitVault(cash_received=(first,))

    appended = vault.append_cash_received(corporate, second)

    assert isinstance(appended, result.Failure)
    assert "only once" in str(appended.error)


def test_receivable_becomes_settled_only_after_billing_payment_allocation() -> None:
    ledger = _billing_with_paid_allocation()
    invoice = ledger.invoices[0]

    receivable = vault.snapshot_accounts_receivable(
        ledger,
        invoice.invoice_id,
        record_id=vault.CorporateVaultRecordId(_uuid(130)),
        recorded_at=_NOW + timedelta(days=1, seconds=2),
    )

    assert receivable.state is vault.CorporateReceivableState.SETTLED
    assert receivable.outstanding == _amount("0")


def test_performance_fee_revenue_uses_billing_assessment_lineage_not_gross_profit() -> None:
    eligible = performance.EligibleClientPaidProfitRecord(
        record_id=performance.ClientPerformanceRecordId(_uuid(140)),
        account_id=accounts.TradingAccountId(_uuid(21)),
        paid_profit_record_id=performance.ClientPerformanceRecordId(_uuid(141)),
        amount=_amount("8000"),
        payout_policy_ref=performance.ClientPayoutPolicyReference(_uuid(142)),
        evaluated_at=_NOW,
        evidence_ref=performance.ClientPerformanceEvidenceReference(_uuid(143)),
    )
    policy = billing.PerformanceFeePolicy(
        policy_id=billing.PerformanceFeePolicyId(_uuid(144)),
        version=billing.PerformanceFeePolicyVersion(1),
    )
    assessment = billing.calculate_performance_fee(policy, eligible)

    revenue = vault.attribute_performance_fee_revenue(
        assessment,
        client_id=accounts.ClientId(_uuid(20)),
        record_id=vault.CorporateVaultRecordId(_uuid(145)),
        period_started_at=_NOW,
        period_ended_at=_NOW + timedelta(days=30),
        attributed_at=_NOW + timedelta(days=1),
    )

    assert revenue.source is vault.CorporateRevenueSource.CORE_PERFORMANCE_FEE
    assert revenue.amount == _amount("1600")
    assert revenue.invoice_id is None
    assert revenue.performance_fee_policy_id == policy.policy_id
    assert revenue.eligible_paid_profit_record_id == eligible.record_id


def test_vault_does_not_accept_client_performance_as_cash_or_trading_authority() -> None:
    assert not hasattr(vault.CorporateProfitVault, "append_realized_performance")
    assert not hasattr(vault.CorporateProfitVault, "submit_order")
    assert not hasattr(vault.CorporateProfitVault, "close_position")
    assert not hasattr(vault.CorporateRevenueAttribution, "mark_paid")
    assert not hasattr(vault.CorporateCashReceived, "execute")
