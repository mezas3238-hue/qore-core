from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeBenchmarkReference,
    DerivativeContractRate,
    DerivativeEvidenceRef,
    DerivativeFloatingRateConvention,
    DerivativeLegDirection,
    DerivativeNotional,
    DerivativeNotionalSchedule,
    DerivativeScheduleConvention,
    DerivativeSettlementStyle,
    DerivativeTermsId,
    FixedRateSwapLeg,
    FloatingRateSwapLeg,
    OptionExerciseTerms,
    SwapContractTerms,
)
from qore.infrastructure.fixed_income_economics import (
    BusinessCalendarRef,
    BusinessDayConventionCode,
    DayCountConventionCode,
    FinancialTenor,
    FixedIncomeSpread,
    SettlementConvention,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class RatesOtcSemanticsError(InfrastructureError):
    """Base error for bounded rates/OTC static contract semantics."""

    __slots__ = ()


class RatesOtcValidationError(RatesOtcSemanticsError):
    """Violation of a rates/OTC static semantic invariant."""

    __slots__ = ()


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        raise RatesOtcValidationError(f"{field_name} must be EconomicIdentityId")


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        raise RatesOtcValidationError(f"{field_name} must be date")


def _validate_code(value: str, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise RatesOtcValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


@dataclass(frozen=True, slots=True)
class FraDiscountingCode:
    """Static FRA discounting qualification; it performs no discounting."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="FRA discounting code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class FraFixingDateOffset:
    """Bounded FRA fixing-date offset relative to calculation start."""

    business_days_offset: int
    fixing_calendar_ref: BusinessCalendarRef
    business_day_convention: BusinessDayConventionCode

    def __post_init__(self) -> None:
        if type(self.business_days_offset) is not int:
            raise RatesOtcValidationError(
                "FRA fixing business_days_offset must be exact int"
            )
        if type(self.fixing_calendar_ref) is not BusinessCalendarRef:
            raise RatesOtcValidationError(
                "FRA fixing calendar ref must be BusinessCalendarRef"
            )
        if type(self.business_day_convention) is not BusinessDayConventionCode:
            raise RatesOtcValidationError(
                "FRA fixing business day convention must be "
                "BusinessDayConventionCode"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.business_days_offset),
            self.fixing_calendar_ref.logical_values(),
            self.business_day_convention.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class RateStrikeStep:
    """One contractual rate-strike change effective on an explicit date."""

    effective_date: date
    rate: DerivativeContractRate

    def __post_init__(self) -> None:
        _validate_date(self.effective_date, field_name="rate strike step effective_date")
        if not isinstance(self.rate, DerivativeContractRate):
            raise RatesOtcValidationError(
                "rate strike step rate must be DerivativeContractRate"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.effective_date.isoformat(), self.rate.logical_values())


@dataclass(frozen=True, slots=True)
class RateStrikeSchedule:
    """Initial strike plus optional dated changes; no schedule generation authority."""

    initial_rate: DerivativeContractRate
    steps: tuple[RateStrikeStep, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.initial_rate, DerivativeContractRate):
            raise RatesOtcValidationError(
                "rate strike schedule initial_rate must be DerivativeContractRate"
            )
        if type(self.steps) is not tuple:
            raise RatesOtcValidationError("rate strike schedule steps must be tuple")
        for step in self.steps:
            if not isinstance(step, RateStrikeStep):
                raise RatesOtcValidationError(
                    "rate strike schedule steps must contain RateStrikeStep"
                )
        dates = tuple(step.effective_date for step in self.steps)
        if len(set(dates)) != len(dates):
            raise RatesOtcValidationError("rate strike step dates must be unique")
        object.__setattr__(
            self,
            "steps",
            tuple(sorted(self.steps, key=lambda step: step.effective_date)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.initial_rate.logical_values(),
            tuple(step.logical_values() for step in self.steps),
        )


class RateCapFloorKind(StrEnum):
    CAP = "cap"
    FLOOR = "floor"
    COLLAR = "collar"


class SwaptionPosition(StrEnum):
    PAYER = "payer"
    RECEIVER = "receiver"


@dataclass(frozen=True, slots=True)
class SwaptionCashSettlementMethodCode:
    """Externally governed static cash-settlement method; no calculation authority."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="swaption cash-settlement method code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class FraTerms:
    """Bounded static Forward Rate Agreement product semantics."""

    terms_id: DerivativeTermsId
    instrument_identity_id: EconomicIdentityId
    calculation_start_date: date
    calculation_end_date: date
    payment_date: date
    notional: DerivativeNotional
    fixed_rate: DerivativeContractRate
    benchmark: DerivativeBenchmarkReference
    day_count: DayCountConventionCode
    fixing_date_offset: FraFixingDateOffset
    discounting: FraDiscountingCode
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, DerivativeTermsId):
            raise RatesOtcValidationError("FRA terms_id must be DerivativeTermsId")
        _validate_identity(self.instrument_identity_id, field_name="FRA instrument identity")
        _validate_date(self.calculation_start_date, field_name="FRA calculation start")
        _validate_date(self.calculation_end_date, field_name="FRA calculation end")
        _validate_date(self.payment_date, field_name="FRA payment date")
        if self.calculation_end_date <= self.calculation_start_date:
            raise RatesOtcValidationError(
                "FRA calculation_end_date must be after calculation_start_date"
            )
        if not isinstance(self.notional, DerivativeNotional):
            raise RatesOtcValidationError("FRA notional must be DerivativeNotional")
        if not isinstance(self.fixed_rate, DerivativeContractRate):
            raise RatesOtcValidationError(
                "FRA fixed_rate must be DerivativeContractRate"
            )
        if not isinstance(self.benchmark, DerivativeBenchmarkReference):
            raise RatesOtcValidationError(
                "FRA benchmark must be DerivativeBenchmarkReference"
            )
        if self.benchmark.reference_identity_id == self.instrument_identity_id:
            raise RatesOtcValidationError(
                "FRA instrument identity must differ from benchmark identity"
            )
        if self.benchmark.tenor is None:
            raise RatesOtcValidationError(
                "bounded FRA requires exactly one benchmark tenor"
            )
        if not isinstance(self.day_count, DayCountConventionCode):
            raise RatesOtcValidationError(
                "FRA day_count must be DayCountConventionCode"
            )
        if type(self.fixing_date_offset) is not FraFixingDateOffset:
            raise RatesOtcValidationError(
                "FRA fixing_date_offset must be FraFixingDateOffset"
            )
        if not isinstance(self.discounting, FraDiscountingCode):
            raise RatesOtcValidationError(
                "FRA discounting must be FraDiscountingCode"
            )
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise RatesOtcValidationError(
                "FRA evidence_ref must be DerivativeEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fra",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.calculation_start_date.isoformat(),
            self.calculation_end_date.isoformat(),
            self.payment_date.isoformat(),
            self.notional.logical_values(),
            self.fixed_rate.logical_values(),
            self.benchmark.logical_values(),
            self.day_count.logical_values(),
            self.fixing_date_offset.logical_values(),
            self.discounting.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class RateCapFloorTerms:
    """Bounded cap/floor/collar stream semantics without rate observation or payoff."""

    terms_id: DerivativeTermsId
    instrument_identity_id: EconomicIdentityId
    kind: RateCapFloorKind
    effective_date: date
    termination_date: date
    notional_schedule: DerivativeNotionalSchedule
    benchmark: DerivativeBenchmarkReference
    spread: FixedIncomeSpread | None
    day_count: DayCountConventionCode
    payment_tenor: FinancialTenor
    reset_tenor: FinancialTenor
    fixing_convention: DerivativeFloatingRateConvention
    schedule_convention: DerivativeScheduleConvention
    settlement_convention: SettlementConvention
    evidence_ref: DerivativeEvidenceRef
    cap_strikes: RateStrikeSchedule | None = None
    floor_strikes: RateStrikeSchedule | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, DerivativeTermsId):
            raise RatesOtcValidationError(
                "cap/floor terms_id must be DerivativeTermsId"
            )
        _validate_identity(
            self.instrument_identity_id,
            field_name="cap/floor instrument identity",
        )
        if not isinstance(self.kind, RateCapFloorKind):
            raise RatesOtcValidationError(
                "cap/floor kind must be RateCapFloorKind"
            )
        _validate_date(self.effective_date, field_name="cap/floor effective_date")
        _validate_date(
            self.termination_date,
            field_name="cap/floor termination_date",
        )
        if self.termination_date <= self.effective_date:
            raise RatesOtcValidationError(
                "cap/floor termination_date must be after effective_date"
            )
        if not isinstance(self.notional_schedule, DerivativeNotionalSchedule):
            raise RatesOtcValidationError(
                "cap/floor notional_schedule must be DerivativeNotionalSchedule"
            )
        if self.notional_schedule.steps[0].effective_date != self.effective_date:
            raise RatesOtcValidationError(
                "cap/floor notional must start at effective_date"
            )
        if any(
            step.effective_date >= self.termination_date
            for step in self.notional_schedule.steps[1:]
        ):
            raise RatesOtcValidationError(
                "cap/floor notional changes must precede termination_date"
            )
        if not isinstance(self.benchmark, DerivativeBenchmarkReference):
            raise RatesOtcValidationError(
                "cap/floor benchmark must be DerivativeBenchmarkReference"
            )
        if self.benchmark.reference_identity_id == self.instrument_identity_id:
            raise RatesOtcValidationError(
                "cap/floor instrument identity must differ from benchmark identity"
            )
        if self.spread is not None and not isinstance(
            self.spread,
            FixedIncomeSpread,
        ):
            raise RatesOtcValidationError(
                "cap/floor spread must be FixedIncomeSpread or None"
            )
        if not isinstance(self.day_count, DayCountConventionCode):
            raise RatesOtcValidationError(
                "cap/floor day_count must be DayCountConventionCode"
            )
        if not isinstance(self.payment_tenor, FinancialTenor):
            raise RatesOtcValidationError(
                "cap/floor payment_tenor must be FinancialTenor"
            )
        if not isinstance(self.reset_tenor, FinancialTenor):
            raise RatesOtcValidationError(
                "cap/floor reset_tenor must be FinancialTenor"
            )
        if not isinstance(self.fixing_convention, DerivativeFloatingRateConvention):
            raise RatesOtcValidationError(
                "cap/floor fixing_convention must be DerivativeFloatingRateConvention"
            )
        if not isinstance(self.schedule_convention, DerivativeScheduleConvention):
            raise RatesOtcValidationError(
                "cap/floor schedule_convention must be DerivativeScheduleConvention"
            )
        if not isinstance(self.settlement_convention, SettlementConvention):
            raise RatesOtcValidationError(
                "cap/floor settlement_convention must be SettlementConvention"
            )
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise RatesOtcValidationError(
                "cap/floor evidence_ref must be DerivativeEvidenceRef"
            )
        if self.cap_strikes is not None and not isinstance(
            self.cap_strikes,
            RateStrikeSchedule,
        ):
            raise RatesOtcValidationError(
                "cap_strikes must be RateStrikeSchedule or None"
            )
        if self.floor_strikes is not None and not isinstance(
            self.floor_strikes,
            RateStrikeSchedule,
        ):
            raise RatesOtcValidationError(
                "floor_strikes must be RateStrikeSchedule or None"
            )
        if self.kind is RateCapFloorKind.CAP:
            if self.cap_strikes is None or self.floor_strikes is not None:
                raise RatesOtcValidationError(
                    "CAP requires cap strikes and forbids floor strikes"
                )
        elif self.kind is RateCapFloorKind.FLOOR:
            if self.floor_strikes is None or self.cap_strikes is not None:
                raise RatesOtcValidationError(
                    "FLOOR requires floor strikes and forbids cap strikes"
                )
        elif self.cap_strikes is None or self.floor_strikes is None:
            raise RatesOtcValidationError(
                "COLLAR requires both cap and floor strike schedules"
            )
        for schedule in (self.cap_strikes, self.floor_strikes):
            if schedule is not None:
                self._validate_strike_schedule(schedule)

    def _validate_strike_schedule(self, schedule: RateStrikeSchedule) -> None:
        for step in schedule.steps:
            if not self.effective_date < step.effective_date < self.termination_date:
                raise RatesOtcValidationError(
                    "cap/floor strike step must fall strictly within product term"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "rate-cap-floor",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.kind.value,
            self.effective_date.isoformat(),
            self.termination_date.isoformat(),
            self.notional_schedule.logical_values(),
            self.benchmark.logical_values(),
            self.spread.logical_values() if self.spread is not None else None,
            self.day_count.logical_values(),
            self.payment_tenor.logical_values(),
            self.reset_tenor.logical_values(),
            self.fixing_convention.logical_values(),
            self.schedule_convention.logical_values(),
            self.settlement_convention.logical_values(),
            self.cap_strikes.logical_values()
            if self.cap_strikes is not None
            else None,
            self.floor_strikes.logical_values()
            if self.floor_strikes is not None
            else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class SwaptionTerms:
    """Bounded vanilla fixed/floating option-on-swap semantics."""

    terms_id: DerivativeTermsId
    instrument_identity_id: EconomicIdentityId
    underlying_swap: SwapContractTerms
    position: SwaptionPosition
    expiry_date: date
    exercise: OptionExerciseTerms
    settlement_style: DerivativeSettlementStyle
    evidence_ref: DerivativeEvidenceRef
    cash_settlement_method: SwaptionCashSettlementMethodCode | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, DerivativeTermsId):
            raise RatesOtcValidationError(
                "swaption terms_id must be DerivativeTermsId"
            )
        _validate_identity(
            self.instrument_identity_id,
            field_name="swaption instrument identity",
        )
        if not isinstance(self.underlying_swap, SwapContractTerms):
            raise RatesOtcValidationError(
                "swaption underlying_swap must be SwapContractTerms"
            )
        if self.instrument_identity_id == self.underlying_swap.instrument_identity_id:
            raise RatesOtcValidationError(
                "swaption instrument must differ from underlying swap identity"
            )
        if not isinstance(self.position, SwaptionPosition):
            raise RatesOtcValidationError(
                "swaption position must be SwaptionPosition"
            )
        _validate_date(self.expiry_date, field_name="swaption expiry_date")
        if self.expiry_date > self.underlying_swap.effective_date:
            raise RatesOtcValidationError(
                "swaption expiry_date must not follow underlying effective_date"
            )
        if not isinstance(self.exercise, OptionExerciseTerms):
            raise RatesOtcValidationError(
                "swaption exercise must be OptionExerciseTerms"
            )
        if (
            self.exercise.american_start_date is not None
            and self.exercise.american_start_date > self.expiry_date
        ):
            raise RatesOtcValidationError(
                "swaption American exercise start must not follow expiry"
            )
        if any(value > self.expiry_date for value in self.exercise.bermudan_dates):
            raise RatesOtcValidationError(
                "swaption Bermudan exercise date must not follow expiry"
            )
        if not isinstance(self.settlement_style, DerivativeSettlementStyle):
            raise RatesOtcValidationError(
                "swaption settlement_style must be DerivativeSettlementStyle"
            )
        if self.cash_settlement_method is not None and not isinstance(
            self.cash_settlement_method,
            SwaptionCashSettlementMethodCode,
        ):
            raise RatesOtcValidationError(
                "swaption cash settlement method has invalid type"
            )
        if (
            self.settlement_style is not DerivativeSettlementStyle.CASH
            and self.cash_settlement_method is not None
        ):
            raise RatesOtcValidationError(
                "physical swaption must not carry cash settlement method"
            )
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise RatesOtcValidationError(
                "swaption evidence_ref must be DerivativeEvidenceRef"
            )
        self._validate_bounded_underlying()

    def _validate_bounded_underlying(self) -> None:
        if len(self.underlying_swap.legs) != 2:
            raise RatesOtcValidationError(
                "bounded swaption requires exactly two underlying swap legs"
            )
        fixed_legs = tuple(
            leg for leg in self.underlying_swap.legs if isinstance(leg, FixedRateSwapLeg)
        )
        floating_legs = tuple(
            leg
            for leg in self.underlying_swap.legs
            if isinstance(leg, FloatingRateSwapLeg)
        )
        if len(fixed_legs) != 1 or len(floating_legs) != 1:
            raise RatesOtcValidationError(
                "bounded swaption requires one fixed and one floating leg"
            )
        fixed = fixed_legs[0]
        floating = floating_legs[0]
        if self.position is SwaptionPosition.PAYER:
            if (
                fixed.direction is not DerivativeLegDirection.PAY
                or floating.direction is not DerivativeLegDirection.RECEIVE
            ):
                raise RatesOtcValidationError(
                    "payer swaption requires PAY fixed / RECEIVE floating underlying"
                )
        elif (
            fixed.direction is not DerivativeLegDirection.RECEIVE
            or floating.direction is not DerivativeLegDirection.PAY
        ):
            raise RatesOtcValidationError(
                "receiver swaption requires RECEIVE fixed / PAY floating underlying"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "swaption",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.underlying_swap.logical_values(),
            self.position.value,
            self.expiry_date.isoformat(),
            self.exercise.logical_values(),
            self.settlement_style.value,
            self.cash_settlement_method.logical_values()
            if self.cash_settlement_method is not None
            else None,
            self.evidence_ref.logical_values(),
        )
