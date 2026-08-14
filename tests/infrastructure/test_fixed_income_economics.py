from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure import fixed_income_economics as fie
from qore.infrastructure import universal_instrument_identity as uii

_ISSUE = date(2026, 1, 1)
_MID = date(2026, 7, 1)
_MATURITY = date(2031, 1, 1)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _identity(value: int) -> uii.EconomicIdentityId:
    return uii.EconomicIdentityId(_uuid(value))


def _evidence(value: int) -> fie.FixedIncomeEvidenceRef:
    return fie.FixedIncomeEvidenceRef(_uuid(10_000 + value))


def _tenor(
    value: int = 6,
    unit: fie.FinancialTenorUnit = fie.FinancialTenorUnit.MONTH,
) -> fie.FinancialTenor:
    return fie.FinancialTenor(value=value, unit=unit)


def _day_count() -> fie.DayCountConventionCode:
    return fie.DayCountConventionCode("actual-365-fixed")


def _settlement() -> fie.SettlementConvention:
    return fie.SettlementConvention(
        business_day_lag=2,
        calendar_ref=fie.BusinessCalendarRef("target2"),
        business_day_convention=fie.BusinessDayConventionCode("following"),
    )


def _yield_convention() -> fie.YieldConvention:
    return fie.YieldConvention(
        yield_code=fie.FixedIncomeYieldCode("yield-to-maturity"),
        day_count=_day_count(),
        compounding=fie.CompoundingConventionCode("periodic"),
        compounding_tenor=_tenor(),
    )


def _fixed_coupon() -> fie.FixedCouponTerms:
    return fie.FixedCouponTerms(
        rate=fie.CouponRate(Decimal("0.05")),
        day_count=_day_count(),
        payment_tenor=_tenor(),
    )


def _terms(
    *,
    instrument: uii.EconomicIdentityId | None = None,
    coupon: fie.FixedIncomeCouponTerms | None = None,
    maturity: date | None = _MATURITY,
) -> fie.FixedIncomeInstrumentTerms:
    return fie.FixedIncomeInstrumentTerms(
        terms_id=fie.FixedIncomeTermsId(_uuid(100)),
        instrument_identity_id=instrument or _identity(1),
        denomination_currency_identity_id=_identity(2),
        face_amount=fie.FaceAmount(Decimal("1000")),
        issue_date=_ISSUE,
        maturity_date=maturity,
        coupon=coupon or _fixed_coupon(),
        settlement=_settlement(),
        yield_convention=_yield_convention(),
        evidence_ref=_evidence(1),
        redemption_amount=(
            fie.FixedIncomeCashAmount(Decimal("1000")) if maturity is not None else None
        ),
    )


def _accrual(
    *,
    start: date = _ISSUE,
    end: date = _MID,
    payment: date = _MID,
) -> fie.AccrualPeriod:
    return fie.AccrualPeriod(
        start_date=start,
        end_date=end,
        payment_date=payment,
        day_count=_day_count(),
    )


def _cash_flow(
    value: int,
    *,
    instrument: uii.EconomicIdentityId | None = None,
    kind: fie.FixedIncomeCashFlowKind = fie.FixedIncomeCashFlowKind.COUPON,
    payment: date = _MID,
) -> fie.FixedIncomeCashFlow:
    is_coupon = kind is fie.FixedIncomeCashFlowKind.COUPON
    return fie.FixedIncomeCashFlow(
        cash_flow_id=fie.FixedIncomeCashFlowId(_uuid(200 + value)),
        instrument_identity_id=instrument or _identity(1),
        kind=kind,
        direction=fie.FixedIncomeCashFlowDirection.RECEIVABLE,
        amount=fie.FixedIncomeCashAmount(Decimal("25") if is_coupon else Decimal("1000")),
        currency_identity_id=_identity(2),
        payment_date=payment,
        evidence_ref=_evidence(200 + value),
        accrual_period=_accrual(payment=payment) if is_coupon else None,
    )


def test_profile_binds_canonical_identity_terms_and_cash_flows() -> None:
    terms = _terms()
    coupon = _cash_flow(1)
    principal = _cash_flow(
        2,
        kind=fie.FixedIncomeCashFlowKind.PRINCIPAL,
        payment=_MATURITY,
    )
    schedule = fie.FixedIncomeCashFlowSchedule(
        instrument_identity_id=terms.instrument_identity_id,
        cash_flows=(principal, coupon),
    )
    profile = fie.FixedIncomeEconomicProfile(terms=terms, cash_flow_schedule=schedule)

    assert profile.terms.instrument_identity_id == _identity(1)
    assert profile.terms.denomination_currency_identity_id == _identity(2)
    assert profile.cash_flow_schedule is not None
    assert profile.cash_flow_schedule.cash_flows == (coupon, principal)
    assert profile.logical_values()[1] == schedule.logical_values()


def test_rate_yield_and_spread_are_distinct_with_canonical_decimal() -> None:
    magnitude = Decimal("0.0500")
    rate = fie.CouponRate(magnitude)
    bond_yield = fie.FixedIncomeYield(magnitude)
    spread = fie.FixedIncomeSpread(magnitude)

    assert rate != bond_yield
    assert bond_yield != spread
    assert rate != spread
    assert rate.logical_values() == fie.CouponRate(Decimal("0.05")).logical_values()
    assert bond_yield.logical_values() == ("0.05",)
    assert spread.logical_values() == ("0.05",)


def test_clean_and_dirty_price_remain_distinct_at_equal_magnitude() -> None:
    basis = fie.FixedIncomePriceBasisCode("percent-of-par")
    clean = fie.FixedIncomePrice(
        value=Decimal("99.2500"),
        kind=fie.FixedIncomePriceKind.CLEAN,
        basis=basis,
    )
    dirty = replace(clean, kind=fie.FixedIncomePriceKind.DIRTY)

    assert clean != dirty
    assert clean.logical_values()[0] == "99.25"
    assert clean.logical_values()[1] == "clean"
    assert dirty.logical_values()[1] == "dirty"


@pytest.mark.parametrize(
    "value",
    [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")],
)
def test_numeric_contracts_reject_non_finite_decimals(value: Decimal) -> None:
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="finite Decimal"):
        fie.CouponRate(value)
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="finite Decimal"):
        fie.FixedIncomeYield(value)
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="finite Decimal"):
        fie.FixedIncomeSpread(value)
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="finite Decimal"):
        fie.FixedIncomePrice(
            value=value,
            kind=fie.FixedIncomePriceKind.CLEAN,
            basis=fie.FixedIncomePriceBasisCode("percent-of-par"),
        )


def test_face_and_cash_amount_are_positive_and_not_generic_quantity() -> None:
    assert fie.FaceAmount(Decimal("1000")).logical_values() == ("1000",)
    assert fie.FixedIncomeCashAmount(Decimal("25.00")).logical_values() == ("25",)
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="positive"):
        fie.FaceAmount(Decimal("0"))
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="positive"):
        fie.FixedIncomeCashAmount(Decimal("-1"))


def test_financial_tenor_is_structural_and_strictly_typed() -> None:
    tenor = fie.FinancialTenor(3, fie.FinancialTenorUnit.MONTH)
    assert tenor.logical_values() == (3, "month")
    assert not hasattr(tenor, "seconds")
    assert not hasattr(tenor, "fixed_seconds")

    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="positive int"):
        fie.FinancialTenor(cast(int, True), fie.FinancialTenorUnit.MONTH)
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="positive int"):
        fie.FinancialTenor(0, fie.FinancialTenorUnit.MONTH)
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="FinancialTenorUnit"):
        fie.FinancialTenor(3, cast(Any, "month"))


def test_day_count_settlement_and_codes_fail_closed() -> None:
    assert fie.DayCountConventionCode("30e-360").logical_values() == ("30e-360",)
    assert _settlement().logical_values()[0] == 2

    with pytest.raises(
        fie.FixedIncomeEconomicsValidationError,
        match="canonical lowercase",
    ):
        fie.DayCountConventionCode("ACT/365")
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="non-negative int"):
        fie.SettlementConvention(
            business_day_lag=cast(int, True),
            calendar_ref=fie.BusinessCalendarRef("target2"),
            business_day_convention=fie.BusinessDayConventionCode("following"),
        )
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="non-negative int"):
        replace(_settlement(), business_day_lag=-1)
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="BusinessCalendarRef"):
        replace(_settlement(), calendar_ref=cast(Any, "target2"))


def test_accrual_chronology_and_runtime_date_types_fail_closed() -> None:
    accrual = _accrual()
    assert accrual.logical_values()[:3] == (
        "2026-01-01",
        "2026-07-01",
        "2026-07-01",
    )

    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="after start_date"):
        _accrual(end=_ISSUE)
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="must not predate"):
        _accrual(payment=date(2026, 6, 30))
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="must be date"):
        replace(accrual, start_date=cast(Any, datetime(2026, 1, 1)))


def test_coupon_families_are_explicit_and_floating_requires_reference() -> None:
    benchmark = fie.FixedIncomeBenchmarkReference(
        reference_identity_id=_identity(20),
        role=fie.FixedIncomeReferenceRoleCode("coupon-benchmark"),
        tenor=fie.FinancialTenor(3, fie.FinancialTenorUnit.MONTH),
    )
    floating = fie.FloatingCouponTerms(
        benchmark=benchmark,
        spread=fie.FixedIncomeSpread(Decimal("0.0015")),
        day_count=fie.DayCountConventionCode("actual-360"),
        payment_tenor=_tenor(),
        reset_tenor=fie.FinancialTenor(3, fie.FinancialTenorUnit.MONTH),
    )
    zero = fie.ZeroCouponTerms(day_count=_day_count())

    assert _fixed_coupon().logical_values()[0] == "fixed"
    assert floating.logical_values()[0] == "floating"
    assert zero.logical_values()[0] == "zero"

    with pytest.raises(
        fie.FixedIncomeEconomicsValidationError,
        match="FixedIncomeBenchmarkReference",
    ):
        replace(floating, benchmark=cast(Any, _identity(20)))
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="maturity_date"):
        _terms(coupon=zero, maturity=None)


def test_benchmark_and_yield_reference_grant_no_curve_engine() -> None:
    reference = fie.FixedIncomeBenchmarkReference(
        reference_identity_id=_identity(30),
        role=fie.FixedIncomeReferenceRoleCode("government-benchmark"),
        tenor=fie.FinancialTenor(10, fie.FinancialTenorUnit.YEAR),
    )
    convention = fie.YieldConvention(
        yield_code=fie.FixedIncomeYieldCode("yield-to-maturity"),
        day_count=fie.DayCountConventionCode("actual-actual"),
        compounding=fie.CompoundingConventionCode("periodic"),
        compounding_tenor=_tenor(),
        reference=reference,
    )

    assert convention.reference == reference
    assert convention.logical_values()[-1] == reference.logical_values()
    assert not hasattr(reference, "curve_points")
    assert not hasattr(reference, "discount_factors")


def test_cash_flow_coupon_accrual_binding_and_non_coupon_separation() -> None:
    coupon = _cash_flow(1)
    assert coupon.accrual_period is not None

    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="requires accrual_period"):
        replace(coupon, accrual_period=None)
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="must match"):
        replace(coupon, payment_date=date(2026, 7, 2))

    principal = _cash_flow(
        2,
        kind=fie.FixedIncomeCashFlowKind.PRINCIPAL,
        payment=_MATURITY,
    )
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="must not carry"):
        replace(principal, accrual_period=_accrual(payment=_MATURITY))


def test_schedule_rejects_duplicates_foreign_instrument_and_mutable_container() -> None:
    instrument = _identity(1)
    first = _cash_flow(1, instrument=instrument)
    second = _cash_flow(
        2,
        instrument=instrument,
        kind=fie.FixedIncomeCashFlowKind.REDEMPTION,
        payment=_MATURITY,
    )
    schedule = fie.FixedIncomeCashFlowSchedule(instrument, (second, first))
    assert schedule.cash_flows == (first, second)

    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="unique"):
        fie.FixedIncomeCashFlowSchedule(instrument, (first, first))
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="schedule instrument"):
        fie.FixedIncomeCashFlowSchedule(
            instrument,
            (replace(first, instrument_identity_id=_identity(99)),),
        )
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="non-empty tuple"):
        fie.FixedIncomeCashFlowSchedule(instrument, ())
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="non-empty tuple"):
        fie.FixedIncomeCashFlowSchedule(instrument, cast(Any, [first]))


def test_schedule_logical_order_is_input_order_independent() -> None:
    first = _cash_flow(1)
    second = _cash_flow(
        2,
        kind=fie.FixedIncomeCashFlowKind.PRINCIPAL,
        payment=_MATURITY,
    )
    left = fie.FixedIncomeCashFlowSchedule(_identity(1), (first, second))
    right = fie.FixedIncomeCashFlowSchedule(_identity(1), (second, first))
    assert left.logical_values() == right.logical_values()


def test_terms_chronology_identity_and_redemption_fail_closed() -> None:
    terms = _terms()
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="must differ"):
        replace(terms, denomination_currency_identity_id=terms.instrument_identity_id)
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="after issue_date"):
        replace(terms, maturity_date=_ISSUE)
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="requires maturity_date"):
        replace(terms, maturity_date=None)
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="EconomicIdentityId"):
        replace(terms, instrument_identity_id=cast(Any, _uuid(1)))


def test_profile_rejects_foreign_schedule_and_pre_issue_cash_flow() -> None:
    terms = _terms()
    foreign = _identity(99)
    foreign_flow = _cash_flow(1, instrument=foreign)
    foreign_schedule = fie.FixedIncomeCashFlowSchedule(foreign, (foreign_flow,))
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="terms instrument"):
        fie.FixedIncomeEconomicProfile(terms, foreign_schedule)

    early_flow = _cash_flow(
        2,
        kind=fie.FixedIncomeCashFlowKind.PRINCIPAL,
        payment=date(2025, 7, 1),
    )
    early_schedule = fie.FixedIncomeCashFlowSchedule(_identity(1), (early_flow,))
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="predate issue_date"):
        fie.FixedIncomeEconomicProfile(terms, early_schedule)


def test_perpetual_fixed_coupon_terms_are_not_forced_to_have_maturity() -> None:
    perpetual = _terms(maturity=None)
    assert perpetual.maturity_date is None
    assert perpetual.redemption_amount is None
    assert isinstance(perpetual.coupon, fie.FixedCouponTerms)


def test_evidence_and_id_boundaries_require_uuid() -> None:
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="UUID"):
        fie.FixedIncomeEvidenceRef(cast(Any, "token=secret"))
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="UUID"):
        fie.FixedIncomeTermsId(cast(Any, "terms"))
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="UUID"):
        fie.FixedIncomeCashFlowId(cast(Any, 1))


def test_profile_logical_values_are_deterministic_and_secret_free() -> None:
    terms = _terms()
    first = _cash_flow(1)
    second = _cash_flow(
        2,
        kind=fie.FixedIncomeCashFlowKind.PRINCIPAL,
        payment=_MATURITY,
    )
    left = fie.FixedIncomeEconomicProfile(
        terms,
        fie.FixedIncomeCashFlowSchedule(_identity(1), (first, second)),
    )
    right = fie.FixedIncomeEconomicProfile(
        terms,
        fie.FixedIncomeCashFlowSchedule(_identity(1), (second, first)),
    )
    assert left.logical_values() == right.logical_values()
    material = repr(left.logical_values()).lower()
    assert "token=" not in material
    assert "password=" not in material
    assert "secret=" not in material
