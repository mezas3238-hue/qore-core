from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest

import qore.infrastructure.commercial_products as commercial
import qore.infrastructure.proprietary_accounts as money
import qore.kernel.result as result

_USD = money.CurrencyCode("USD")


def _uuid(suffix: int) -> UUID:
    return UUID(f"38000000-0000-0000-0000-{suffix:012d}")


def _product(
    kind: commercial.CommercialProductKind,
    suffix: int,
    *,
    availability: commercial.CommercialProductAvailability = (
        commercial.CommercialProductAvailability.CONFIRMED
    ),
) -> commercial.CommercialProduct:
    return commercial.CommercialProduct(
        product_id=commercial.CommercialProductId(_uuid(suffix)),
        kind=kind,
        availability=availability,
    )


def _plan(
    product: commercial.CommercialProduct,
    suffix: int,
    *,
    unit: commercial.CommercialBillingUnit,
    price: str | None,
) -> commercial.CommercialPlan:
    return commercial.CommercialPlan(
        plan_id=commercial.CommercialPlanId(_uuid(suffix)),
        version=commercial.CommercialPlanVersion(1),
        product=product,
        billing_unit=unit,
        cadence=commercial.CommercialBillingCadence.MONTHLY,
        price=(
            money.MoneyAmount(currency=_USD, amount=Decimal(price))
            if price is not None
            else None
        ),
    )


def test_ea_plan_is_confirmed_at_29_usd_per_account_month() -> None:
    product = _product(commercial.CommercialProductKind.CLIENT_EXECUTION_AGENT, 1)
    plan = _plan(
        product,
        11,
        unit=commercial.CommercialBillingUnit.ACCOUNT,
        price="29.00",
    )

    assert plan.price == money.MoneyAmount(currency=_USD, amount=Decimal("29"))
    assert plan.billing_unit is commercial.CommercialBillingUnit.ACCOUNT
    assert plan.cadence is commercial.CommercialBillingCadence.MONTHLY


def test_widget_plan_is_9_99_usd_per_client_not_per_account() -> None:
    product = _product(commercial.CommercialProductKind.CLIENT_WIDGET, 2)
    plan = _plan(
        product,
        12,
        unit=commercial.CommercialBillingUnit.CLIENT,
        price="9.99",
    )

    assert plan.price == money.MoneyAmount(currency=_USD, amount=Decimal("9.99"))
    assert plan.billing_unit is commercial.CommercialBillingUnit.CLIENT


def test_ea_and_widget_reject_wrong_billing_scope() -> None:
    ea = _product(commercial.CommercialProductKind.CLIENT_EXECUTION_AGENT, 3)
    widget = _product(commercial.CommercialProductKind.CLIENT_WIDGET, 4)

    with pytest.raises(commercial.CommercialProductValidationError):
        _plan(
            ea,
            13,
            unit=commercial.CommercialBillingUnit.CLIENT,
            price="29",
        )
    with pytest.raises(commercial.CommercialProductValidationError):
        _plan(
            widget,
            14,
            unit=commercial.CommercialBillingUnit.ACCOUNT,
            price="9.99",
        )


def test_hosting_is_independent_and_not_implicitly_included_in_ea() -> None:
    ea = _product(commercial.CommercialProductKind.CLIENT_EXECUTION_AGENT, 5)
    hosting = _product(
        commercial.CommercialProductKind.MANAGED_HOSTING,
        6,
        availability=commercial.CommercialProductAvailability.VALIDATION_REQUIRED,
    )
    ea_plan = _plan(
        ea,
        15,
        unit=commercial.CommercialBillingUnit.ACCOUNT,
        price="29",
    )
    hosting_plan = _plan(
        hosting,
        16,
        unit=commercial.CommercialBillingUnit.SERVICE,
        price=None,
    )

    assert ea_plan.product.product_id != hosting_plan.product.product_id
    assert hosting_plan.price is None
    assert not hasattr(ea_plan, "hosting_included")


def test_managed_futures_remains_validation_required_without_149_price() -> None:
    futures = _product(
        commercial.CommercialProductKind.MANAGED_FUTURES,
        7,
        availability=commercial.CommercialProductAvailability.VALIDATION_REQUIRED,
    )
    plan = _plan(
        futures,
        17,
        unit=commercial.CommercialBillingUnit.ACCOUNT,
        price=None,
    )

    assert plan.product.availability is (
        commercial.CommercialProductAvailability.VALIDATION_REQUIRED
    )
    assert plan.price is None

    with pytest.raises(commercial.CommercialProductValidationError):
        _plan(
            futures,
            18,
            unit=commercial.CommercialBillingUnit.ACCOUNT,
            price="149",
        )


def test_catalog_keeps_all_products_independent_and_versioned() -> None:
    ea = _product(commercial.CommercialProductKind.CLIENT_EXECUTION_AGENT, 20)
    widget = _product(commercial.CommercialProductKind.CLIENT_WIDGET, 21)
    core = _product(
        commercial.CommercialProductKind.CORE_SERVICES,
        22,
        availability=commercial.CommercialProductAvailability.VALIDATION_REQUIRED,
    )
    hosting = _product(
        commercial.CommercialProductKind.MANAGED_HOSTING,
        23,
        availability=commercial.CommercialProductAvailability.VALIDATION_REQUIRED,
    )
    futures = _product(
        commercial.CommercialProductKind.MANAGED_FUTURES,
        24,
        availability=commercial.CommercialProductAvailability.VALIDATION_REQUIRED,
    )
    plans = (
        _plan(ea, 30, unit=commercial.CommercialBillingUnit.ACCOUNT, price="29"),
        _plan(widget, 31, unit=commercial.CommercialBillingUnit.CLIENT, price="9.99"),
        _plan(core, 32, unit=commercial.CommercialBillingUnit.SERVICE, price=None),
        _plan(hosting, 33, unit=commercial.CommercialBillingUnit.SERVICE, price=None),
        _plan(futures, 34, unit=commercial.CommercialBillingUnit.ACCOUNT, price=None),
    )
    catalog = commercial.CommercialCatalog(
        products=(ea, widget, core, hosting, futures),
        plans=plans,
    )

    assert len(catalog.products) == 5
    resolved = catalog.plan_for(
        commercial.CommercialProductKind.CLIENT_EXECUTION_AGENT,
        commercial.CommercialPlanVersion(1),
    )
    assert isinstance(resolved, result.Success)
    assert resolved.value.price == money.MoneyAmount(
        currency=_USD,
        amount=Decimal("29"),
    )


def test_products_and_plans_have_no_payment_or_trading_authority() -> None:
    assert not hasattr(commercial.CommercialPlan, "charge")
    assert not hasattr(commercial.CommercialPlan, "mark_paid")
    assert not hasattr(commercial.CommercialProduct, "execute")
    assert not hasattr(commercial.CommercialCatalog, "submit_order")
