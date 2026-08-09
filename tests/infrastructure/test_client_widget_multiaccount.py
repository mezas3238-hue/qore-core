from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

import qore.infrastructure.client_accounts as accounts
import qore.infrastructure.client_multiaccount_read_model as read_model
import qore.infrastructure.client_trial_licensing as licensing
import qore.infrastructure.client_widget_multiaccount as widget
import qore.infrastructure.commercial_billing as billing
import qore.infrastructure.commercial_products as products
import qore.infrastructure.proprietary_accounts as money

_NOW = datetime(2026, 8, 9, 15, 0, tzinfo=UTC)
_USD = money.CurrencyCode("USD")


def _uuid(suffix: int) -> UUID:
    return UUID(f"42000000-0000-0000-0000-{suffix:012d}")


def _widget_plan() -> products.CommercialPlan:
    product = products.CommercialProduct(
        product_id=products.CommercialProductId(_uuid(1)),
        kind=products.CommercialProductKind.CLIENT_WIDGET,
        availability=products.CommercialProductAvailability.CONFIRMED,
    )
    return products.CommercialPlan(
        plan_id=products.CommercialPlanId(_uuid(2)),
        version=products.CommercialPlanVersion(1),
        product=product,
        billing_unit=products.CommercialBillingUnit.CLIENT,
        cadence=products.CommercialBillingCadence.MONTHLY,
        price=money.MoneyAmount(currency=_USD, amount=Decimal("9.99")),
    )


def _ea_plan() -> products.CommercialPlan:
    product = products.CommercialProduct(
        product_id=products.CommercialProductId(_uuid(3)),
        kind=products.CommercialProductKind.CLIENT_EXECUTION_AGENT,
        availability=products.CommercialProductAvailability.CONFIRMED,
    )
    return products.CommercialPlan(
        plan_id=products.CommercialPlanId(_uuid(4)),
        version=products.CommercialPlanVersion(1),
        product=product,
        billing_unit=products.CommercialBillingUnit.ACCOUNT,
        cadence=products.CommercialBillingCadence.MONTHLY,
        price=money.MoneyAmount(currency=_USD, amount=Decimal("29")),
    )


def _account(account_suffix: int) -> read_model.ClientAccountReadSnapshot:
    return read_model.ClientAccountReadSnapshot(
        client_id=accounts.ClientId(_uuid(10)),
        account_id=accounts.TradingAccountId(_uuid(account_suffix)),
        account_state=accounts.TradingAccountLifecycleState.ACTIVE,
        balance=money.MoneyAmount(currency=_USD, amount=Decimal("10000")),
        generated_today=money.MoneyAmount(currency=_USD, amount=Decimal("100")),
        generated_week=money.MoneyAmount(currency=_USD, amount=Decimal("300")),
        service_status=read_model.ClientServiceStatus.ONLINE,
        license_state=licensing.ClientLicenseState.LICENSED,
        billing_state=billing.CommercialBillingStandingState.CURRENT,
        trade_pulses=(),
        captured_at=_NOW - timedelta(seconds=2),
    )


def _read_model() -> read_model.ClientMultiAccountReadModel:
    return read_model.build_client_multiaccount_read_model(
        read_model_id=read_model.ClientReadModelId(_uuid(20)),
        client_id=accounts.ClientId(_uuid(10)),
        today_window=read_model.ClientPerformanceWindow(
            started_at=_NOW - timedelta(hours=15),
            ended_at=_NOW - timedelta(seconds=1),
        ),
        week_window=read_model.ClientPerformanceWindow(
            started_at=_NOW - timedelta(days=6, hours=15),
            ended_at=_NOW - timedelta(seconds=1),
        ),
        accounts=(_account(30), _account(31)),
        generated_at=_NOW - timedelta(seconds=1),
    )


def _standing(
    state: billing.CommercialBillingStandingState,
) -> widget.ClientWidgetCommercialStanding:
    return widget.ClientWidgetCommercialStanding.from_plan(
        client_id=accounts.ClientId(_uuid(10)),
        plan=_widget_plan(),
        billing_state=state,
        evaluated_at=_NOW - timedelta(seconds=1),
        evidence_ref=billing.CommercialBillingEvidenceReference(_uuid(40)),
    )


def test_one_active_widget_presents_n_accounts_from_read_model() -> None:
    model = _read_model()
    view = widget.build_client_widget_view_model(
        widget_id=widget.ClientWidgetId(_uuid(50)),
        standing=_standing(billing.CommercialBillingStandingState.CURRENT),
        read_model=model,
        generated_at=_NOW,
    )

    assert view.access_state is widget.ClientWidgetAccessState.ACTIVE
    assert view.client_id == model.client_id
    assert view.account_count == 2
    assert view.read_model is model
    assert not hasattr(view, "monthly_price")


def test_widget_payment_failure_suspends_immediately_and_hides_account_data() -> None:
    model = _read_model()
    original_accounts = model.accounts
    view = widget.build_client_widget_view_model(
        widget_id=widget.ClientWidgetId(_uuid(51)),
        standing=_standing(
            billing.CommercialBillingStandingState.PAYMENT_FAILED
        ),
        read_model=model,
        generated_at=_NOW,
    )

    assert view.access_state is widget.ClientWidgetAccessState.SUSPENDED
    assert view.read_model is None
    assert view.account_count == 0
    assert model.accounts == original_accounts
    assert all(
        account.license_state is licensing.ClientLicenseState.LICENSED
        for account in model.accounts
    )


def test_unknown_widget_commercial_state_fails_closed() -> None:
    view = widget.build_client_widget_view_model(
        widget_id=widget.ClientWidgetId(_uuid(52)),
        standing=_standing(billing.CommercialBillingStandingState.UNKNOWN),
        read_model=_read_model(),
        generated_at=_NOW,
    )

    assert view.access_state is widget.ClientWidgetAccessState.SUSPENDED
    assert view.read_model is None


def test_widget_standing_rejects_ea_account_scoped_plan() -> None:
    with pytest.raises(widget.ClientWidgetValidationError):
        widget.ClientWidgetCommercialStanding.from_plan(
            client_id=accounts.ClientId(_uuid(10)),
            plan=_ea_plan(),
            billing_state=billing.CommercialBillingStandingState.CURRENT,
            evaluated_at=_NOW,
            evidence_ref=billing.CommercialBillingEvidenceReference(_uuid(41)),
        )


def test_widget_rejects_read_model_for_another_client() -> None:
    model = _read_model()
    foreign_standing = widget.ClientWidgetCommercialStanding.from_plan(
        client_id=accounts.ClientId(_uuid(99)),
        plan=_widget_plan(),
        billing_state=billing.CommercialBillingStandingState.CURRENT,
        evaluated_at=_NOW - timedelta(seconds=1),
        evidence_ref=billing.CommercialBillingEvidenceReference(_uuid(42)),
    )

    with pytest.raises(widget.ClientWidgetValidationError):
        widget.build_client_widget_view_model(
            widget_id=widget.ClientWidgetId(_uuid(53)),
            standing=foreign_standing,
            read_model=model,
            generated_at=_NOW,
        )


def test_widget_does_not_propagate_suspension_to_execution_or_risk() -> None:
    model = _read_model()
    view = widget.build_client_widget_view_model(
        widget_id=widget.ClientWidgetId(_uuid(54)),
        standing=_standing(
            billing.CommercialBillingStandingState.PAYMENT_FAILED
        ),
        read_model=model,
        generated_at=_NOW,
    )

    assert view.access_state is widget.ClientWidgetAccessState.SUSPENDED
    assert not hasattr(view, "suspend_ea")
    assert not hasattr(view, "set_risk")
    assert not hasattr(view, "close_position")
    assert not hasattr(view, "stop_hosting")


def test_widget_has_no_broker_or_trading_authority() -> None:
    assert not hasattr(widget.ClientWidgetViewModel, "submit_order")
    assert not hasattr(widget.ClientWidgetViewModel, "broker")
    assert not hasattr(widget.ClientWidgetCommercialStanding, "mark_paid")
    assert not hasattr(widget.ClientWidgetCommercialStanding, "charge")
