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
    day_count: fie.DayCountConventionCode | None = None,
) -> fie.AccrualPeriod:
    return fie.AccrualPeriod(
        start_date=start,
        end_date=end,
        payment_date=payment,
        day_count=day_count or _day_count(),
    )


def _cash_flow(
    value: int,
    *,
    instrument: uii.EconomicIdentityId | None = None,
    kind: fie.FixedIncomeCashFlowKind = fie.FixedIncomeCashFlowKind.COUPON,
    payment: date = _MID,
    accrual: fie.AccrualPeriod | None = None,
) -> fie.FixedIncomeCashFlow:
    is_coupon = kind is fie.FixedIncomeCashFlowKind.COUPON
    return fie.FixedIncomeCashFlow(
        cash_flow_id=fie.FixedIncomeCashFlowId(_uuid(200 + value)),
        instrument_identity_id=instrument or _identity(1),
        kind=kind,
        direction=fie.FixedIncomeCashFlowDirection.RECEIVABLE,
        amount=fie.FixedIncomeCashAmount(
            Decimal("25") if is_coupon else Decimal("1000")
        ),
        currency_identity_id=_identity(2),
        payment_date=payment,
        evidence_ref=_evidence(200 + value),
        accrual_period=(accrual or _accrual(payment=payment)) if is_coupon else None,
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

    assert type(rate) is fie.CouponRate
    assert type(bond_yield) is fie.FixedIncomeYield
    assert type(spread) is fie.FixedIncomeSpread
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
        fie.FaceAmount(value)
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="finite Decimal"):
        fie.FixedIncomeCashAmount(value)
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

    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="canonical lowercase"):
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

    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="benchmark"):
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


def test_periodic_yield_compounding_requires_frequency_tenor() -> None:
    with pytest.raises(
        fie.FixedIncomeEconomicsValidationError,
        match="periodic yield compounding requires compounding_tenor",
    ):
        fie.YieldConvention(
            yield_code=fie.FixedIncomeYieldCode("yield-to-maturity"),
            day_count=_day_count(),
            compounding=fie.CompoundingConventionCode("periodic"),
            compounding_tenor=None,
        )


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


def test_zero_coupon_profile_rejects_coupon_cash_flow() -> None:
    terms = _terms(coupon=fie.ZeroCouponTerms(day_count=_day_count()))
    schedule = fie.FixedIncomeCashFlowSchedule(_identity(1), (_cash_flow(1),))

    with pytest.raises(
        fie.FixedIncomeEconomicsValidationError,
        match="zero-coupon terms must not carry coupon cash flows",
    ):
        fie.FixedIncomeEconomicProfile(terms, schedule)


def test_profile_rejects_coupon_accrual_day_count_mismatch() -> None:
    mismatched = _accrual(
        day_count=fie.DayCountConventionCode("actual-360"),
    )
    flow = _cash_flow(1, accrual=mismatched)
    schedule = fie.FixedIncomeCashFlowSchedule(_identity(1), (flow,))

    with pytest.raises(
        fie.FixedIncomeEconomicsValidationError,
        match="day_count must match coupon terms",
    ):
        fie.FixedIncomeEconomicProfile(_terms(), schedule)


def test_perpetual_coupon_debt_is_not_forced_to_have_maturity() -> None:
    fixed = _terms(maturity=None)
    floating_coupon = fie.FloatingCouponTerms(
        benchmark=fie.FixedIncomeBenchmarkReference(
            reference_identity_id=_identity(20),
            role=fie.FixedIncomeReferenceRoleCode("coupon-benchmark"),
        ),
        spread=fie.FixedIncomeSpread(Decimal("0.001")),
        day_count=fie.DayCountConventionCode("actual-360"),
        payment_tenor=_tenor(),
        reset_tenor=fie.FinancialTenor(3, fie.FinancialTenorUnit.MONTH),
    )
    floating = _terms(coupon=floating_coupon, maturity=None)

    assert fixed.maturity_date is None
    assert fixed.redemption_amount is None
    assert floating.maturity_date is None
    assert isinstance(floating.coupon, fie.FloatingCouponTerms)


def test_secret_like_material_cannot_enter_id_evidence_contracts() -> None:
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="UUID"):
        fie.FixedIncomeEvidenceRef(cast(Any, "token=secret"))
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="UUID"):
        fie.FixedIncomeTermsId(cast(Any, "password=secret"))
    with pytest.raises(fie.FixedIncomeEconomicsValidationError, match="UUID"):
        fie.FixedIncomeCashFlowId(cast(Any, "secret=value"))


def test_logical_values_are_deterministic_and_secret_free() -> None:
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


# ---- Oracle test constants ----
_ISSUE_STR = "2026-01-01"
_MID_STR = "2026-07-01"
_MATURITY_STR = "2031-01-01"
_PRICE_STR = "99.25"
_COUPON_RATE_STR = "0.05"
_SPREAD_STR = "0.0015"
_FACE_STR = "1000"
_REDEMPTION_STR = "1000"


# ---- Expected-value oracles (independent) ----

def _expected_fixed_income_price(
    price: fie.FixedIncomePrice,
    expected_price: str,
) -> tuple[object, ...]:
    return (
        expected_price,
        price.kind.value,
        (price.basis.value,),
    )


def _expected_benchmark_reference(
    ref: fie.FixedIncomeBenchmarkReference,
) -> tuple[object, ...]:
    tenor_tuple = None
    if ref.tenor is not None:
        tenor_tuple = (ref.tenor.value, ref.tenor.unit.value)
    return (
        (str(ref.reference_identity_id.value),),
        (ref.role.value,),
        tenor_tuple,
    )


def _expected_fixed_coupon_terms(
    terms: fie.FixedCouponTerms,
    expected_rate: str,
) -> tuple[object, ...]:
    return (
        "fixed",
        (expected_rate,),
        (terms.day_count.value,),
        (terms.payment_tenor.value, terms.payment_tenor.unit.value),
    )


def _expected_floating_coupon_terms(
    terms: fie.FloatingCouponTerms,
    expected_spread: str,
) -> tuple[object, ...]:
    return (
        "floating",
        _expected_benchmark_reference(terms.benchmark),
        (expected_spread,),
        (terms.day_count.value,),
        (terms.payment_tenor.value, terms.payment_tenor.unit.value),
        (terms.reset_tenor.value, terms.reset_tenor.unit.value),
    )


def _expected_zero_coupon_terms(
    terms: fie.ZeroCouponTerms,
) -> tuple[object, ...]:
    return (
        "zero",
        (terms.day_count.value,),
    )


def _expected_accrual_period(
    period: fie.AccrualPeriod,
    *,
    expected_start: str,
    expected_end: str,
    expected_payment: str,
) -> tuple[object, ...]:
    return (
        expected_start,
        expected_end,
        expected_payment,
        (period.day_count.value,),
    )


def _expected_settlement_convention(
    conv: fie.SettlementConvention,
) -> tuple[object, ...]:
    return (
        conv.business_day_lag,
        (conv.calendar_ref.value,),
        (conv.business_day_convention.value,),
    )


def _expected_yield_convention(
    conv: fie.YieldConvention,
) -> tuple[object, ...]:
    comp_tenor = None
    if conv.compounding_tenor is not None:
        comp_tenor = (conv.compounding_tenor.value, conv.compounding_tenor.unit.value)
    ref_tuple = None
    if conv.reference is not None:
        ref_tuple = _expected_benchmark_reference(conv.reference)
    return (
        (conv.yield_code.value,),
        (conv.day_count.value,),
        (conv.compounding.value,),
        comp_tenor,
        ref_tuple,
    )


def _expected_cash_flow(
    flow: fie.FixedIncomeCashFlow,
    *,
    expected_amount: str,
    expected_payment_date: str,
    expected_accrual: tuple[object, ...] | None,
) -> tuple[object, ...]:
    return (
        (str(flow.cash_flow_id.value),),
        (str(flow.instrument_identity_id.value),),
        flow.kind.value,
        flow.direction.value,
        (expected_amount,),
        (str(flow.currency_identity_id.value),),
        expected_payment_date,
        (str(flow.evidence_ref.value),),
        expected_accrual,
    )


def _expected_cash_flow_schedule(
    schedule: fie.FixedIncomeCashFlowSchedule,
    expected_flows: tuple[tuple[object, ...], ...],
) -> tuple[object, ...]:
    return (
        (str(schedule.instrument_identity_id.value),),
        expected_flows,
    )


def _expected_instrument_terms(
    terms: fie.FixedIncomeInstrumentTerms,
    *,
    expected_face: str,
    expected_issue_date: str,
    expected_maturity_date: str | None,
    expected_coupon: tuple[object, ...],
    expected_settlement: tuple[object, ...],
    expected_yield: tuple[object, ...],
    expected_redemption: str | None,
) -> tuple[object, ...]:
    return (
        (str(terms.terms_id.value),),
        (str(terms.instrument_identity_id.value),),
        (str(terms.denomination_currency_identity_id.value),),
        (expected_face,),
        expected_issue_date,
        expected_maturity_date,
        expected_coupon,
        expected_settlement,
        expected_yield,
        (str(terms.evidence_ref.value),),
        (expected_redemption,) if expected_redemption is not None else None,
    )


def _expected_economic_profile(
    profile: fie.FixedIncomeEconomicProfile,
    *,
    expected_terms: tuple[object, ...],
    expected_schedule: tuple[object, ...] | None,
) -> tuple[object, ...]:
    return (
        expected_terms,
        expected_schedule,
    )


# ---- Complete projection oracles ----

def test_fixed_income_price_complete_projection() -> None:
    price = fie.FixedIncomePrice(
        value=Decimal("99.2500"),
        kind=fie.FixedIncomePriceKind.CLEAN,
        basis=fie.FixedIncomePriceBasisCode("percent-of-par"),
    )
    expected = _expected_fixed_income_price(price, _PRICE_STR)
    assert price.logical_values() == expected


def test_benchmark_reference_complete_projection_tenor_populated() -> None:
    identity = _identity(20)
    tenor = _tenor(6, fie.FinancialTenorUnit.MONTH)
    ref = fie.FixedIncomeBenchmarkReference(
        reference_identity_id=identity,
        role=fie.FixedIncomeReferenceRoleCode("government-benchmark"),
        tenor=tenor,
    )
    expected = _expected_benchmark_reference(ref)
    assert ref.logical_values() == expected


def test_benchmark_reference_complete_projection_tenor_none() -> None:
    identity = _identity(21)
    ref = fie.FixedIncomeBenchmarkReference(
        reference_identity_id=identity,
        role=fie.FixedIncomeReferenceRoleCode("government-benchmark"),
        tenor=None,
    )
    expected = _expected_benchmark_reference(ref)
    assert ref.logical_values() == expected


def test_fixed_coupon_terms_complete_projection() -> None:
    terms = _fixed_coupon()
    expected = _expected_fixed_coupon_terms(terms, _COUPON_RATE_STR)
    assert terms.logical_values() == expected


def test_floating_coupon_terms_complete_projection() -> None:
    identity = _identity(22)
    benchmark = fie.FixedIncomeBenchmarkReference(
        reference_identity_id=identity,
        role=fie.FixedIncomeReferenceRoleCode("government-benchmark"),
        tenor=None,
    )
    terms = fie.FloatingCouponTerms(
        benchmark=benchmark,
        spread=fie.FixedIncomeSpread(Decimal("0.0015")),
        day_count=fie.DayCountConventionCode("actual-360"),
        payment_tenor=_tenor(6, fie.FinancialTenorUnit.MONTH),
        reset_tenor=fie.FinancialTenor(3, fie.FinancialTenorUnit.MONTH),
    )
    expected = _expected_floating_coupon_terms(terms, _SPREAD_STR)
    assert terms.logical_values() == expected


def test_zero_coupon_terms_complete_projection() -> None:
    terms = fie.ZeroCouponTerms(day_count=_day_count())
    expected = _expected_zero_coupon_terms(terms)
    assert terms.logical_values() == expected


def test_accrual_period_complete_projection() -> None:
    period = _accrual(payment=date(2026, 7, 2))
    expected = _expected_accrual_period(
        period,
        expected_start=_ISSUE_STR,
        expected_end=_MID_STR,
        expected_payment="2026-07-02",
    )
    assert period.logical_values() == expected


def test_settlement_convention_complete_projection() -> None:
    conv = _settlement()
    expected = _expected_settlement_convention(conv)
    assert conv.logical_values() == expected


def test_yield_convention_complete_projection_populated() -> None:
    identity = _identity(23)
    benchmark = fie.FixedIncomeBenchmarkReference(
        reference_identity_id=identity,
        role=fie.FixedIncomeReferenceRoleCode("government-benchmark"),
        tenor=None,
    )
    conv = fie.YieldConvention(
        yield_code=fie.FixedIncomeYieldCode("yield-to-maturity"),
        day_count=_day_count(),
        compounding=fie.CompoundingConventionCode("periodic"),
        compounding_tenor=_tenor(6, fie.FinancialTenorUnit.MONTH),
        reference=benchmark,
    )
    expected = _expected_yield_convention(conv)
    assert conv.logical_values() == expected


def test_yield_convention_complete_projection_none_branches() -> None:
    conv = fie.YieldConvention(
        yield_code=fie.FixedIncomeYieldCode("yield-to-maturity"),
        day_count=_day_count(),
        compounding=fie.CompoundingConventionCode("simple"),
        compounding_tenor=None,
        reference=None,
    )
    expected = _expected_yield_convention(conv)
    assert conv.logical_values() == expected


def test_cash_flow_coupon_with_accrual_complete_projection() -> None:
    instrument = _identity(24)
    flow = _cash_flow(1, instrument=instrument)
    accrual = flow.accrual_period
    assert accrual is not None
    expected = _expected_cash_flow(
        flow,
        expected_amount="25",
        expected_payment_date=_MID_STR,
        expected_accrual=_expected_accrual_period(
            accrual,
            expected_start=_ISSUE_STR,
            expected_end=_MID_STR,
            expected_payment=_MID_STR,
        ),
    )
    assert flow.logical_values() == expected


def test_cash_flow_principal_no_accrual_complete_projection() -> None:
    instrument = _identity(25)
    flow = _cash_flow(
        2,
        instrument=instrument,
        kind=fie.FixedIncomeCashFlowKind.PRINCIPAL,
        payment=_MATURITY,
    )
    expected = _expected_cash_flow(
        flow,
        expected_amount=_FACE_STR,
        expected_payment_date=_MATURITY_STR,
        expected_accrual=None,
    )
    assert flow.logical_values() == expected


def test_cash_flow_schedule_complete_projection_with_order() -> None:
    instrument = _identity(40)
    early = _cash_flow(
        3,
        instrument=instrument,
        payment=_MID,
    )
    late_first = _cash_flow(
        1,
        instrument=instrument,
        kind=fie.FixedIncomeCashFlowKind.PRINCIPAL,
        payment=_MATURITY,
    )
    late_second = _cash_flow(
        2,
        instrument=instrument,
        kind=fie.FixedIncomeCashFlowKind.REDEMPTION,
        payment=_MATURITY,
    )
    schedule = fie.FixedIncomeCashFlowSchedule(
        instrument_identity_id=instrument,
        cash_flows=(late_second, early, late_first),
    )

    early_accrual = early.accrual_period
    assert early_accrual is not None
    early_expected = _expected_cash_flow(
        early,
        expected_amount="25",
        expected_payment_date=_MID_STR,
        expected_accrual=_expected_accrual_period(
            early_accrual,
            expected_start=_ISSUE_STR,
            expected_end=_MID_STR,
            expected_payment=_MID_STR,
        ),
    )
    late_first_expected = _expected_cash_flow(
        late_first,
        expected_amount=_FACE_STR,
        expected_payment_date=_MATURITY_STR,
        expected_accrual=None,
    )
    late_second_expected = _expected_cash_flow(
        late_second,
        expected_amount=_REDEMPTION_STR,
        expected_payment_date=_MATURITY_STR,
        expected_accrual=None,
    )
    expected_flows = (early_expected, late_first_expected, late_second_expected)
    expected = _expected_cash_flow_schedule(schedule, expected_flows)
    assert schedule.logical_values() == expected


def test_instrument_terms_fixed_coupon_maturity_redemption() -> None:
    terms = replace(
        _terms(),
        redemption_amount=fie.FixedIncomeCashAmount(Decimal("950")),
    )
    fixed_coupon = terms.coupon
    assert isinstance(fixed_coupon, fie.FixedCouponTerms)
    expected = _expected_instrument_terms(
        terms,
        expected_face=_FACE_STR,
        expected_issue_date=_ISSUE_STR,
        expected_maturity_date=_MATURITY_STR,
        expected_coupon=_expected_fixed_coupon_terms(
            fixed_coupon,
            _COUPON_RATE_STR,
        ),
        expected_settlement=_expected_settlement_convention(terms.settlement),
        expected_yield=_expected_yield_convention(terms.yield_convention),
        expected_redemption="950",
    )
    assert terms.logical_values() == expected


def test_instrument_terms_floating_coupon() -> None:
    identity = _identity(26)
    benchmark = fie.FixedIncomeBenchmarkReference(
        reference_identity_id=identity,
        role=fie.FixedIncomeReferenceRoleCode("government-benchmark"),
        tenor=None,
    )
    floating = fie.FloatingCouponTerms(
        benchmark=benchmark,
        spread=fie.FixedIncomeSpread(Decimal("0.0015")),
        day_count=fie.DayCountConventionCode("actual-360"),
        payment_tenor=_tenor(6, fie.FinancialTenorUnit.MONTH),
        reset_tenor=fie.FinancialTenor(3, fie.FinancialTenorUnit.MONTH),
    )
    terms = _terms(coupon=floating)
    expected = _expected_instrument_terms(
        terms,
        expected_face=_FACE_STR,
        expected_issue_date=_ISSUE_STR,
        expected_maturity_date=_MATURITY_STR,
        expected_coupon=_expected_floating_coupon_terms(floating, _SPREAD_STR),
        expected_settlement=_expected_settlement_convention(terms.settlement),
        expected_yield=_expected_yield_convention(terms.yield_convention),
        expected_redemption=_REDEMPTION_STR,
    )
    assert terms.logical_values() == expected


def test_instrument_terms_zero_coupon() -> None:
    zero = fie.ZeroCouponTerms(day_count=_day_count())
    terms = _terms(coupon=zero)
    expected = _expected_instrument_terms(
        terms,
        expected_face=_FACE_STR,
        expected_issue_date=_ISSUE_STR,
        expected_maturity_date=_MATURITY_STR,
        expected_coupon=_expected_zero_coupon_terms(zero),
        expected_settlement=_expected_settlement_convention(terms.settlement),
        expected_yield=_expected_yield_convention(terms.yield_convention),
        expected_redemption=_REDEMPTION_STR,
    )
    assert terms.logical_values() == expected


def test_instrument_terms_perpetual() -> None:
    terms = _terms(maturity=None)
    fixed_coupon = terms.coupon
    assert isinstance(fixed_coupon, fie.FixedCouponTerms)
    expected = _expected_instrument_terms(
        terms,
        expected_face=_FACE_STR,
        expected_issue_date=_ISSUE_STR,
        expected_maturity_date=None,
        expected_coupon=_expected_fixed_coupon_terms(
            fixed_coupon,
            _COUPON_RATE_STR,
        ),
        expected_settlement=_expected_settlement_convention(terms.settlement),
        expected_yield=_expected_yield_convention(terms.yield_convention),
        expected_redemption=None,
    )
    assert terms.logical_values() == expected


def test_economic_profile_with_schedule() -> None:
    terms = _terms()
    instrument = terms.instrument_identity_id
    coupon_flow = _cash_flow(10, instrument=instrument)
    principal_flow = _cash_flow(
        11,
        instrument=instrument,
        kind=fie.FixedIncomeCashFlowKind.PRINCIPAL,
        payment=_MATURITY,
    )
    schedule = fie.FixedIncomeCashFlowSchedule(
        instrument_identity_id=instrument,
        cash_flows=(principal_flow, coupon_flow),
    )
    profile = fie.FixedIncomeEconomicProfile(
        terms=terms,
        cash_flow_schedule=schedule,
    )

    coupon_accrual = coupon_flow.accrual_period
    assert coupon_accrual is not None
    coupon_expected = _expected_cash_flow(
        coupon_flow,
        expected_amount="25",
        expected_payment_date=_MID_STR,
        expected_accrual=_expected_accrual_period(
            coupon_accrual,
            expected_start=_ISSUE_STR,
            expected_end=_MID_STR,
            expected_payment=_MID_STR,
        ),
    )
    principal_expected = _expected_cash_flow(
        principal_flow,
        expected_amount=_FACE_STR,
        expected_payment_date=_MATURITY_STR,
        expected_accrual=None,
    )

    fixed_coupon = terms.coupon
    assert isinstance(fixed_coupon, fie.FixedCouponTerms)
    expected_terms = _expected_instrument_terms(
        terms,
        expected_face=_FACE_STR,
        expected_issue_date=_ISSUE_STR,
        expected_maturity_date=_MATURITY_STR,
        expected_coupon=_expected_fixed_coupon_terms(fixed_coupon, _COUPON_RATE_STR),
        expected_settlement=_expected_settlement_convention(terms.settlement),
        expected_yield=_expected_yield_convention(terms.yield_convention),
        expected_redemption=_REDEMPTION_STR,
    )
    expected_schedule = _expected_cash_flow_schedule(
        schedule,
        expected_flows=(coupon_expected, principal_expected),
    )
    expected = _expected_economic_profile(
        profile,
        expected_terms=expected_terms,
        expected_schedule=expected_schedule,
    )
    assert profile.logical_values() == expected


def test_economic_profile_schedule_none() -> None:
    terms = _terms()
    profile = fie.FixedIncomeEconomicProfile(
        terms=terms,
        cash_flow_schedule=None,
    )
    fixed_coupon = terms.coupon
    assert isinstance(fixed_coupon, fie.FixedCouponTerms)
    expected_terms = _expected_instrument_terms(
        terms,
        expected_face=_FACE_STR,
        expected_issue_date=_ISSUE_STR,
        expected_maturity_date=_MATURITY_STR,
        expected_coupon=_expected_fixed_coupon_terms(fixed_coupon, _COUPON_RATE_STR),
        expected_settlement=_expected_settlement_convention(terms.settlement),
        expected_yield=_expected_yield_convention(terms.yield_convention),
        expected_redemption=_REDEMPTION_STR,
    )
    expected = _expected_economic_profile(
        profile,
        expected_terms=expected_terms,
        expected_schedule=None,
    )
    assert profile.logical_values() == expected
