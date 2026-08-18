from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

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


def _underlying_swap() -> SwapContractTerms:
    effective = date(2027, 1, 1)
    fixed = FixedRateSwapLeg(
        leg_id=DerivativeLegId(_uuid(300)),
        ordinal=DerivativeLegOrdinal(1),
        direction=DerivativeLegDirection.PAY,
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
        direction=DerivativeLegDirection.RECEIVE,
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


def _swaption_terms() -> SwaptionTerms:
    return SwaptionTerms(
        terms_id=DerivativeTermsId(_uuid(400)),
        instrument_identity_id=_identity(401),
        underlying_swap=_underlying_swap(),
        position=SwaptionPosition.PAYER,
        expiry_date=date(2026, 12, 15),
        exercise=OptionExerciseTerms(
            style=OptionExerciseStyle.BERMUDAN,
            bermudan_dates=(date(2026, 12, 10),),
        ),
        settlement_style=DerivativeSettlementStyle.CASH,
        evidence_ref=_evidence(402),
        cash_settlement_method=SwaptionCashSettlementMethodCode("cash-price"),
    )


def test_fra_logical_values_projects_every_contract_field() -> None:
    terms = _fra_terms()
    assert terms.logical_values() == (
        "fra",
        terms.terms_id.logical_values(),
        terms.instrument_identity_id.logical_values(),
        terms.calculation_start_date.isoformat(),
        terms.calculation_end_date.isoformat(),
        terms.payment_date.isoformat(),
        terms.notional.logical_values(),
        terms.fixed_rate.logical_values(),
        terms.benchmark.logical_values(),
        terms.day_count.logical_values(),
        terms.fixing_date_offset.logical_values(),
        terms.discounting.logical_values(),
        terms.evidence_ref.logical_values(),
    )


def test_cap_floor_logical_values_projects_every_contract_field() -> None:
    terms = _cap_floor_terms()
    assert terms.cap_strikes is not None
    assert terms.floor_strikes is not None
    assert terms.spread is not None
    assert terms.logical_values() == (
        "rate-cap-floor",
        terms.terms_id.logical_values(),
        terms.instrument_identity_id.logical_values(),
        terms.kind.value,
        terms.effective_date.isoformat(),
        terms.termination_date.isoformat(),
        terms.notional_schedule.logical_values(),
        terms.benchmark.logical_values(),
        terms.spread.logical_values(),
        terms.day_count.logical_values(),
        terms.payment_tenor.logical_values(),
        terms.reset_tenor.logical_values(),
        terms.fixing_convention.logical_values(),
        terms.schedule_convention.logical_values(),
        terms.settlement_convention.logical_values(),
        terms.cap_strikes.logical_values(),
        terms.floor_strikes.logical_values(),
        terms.evidence_ref.logical_values(),
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


def test_swaption_logical_values_projects_every_contract_field() -> None:
    terms = _swaption_terms()
    assert terms.cash_settlement_method is not None
    assert terms.logical_values() == (
        "swaption",
        terms.terms_id.logical_values(),
        terms.instrument_identity_id.logical_values(),
        terms.underlying_swap.logical_values(),
        terms.position.value,
        terms.expiry_date.isoformat(),
        terms.exercise.logical_values(),
        terms.settlement_style.value,
        terms.cash_settlement_method.logical_values(),
        terms.evidence_ref.logical_values(),
    )


def test_swaption_position_has_direct_logical_projection() -> None:
    terms = _swaption_terms()
    values = terms.logical_values()
    assert values[4] == terms.position.value
