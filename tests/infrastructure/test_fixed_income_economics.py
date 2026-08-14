from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.fixed_income_economics import (
    AccrualPeriod,
    BusinessCalendarRef,
    BusinessDayConventionCode,
    CompoundingConventionCode,
    CouponRate,
    DayCountConventionCode,
    FaceAmount,
    FinancialTenor,
    FinancialTenorUnit,
    FixedCouponTerms,
    FixedIncomeBenchmarkReference,
    FixedIncomeCashAmount,
    FixedIncomeCashFlow,
    FixedIncomeCashFlowDirection,
    FixedIncomeCashFlowId,
    FixedIncomeCashFlowKind,
    FixedIncomeCashFlowSchedule,
    FixedIncomeEconomicProfile,
    FixedIncomeEconomicsValidationError,
    FixedIncomeEvidenceRef,
    FixedIncomeInstrumentTerms,
    FixedIncomePrice,
    FixedIncomePriceBasisCode,
    FixedIncomePriceKind,
    FixedIncomeReferenceRoleCode,
    FixedIncomeSpread,
    FixedIncomeTermsId,
    FixedIncomeYield,
    FixedIncomeYieldCode,
    FloatingCouponTerms,
    SettlementConvention,
    YieldConvention,
    ZeroCouponTerms,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


_ISSUE = date(2026, 1, 1)
_MID = date(2026, 7, 1)
_MATURITY = date(2031, 1, 1)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _evidence(value: int) -> FixedIncomeEvidenceRef:
    return FixedIncomeEvidenceRef(_uuid(10_000 + value))


def _tenor(
    value: int = 6,
    unit: FinancialTenorUnit = FinancialTenorUnit.MONTH,
) -> FinancialTenor:
    return FinancialTenor(value=value, unit=unit)


def _day_count() -> DayCountConventionCode:
    return DayCountConventionCode("actual-365-fixed")


def _settlement() -> SettlementConvention:
    return SettlementConvention(
        business_day_lag=2,
        calendar_ref=BusinessCalendarRef("target2"),
        business_day_convention=BusinessDayConventionCode("following"),
    )


def _yield_convention() -> YieldConvention:
    return YieldConvention(
        yield_code=FixedIncomeYieldCode("yield-to-maturity"),
        day_count=_day_count(),
        compounding=CompoundingConventionCode("periodic"),
        compounding_tenor=_tenor(),
    )


def _fixed_coupon() -> FixedCouponTerms:
    return FixedCouponTerms(
        rate=CouponRate(Decimal("0.05")),
        day_count=_day_count(),
        payment_tenor=_tenor(),
    )


def _terms(
    *,
    instrument: EconomicIdentityId | None = None,
    coupon: FixedCouponTerms | FloatingCouponTerms | ZeroCouponTerms | None = None,
    maturity: date | None = _MATURITY,
) -> FixedIncomeInstrumentTerms:
    return FixedIncomeInstrumentTerms(
        terms_id=FixedIncomeTermsId(_uuid(100)),
        instrument_identity_id=instrument or _identity(1),
        denomination_currency_identity_id=_identity(2),
        face_amount=FaceAmount(Decimal("1000")),
        issue_date=_ISSUE,
        maturity_date=maturity,
        coupon=coupon or _fixed_coupon(),
        settlement=_settlement(),
        yield_convention=_yield_convention(),
        evidence_ref=_evidence(1),
        redemption_amount=FixedIncomeCashAmount(Decimal("1000"))
        if maturity is not None
        else None,
    )


def _accrual(
    *,
    start: date = _ISSUE,
    end: date = _MID,
    payment: date = _MID,
) -> AccrualPeriod:
    return AccrualPeriod(
        start_date=start,
        end_date=end,
        payment_date=payment,
        day_count=_day_count(),
    )


def _cash_flow(
    value: int,
    *,
    instrument: EconomicIdentityId | None = None,
    kind: FixedIncomeCashFlowKind = FixedIncomeCashFlowKind.COUPON,
    payment: date = _MID,
) -> FixedIncomeCashFlow:
    return FixedIncomeCashFlow(
        cash_flow_id=FixedIncomeCashFlowId(_uuid(200 + value)),
        instrument_identity_id=instrument or _identity(1),
        kind=kind,
        direction=FixedIncomeCashFlowDirection.RECEIVABLE,
        amount=FixedIncomeCashAmount(
            Decimal("25")
            if kind is FixedIncomeCashFlowKind.COUPON
            else Decimal("1000")
        ),
        currency_identity_id=_identity(2),
        payment_date=payment,
        evidence_ref=_evidence(200 + value),
        accrual_period=_accrual(payment=payment)
        if kind is FixedIncomeCashFlowKind.COUPON
        else None,
    )


def test_fixed_income_profile_binds_identity_terms_and_cash_flows() -> None:
    terms = _terms()
    coupon = _cash_flow(1)
    principal = _cash_flow(
        2,
        kind=FixedIncomeCashFlowKind.PRINCIPAL,
        payment=_MATURITY,
    )
    schedule = FixedIncomeCashFlowSchedule(
        instrument_identity_id=terms.instrument_identity_id,
        cash_flows=(principal, coupon),
    )
    profile = FixedIncomeEconomicProfile(terms=terms, cash_flow_schedule=schedule)

    assert profile.terms.instrument_identity_id == _identity(1)
    assert profile.terms.denomination_currency_identity_id == _identity(2)
    assert profile.cash_flow_schedule is not None
    assert profile.cash_flow_schedule.cash_flows == (coupon, principal)
    assert profile.logical_values()[1] == schedule.logical_values()


def test_rate_yield_and_spread_are_distinct_semantics_with_canonical_decimal() -> None:
    magnitude = Decimal("0.0500")
    rate = CouponRate(magnitude)
    bond_yield = FixedIncomeYield(magnitude)
    spread = FixedIncomeSpread(magnitude)

    assert rate != bond_yield
    assert bond_yield != spread
    assert rate != spread
    assert rate.logical_values() == CouponRate(Decimal("0.05")).logical_values()
    assert bond_yield.logical_values() == ("0.05",)
    assert spread.logical_values() == ("0.05",)


def test_clean_and_dirty_price_remain_distinct_even_when_numeric_value_matches(
) -> None:
    basis = FixedIncomePriceBasisCode("percent-of-par")
    clean = FixedIncomePrice(
        value=Decimal("99.2500"),
        kind=FixedIncomePriceKind.CLEAN,
        basis=basis,
    )
    dirty = replace(clean, kind=FixedIncomePriceKind.DIRTY)

    assert clean != dirty
    assert clean.logical_values()[0] == "99.25"
    assert clean.logical_values()[1] == "clean"
    assert dirty.logical_values()[1] == "dirty"


@pytest.mark.parametrize(
    "value",
    [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")],
)
def test_numeric_contracts_reject_non_finite_decimals(value: Decimal) -> None:
    with pytest.raises(FixedIncomeEconomicsValidationError, match="finite Decimal"):
        CouponRate(value)
    with pytest.raises(FixedIncomeEconomicsValidationError, match="finite Decimal"):
        FixedIncomeYield(value)
    with pytest.raises(FixedIncomeEconomicsValidationError, match="finite Decimal"):
        FixedIncomeSpread(value)
    with pytest.raises(FixedIncomeEconomicsValidationError, match="finite Decimal"):
        FixedIncomePrice(
            value=value,
            kind=FixedIncomePriceKind.CLEAN,
            basis=FixedIncomePriceBasisCode("percent-of-par"),
        )


def test_face_and_cash_amount_are_positive_and_not_generic_quantity() -> None:
    assert FaceAmount(Decimal("1000")).logical_values() == ("1000",)
    assert FixedIncomeCashAmount(Decimal("25.00")).logical_values() == ("25",)
    with pytest.raises(FixedIncomeEconomicsValidationError, match="positive"):
        FaceAmount(Decimal("0"))
    with pytest.raises(FixedIncomeEconomicsValidationError, match="positive"):
        FixedIncomeCashAmount(Decimal("-1"))


def test_financial_tenor_is_structural_and_strictly_typed() -> None:
    tenor = FinancialTenor(3, FinancialTenorUnit.MONTH)
    assert tenor.logical_values() == (3, "month")
    assert not hasattr(tenor, "seconds")
    assert not hasattr(tenor, "fixed_seconds")

    with pytest.raises(FixedIncomeEconomicsValidationError, match="positive int"):
        FinancialTenor(cast(int, True), FinancialTenorUnit.MONTH)
    with pytest.raises(FixedIncomeEconomicsValidationError, match="positive int"):
        FinancialTenor(0, FinancialTenorUnit.MONTH)
    with pytest.raises(FixedIncomeEconomicsValidationError, match="FinancialTenorUnit"):
        FinancialTenor(3, cast(Any, "month"))


def test_day_count_settlement_and_codes_fail_closed() -> None:
    assert DayCountConventionCode("30e-360").logical_values() == ("30e-360",)
    assert _settlement().logical_values()[0] == 2

    with pytest.raises(
        FixedIncomeEconomicsValidationError,
        match="canonical lowercase",
    ):
        DayCountConventionCode("ACT/365")
    with pytest.raises(FixedIncomeEconomicsValidationError, match="non-negative int"):
        SettlementConvention(
            business_day_lag=cast(int, True),
            calendar_ref=BusinessCalendarRef("target2"),
            business_day_convention=BusinessDayConventionCode("following"),
        )
    with pytest.raises(FixedIncomeEconomicsValidationError, match="non-negative int"):
        replace(_settlement(), business_day_lag=-1)
    with pytest.raises(
        FixedIncomeEconomicsValidationError,
        match="BusinessCalendarRef",
    ):
        replace(_settlement(), calendar_ref=cast(Any, "target2"))


def test_accrual_chronology_and_runtime_date_types_fail_closed() -> None:
    accrual = _accrual()
    assert accrual.logical_values()[:3] == (
        "2026-01-01",
        "2026-07-01",
        "2026-07-01",
    )

    with pytest.raises(FixedIncomeEconomicsValidationError, match="after start_date"):
        _accrual(end=_ISSUE)
    with pytest.raises(FixedIncomeEconomicsValidationError, match="must not predate"):
        _accrual(payment=date(2026, 6, 30))
    with pytest.raises(FixedIncomeEconomicsValidationError, match="must be date"):
        replace(accrual, start_date=cast(Any, datetime(2026, 1, 1)))


def test_coupon_families_are_explicit_and_cannot_be_mixed_by_raw_values() -> None:
    benchmark = FixedIncomeBenchmarkReference(
        reference_identity_id=_identity(20),
        role=FixedIncomeReferenceRoleCode("coupon-benchmark"),
        tenor=FinancialTenor(3, FinancialTenorUnit.MONTH),
    )
    floating = FloatingCouponTerms(
        benchmark=benchmark,
        spread=FixedIncomeSpread(Decimal("0.0015")),
        day_count=DayCountConventionCode("actual-360"),
        payment_tenor=_tenor(),
        reset_tenor=FinancialTenor(3, FinancialTenorUnit.MONTH),
    )
    zero = ZeroCouponTerms(day_count=_day_count())

    assert _fixed_coupon().logical_values()[0] == "fixed"
    assert floating.logical_values()[0] == "floating"
    assert zero.logical_values()[0] == "zero"

    with pytest.raises(
        FixedIncomeEconomicsValidationError,
        match="FixedIncomeBenchmarkReference",
    ):
        replace(floating, benchmark=cast(Any, _identity(20)))
    with pytest.raises(FixedIncomeEconomicsValidationError, match="maturity_date"):
        _terms(coupon=zero, maturity=None)


def test_benchmark_and_yield_convention_retain_semantics_without_curve_engine() -> None:
    reference = FixedIncomeBenchmarkReference(
        reference_identity_id=_identity(30),
        role=FixedIncomeReferenceRoleCode("government-benchmark"),
        tenor=FinancialTenor(10, FinancialTenorUnit.YEAR),
    )
    convention = YieldConvention(
        yield_code=FixedIncomeYieldCode("yield-to-maturity"),
        day_count=DayCountConventionCode("actual-actual"),
        compounding=CompoundingConventionCode("periodic"),
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

    with pytest.raises(
        FixedIncomeEconomicsValidationError,
        match="requires accrual_period",
    ):
        replace(coupon, accrual_period=None)
    with pytest.raises(FixedIncomeEconomicsValidationError, match="must match"):
        replace(coupon, payment_date=date(2026, 7, 2))

    principal = _cash_flow(
        2,
        kind=FixedIncomeCashFlowKind.PRINCIPAL,
        payment=_MATURITY,
    )
    with pytest.raises(FixedIncomeEconomicsValidationError, match="must not carry"):
        replace(principal, accrual_period=_accrual(payment=_MATURITY))


def test_cash_flow_schedule_rejects_duplicates_foreign_instrument_and_bad_container(
) -> None:
    instrument = _identity(1)
    first = _cash_flow(1, instrument=instrument)
    second = _cash_flow(
        2,
        instrument=instrument,
        kind=FixedIncomeCashFlowKind.REDEMPTION,
        payment=_MATURITY,
    )
    schedule = FixedIncomeCashFlowSchedule(instrument, (second, first))
    assert schedule.cash_flows == (first, second)

    with pytest.raises(FixedIncomeEconomicsValidationError, match="unique"):
        FixedIncomeCashFlowSchedule(instrument, (first, first))
    with pytest.raises(
        FixedIncomeEconomicsValidationError,
        match="schedule instrument",
    ):
        FixedIncomeCashFlowSchedule(
            instrument,
            (replace(first, instrument_identity_id=_identity(99)),),
        )
    with pytest.raises(FixedIncomeEconomicsValidationError, match="non-empty tuple"):
        FixedIncomeCashFlowSchedule(instrument, ())
    with pytest.raises(FixedIncomeEconomicsValidationError, match="non-empty tuple"):
        FixedIncomeCashFlowSchedule(instrument, cast(Any, [first]))


def test_cash_flow_schedule_logical_order_is_input_order_independent() -> None:
    first = _cash_flow(1)
    second = _cash_flow(
        2,
        kind=FixedIncomeCashFlowKind.PRINCIPAL,
        payment=_MATURITY,
    )
    left = FixedIncomeCashFlowSchedule(_identity(1), (first, second))
    right = FixedIncomeCashFlowSchedule(_identity(1), (second, first))
    assert left.logical_values() == right.logical_values()


def test_terms_chronology_identity_and_redemption_invariants_fail_closed() -> None:
    terms = _terms()
    with pytest.raises(FixedIncomeEconomicsValidationError, match="must differ"):
        replace(
            terms,
            denomination_currency_identity_id=terms.instrument_identity_id,
        )
    with pytest.raises(FixedIncomeEconomicsValidationError, match="after issue_date"):
        replace(terms, maturity_date=_ISSUE)
    with pytest.raises(
        FixedIncomeEconomicsValidationError,
        match="requires maturity_date",
    ):
        replace(terms, maturity_date=None)
    with pytest.raises(FixedIncomeEconomicsValidationError, match="EconomicIdentityId"):
        replace(terms, instrument_identity_id=cast(Any, _uuid(1)))


def test_profile_rejects_foreign_schedule_and_pre_issue_cash_flow() -> None:
    terms = _terms()
    foreign = _identity(99)
    foreign_flow = _cash_flow(1, instrument=foreign)
    foreign_schedule = FixedIncomeCashFlowSchedule(foreign, (foreign_flow,))
    with pytest.raises(FixedIncomeEconomicsValidationError, match="terms instrument"):
        FixedIncomeEconomicProfile(terms, foreign_schedule)

    early_flow = _cash_flow(
        2,
        kind=FixedIncomeCashFlowKind.PRINCIPAL,
        payment=date(2025, 7, 1),
    )
    early_schedule = FixedIncomeCashFlowSchedule(_identity(1), (early_flow,))
    with pytest.raises(FixedIncomeEconomicsValidationError, match="predate issue_date"):
        FixedIncomeEconomicProfile(terms, early_schedule)


def test_perpetual_fixed_coupon_terms_are_not_forced_to_have_maturity() -> None:
    perpetual = _terms(maturity=None)
    assert perpetual.maturity_date is None
    assert perpetual.redemption_amount is None
    assert isinstance(perpetual.coupon, FixedCouponTerms)


def test_evidence_and_id_types_are_strict_uuid_boundaries() -> None:
    with pytest.raises(FixedIncomeEconomicsValidationError, match="UUID"):
        FixedIncomeEvidenceRef(cast(Any, "token=secret"))
    with pytest.raises(FixedIncomeEconomicsValidationError, match="UUID"):
        FixedIncomeTermsId(cast(Any, "terms"))
    with pytest.raises(FixedIncomeEconomicsValidationError, match="UUID"):
        FixedIncomeCashFlowId(cast(Any, 1))


def test_profile_logical_values_are_deterministic_and_secret_free() -> None:
    terms = _terms()
    first = _cash_flow(1)
    second = _cash_flow(
        2,
        kind=FixedIncomeCashFlowKind.PRINCIPAL,
        payment=_MATURITY,
    )
    left = FixedIncomeEconomicProfile(
        terms,
        FixedIncomeCashFlowSchedule(_identity(1), (first, second)),
    )
    right = FixedIncomeEconomicProfile(
        terms,
        FixedIncomeCashFlowSchedule(_identity(1), (second, first)),
    )
    assert left.logical_values() == right.logical_values()
    material = repr(left.logical_values()).lower()
    assert "token=" not in material
    assert "password=" not in material
    assert "secret=" not in material
