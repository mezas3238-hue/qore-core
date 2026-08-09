from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.client_decision_security as security
import qore.infrastructure.client_execution_agent as agent
import qore.infrastructure.client_multiaccount_read_model as read_model
import qore.infrastructure.client_performance_ledger as performance
import qore.infrastructure.client_position_lifecycle as lifecycle
import qore.infrastructure.client_trial_licensing as licensing
import qore.infrastructure.client_widget_multiaccount as widget
import qore.infrastructure.commercial_billing as billing
import qore.infrastructure.commercial_products as products
import qore.infrastructure.corporate_profit_vault as vault
import qore.infrastructure.proprietary_accounts as money
import qore.kernel.result as result

_NOW = datetime(2026, 8, 9, 16, 30, tzinfo=UTC)
_USD = money.CurrencyCode("USD")

_MISSION07_DELIVERIES = (
    "QORE-MISSION07-DOCS-001",
    "QORE-CLIENT-ACCOUNT-FOUNDATION-001",
    "QORE-ACCOUNT-PROP-POLICY-001",
    "QORE-CLIENT-EXECUTION-AGENT-CONTRACTS-001",
    "QORE-CLIENT-DECISION-SECURITY-001",
    "QORE-CLIENT-POSITION-LIFECYCLE-001",
    "QORE-CLIENT-PERFORMANCE-LEDGER-001",
    "QORE-CLIENT-TRIAL-LICENSING-001",
    "QORE-COMMERCIAL-PRODUCTS-PLANS-001",
    "QORE-COMMERCIAL-BILLING-PAYMENTS-001",
    "QORE-CORPORATE-PROFIT-VAULT-EXPANSION-001",
    "QORE-CLIENT-MULTIACCOUNT-READ-MODEL-001",
    "QORE-CLIENT-WIDGET-MULTIACCOUNT-001",
    "QORE-MISSION07-E2E-OFFLINE-001",
    "QORE-MISSION07-CLOSURE-001",
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"44000000-0000-0000-0000-{suffix:012d}")


def _amount(value: str) -> money.MoneyAmount:
    return money.MoneyAmount(currency=_USD, amount=Decimal(value))


def _product(
    *,
    suffix: int,
    kind: products.CommercialProductKind,
    availability: products.CommercialProductAvailability,
) -> products.CommercialProduct:
    return products.CommercialProduct(
        product_id=products.CommercialProductId(_uuid(suffix)),
        kind=kind,
        availability=availability,
    )


def _confirmed_plan(
    *,
    plan_suffix: int,
    product: products.CommercialProduct,
    unit: products.CommercialBillingUnit,
    amount: str,
) -> products.CommercialPlan:
    return products.CommercialPlan(
        plan_id=products.CommercialPlanId(_uuid(plan_suffix)),
        version=products.CommercialPlanVersion(1),
        product=product,
        billing_unit=unit,
        cadence=products.CommercialBillingCadence.MONTHLY,
        price=_amount(amount),
    )


def test_mission07_security_and_execution_authority_remain_fail_closed() -> None:
    envelope_fields = {field.name for field in fields(security.ClientDecisionEnvelope)}
    assert envelope_fields.isdisjoint(
        {"instrument", "side", "quantity", "stop_loss", "take_profit", "lot_size"}
    )

    assert not hasattr(security.ClientDecisionReplayClaimPort, "release")
    assert not hasattr(security.ClientDecisionReplayClaimPort, "retry")
    assert not hasattr(agent.ClientExecutionPlan, "submit_order")
    assert not hasattr(agent.ClientExecutionPlan, "broker")
    assert not hasattr(lifecycle.ClientPositionLifecycle, "submit_order")
    assert not hasattr(lifecycle.ClientPositionLifecycle, "redispatch")
    assert not hasattr(lifecycle.ClientPositionAction, "execute")


def test_mission07_client_performance_and_corporate_vault_remain_separate() -> None:
    assert not hasattr(performance.ClientPerformanceLedger, "corporate_revenue")
    assert not hasattr(performance.ClientPerformanceLedger, "mark_invoice_paid")
    assert not hasattr(performance.ClientPerformanceLedger, "charge")
    assert not hasattr(vault.CorporateProfitVault, "append_realized_performance")
    assert not hasattr(vault.CorporateProfitVault, "submit_order")
    assert not hasattr(vault.CorporateRevenueAttribution, "mark_paid")

    eligible = performance.EligibleClientPaidProfitRecord(
        record_id=performance.ClientPerformanceRecordId(_uuid(10)),
        account_id=accounts.TradingAccountId(_uuid(11)),
        paid_profit_record_id=performance.ClientPerformanceRecordId(_uuid(12)),
        amount=_amount("8000"),
        payout_policy_ref=performance.ClientPayoutPolicyReference(_uuid(13)),
        evaluated_at=_NOW,
        evidence_ref=performance.ClientPerformanceEvidenceReference(_uuid(14)),
    )
    policy = billing.PerformanceFeePolicy(
        policy_id=billing.PerformanceFeePolicyId(_uuid(15)),
        version=billing.PerformanceFeePolicyVersion(1),
    )
    assessment = billing.calculate_performance_fee(policy, eligible)
    assert assessment.eligible_paid_profit == _amount("8000")
    assert assessment.fee_amount == _amount("1600")
    assert assessment.eligible_paid_profit_record_id == eligible.record_id


def test_mission07_confirmed_pricing_and_future_validation_state_are_preserved() -> None:
    ea_product = _product(
        suffix=20,
        kind=products.CommercialProductKind.CLIENT_EXECUTION_AGENT,
        availability=products.CommercialProductAvailability.CONFIRMED,
    )
    widget_product = _product(
        suffix=21,
        kind=products.CommercialProductKind.CLIENT_WIDGET,
        availability=products.CommercialProductAvailability.CONFIRMED,
    )
    hosting_product = _product(
        suffix=22,
        kind=products.CommercialProductKind.MANAGED_HOSTING,
        availability=products.CommercialProductAvailability.VALIDATION_REQUIRED,
    )
    futures_product = _product(
        suffix=23,
        kind=products.CommercialProductKind.MANAGED_FUTURES,
        availability=products.CommercialProductAvailability.VALIDATION_REQUIRED,
    )
    ea_plan = _confirmed_plan(
        plan_suffix=30,
        product=ea_product,
        unit=products.CommercialBillingUnit.ACCOUNT,
        amount="29",
    )
    widget_plan = _confirmed_plan(
        plan_suffix=31,
        product=widget_product,
        unit=products.CommercialBillingUnit.CLIENT,
        amount="9.99",
    )
    hosting_plan = products.CommercialPlan(
        plan_id=products.CommercialPlanId(_uuid(32)),
        version=products.CommercialPlanVersion(1),
        product=hosting_product,
        billing_unit=products.CommercialBillingUnit.SERVICE,
        cadence=products.CommercialBillingCadence.MONTHLY,
        price=None,
    )
    futures_plan = products.CommercialPlan(
        plan_id=products.CommercialPlanId(_uuid(33)),
        version=products.CommercialPlanVersion(1),
        product=futures_product,
        billing_unit=products.CommercialBillingUnit.ACCOUNT,
        cadence=products.CommercialBillingCadence.MONTHLY,
        price=None,
    )

    assert ea_plan.price == _amount("29")
    assert ea_plan.billing_unit is products.CommercialBillingUnit.ACCOUNT
    assert widget_plan.price == _amount("9.99")
    assert widget_plan.billing_unit is products.CommercialBillingUnit.CLIENT
    assert hosting_plan.price is None
    assert futures_plan.price is None
    assert futures_plan.product.availability is (
        products.CommercialProductAvailability.VALIDATION_REQUIRED
    )


def test_mission07_due_is_not_paid_and_billing_has_no_trade_authority() -> None:
    ea_product = _product(
        suffix=40,
        kind=products.CommercialProductKind.CLIENT_EXECUTION_AGENT,
        availability=products.CommercialProductAvailability.CONFIRMED,
    )
    ea_plan = _confirmed_plan(
        plan_suffix=41,
        product=ea_product,
        unit=products.CommercialBillingUnit.ACCOUNT,
        amount="29",
    )
    invoice = billing.CommercialInvoice.from_plan(
        invoice_id=billing.CommercialInvoiceId(_uuid(42)),
        client_id=accounts.ClientId(_uuid(43)),
        account_id=accounts.TradingAccountId(_uuid(44)),
        plan=ea_plan,
        period_started_at=_NOW,
        period_ended_at=_NOW + timedelta(days=30),
        issued_at=_NOW,
        due_at=_NOW + timedelta(days=7),
    )
    appended = billing.append_invoice(billing.CommercialBillingLedger(), invoice)
    assert isinstance(appended, result.Success)
    assert appended.value.invoice_status(invoice.invoice_id) is (
        billing.CommercialInvoiceStatus.DUE
    )
    assert appended.value.outstanding(invoice.invoice_id) == _amount("29")
    assert not hasattr(invoice, "mark_paid")
    assert not hasattr(billing.CommercialBillingLedger, "close_position")
    assert not hasattr(billing.CommercialBillingLedger, "submit_order")


def test_mission07_trial_payment_failure_blocks_entries_without_forced_close() -> None:
    started_at = _NOW - timedelta(days=1)
    snapshot = licensing.ClientAgentLicenseSnapshot(
        account_id=accounts.TradingAccountId(_uuid(50)),
        entitlement_ref=accounts.ProductEntitlementReference(_uuid(51)),
        trial_state=licensing.ClientTrialState.ACTIVE,
        license_state=licensing.ClientLicenseState.TRIAL_ACTIVE,
        trial_started_at=started_at,
        trial_expires_at=started_at + timedelta(days=14),
        first_live_evidence_ref=licensing.TrialEvidenceReference(_uuid(52)),
        updated_at=_NOW - timedelta(seconds=1),
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(53)),
    )
    evaluated = licensing.evaluate_client_license(
        snapshot,
        payment_standing=licensing.CommercialPaymentStanding.PAYMENT_FAILED,
        open_positions=1,
        evaluated_at=_NOW,
        evidence_ref=licensing.LicensingEvidenceReference(_uuid(54)),
    )
    assert isinstance(evaluated, result.Success)
    assert evaluated.value.license_state is (
        licensing.ClientLicenseState.SUSPEND_PENDING_FLAT
    )
    entitlement = licensing.project_agent_entitlement(
        evaluated.value,
        evaluated_at=_NOW,
    )
    assert entitlement.state is agent.ClientAgentEntitlementState.BLOCKED
    assert not hasattr(evaluated.value, "close_position")
    assert not hasattr(evaluated.value, "liquidate")


def test_mission07_read_model_and_widget_remain_presentation_only() -> None:
    assert not hasattr(read_model.ClientMultiAccountReadModel, "total_balance")
    assert not hasattr(read_model.ClientMultiAccountReadModel, "aggregate_risk")
    assert not hasattr(read_model.ClientMultiAccountReadModel, "submit_order")
    assert not hasattr(read_model.ClientMultiAccountReadModel, "set_risk")
    assert not hasattr(widget.ClientWidgetViewModel, "submit_order")
    assert not hasattr(widget.ClientWidgetViewModel, "suspend_ea")
    assert not hasattr(widget.ClientWidgetViewModel, "set_risk")
    assert not hasattr(widget.ClientWidgetCommercialStanding, "mark_paid")


def test_mission07_closure_documents_record_complete_scope_and_external_blocks() -> None:
    opening = Path(
        "docs/missions/MISSION-07-CLIENT-EXECUTION-COMMERCIAL-PLATFORM.md"
    ).read_text(encoding="utf-8")
    closure = Path("docs/missions/MISSION-07-CLOSURE.md").read_text(encoding="utf-8")
    e2e = Path("tests/infrastructure/test_mission07_e2e_offline.py")

    for delivery in _MISSION07_DELIVERIES:
        assert delivery in opening or delivery in closure
    assert e2e.is_file()
    assert "#146" in closure
    assert "MISSION-06 = CLOSED" in closure
    assert "Production = CLOSED" in closure
    assert "Managed Hosting" in closure
    assert "Native Broker Execution" in closure
    assert "Regional Futures Execution" in closure
    assert "Commercial Futures Validation" in closure
