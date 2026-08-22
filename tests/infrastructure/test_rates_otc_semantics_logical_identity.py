from __future__ import annotations

from dataclasses import fields
from datetime import date
from decimal import Decimal
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


def _calendar(code: str = "target") -> BusinessCalendarRef:
    return BusinessCalendarRef(code)


def _business_day(code: str = "modified-following") -> BusinessDayConventionCode:
    return BusinessDayConventionCode(code)


def _settlement() -> SettlementConvention:
    return SettlementConvention(2, _calendar(), _business_day())


def _fixing_convention() -> DerivativeFloatingRateConvention:
    return DerivativeFloatingRateConvention(
        calculation=DerivativeFloatingRateCalculationCode("simple"),
        fixing_calendar_ref=_calendar(),
        fixing_lag_business_days=2,
    )


def _schedule_convention() -> DerivativeScheduleConvention:
    return DerivativeScheduleConvention(
        stub=DerivativeScheduleStubCode("short-final"),
        roll=DerivativeScheduleRollCode("day-1"),
        calendar_ref=_calendar(),
        business_day_convention=_business_day(),
    )


def _benchmark(identity_value: int = 10) -> DerivativeBenchmarkReference:
    return DerivativeBenchmarkReference(
        reference_identity_id=_identity(identity_value),
        role=DerivativeReferenceRoleCode("floating-rate"),
        tenor=_tenor(3),
    )


def _notional(value: str = "1000000") -> DerivativeNotional:
    return DerivativeNotional(Decimal(value), _identity(20))


def _notional_schedule(start: date) -> DerivativeNotionalSchedule:
    return DerivativeNotionalSchedule(
        (DerivativeNotionalStep(start, _notional()),)
    )


def _strike_schedule(initial: str) -> RateStrikeSchedule:
    return RateStrikeSchedule(
        initial_rate=DerivativeContractRate(Decimal(initial)),
        steps=(
            RateStrikeStep(
                date(2028, 1, 1),
                DerivativeContractRate(Decimal(initial) + Decimal("0.001")),
            ),
        ),
    )


def _fra_terms() -> FraTerms:
    return FraTerms(
        terms_id=DerivativeTermsId(_uuid(100)),
        instrument_identity_id=_identity(101),
        calculation_start_date=date(2027, 3, 15),
        calculation_end_date=date(2027, 6, 15),
        payment_date=date(2027, 3, 15),
        notional=_notional(),
        fixed_rate=DerivativeContractRate(Decimal("0.045")),
        benchmark=_benchmark(),
        day_count=DayCountConventionCode("act-360"),
        fixing_date_offset=FraFixingDateOffset(
            business_days_offset=2,
            fixing_calendar_ref=_calendar(),
            business_day_convention=_business_day(),
        ),
        discounting=FraDiscountingCode("isda"),
        evidence_ref=_evidence(102),
    )


def _cap_floor_terms(
    *,
    kind: RateCapFloorKind = RateCapFloorKind.COLLAR,
    cap: RateStrikeSchedule | None = None,
    floor: RateStrikeSchedule | None = None,
) -> RateCapFloorTerms:
    effective = date(2027, 1, 1)
    if kind is RateCapFloorKind.CAP:
        cap = cap or _strike_schedule("0.05")
        floor = None
    elif kind is RateCapFloorKind.FLOOR:
        cap = None
        floor = floor or _strike_schedule("0.02")
    else:
        cap = cap or _strike_schedule("0.05")
        floor = floor or _strike_schedule("0.02")
    return RateCapFloorTerms(
        terms_id=DerivativeTermsId(_uuid(200)),
        instrument_identity_id=_identity(201),
        kind=kind,
        effective_date=effective,
        termination_date=date(2030, 1, 1),
        notional_schedule=_notional_schedule(effective),
        benchmark=_benchmark(),
        spread=FixedIncomeSpread(Decimal("0.001")),
        day_count=DayCountConventionCode("act-360"),
        payment_tenor=_tenor(3),
        reset_tenor=_tenor(6),
        fixing_convention=_fixing_convention(),
        schedule_convention=_schedule_convention(),
        settlement_convention=_settlement(),
        evidence_ref=_evidence(202),
        cap_strikes=cap,
        floor_strikes=floor,
    )


def _underlying_swap(position: SwaptionPosition) -> SwapContractTerms:
    effective = date(2027, 1, 1)
    fixed_direction = (
        DerivativeLegDirection.PAY
        if position is SwaptionPosition.PAYER
        else DerivativeLegDirection.RECEIVE
    )
    floating_direction = (
        DerivativeLegDirection.RECEIVE
        if position is SwaptionPosition.PAYER
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
    return SwapContractTerms(
        terms_id=DerivativeTermsId(_uuid(306)),
        instrument_identity_id=_identity(307),
        effective_date=effective,
        termination_date=date(2032, 1, 1),
        legs=(fixed, floating),
        evidence_ref=_evidence(308),
    )


def _swaption_terms(position: SwaptionPosition = SwaptionPosition.PAYER) -> SwaptionTerms:
    return SwaptionTerms(
        terms_id=DerivativeTermsId(_uuid(400)),
        instrument_identity_id=_identity(401),
        underlying_swap=_underlying_swap(position),
        position=position,
        expiry_date=date(2026, 12, 15),
        exercise=OptionExerciseTerms(
            style=OptionExerciseStyle.BERMUDAN,
            bermudan_dates=(date(2026, 12, 10),),
        ),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_evidence(402),
        cash_settlement_method=SwaptionCashSettlementMethodCode("cash-price"),
    )


def _canonical_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


def _identity_expected(value: EconomicIdentityId) -> tuple[str, ...]:
    return (str(value.value),)


def _terms_id_expected(value: DerivativeTermsId) -> tuple[str, ...]:
    return (str(value.value),)


def _leg_id_expected(value: DerivativeLegId) -> tuple[str, ...]:
    return (str(value.value),)


def _evidence_expected(value: DerivativeEvidenceRef) -> tuple[str, ...]:
    return (str(value.value),)


def _tenor_expected(value: FinancialTenor) -> tuple[object, ...]:
    return (value.value, value.unit.value)


def _notional_expected(value: DerivativeNotional) -> tuple[object, ...]:
    return (
        _canonical_decimal(value.value),
        _identity_expected(value.unit_identity_id),
    )


def _notional_schedule_expected(
    value: DerivativeNotionalSchedule,
) -> tuple[object, ...]:
    return (
        tuple(
            (
                step.effective_date.isoformat(),
                _notional_expected(step.notional),
            )
            for step in value.steps
        ),
    )


def _rate_expected(value: DerivativeContractRate) -> tuple[str, ...]:
    return (_canonical_decimal(value.value),)


def _spread_expected(value: FixedIncomeSpread) -> tuple[str, ...]:
    return (_canonical_decimal(value.value),)


def _benchmark_expected(value: DerivativeBenchmarkReference) -> tuple[object, ...]:
    return (
        _identity_expected(value.reference_identity_id),
        (value.role.value,),
        _tenor_expected(value.tenor) if value.tenor is not None else None,
    )


def _fixing_convention_expected(
    value: DerivativeFloatingRateConvention,
) -> tuple[object, ...]:
    return (
        (value.calculation.value,),
        (value.fixing_calendar_ref.value,),
        value.fixing_lag_business_days,
        value.lockout_business_days,
        value.observation_shift,
    )


def _schedule_convention_expected(
    value: DerivativeScheduleConvention,
) -> tuple[object, ...]:
    return (
        (value.stub.value,),
        (value.roll.value,),
        (value.calendar_ref.value,),
        (value.business_day_convention.value,),
    )


def _settlement_expected(value: SettlementConvention) -> tuple[object, ...]:
    return (
        value.business_day_lag,
        (value.calendar_ref.value,),
        (value.business_day_convention.value,),
    )


def _fixing_offset_expected(value: FraFixingDateOffset) -> tuple[object, ...]:
    return (
        str(value.business_days_offset),
        (value.fixing_calendar_ref.value,),
        (value.business_day_convention.value,),
    )


def _strike_schedule_expected(value: RateStrikeSchedule) -> tuple[object, ...]:
    return (
        _rate_expected(value.initial_rate),
        tuple(
            (
                step.effective_date.isoformat(),
                _rate_expected(step.rate),
            )
            for step in value.steps
        ),
    )


def _exercise_expected(value: OptionExerciseTerms) -> tuple[object, ...]:
    return (
        value.style.value,
        value.american_start_date.isoformat()
        if value.american_start_date is not None
        else None,
        tuple(item.isoformat() for item in value.bermudan_dates),
    )


def _fixed_leg_expected(value: FixedRateSwapLeg) -> tuple[object, ...]:
    return (
        "fixed-rate",
        _leg_id_expected(value.leg_id),
        (value.ordinal.value,),
        value.direction.value,
        _notional_schedule_expected(value.notional_schedule),
        _rate_expected(value.rate),
        (value.day_count.value,),
        _tenor_expected(value.payment_tenor),
        _settlement_expected(value.settlement_convention),
        _schedule_convention_expected(value.schedule_convention),
        _evidence_expected(value.evidence_ref),
    )


def _floating_leg_expected(value: FloatingRateSwapLeg) -> tuple[object, ...]:
    return (
        "floating-rate",
        _leg_id_expected(value.leg_id),
        (value.ordinal.value,),
        value.direction.value,
        _notional_schedule_expected(value.notional_schedule),
        _benchmark_expected(value.benchmark),
        _spread_expected(value.spread),
        (value.day_count.value,),
        _tenor_expected(value.payment_tenor),
        _tenor_expected(value.reset_tenor),
        _fixing_convention_expected(value.fixing_convention),
        _settlement_expected(value.settlement_convention),
        _schedule_convention_expected(value.schedule_convention),
        _evidence_expected(value.evidence_ref),
    )


def _swap_expected(value: SwapContractTerms) -> tuple[object, ...]:
    legs: list[tuple[object, ...]] = []
    for leg in value.legs:
        if isinstance(leg, FixedRateSwapLeg):
            legs.append(_fixed_leg_expected(leg))
        elif isinstance(leg, FloatingRateSwapLeg):
            legs.append(_floating_leg_expected(leg))
        else:
            raise AssertionError("bounded swaption fixture must use fixed/floating legs")
    return (
        "swap",
        _terms_id_expected(value.terms_id),
        _identity_expected(value.instrument_identity_id),
        value.effective_date.isoformat(),
        value.termination_date.isoformat(),
        tuple(legs),
        _evidence_expected(value.evidence_ref),
    )


def test_fra_logical_values_projects_every_contract_field_independently() -> None:
    terms = _fra_terms()
    assert terms.logical_values() == (
        "fra",
        _terms_id_expected(terms.terms_id),
        _identity_expected(terms.instrument_identity_id),
        terms.calculation_start_date.isoformat(),
        terms.calculation_end_date.isoformat(),
        terms.payment_date.isoformat(),
        _notional_expected(terms.notional),
        _rate_expected(terms.fixed_rate),
        _benchmark_expected(terms.benchmark),
        (terms.day_count.value,),
        _fixing_offset_expected(terms.fixing_date_offset),
        (terms.discounting.value,),
        _evidence_expected(terms.evidence_ref),
    )


def test_cap_floor_logical_values_projects_every_contract_field_independently() -> None:
    terms = _cap_floor_terms()
    assert terms.cap_strikes is not None
    assert terms.floor_strikes is not None
    assert terms.spread is not None
    assert terms.logical_values() == (
        "rate-cap-floor",
        _terms_id_expected(terms.terms_id),
        _identity_expected(terms.instrument_identity_id),
        terms.kind.value,
        terms.effective_date.isoformat(),
        terms.termination_date.isoformat(),
        _notional_schedule_expected(terms.notional_schedule),
        _benchmark_expected(terms.benchmark),
        _spread_expected(terms.spread),
        (terms.day_count.value,),
        _tenor_expected(terms.payment_tenor),
        _tenor_expected(terms.reset_tenor),
        _fixing_convention_expected(terms.fixing_convention),
        _schedule_convention_expected(terms.schedule_convention),
        _settlement_expected(terms.settlement_convention),
        _strike_schedule_expected(terms.cap_strikes),
        _strike_schedule_expected(terms.floor_strikes),
        _evidence_expected(terms.evidence_ref),
    )


def test_floor_strike_payload_is_distinct_logical_material() -> None:
    two_percent = _cap_floor_terms(
        kind=RateCapFloorKind.FLOOR,
        floor=_strike_schedule("0.02"),
    )
    three_percent = _cap_floor_terms(
        kind=RateCapFloorKind.FLOOR,
        floor=_strike_schedule("0.03"),
    )
    assert two_percent.logical_values() != three_percent.logical_values()


@pytest.mark.parametrize(
    ("position", "expected_position"),
    (
        (SwaptionPosition.PAYER, "payer"),
        (SwaptionPosition.RECEIVER, "receiver"),
    ),
)
def test_swaption_logical_values_projects_every_contract_field_independently(
    position: SwaptionPosition,
    expected_position: str,
) -> None:
    terms = _swaption_terms(position)
    assert terms.cash_settlement_method is not None
    assert terms.logical_values() == (
        "swaption",
        _terms_id_expected(terms.terms_id),
        _identity_expected(terms.instrument_identity_id),
        _swap_expected(terms.underlying_swap),
        expected_position,
        terms.expiry_date.isoformat(),
        _exercise_expected(terms.exercise),
        terms.settlement_style.value,
        (terms.cash_settlement_method.value,),
        _evidence_expected(terms.evidence_ref),
    )


def test_gatec_exact_contract_field_surfaces_are_closed() -> None:
    assert tuple(item.name for item in fields(FraTerms)) == (
        "terms_id",
        "instrument_identity_id",
        "calculation_start_date",
        "calculation_end_date",
        "payment_date",
        "notional",
        "fixed_rate",
        "benchmark",
        "day_count",
        "fixing_date_offset",
        "discounting",
        "evidence_ref",
    )
    assert tuple(item.name for item in fields(RateCapFloorTerms)) == (
        "terms_id",
        "instrument_identity_id",
        "kind",
        "effective_date",
        "termination_date",
        "notional_schedule",
        "benchmark",
        "spread",
        "day_count",
        "payment_tenor",
        "reset_tenor",
        "fixing_convention",
        "schedule_convention",
        "settlement_convention",
        "evidence_ref",
        "cap_strikes",
        "floor_strikes",
    )
    assert tuple(item.name for item in fields(SwaptionTerms)) == (
        "terms_id",
        "instrument_identity_id",
        "underlying_swap",
        "position",
        "expiry_date",
        "exercise",
        "settlement_style",
        "evidence_ref",
        "cash_settlement_method",
    )


@pytest.mark.parametrize(
    "step_date",
    (date(2027, 1, 1), date(2030, 1, 1)),
)
def test_gatec_cap_strike_steps_must_be_strictly_inside_product_term(
    step_date: date,
) -> None:
    schedule = RateStrikeSchedule(
        initial_rate=DerivativeContractRate(Decimal("0.05")),
        steps=(
            RateStrikeStep(
                step_date,
                DerivativeContractRate(Decimal("0.055")),
            ),
        ),
    )
    with pytest.raises(RatesOtcValidationError, match="within product term"):
        _cap_floor_terms(kind=RateCapFloorKind.CAP, cap=schedule)
