from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeBenchmarkReference,
    DerivativeContractRate,
    DerivativeEvidenceRef,
    DerivativeFloatingRateCalculationCode,
    DerivativeFloatingRateConvention,
    DerivativeLegDirection,
    DerivativeLegId,
    DerivativeLegOrdinal,
    DerivativeNotional,
    DerivativeNotionalSchedule,
    DerivativeNotionalStep,
    DerivativeReferenceRoleCode,
    DerivativeScheduleConvention,
    DerivativeScheduleRollCode,
    DerivativeScheduleStubCode,
    DerivativeSettlementStyle,
    DerivativeTermsId,
    FixedRateSwapLeg,
    FloatingRateSwapLeg,
    OptionExerciseStyle,
    OptionExerciseTerms,
    ReferenceReturnSwapLeg,
    SwapContractTerms,
)
from qore.infrastructure.fixed_income_economics import (
    BusinessCalendarRef,
    BusinessDayConventionCode,
    DayCountConventionCode,
    FinancialTenor,
    FinancialTenorUnit,
    FixedIncomeSpread,
    SettlementConvention,
)
from qore.infrastructure.rates_otc_semantics import (
    FraDiscountingCode,
    FraFixingDateOffset,
    FraTerms,
    RateCapFloorKind,
    RateCapFloorTerms,
    RatesOtcValidationError,
    RateStrikeSchedule,
    RateStrikeStep,
    SwaptionCashSettlementMethodCode,
    SwaptionPosition,
    SwaptionTerms,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId


def _uuid(value: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{value:012d}")


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _evidence(value: int) -> DerivativeEvidenceRef:
    return DerivativeEvidenceRef(_uuid(value))


def _tenor(months: int) -> FinancialTenor:
    return FinancialTenor(months, FinancialTenorUnit.MONTH)


def _calendar() -> BusinessCalendarRef:
    return BusinessCalendarRef("target")


def _business_day() -> BusinessDayConventionCode:
    return BusinessDayConventionCode("modified-following")


def _settlement() -> SettlementConvention:
    return SettlementConvention(2, _calendar(), _business_day())


def _fixing_convention() -> DerivativeFloatingRateConvention:
    return DerivativeFloatingRateConvention(
        calculation=DerivativeFloatingRateCalculationCode("simple"),
        fixing_calendar_ref=_calendar(),
        fixing_lag_business_days=2,
    )


def _fixing_offset(
    offset: int = 2,
    *,
    calendar: BusinessCalendarRef | None = None,
    convention: BusinessDayConventionCode | None = None,
) -> FraFixingDateOffset:
    return FraFixingDateOffset(
        business_days_offset=offset,
        fixing_calendar_ref=calendar or _calendar(),
        business_day_convention=convention or _business_day(),
    )


def _schedule_convention() -> DerivativeScheduleConvention:
    return DerivativeScheduleConvention(
        stub=DerivativeScheduleStubCode("short-final"),
        roll=DerivativeScheduleRollCode("day-1"),
        calendar_ref=_calendar(),
        business_day_convention=_business_day(),
    )


def _benchmark(*, include_tenor: bool = True) -> DerivativeBenchmarkReference:
    return DerivativeBenchmarkReference(
        reference_identity_id=_identity(10),
        role=DerivativeReferenceRoleCode("floating-rate"),
        tenor=_tenor(3) if include_tenor else None,
    )


def _notional(value: str = "1000000") -> DerivativeNotional:
    return DerivativeNotional(Decimal(value), _identity(20))


def _notional_schedule(
    start: date = date(2027, 1, 1),
) -> DerivativeNotionalSchedule:
    return DerivativeNotionalSchedule(
        (DerivativeNotionalStep(start, _notional()),)
    )


def _fra(
    *,
    calculation_start_date: date = date(2027, 3, 15),
    calculation_end_date: date = date(2027, 6, 15),
    payment_date: date = date(2027, 3, 15),
    fixed_rate: DerivativeContractRate | None = None,
    discounting: FraDiscountingCode | None = None,
    instrument_identity_id: EconomicIdentityId | None = None,
    benchmark: DerivativeBenchmarkReference | None = None,
    fixing_date_offset: FraFixingDateOffset | None = None,
) -> FraTerms:
    return FraTerms(
        terms_id=DerivativeTermsId(_uuid(100)),
        instrument_identity_id=instrument_identity_id or _identity(101),
        calculation_start_date=calculation_start_date,
        calculation_end_date=calculation_end_date,
        payment_date=payment_date,
        notional=_notional(),
        fixed_rate=fixed_rate or DerivativeContractRate(Decimal("0.045")),
        benchmark=benchmark or _benchmark(),
        day_count=DayCountConventionCode("act-360"),
        fixing_date_offset=fixing_date_offset or _fixing_offset(),
        discounting=discounting or FraDiscountingCode("isda"),
        evidence_ref=_evidence(102),
    )


def _strike_schedule(
    initial: str,
    *steps: tuple[date, str],
) -> RateStrikeSchedule:
    return RateStrikeSchedule(
        initial_rate=DerivativeContractRate(Decimal(initial)),
        steps=tuple(
            RateStrikeStep(step_date, DerivativeContractRate(Decimal(rate)))
            for step_date, rate in steps
        ),
    )


def _cap_floor(
    kind: RateCapFloorKind,
    *,
    cap: RateStrikeSchedule | None = None,
    floor: RateStrikeSchedule | None = None,
    effective: date = date(2027, 1, 1),
    termination: date = date(2030, 1, 1),
    spread: FixedIncomeSpread | None = None,
) -> RateCapFloorTerms:
    return RateCapFloorTerms(
        terms_id=DerivativeTermsId(_uuid(200)),
        instrument_identity_id=_identity(201),
        kind=kind,
        effective_date=effective,
        termination_date=termination,
        notional_schedule=_notional_schedule(effective),
        benchmark=_benchmark(),
        spread=spread,
        day_count=DayCountConventionCode("act-360"),
        payment_tenor=_tenor(3),
        reset_tenor=_tenor(3),
        fixing_convention=_fixing_convention(),
        schedule_convention=_schedule_convention(),
        settlement_convention=_settlement(),
        evidence_ref=_evidence(202),
        cap_strikes=cap,
        floor_strikes=floor,
    )


def _swap(
    *,
    fixed_direction: DerivativeLegDirection = DerivativeLegDirection.PAY,
    extra_reference_leg: bool = False,
) -> SwapContractTerms:
    effective = date(2027, 1, 1)
    floating_direction = (
        DerivativeLegDirection.RECEIVE
        if fixed_direction is DerivativeLegDirection.PAY
        else DerivativeLegDirection.PAY
    )
    fixed = FixedRateSwapLeg(
        leg_id=DerivativeLegId(_uuid(300)),
        ordinal=DerivativeLegOrdinal(1),
        direction=fixed_direction,
        notional_schedule=_notional_schedule(effective),
        rate=DerivativeContractRate(Decimal("0.04")),
        day_count=DayCountConventionCode("30-360"),
        payment_tenor=_tenor(6),
        schedule_convention=_schedule_convention(),
        settlement_convention=_settlement(),
        evidence_ref=_evidence(301),
    )
    floating = FloatingRateSwapLeg(
        leg_id=DerivativeLegId(_uuid(302)),
        ordinal=DerivativeLegOrdinal(2),
        direction=floating_direction,
        notional_schedule=_notional_schedule(effective),
        benchmark=_benchmark(),
        spread=FixedIncomeSpread(Decimal("0")),
        day_count=DayCountConventionCode("act-360"),
        payment_tenor=_tenor(3),
        reset_tenor=_tenor(3),
        fixing_convention=_fixing_convention(),
        schedule_convention=_schedule_convention(),
        settlement_convention=_settlement(),
        evidence_ref=_evidence(303),
    )
    legs: tuple[
        FixedRateSwapLeg | FloatingRateSwapLeg | ReferenceReturnSwapLeg,
        ...,
    ]
    if not extra_reference_leg:
        legs = (fixed, floating)
    else:
        reference = ReferenceReturnSwapLeg(
            leg_id=DerivativeLegId(_uuid(304)),
            ordinal=DerivativeLegOrdinal(3),
            direction=floating_direction,
            notional_schedule=_notional_schedule(effective),
            reference=_benchmark(),
            payment_tenor=_tenor(3),
            schedule_convention=_schedule_convention(),
            settlement_convention=_settlement(),
            evidence_ref=_evidence(305),
        )
        legs = (fixed, floating, reference)
    return SwapContractTerms(
        terms_id=DerivativeTermsId(_uuid(306)),
        instrument_identity_id=_identity(307),
        effective_date=effective,
        termination_date=date(2032, 1, 1),
        legs=legs,
        evidence_ref=_evidence(308),
    )


def _swaption(
    position: SwaptionPosition,
    *,
    swap: SwapContractTerms | None = None,
    settlement_style: DerivativeSettlementStyle = DerivativeSettlementStyle.PHYSICAL,
    cash_method: SwaptionCashSettlementMethodCode | None = None,
    expiry: date = date(2026, 12, 15),
) -> SwaptionTerms:
    underlying = swap or _swap(
        fixed_direction=(
            DerivativeLegDirection.PAY
            if position is SwaptionPosition.PAYER
            else DerivativeLegDirection.RECEIVE
        )
    )
    return SwaptionTerms(
        terms_id=DerivativeTermsId(_uuid(400)),
        instrument_identity_id=_identity(401),
        underlying_swap=underlying,
        position=position,
        expiry_date=expiry,
        exercise=OptionExerciseTerms(style=OptionExerciseStyle.EUROPEAN),
        settlement_style=settlement_style,
        evidence_ref=_evidence(402),
        cash_settlement_method=cash_method,
    )


def test_fra_preserves_distinct_calculation_period() -> None:
    terms = _fra()
    assert terms.calculation_start_date != terms.calculation_end_date
    assert terms.logical_values()[0] == "fra"


def test_fra_allows_payment_at_calculation_start() -> None:
    terms = _fra(payment_date=date(2027, 3, 15))
    assert terms.payment_date == terms.calculation_start_date


@pytest.mark.parametrize(
    "payment_date",
    (date(2027, 3, 14), date(2027, 6, 16)),
)
def test_fra_has_no_invented_payment_period_chronology(payment_date: date) -> None:
    terms = _fra(payment_date=payment_date)
    assert terms.payment_date == payment_date


def test_fra_rejects_non_increasing_calculation_period() -> None:
    with pytest.raises(RatesOtcValidationError, match="must be after"):
        _fra(
            calculation_start_date=date(2027, 6, 15),
            calculation_end_date=date(2027, 6, 15),
        )


def test_fra_strict_date_rejects_datetime() -> None:
    with pytest.raises(RatesOtcValidationError, match="must be date"):
        _fra(
            calculation_start_date=cast(
                date,
                datetime(2027, 3, 15),
            )
        )


def test_fra_discounting_is_explicit_logical_material() -> None:
    isda = _fra(discounting=FraDiscountingCode("isda"))
    none = _fra(discounting=FraDiscountingCode("none"))
    assert isda.logical_values() != none.logical_values()


def test_fra_discounting_remains_required() -> None:
    with pytest.raises(RatesOtcValidationError, match="discounting"):
        replace(_fra(), discounting=cast(FraDiscountingCode, None))


def test_fra_fixed_rate_is_contractual_and_distinct() -> None:
    left = _fra(fixed_rate=DerivativeContractRate(Decimal("0.04")))
    right = _fra(fixed_rate=DerivativeContractRate(Decimal("0.05")))
    assert left.logical_values() != right.logical_values()


def test_fra_rejects_instrument_equal_to_benchmark_identity() -> None:
    with pytest.raises(RatesOtcValidationError, match="benchmark"):
        _fra(instrument_identity_id=_benchmark().reference_identity_id)


def test_fra_requires_exactly_one_benchmark_tenor() -> None:
    with pytest.raises(RatesOtcValidationError, match="exactly one benchmark tenor"):
        _fra(benchmark=_benchmark(include_tenor=False))


def test_fra_accepts_one_benchmark_tenor() -> None:
    terms = _fra(benchmark=_benchmark(include_tenor=True))
    assert terms.benchmark.tenor is not None


def test_fra_fixing_offset_accepts_negative_zero_positive() -> None:
    assert _fixing_offset(-2).business_days_offset == -2
    assert _fixing_offset(0).business_days_offset == 0
    assert _fixing_offset(2).business_days_offset == 2


def test_fra_fixing_offset_rejects_bool_float_decimal_string() -> None:
    for value in (
        True,
        1.0,
        Decimal("2"),
        "2",
    ):
        with pytest.raises(RatesOtcValidationError, match="exact int"):
            FraFixingDateOffset(
                business_days_offset=cast(int, value),
                fixing_calendar_ref=_calendar(),
                business_day_convention=_business_day(),
            )


def test_fra_fixing_offset_rejects_invalid_calendar_type() -> None:
    with pytest.raises(RatesOtcValidationError, match="calendar ref"):
        FraFixingDateOffset(
            business_days_offset=2,
            fixing_calendar_ref=cast(BusinessCalendarRef, object()),
            business_day_convention=_business_day(),
        )


def test_fra_fixing_offset_rejects_invalid_business_day_convention_type() -> None:
    with pytest.raises(RatesOtcValidationError, match="business day convention"):
        FraFixingDateOffset(
            business_days_offset=2,
            fixing_calendar_ref=_calendar(),
            business_day_convention=cast(BusinessDayConventionCode, object()),
        )


def test_fra_fixing_offset_logical_sensitivity() -> None:
    a = _fixing_offset(-2)
    b = _fixing_offset(2)
    c = _fixing_offset(2, calendar=BusinessCalendarRef("other"))
    d = _fixing_offset(
        2,
        convention=BusinessDayConventionCode("preceding"),
    )
    assert len(
        {a.logical_values(), b.logical_values(), c.logical_values(), d.logical_values()}
    ) == 4


def test_fra_retains_fixing_date_offset_logical_material() -> None:
    offset = _fixing_offset(2)
    terms = _fra(fixing_date_offset=offset)
    assert offset.logical_values() in terms.logical_values()


def test_rate_strike_schedule_canonicalizes_step_order() -> None:
    left = _strike_schedule(
        "0.05",
        (date(2028, 1, 1), "0.055"),
        (date(2027, 7, 1), "0.052"),
    )
    right = _strike_schedule(
        "0.05",
        (date(2027, 7, 1), "0.052"),
        (date(2028, 1, 1), "0.055"),
    )
    assert left.logical_values() == right.logical_values()


def test_rate_strike_schedule_rejects_duplicate_dates() -> None:
    with pytest.raises(RatesOtcValidationError, match="unique"):
        _strike_schedule(
            "0.05",
            (date(2027, 7, 1), "0.052"),
            (date(2027, 7, 1), "0.053"),
        )


def test_cap_requires_cap_schedule_only() -> None:
    cap = _strike_schedule("0.05")
    terms = _cap_floor(RateCapFloorKind.CAP, cap=cap)
    assert terms.cap_strikes is cap
    with pytest.raises(RatesOtcValidationError, match="CAP requires"):
        _cap_floor(
            RateCapFloorKind.CAP,
            cap=cap,
            floor=_strike_schedule("0.02"),
        )


def test_floor_requires_floor_schedule_only() -> None:
    floor = _strike_schedule("0.02")
    terms = _cap_floor(RateCapFloorKind.FLOOR, floor=floor)
    assert terms.floor_strikes is floor
    with pytest.raises(RatesOtcValidationError, match="FLOOR requires"):
        _cap_floor(RateCapFloorKind.FLOOR, cap=_strike_schedule("0.05"))


def test_collar_requires_both_strike_schedules() -> None:
    with pytest.raises(RatesOtcValidationError, match="COLLAR requires"):
        _cap_floor(RateCapFloorKind.COLLAR, cap=_strike_schedule("0.05"))
    terms = _cap_floor(
        RateCapFloorKind.COLLAR,
        cap=_strike_schedule("0.05"),
        floor=_strike_schedule("0.02"),
    )
    assert terms.cap_strikes is not None
    assert terms.floor_strikes is not None


def test_cap_floor_and_collar_are_distinct_logical_material() -> None:
    cap = _cap_floor(RateCapFloorKind.CAP, cap=_strike_schedule("0.05"))
    floor = _cap_floor(RateCapFloorKind.FLOOR, floor=_strike_schedule("0.02"))
    collar = _cap_floor(
        RateCapFloorKind.COLLAR,
        cap=_strike_schedule("0.05"),
        floor=_strike_schedule("0.02"),
    )
    assert len(
        {cap.logical_values(), floor.logical_values(), collar.logical_values()}
    ) == 3


def test_cap_floor_strike_step_must_be_inside_product_term() -> None:
    with pytest.raises(RatesOtcValidationError, match="within product term"):
        _cap_floor(
            RateCapFloorKind.CAP,
            cap=_strike_schedule(
                "0.05",
                (date(2030, 1, 1), "0.06"),
            ),
        )


def test_cap_floor_notional_must_start_at_effective_date() -> None:
    with pytest.raises(RatesOtcValidationError, match="notional must start"):
        RateCapFloorTerms(
            terms_id=DerivativeTermsId(_uuid(200)),
            instrument_identity_id=_identity(201),
            kind=RateCapFloorKind.CAP,
            effective_date=date(2027, 1, 1),
            termination_date=date(2030, 1, 1),
            notional_schedule=_notional_schedule(date(2027, 2, 1)),
            benchmark=_benchmark(),
            spread=FixedIncomeSpread(Decimal("0")),
            day_count=DayCountConventionCode("act-360"),
            payment_tenor=_tenor(3),
            reset_tenor=_tenor(3),
            fixing_convention=_fixing_convention(),
            schedule_convention=_schedule_convention(),
            settlement_convention=_settlement(),
            evidence_ref=_evidence(202),
            cap_strikes=_strike_schedule("0.05"),
        )


def test_cap_floor_benchmark_is_static_reference_not_current_rate() -> None:
    terms = _cap_floor(RateCapFloorKind.CAP, cap=_strike_schedule("0.05"))
    assert terms.benchmark == _benchmark()
    assert "current_rate" not in RateCapFloorTerms.__dataclass_fields__


def test_cap_floor_spread_optional_none_accepted() -> None:
    terms = _cap_floor(
        RateCapFloorKind.CAP,
        cap=_strike_schedule("0.05"),
        spread=None,
    )
    assert terms.spread is None


def test_cap_floor_spread_explicit_zero_accepted() -> None:
    terms = _cap_floor(
        RateCapFloorKind.CAP,
        cap=_strike_schedule("0.05"),
        spread=FixedIncomeSpread(Decimal("0")),
    )
    assert terms.spread is not None


def test_cap_floor_spread_negative_and_positive_explicit_accepted() -> None:
    for value in (Decimal("-0.01"), Decimal("0.01")):
        terms = _cap_floor(
            RateCapFloorKind.CAP,
            cap=_strike_schedule("0.05"),
            spread=FixedIncomeSpread(value),
        )
        assert terms.spread is not None


def test_cap_floor_spread_none_vs_explicit_zero_distinct() -> None:
    none_terms = _cap_floor(
        RateCapFloorKind.CAP,
        cap=_strike_schedule("0.05"),
        spread=None,
    )
    zero_terms = _cap_floor(
        RateCapFloorKind.CAP,
        cap=_strike_schedule("0.05"),
        spread=FixedIncomeSpread(Decimal("0")),
    )
    assert none_terms.logical_values() != zero_terms.logical_values()


def test_cap_floor_different_explicit_spreads_distinct() -> None:
    a = _cap_floor(
        RateCapFloorKind.CAP,
        cap=_strike_schedule("0.05"),
        spread=FixedIncomeSpread(Decimal("0")),
    )
    b = _cap_floor(
        RateCapFloorKind.CAP,
        cap=_strike_schedule("0.05"),
        spread=FixedIncomeSpread(Decimal("0.01")),
    )
    assert a.logical_values() != b.logical_values()


def test_cap_floor_invalid_spread_type_rejected() -> None:
    with pytest.raises(RatesOtcValidationError, match="spread"):
        _cap_floor(
            RateCapFloorKind.CAP,
            cap=_strike_schedule("0.05"),
            spread=cast(FixedIncomeSpread, object()),
        )


def test_valid_payer_swaption_binds_exact_underlying_swap() -> None:
    underlying = _swap(fixed_direction=DerivativeLegDirection.PAY)
    terms = _swaption(SwaptionPosition.PAYER, swap=underlying)
    assert terms.underlying_swap is underlying
    assert terms.logical_values()[0] == "swaption"


def test_valid_receiver_swaption_binds_exact_underlying_swap() -> None:
    underlying = _swap(fixed_direction=DerivativeLegDirection.RECEIVE)
    terms = _swaption(SwaptionPosition.RECEIVER, swap=underlying)
    assert terms.underlying_swap is underlying


def test_payer_and_receiver_are_distinct_logical_material() -> None:
    payer = _swaption(SwaptionPosition.PAYER)
    receiver = _swaption(SwaptionPosition.RECEIVER)
    assert payer.logical_values() != receiver.logical_values()


def test_payer_swaption_rejects_receiver_underlying_direction() -> None:
    underlying = _swap(fixed_direction=DerivativeLegDirection.RECEIVE)
    with pytest.raises(RatesOtcValidationError, match="payer swaption"):
        _swaption(SwaptionPosition.PAYER, swap=underlying)


def test_receiver_swaption_rejects_payer_underlying_direction() -> None:
    underlying = _swap(fixed_direction=DerivativeLegDirection.PAY)
    with pytest.raises(RatesOtcValidationError, match="receiver swaption"):
        _swaption(SwaptionPosition.RECEIVER, swap=underlying)


def test_bounded_swaption_rejects_non_vanilla_underlying_leg_set() -> None:
    underlying = _swap(
        fixed_direction=DerivativeLegDirection.PAY,
        extra_reference_leg=True,
    )
    with pytest.raises(RatesOtcValidationError, match="exactly two"):
        _swaption(SwaptionPosition.PAYER, swap=underlying)


def test_swaption_expiry_must_not_follow_underlying_effective_date() -> None:
    with pytest.raises(RatesOtcValidationError, match="effective_date"):
        _swaption(SwaptionPosition.PAYER, expiry=date(2027, 1, 2))


def test_cash_swaption_accepts_none_cash_settlement_method() -> None:
    terms = _swaption(
        SwaptionPosition.PAYER,
        settlement_style=DerivativeSettlementStyle.CASH,
        cash_method=None,
    )
    assert terms.cash_settlement_method is None


def test_cash_swaption_accepts_explicit_cash_settlement_method() -> None:
    method = SwaptionCashSettlementMethodCode("collateralized-cash-price")
    terms = _swaption(
        SwaptionPosition.PAYER,
        settlement_style=DerivativeSettlementStyle.CASH,
        cash_method=method,
    )
    assert terms.cash_settlement_method is method


def test_cash_swaption_method_none_vs_explicit_distinct() -> None:
    none_terms = _swaption(
        SwaptionPosition.PAYER,
        settlement_style=DerivativeSettlementStyle.CASH,
        cash_method=None,
    )
    method_terms = _swaption(
        SwaptionPosition.PAYER,
        settlement_style=DerivativeSettlementStyle.CASH,
        cash_method=SwaptionCashSettlementMethodCode("cash-price"),
    )
    assert none_terms.logical_values() != method_terms.logical_values()


def test_cash_and_physical_swaption_remain_distinct_with_none_method() -> None:
    cash_terms = _swaption(
        SwaptionPosition.PAYER,
        settlement_style=DerivativeSettlementStyle.CASH,
        cash_method=None,
    )
    physical_terms = _swaption(
        SwaptionPosition.PAYER,
        settlement_style=DerivativeSettlementStyle.PHYSICAL,
        cash_method=None,
    )
    assert cash_terms.logical_values() != physical_terms.logical_values()


def test_physical_swaption_forbids_cash_settlement_method() -> None:
    with pytest.raises(RatesOtcValidationError, match="must not carry"):
        _swaption(
            SwaptionPosition.PAYER,
            settlement_style=DerivativeSettlementStyle.PHYSICAL,
            cash_method=SwaptionCashSettlementMethodCode("cash-price"),
        )


def test_swaption_instrument_must_differ_from_underlying_swap_identity() -> None:
    underlying = _swap()
    with pytest.raises(RatesOtcValidationError, match="must differ"):
        SwaptionTerms(
            terms_id=DerivativeTermsId(_uuid(400)),
            instrument_identity_id=underlying.instrument_identity_id,
            underlying_swap=underlying,
            position=SwaptionPosition.PAYER,
            expiry_date=date(2026, 12, 15),
            exercise=OptionExerciseTerms(style=OptionExerciseStyle.EUROPEAN),
            settlement_style=DerivativeSettlementStyle.PHYSICAL,
            evidence_ref=_evidence(402),
        )


def test_swaption_bermudan_date_must_not_follow_expiry() -> None:
    underlying = _swap()
    with pytest.raises(RatesOtcValidationError, match="Bermudan"):
        SwaptionTerms(
            terms_id=DerivativeTermsId(_uuid(400)),
            instrument_identity_id=_identity(401),
            underlying_swap=underlying,
            position=SwaptionPosition.PAYER,
            expiry_date=date(2026, 12, 15),
            exercise=OptionExerciseTerms(
                style=OptionExerciseStyle.BERMUDAN,
                bermudan_dates=(date(2026, 12, 16),),
            ),
            settlement_style=DerivativeSettlementStyle.PHYSICAL,
            evidence_ref=_evidence(402),
        )


def test_bounded_rates_products_expose_no_premium_fields() -> None:
    for contract_type in (FraTerms, RateCapFloorTerms, SwaptionTerms):
        assert not any(
            "premium" in field_name
            for field_name in contract_type.__dataclass_fields__
        )


def test_codes_require_canonical_lowercase_syntax() -> None:
    with pytest.raises(RatesOtcValidationError):
        FraDiscountingCode("ISDA Discounting")
    with pytest.raises(RatesOtcValidationError):
        SwaptionCashSettlementMethodCode("Cash Price")


def test_values_are_frozen_and_slotted() -> None:
    value = FraDiscountingCode("isda")
    with pytest.raises(FrozenInstanceError):
        value.__setattr__("value", "none")
    assert not hasattr(value, "__dict__")


def test_static_terms_have_no_operational_methods() -> None:
    prohibited = {
        "execute",
        "submit",
        "settle",
        "price",
        "calculate",
        "discount",
        "fetch",
        "observe",
        "exercise_now",
    }
    for contract_type in (FraTerms, RateCapFloorTerms, SwaptionTerms):
        assert prohibited.isdisjoint(contract_type.__dict__)


def test_rate_strike_type_guards_are_direct() -> None:
    with pytest.raises(RatesOtcValidationError, match="step rate"):
        RateStrikeStep(
            date(2027, 7, 1),
            cast(DerivativeContractRate, object()),
        )
    with pytest.raises(RatesOtcValidationError, match="initial_rate"):
        RateStrikeSchedule(cast(DerivativeContractRate, object()))
    with pytest.raises(RatesOtcValidationError, match="steps must be tuple"):
        RateStrikeSchedule(
            DerivativeContractRate(Decimal("0.05")),
            cast(tuple[RateStrikeStep, ...], []),
        )
    with pytest.raises(RatesOtcValidationError, match="contain RateStrikeStep"):
        RateStrikeSchedule(
            DerivativeContractRate(Decimal("0.05")),
            (cast(RateStrikeStep, object()),),
        )


def test_fra_structural_type_guards_are_direct() -> None:
    valid = _fra()
    with pytest.raises(RatesOtcValidationError, match="terms_id"):
        replace(valid, terms_id=cast(DerivativeTermsId, object()))
    with pytest.raises(RatesOtcValidationError, match="instrument identity"):
        replace(
            valid,
            instrument_identity_id=cast(EconomicIdentityId, object()),
        )
    with pytest.raises(RatesOtcValidationError, match="notional"):
        replace(valid, notional=cast(DerivativeNotional, object()))
    with pytest.raises(RatesOtcValidationError, match="fixed_rate"):
        replace(valid, fixed_rate=cast(DerivativeContractRate, object()))
    with pytest.raises(RatesOtcValidationError, match="benchmark must"):
        replace(valid, benchmark=cast(DerivativeBenchmarkReference, object()))
    with pytest.raises(RatesOtcValidationError, match="day_count"):
        replace(valid, day_count=cast(DayCountConventionCode, object()))
    with pytest.raises(RatesOtcValidationError, match="fixing_date_offset"):
        replace(valid, fixing_date_offset=cast(FraFixingDateOffset, object()))
    with pytest.raises(RatesOtcValidationError, match="evidence_ref"):
        replace(valid, evidence_ref=cast(DerivativeEvidenceRef, object()))


def test_cap_floor_structural_type_and_chronology_guards_are_direct() -> None:
    valid = _cap_floor(RateCapFloorKind.CAP, cap=_strike_schedule("0.05"))
    with pytest.raises(RatesOtcValidationError, match="terms_id"):
        replace(valid, terms_id=cast(DerivativeTermsId, object()))
    with pytest.raises(RatesOtcValidationError, match="instrument identity"):
        replace(
            valid,
            instrument_identity_id=cast(EconomicIdentityId, object()),
        )
    with pytest.raises(RatesOtcValidationError, match="kind"):
        replace(valid, kind=cast(RateCapFloorKind, "cap"))
    with pytest.raises(RatesOtcValidationError, match="termination_date"):
        replace(valid, termination_date=valid.effective_date)
    with pytest.raises(RatesOtcValidationError, match="notional_schedule"):
        replace(
            valid,
            notional_schedule=cast(DerivativeNotionalSchedule, object()),
        )

    later_change = DerivativeNotionalSchedule(
        (
            DerivativeNotionalStep(valid.effective_date, _notional()),
            DerivativeNotionalStep(valid.termination_date, _notional("900000")),
        )
    )
    with pytest.raises(RatesOtcValidationError, match="changes must precede"):
        replace(valid, notional_schedule=later_change)
    with pytest.raises(RatesOtcValidationError, match="benchmark must"):
        replace(valid, benchmark=cast(DerivativeBenchmarkReference, object()))
    with pytest.raises(RatesOtcValidationError, match="benchmark identity"):
        replace(
            valid,
            benchmark=replace(
                valid.benchmark,
                reference_identity_id=valid.instrument_identity_id,
            ),
        )
    with pytest.raises(RatesOtcValidationError, match="day_count"):
        replace(valid, day_count=cast(DayCountConventionCode, object()))
    with pytest.raises(RatesOtcValidationError, match="payment_tenor"):
        replace(valid, payment_tenor=cast(FinancialTenor, object()))
    with pytest.raises(RatesOtcValidationError, match="reset_tenor"):
        replace(valid, reset_tenor=cast(FinancialTenor, object()))
    with pytest.raises(RatesOtcValidationError, match="fixing_convention"):
        replace(
            valid,
            fixing_convention=cast(DerivativeFloatingRateConvention, object()),
        )
    with pytest.raises(RatesOtcValidationError, match="schedule_convention"):
        replace(
            valid,
            schedule_convention=cast(DerivativeScheduleConvention, object()),
        )
    with pytest.raises(RatesOtcValidationError, match="settlement_convention"):
        replace(
            valid,
            settlement_convention=cast(SettlementConvention, object()),
        )
    with pytest.raises(RatesOtcValidationError, match="evidence_ref"):
        replace(valid, evidence_ref=cast(DerivativeEvidenceRef, object()))
    with pytest.raises(RatesOtcValidationError, match="cap_strikes"):
        replace(valid, cap_strikes=cast(RateStrikeSchedule, object()))

    floor_valid = _cap_floor(
        RateCapFloorKind.FLOOR,
        floor=_strike_schedule("0.02"),
    )
    with pytest.raises(RatesOtcValidationError, match="floor_strikes"):
        replace(floor_valid, floor_strikes=cast(RateStrikeSchedule, object()))


def test_swaption_structural_type_and_exercise_guards_are_direct() -> None:
    valid = _swaption(SwaptionPosition.PAYER)
    with pytest.raises(RatesOtcValidationError, match="terms_id"):
        replace(valid, terms_id=cast(DerivativeTermsId, object()))
    with pytest.raises(RatesOtcValidationError, match="instrument identity"):
        replace(
            valid,
            instrument_identity_id=cast(EconomicIdentityId, object()),
        )
    with pytest.raises(RatesOtcValidationError, match="underlying_swap"):
        replace(valid, underlying_swap=cast(SwapContractTerms, object()))
    with pytest.raises(RatesOtcValidationError, match="position"):
        replace(valid, position=cast(SwaptionPosition, "payer"))
    with pytest.raises(RatesOtcValidationError, match="exercise must"):
        replace(valid, exercise=cast(OptionExerciseTerms, object()))

    american = OptionExerciseTerms(
        style=OptionExerciseStyle.AMERICAN,
        american_start_date=date(2026, 12, 16),
    )
    with pytest.raises(RatesOtcValidationError, match="American exercise start"):
        replace(valid, exercise=american)
    with pytest.raises(RatesOtcValidationError, match="settlement_style"):
        replace(
            valid,
            settlement_style=cast(DerivativeSettlementStyle, "physical"),
        )
    with pytest.raises(RatesOtcValidationError, match="cash settlement method"):
        replace(
            valid,
            cash_settlement_method=cast(
                SwaptionCashSettlementMethodCode,
                object(),
            ),
        )
    with pytest.raises(RatesOtcValidationError, match="evidence_ref"):
        replace(valid, evidence_ref=cast(DerivativeEvidenceRef, object()))


def test_swaption_bounded_underlying_requires_one_fixed_and_one_floating() -> None:
    underlying = _swap()
    first_fixed = cast(FixedRateSwapLeg, underlying.legs[0])
    second_fixed = replace(
        first_fixed,
        leg_id=DerivativeLegId(_uuid(309)),
        ordinal=DerivativeLegOrdinal(2),
        direction=DerivativeLegDirection.RECEIVE,
    )
    two_fixed = replace(underlying, legs=(first_fixed, second_fixed))
    with pytest.raises(RatesOtcValidationError, match="one fixed and one floating"):
        _swaption(SwaptionPosition.PAYER, swap=two_fixed)
