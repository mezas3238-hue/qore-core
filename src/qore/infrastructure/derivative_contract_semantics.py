from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.fixed_income_economics import (
    BusinessCalendarRef,
    DayCountConventionCode,
    FinancialTenor,
    FixedIncomeSpread,
    SettlementConvention,
    YieldConvention,
)
from qore.infrastructure.rate_term_structure import RateCurveConvention
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class DerivativeContractSemanticsError(InfrastructureError):
    """Base error for provider-neutral derivative contractual semantics."""

    __slots__ = ()


class DerivativeContractValidationError(DerivativeContractSemanticsError):
    """Violation of a derivative contractual semantic invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise DerivativeContractValidationError(f"{field_name} must be UUID")


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        raise DerivativeContractValidationError(
            f"{field_name} must be EconomicIdentityId"
        )


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        raise DerivativeContractValidationError(f"{field_name} must be date")


def _validate_code(value: str, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise DerivativeContractValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


def _validate_decimal(
    value: Decimal,
    *,
    field_name: str,
    positive: bool = False,
) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise DerivativeContractValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if positive and value <= 0:
        raise DerivativeContractValidationError(f"{field_name} must be positive")


def _validate_non_negative_int(value: int, *, field_name: str) -> None:
    if type(value) is not int or value < 0:
        raise DerivativeContractValidationError(
            f"{field_name} must be a non-negative int"
        )


def _canonical_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class DerivativeTermsId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="derivative terms id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class DerivativeLegId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="derivative leg id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class DerivativeEvidenceRef:
    """Opaque reference to retained derivative evidence; never evidence content."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="derivative evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class DerivativeLegOrdinal:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value <= 0:
            raise DerivativeContractValidationError(
                "derivative leg ordinal must be a positive int"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class DerivativeContractMonth:
    year: int
    month: int

    def __post_init__(self) -> None:
        if type(self.year) is not int or not 1 <= self.year <= 9999:
            raise DerivativeContractValidationError(
                "derivative contract month year must be an int in 1..9999"
            )
        if type(self.month) is not int or not 1 <= self.month <= 12:
            raise DerivativeContractValidationError(
                "derivative contract month month must be an int in 1..12"
            )

    def logical_values(self) -> tuple[int, int]:
        return (self.year, self.month)


@dataclass(frozen=True, slots=True)
class DerivativeReferenceRoleCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="derivative reference role code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class DerivativeContingencyCode:
    """Typed contractual trigger role; it implements no event-detection engine."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="derivative contingency code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class DerivativeFloatingRateCalculationCode:
    """Contractual fixing/calculation method code; no fixing engine is implemented."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="floating-rate calculation code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class DerivativeNotional:
    """Positive contractual notional with explicit economic unit/reference identity."""

    value: Decimal
    unit_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="derivative notional", positive=True)
        _validate_identity(
            self.unit_identity_id,
            field_name="derivative notional unit identity",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            _canonical_decimal(self.value),
            self.unit_identity_id.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class DerivativeNotionalStep:
    effective_date: date
    notional: DerivativeNotional

    def __post_init__(self) -> None:
        _validate_date(self.effective_date, field_name="notional step effective_date")
        if not isinstance(self.notional, DerivativeNotional):
            raise DerivativeContractValidationError(
                "notional step notional must be DerivativeNotional"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.effective_date.isoformat(),
            self.notional.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class DerivativeNotionalSchedule:
    steps: tuple[DerivativeNotionalStep, ...]

    def __post_init__(self) -> None:
        if type(self.steps) is not tuple or not self.steps:
            raise DerivativeContractValidationError(
                "derivative notional schedule steps must be a non-empty tuple"
            )
        for step in self.steps:
            if not isinstance(step, DerivativeNotionalStep):
                raise DerivativeContractValidationError(
                    "notional schedule must contain DerivativeNotionalStep"
                )

        ordered = tuple(sorted(self.steps, key=lambda step: step.effective_date))
        dates = tuple(step.effective_date for step in ordered)
        if len(set(dates)) != len(dates):
            raise DerivativeContractValidationError(
                "notional schedule effective dates must be unique"
            )
        units = tuple(step.notional.unit_identity_id for step in ordered)
        if len(set(units)) != 1:
            raise DerivativeContractValidationError(
                "notional schedule steps must retain one notional unit identity"
            )
        object.__setattr__(self, "steps", ordered)

    def logical_values(self) -> tuple[object, ...]:
        return (tuple(step.logical_values() for step in self.steps),)


@dataclass(frozen=True, slots=True)
class DerivativeContractMultiplier:
    """Per-contract multiplier; semantic != quantity and != notional."""

    value: Decimal
    unit_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        _validate_decimal(
            self.value,
            field_name="derivative contract multiplier",
            positive=True,
        )
        _validate_identity(
            self.unit_identity_id,
            field_name="derivative contract multiplier unit identity",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            _canonical_decimal(self.value),
            self.unit_identity_id.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class DerivativeTickValue:
    """Economic value of one contractual minimum tick per contract."""

    value: Decimal
    value_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="derivative tick value", positive=True)
        _validate_identity(
            self.value_identity_id,
            field_name="derivative tick value identity",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            _canonical_decimal(self.value),
            self.value_identity_id.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class DerivativeContractRate:
    """Contractual fixed-rate magnitude; semantic != curve rate, yield, or spread."""

    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="derivative contract rate")

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class DerivativeBenchmarkReference:
    """Reference attachment only; no rate/curve construction authority is granted."""

    reference_identity_id: EconomicIdentityId
    role: DerivativeReferenceRoleCode
    tenor: FinancialTenor | None = None

    def __post_init__(self) -> None:
        _validate_identity(
            self.reference_identity_id,
            field_name="derivative benchmark reference identity",
        )
        if not isinstance(self.role, DerivativeReferenceRoleCode):
            raise DerivativeContractValidationError(
                "derivative benchmark role must be DerivativeReferenceRoleCode"
            )
        if self.tenor is not None and not isinstance(self.tenor, FinancialTenor):
            raise DerivativeContractValidationError(
                "derivative benchmark tenor must be FinancialTenor or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.reference_identity_id.logical_values(),
            self.role.logical_values(),
            self.tenor.logical_values() if self.tenor is not None else None,
        )


@dataclass(frozen=True, slots=True)
class DerivativeFloatingRateConvention:
    """Retained fixing/calculation semantics without resolving calendars or fixings."""

    calculation: DerivativeFloatingRateCalculationCode
    fixing_calendar_ref: BusinessCalendarRef
    fixing_lag_business_days: int = 0
    lockout_business_days: int = 0
    observation_shift: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.calculation, DerivativeFloatingRateCalculationCode):
            raise DerivativeContractValidationError(
                "floating-rate calculation must be DerivativeFloatingRateCalculationCode"
            )
        if not isinstance(self.fixing_calendar_ref, BusinessCalendarRef):
            raise DerivativeContractValidationError(
                "floating-rate fixing_calendar_ref must be BusinessCalendarRef"
            )
        _validate_non_negative_int(
            self.fixing_lag_business_days,
            field_name="floating-rate fixing_lag_business_days",
        )
        _validate_non_negative_int(
            self.lockout_business_days,
            field_name="floating-rate lockout_business_days",
        )
        if type(self.observation_shift) is not bool:
            raise DerivativeContractValidationError(
                "floating-rate observation_shift must be bool"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.calculation.logical_values(),
            self.fixing_calendar_ref.logical_values(),
            self.fixing_lag_business_days,
            self.lockout_business_days,
            self.observation_shift,
        )


class DerivativeSettlementStyle(StrEnum):
    CASH = "cash"
    PHYSICAL = "physical"


class DerivativeStrikeBasis(StrEnum):
    PRICE = "price"
    RATE = "rate"
    YIELD = "yield"
    SPREAD = "spread"
    LEVEL = "level"


type DerivativeStrikeConvention = RateCurveConvention | YieldConvention


@dataclass(frozen=True, slots=True)
class DerivativeStrike:
    """Explicit strike semantic; never an unqualified generic Decimal."""

    value: Decimal
    basis: DerivativeStrikeBasis
    quote_identity_id: EconomicIdentityId | None = None
    convention: DerivativeStrikeConvention | None = None

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="derivative strike")
        if not isinstance(self.basis, DerivativeStrikeBasis):
            raise DerivativeContractValidationError(
                "derivative strike basis must be DerivativeStrikeBasis"
            )
        if self.quote_identity_id is not None:
            _validate_identity(
                self.quote_identity_id,
                field_name="derivative strike quote identity",
            )
        if self.convention is not None and not isinstance(
            self.convention,
            (RateCurveConvention, YieldConvention),
        ):
            raise DerivativeContractValidationError(
                "derivative strike convention must be RateCurveConvention, "
                "YieldConvention, or None"
            )

        if self.basis is DerivativeStrikeBasis.PRICE:
            if self.quote_identity_id is None or self.convention is not None:
                raise DerivativeContractValidationError(
                    "price strike requires quote identity and no rate/yield convention"
                )
        elif self.basis is DerivativeStrikeBasis.RATE:
            if self.quote_identity_id is not None or not isinstance(
                self.convention, RateCurveConvention
            ):
                raise DerivativeContractValidationError(
                    "rate strike requires RateCurveConvention and no quote identity"
                )
        elif self.basis is DerivativeStrikeBasis.YIELD:
            if self.quote_identity_id is not None or not isinstance(
                self.convention, YieldConvention
            ):
                raise DerivativeContractValidationError(
                    "yield strike requires YieldConvention and no quote identity"
                )
        elif self.quote_identity_id is not None or self.convention is not None:
            raise DerivativeContractValidationError(
                "spread/level strike must not carry quote identity or rate/yield convention"
            )

    def logical_values(self) -> tuple[object, ...]:
        if isinstance(self.convention, RateCurveConvention):
            convention_values: tuple[object, ...] | None = self.convention.logical_values()
        elif isinstance(self.convention, YieldConvention):
            convention_values = ("yield-convention", self.convention.logical_values())
        else:
            convention_values = None
        return (
            _canonical_decimal(self.value),
            self.basis.value,
            self.quote_identity_id.logical_values()
            if self.quote_identity_id is not None
            else None,
            convention_values,
        )


class OptionRight(StrEnum):
    CALL = "call"
    PUT = "put"


class OptionExerciseStyle(StrEnum):
    EUROPEAN = "european"
    AMERICAN = "american"
    BERMUDAN = "bermudan"


@dataclass(frozen=True, slots=True)
class OptionExerciseTerms:
    style: OptionExerciseStyle
    bermudan_dates: tuple[date, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.style, OptionExerciseStyle):
            raise DerivativeContractValidationError(
                "option exercise style must be OptionExerciseStyle"
            )
        if type(self.bermudan_dates) is not tuple:
            raise DerivativeContractValidationError(
                "bermudan_dates must be an immutable tuple"
            )
        for exercise_date in self.bermudan_dates:
            _validate_date(exercise_date, field_name="bermudan exercise date")
        if self.style is OptionExerciseStyle.BERMUDAN:
            if not self.bermudan_dates:
                raise DerivativeContractValidationError(
                    "Bermudan exercise requires explicit exercise dates"
                )
            if len(set(self.bermudan_dates)) != len(self.bermudan_dates):
                raise DerivativeContractValidationError(
                    "Bermudan exercise dates must be unique"
                )
            object.__setattr__(self, "bermudan_dates", tuple(sorted(self.bermudan_dates)))
        elif self.bermudan_dates:
            raise DerivativeContractValidationError(
                "only Bermudan exercise may carry explicit exercise dates"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.style.value,
            tuple(value.isoformat() for value in self.bermudan_dates),
        )


@dataclass(frozen=True, slots=True)
class FuturesContractTerms:
    terms_id: DerivativeTermsId
    instrument_identity_id: EconomicIdentityId
    reference_identity_id: EconomicIdentityId
    settlement_identity_id: EconomicIdentityId
    contract_month: DerivativeContractMonth
    expiry_date: date
    multiplier: DerivativeContractMultiplier
    settlement_style: DerivativeSettlementStyle
    evidence_ref: DerivativeEvidenceRef
    tick_value: DerivativeTickValue | None = None
    first_notice_date: date | None = None
    last_trade_date: date | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, DerivativeTermsId):
            raise DerivativeContractValidationError(
                "futures terms_id must be DerivativeTermsId"
            )
        _validate_identity(
            self.instrument_identity_id,
            field_name="futures instrument identity",
        )
        _validate_identity(
            self.reference_identity_id,
            field_name="futures reference identity",
        )
        _validate_identity(
            self.settlement_identity_id,
            field_name="futures settlement identity",
        )
        if self.instrument_identity_id == self.reference_identity_id:
            raise DerivativeContractValidationError(
                "futures instrument and reference identity must differ"
            )
        if self.instrument_identity_id == self.settlement_identity_id:
            raise DerivativeContractValidationError(
                "futures instrument and settlement identity must differ"
            )
        if not isinstance(self.contract_month, DerivativeContractMonth):
            raise DerivativeContractValidationError(
                "futures contract_month must be DerivativeContractMonth"
            )
        _validate_date(self.expiry_date, field_name="futures expiry_date")
        if not isinstance(self.multiplier, DerivativeContractMultiplier):
            raise DerivativeContractValidationError(
                "futures multiplier must be DerivativeContractMultiplier"
            )
        if not isinstance(self.settlement_style, DerivativeSettlementStyle):
            raise DerivativeContractValidationError(
                "futures settlement_style must be DerivativeSettlementStyle"
            )
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise DerivativeContractValidationError(
                "futures evidence_ref must be DerivativeEvidenceRef"
            )
        if self.tick_value is not None and not isinstance(
            self.tick_value, DerivativeTickValue
        ):
            raise DerivativeContractValidationError(
                "futures tick_value must be DerivativeTickValue or None"
            )
        if self.first_notice_date is not None:
            _validate_date(
                self.first_notice_date,
                field_name="futures first_notice_date",
            )
            if self.first_notice_date > self.expiry_date:
                raise DerivativeContractValidationError(
                    "futures first_notice_date must not be after expiry_date"
                )
            if self.settlement_style is DerivativeSettlementStyle.CASH:
                raise DerivativeContractValidationError(
                    "cash-settled futures must not carry first_notice_date"
                )
        if self.last_trade_date is not None:
            _validate_date(self.last_trade_date, field_name="futures last_trade_date")
            if self.last_trade_date > self.expiry_date:
                raise DerivativeContractValidationError(
                    "futures last_trade_date must not be after expiry_date"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "futures",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.reference_identity_id.logical_values(),
            self.settlement_identity_id.logical_values(),
            self.contract_month.logical_values(),
            self.expiry_date.isoformat(),
            self.multiplier.logical_values(),
            self.settlement_style.value,
            self.evidence_ref.logical_values(),
            self.tick_value.logical_values() if self.tick_value is not None else None,
            self.first_notice_date.isoformat()
            if self.first_notice_date is not None
            else None,
            self.last_trade_date.isoformat() if self.last_trade_date is not None else None,
        )


@dataclass(frozen=True, slots=True)
class OptionContractTerms:
    terms_id: DerivativeTermsId
    instrument_identity_id: EconomicIdentityId
    underlying_identity_id: EconomicIdentityId
    settlement_identity_id: EconomicIdentityId
    right: OptionRight
    strike: DerivativeStrike
    expiry_date: date
    exercise: OptionExerciseTerms
    settlement_style: DerivativeSettlementStyle
    evidence_ref: DerivativeEvidenceRef
    multiplier: DerivativeContractMultiplier | None = None
    notional: DerivativeNotional | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, DerivativeTermsId):
            raise DerivativeContractValidationError(
                "option terms_id must be DerivativeTermsId"
            )
        _validate_identity(
            self.instrument_identity_id,
            field_name="option instrument identity",
        )
        _validate_identity(
            self.underlying_identity_id,
            field_name="option underlying identity",
        )
        _validate_identity(
            self.settlement_identity_id,
            field_name="option settlement identity",
        )
        if self.instrument_identity_id == self.underlying_identity_id:
            raise DerivativeContractValidationError(
                "option instrument and underlying identity must differ"
            )
        if self.instrument_identity_id == self.settlement_identity_id:
            raise DerivativeContractValidationError(
                "option instrument and settlement identity must differ"
            )
        if not isinstance(self.right, OptionRight):
            raise DerivativeContractValidationError("option right must be OptionRight")
        if not isinstance(self.strike, DerivativeStrike):
            raise DerivativeContractValidationError(
                "option strike must be DerivativeStrike"
            )
        _validate_date(self.expiry_date, field_name="option expiry_date")
        if not isinstance(self.exercise, OptionExerciseTerms):
            raise DerivativeContractValidationError(
                "option exercise must be OptionExerciseTerms"
            )
        if any(value > self.expiry_date for value in self.exercise.bermudan_dates):
            raise DerivativeContractValidationError(
                "Bermudan exercise date must not be after option expiry_date"
            )
        if not isinstance(self.settlement_style, DerivativeSettlementStyle):
            raise DerivativeContractValidationError(
                "option settlement_style must be DerivativeSettlementStyle"
            )
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise DerivativeContractValidationError(
                "option evidence_ref must be DerivativeEvidenceRef"
            )
        if self.multiplier is not None and not isinstance(
            self.multiplier, DerivativeContractMultiplier
        ):
            raise DerivativeContractValidationError(
                "option multiplier must be DerivativeContractMultiplier or None"
            )
        if self.notional is not None and not isinstance(
            self.notional, DerivativeNotional
        ):
            raise DerivativeContractValidationError(
                "option notional must be DerivativeNotional or None"
            )
        if self.multiplier is None and self.notional is None:
            raise DerivativeContractValidationError(
                "option requires contract multiplier and/or contractual notional"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "option",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.underlying_identity_id.logical_values(),
            self.settlement_identity_id.logical_values(),
            self.right.value,
            self.strike.logical_values(),
            self.expiry_date.isoformat(),
            self.exercise.logical_values(),
            self.settlement_style.value,
            self.evidence_ref.logical_values(),
            self.multiplier.logical_values() if self.multiplier is not None else None,
            self.notional.logical_values() if self.notional is not None else None,
        )


@dataclass(frozen=True, slots=True)
class DerivativeFixingTerms:
    reference: DerivativeBenchmarkReference
    fixing_date: date
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.reference, DerivativeBenchmarkReference):
            raise DerivativeContractValidationError(
                "derivative fixing reference must be DerivativeBenchmarkReference"
            )
        _validate_date(self.fixing_date, field_name="derivative fixing_date")
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise DerivativeContractValidationError(
                "derivative fixing evidence_ref must be DerivativeEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.reference.logical_values(),
            self.fixing_date.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ForwardContractTerms:
    terms_id: DerivativeTermsId
    instrument_identity_id: EconomicIdentityId
    reference_identity_id: EconomicIdentityId
    settlement_identity_id: EconomicIdentityId
    notional: DerivativeNotional
    agreed_strike: DerivativeStrike
    maturity_date: date
    settlement_style: DerivativeSettlementStyle
    evidence_ref: DerivativeEvidenceRef
    fixing: DerivativeFixingTerms | None = None
    settlement_convention: SettlementConvention | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, DerivativeTermsId):
            raise DerivativeContractValidationError(
                "forward terms_id must be DerivativeTermsId"
            )
        _validate_identity(
            self.instrument_identity_id,
            field_name="forward instrument identity",
        )
        _validate_identity(
            self.reference_identity_id,
            field_name="forward reference identity",
        )
        _validate_identity(
            self.settlement_identity_id,
            field_name="forward settlement identity",
        )
        if self.instrument_identity_id == self.reference_identity_id:
            raise DerivativeContractValidationError(
                "forward instrument and reference identity must differ"
            )
        if self.instrument_identity_id == self.settlement_identity_id:
            raise DerivativeContractValidationError(
                "forward instrument and settlement identity must differ"
            )
        if not isinstance(self.notional, DerivativeNotional):
            raise DerivativeContractValidationError(
                "forward notional must be DerivativeNotional"
            )
        if not isinstance(self.agreed_strike, DerivativeStrike):
            raise DerivativeContractValidationError(
                "forward agreed_strike must be DerivativeStrike"
            )
        _validate_date(self.maturity_date, field_name="forward maturity_date")
        if not isinstance(self.settlement_style, DerivativeSettlementStyle):
            raise DerivativeContractValidationError(
                "forward settlement_style must be DerivativeSettlementStyle"
            )
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise DerivativeContractValidationError(
                "forward evidence_ref must be DerivativeEvidenceRef"
            )
        if self.fixing is not None and not isinstance(
            self.fixing, DerivativeFixingTerms
        ):
            raise DerivativeContractValidationError(
                "forward fixing must be DerivativeFixingTerms or None"
            )
        if self.settlement_convention is not None and not isinstance(
            self.settlement_convention, SettlementConvention
        ):
            raise DerivativeContractValidationError(
                "forward settlement_convention must be SettlementConvention or None"
            )
        if self.settlement_style is DerivativeSettlementStyle.CASH and self.fixing is None:
            raise DerivativeContractValidationError(
                "cash-settled forward requires explicit fixing terms"
            )
        if self.fixing is not None and self.fixing.fixing_date > self.maturity_date:
            raise DerivativeContractValidationError(
                "forward fixing_date must not be after maturity_date"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "forward",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.reference_identity_id.logical_values(),
            self.settlement_identity_id.logical_values(),
            self.notional.logical_values(),
            self.agreed_strike.logical_values(),
            self.maturity_date.isoformat(),
            self.settlement_style.value,
            self.evidence_ref.logical_values(),
            self.fixing.logical_values() if self.fixing is not None else None,
            self.settlement_convention.logical_values()
            if self.settlement_convention is not None
            else None,
        )


class DerivativeLegDirection(StrEnum):
    PAY = "pay"
    RECEIVE = "receive"


@dataclass(frozen=True, slots=True)
class FixedRateSwapLeg:
    leg_id: DerivativeLegId
    ordinal: DerivativeLegOrdinal
    direction: DerivativeLegDirection
    notional_schedule: DerivativeNotionalSchedule
    rate: DerivativeContractRate
    day_count: DayCountConventionCode
    payment_tenor: FinancialTenor
    settlement_convention: SettlementConvention
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.leg_id, DerivativeLegId):
            raise DerivativeContractValidationError(
                "fixed-rate swap leg_id must be DerivativeLegId"
            )
        _validate_leg_ordinal_direction(self.ordinal, self.direction)
        if not isinstance(self.notional_schedule, DerivativeNotionalSchedule):
            raise DerivativeContractValidationError(
                "fixed-rate leg notional_schedule must be DerivativeNotionalSchedule"
            )
        if not isinstance(self.rate, DerivativeContractRate):
            raise DerivativeContractValidationError(
                "fixed-rate leg rate must be DerivativeContractRate"
            )
        _validate_payment_semantics(
            self.day_count,
            self.payment_tenor,
            self.settlement_convention,
        )
        _validate_leg_evidence(self.evidence_ref)

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fixed-rate",
            self.leg_id.logical_values(),
            self.ordinal.logical_values(),
            self.direction.value,
            self.notional_schedule.logical_values(),
            self.rate.logical_values(),
            self.day_count.logical_values(),
            self.payment_tenor.logical_values(),
            self.settlement_convention.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FloatingRateSwapLeg:
    leg_id: DerivativeLegId
    ordinal: DerivativeLegOrdinal
    direction: DerivativeLegDirection
    notional_schedule: DerivativeNotionalSchedule
    benchmark: DerivativeBenchmarkReference
    spread: FixedIncomeSpread
    day_count: DayCountConventionCode
    payment_tenor: FinancialTenor
    reset_tenor: FinancialTenor
    fixing_convention: DerivativeFloatingRateConvention
    settlement_convention: SettlementConvention
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.leg_id, DerivativeLegId):
            raise DerivativeContractValidationError(
                "floating-rate swap leg_id must be DerivativeLegId"
            )
        _validate_leg_ordinal_direction(self.ordinal, self.direction)
        if not isinstance(self.notional_schedule, DerivativeNotionalSchedule):
            raise DerivativeContractValidationError(
                "floating-rate leg notional_schedule must be DerivativeNotionalSchedule"
            )
        if not isinstance(self.benchmark, DerivativeBenchmarkReference):
            raise DerivativeContractValidationError(
                "floating-rate leg benchmark must be DerivativeBenchmarkReference"
            )
        if not isinstance(self.spread, FixedIncomeSpread):
            raise DerivativeContractValidationError(
                "floating-rate leg spread must be FixedIncomeSpread"
            )
        _validate_payment_semantics(
            self.day_count,
            self.payment_tenor,
            self.settlement_convention,
        )
        if not isinstance(self.reset_tenor, FinancialTenor):
            raise DerivativeContractValidationError(
                "floating-rate leg reset_tenor must be FinancialTenor"
            )
        if not isinstance(self.fixing_convention, DerivativeFloatingRateConvention):
            raise DerivativeContractValidationError(
                "floating-rate leg fixing_convention must be "
                "DerivativeFloatingRateConvention"
            )
        _validate_leg_evidence(self.evidence_ref)

    def logical_values(self) -> tuple[object, ...]:
        return (
            "floating-rate",
            self.leg_id.logical_values(),
            self.ordinal.logical_values(),
            self.direction.value,
            self.notional_schedule.logical_values(),
            self.benchmark.logical_values(),
            self.spread.logical_values(),
            self.day_count.logical_values(),
            self.payment_tenor.logical_values(),
            self.reset_tenor.logical_values(),
            self.fixing_convention.logical_values(),
            self.settlement_convention.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ReferenceReturnSwapLeg:
    leg_id: DerivativeLegId
    ordinal: DerivativeLegOrdinal
    direction: DerivativeLegDirection
    notional_schedule: DerivativeNotionalSchedule
    reference: DerivativeBenchmarkReference
    payment_tenor: FinancialTenor
    settlement_convention: SettlementConvention
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.leg_id, DerivativeLegId):
            raise DerivativeContractValidationError(
                "reference-return swap leg_id must be DerivativeLegId"
            )
        _validate_leg_ordinal_direction(self.ordinal, self.direction)
        if not isinstance(self.notional_schedule, DerivativeNotionalSchedule):
            raise DerivativeContractValidationError(
                "reference-return leg notional_schedule must be DerivativeNotionalSchedule"
            )
        if not isinstance(self.reference, DerivativeBenchmarkReference):
            raise DerivativeContractValidationError(
                "reference-return leg reference must be DerivativeBenchmarkReference"
            )
        if not isinstance(self.payment_tenor, FinancialTenor):
            raise DerivativeContractValidationError(
                "reference-return leg payment_tenor must be FinancialTenor"
            )
        if not isinstance(self.settlement_convention, SettlementConvention):
            raise DerivativeContractValidationError(
                "reference-return leg settlement_convention must be SettlementConvention"
            )
        _validate_leg_evidence(self.evidence_ref)

    def logical_values(self) -> tuple[object, ...]:
        return (
            "reference-return",
            self.leg_id.logical_values(),
            self.ordinal.logical_values(),
            self.direction.value,
            self.notional_schedule.logical_values(),
            self.reference.logical_values(),
            self.payment_tenor.logical_values(),
            self.settlement_convention.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ExchangeSwapLeg:
    leg_id: DerivativeLegId
    ordinal: DerivativeLegOrdinal
    direction: DerivativeLegDirection
    amount: DerivativeNotional
    payment_date: date
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.leg_id, DerivativeLegId):
            raise DerivativeContractValidationError(
                "exchange swap leg_id must be DerivativeLegId"
            )
        _validate_leg_ordinal_direction(self.ordinal, self.direction)
        if not isinstance(self.amount, DerivativeNotional):
            raise DerivativeContractValidationError(
                "exchange leg amount must be DerivativeNotional"
            )
        _validate_date(self.payment_date, field_name="exchange leg payment_date")
        _validate_leg_evidence(self.evidence_ref)

    def logical_values(self) -> tuple[object, ...]:
        return (
            "exchange",
            self.leg_id.logical_values(),
            self.ordinal.logical_values(),
            self.direction.value,
            self.amount.logical_values(),
            self.payment_date.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ProtectionSwapLeg:
    leg_id: DerivativeLegId
    ordinal: DerivativeLegOrdinal
    direction: DerivativeLegDirection
    notional_schedule: DerivativeNotionalSchedule
    reference: DerivativeBenchmarkReference
    contingency: DerivativeContingencyCode
    settlement_style: DerivativeSettlementStyle
    settlement_identity_id: EconomicIdentityId
    settlement_convention: SettlementConvention
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.leg_id, DerivativeLegId):
            raise DerivativeContractValidationError(
                "protection swap leg_id must be DerivativeLegId"
            )
        _validate_leg_ordinal_direction(self.ordinal, self.direction)
        if not isinstance(self.notional_schedule, DerivativeNotionalSchedule):
            raise DerivativeContractValidationError(
                "protection leg notional_schedule must be DerivativeNotionalSchedule"
            )
        if not isinstance(self.reference, DerivativeBenchmarkReference):
            raise DerivativeContractValidationError(
                "protection leg reference must be DerivativeBenchmarkReference"
            )
        if not isinstance(self.contingency, DerivativeContingencyCode):
            raise DerivativeContractValidationError(
                "protection leg contingency must be DerivativeContingencyCode"
            )
        if not isinstance(self.settlement_style, DerivativeSettlementStyle):
            raise DerivativeContractValidationError(
                "protection leg settlement_style must be DerivativeSettlementStyle"
            )
        _validate_identity(
            self.settlement_identity_id,
            field_name="protection settlement identity",
        )
        if not isinstance(self.settlement_convention, SettlementConvention):
            raise DerivativeContractValidationError(
                "protection leg settlement_convention must be SettlementConvention"
            )
        _validate_leg_evidence(self.evidence_ref)

    def logical_values(self) -> tuple[object, ...]:
        return (
            "protection",
            self.leg_id.logical_values(),
            self.ordinal.logical_values(),
            self.direction.value,
            self.notional_schedule.logical_values(),
            self.reference.logical_values(),
            self.contingency.logical_values(),
            self.settlement_style.value,
            self.settlement_identity_id.logical_values(),
            self.settlement_convention.logical_values(),
            self.evidence_ref.logical_values(),
        )


type DerivativeSwapLeg = (
    FixedRateSwapLeg
    | FloatingRateSwapLeg
    | ReferenceReturnSwapLeg
    | ExchangeSwapLeg
    | ProtectionSwapLeg
)


def _validate_leg_ordinal_direction(
    ordinal: DerivativeLegOrdinal,
    direction: DerivativeLegDirection,
) -> None:
    if not isinstance(ordinal, DerivativeLegOrdinal):
        raise DerivativeContractValidationError(
            "swap leg ordinal must be DerivativeLegOrdinal"
        )
    if not isinstance(direction, DerivativeLegDirection):
        raise DerivativeContractValidationError(
            "swap leg direction must be DerivativeLegDirection"
        )


def _validate_payment_semantics(
    day_count: DayCountConventionCode,
    payment_tenor: FinancialTenor,
    settlement_convention: SettlementConvention,
) -> None:
    if not isinstance(day_count, DayCountConventionCode):
        raise DerivativeContractValidationError(
            "swap leg day_count must be DayCountConventionCode"
        )
    if not isinstance(payment_tenor, FinancialTenor):
        raise DerivativeContractValidationError(
            "swap leg payment_tenor must be FinancialTenor"
        )
    if not isinstance(settlement_convention, SettlementConvention):
        raise DerivativeContractValidationError(
            "swap leg settlement_convention must be SettlementConvention"
        )


def _validate_leg_evidence(evidence_ref: DerivativeEvidenceRef) -> None:
    if not isinstance(evidence_ref, DerivativeEvidenceRef):
        raise DerivativeContractValidationError(
            "swap leg evidence_ref must be DerivativeEvidenceRef"
        )


def _swap_leg_id(leg: DerivativeSwapLeg) -> DerivativeLegId:
    return leg.leg_id


def _swap_leg_ordinal(leg: DerivativeSwapLeg) -> DerivativeLegOrdinal:
    return leg.ordinal


def _swap_leg_direction(leg: DerivativeSwapLeg) -> DerivativeLegDirection:
    return leg.direction


def _swap_leg_logical_values(leg: DerivativeSwapLeg) -> tuple[object, ...]:
    return leg.logical_values()


@dataclass(frozen=True, slots=True)
class SwapContractTerms:
    terms_id: DerivativeTermsId
    instrument_identity_id: EconomicIdentityId
    effective_date: date
    termination_date: date
    legs: tuple[DerivativeSwapLeg, ...]
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, DerivativeTermsId):
            raise DerivativeContractValidationError(
                "swap terms_id must be DerivativeTermsId"
            )
        _validate_identity(
            self.instrument_identity_id,
            field_name="swap instrument identity",
        )
        _validate_date(self.effective_date, field_name="swap effective_date")
        _validate_date(self.termination_date, field_name="swap termination_date")
        if self.termination_date <= self.effective_date:
            raise DerivativeContractValidationError(
                "swap termination_date must be after effective_date"
            )
        if type(self.legs) is not tuple or len(self.legs) < 2:
            raise DerivativeContractValidationError(
                "swap legs must be an immutable tuple with at least two legs"
            )
        allowed_leg_types = (
            FixedRateSwapLeg,
            FloatingRateSwapLeg,
            ReferenceReturnSwapLeg,
            ExchangeSwapLeg,
            ProtectionSwapLeg,
        )
        for leg in self.legs:
            if not isinstance(leg, allowed_leg_types):
                raise DerivativeContractValidationError(
                    "swap legs must contain certified derivative swap leg types"
                )
            self._validate_leg_dates(leg)

        leg_ids = tuple(_swap_leg_id(leg) for leg in self.legs)
        if len(set(leg_ids)) != len(leg_ids):
            raise DerivativeContractValidationError("swap leg ids must be unique")
        ordinals = tuple(_swap_leg_ordinal(leg).value for leg in self.legs)
        if len(set(ordinals)) != len(ordinals):
            raise DerivativeContractValidationError("swap leg ordinals must be unique")
        directions = {_swap_leg_direction(leg) for leg in self.legs}
        if directions != {
            DerivativeLegDirection.PAY,
            DerivativeLegDirection.RECEIVE,
        }:
            raise DerivativeContractValidationError(
                "swap must retain at least one PAY and one RECEIVE leg"
            )

        ordered = tuple(sorted(self.legs, key=lambda leg: _swap_leg_ordinal(leg).value))
        expected = tuple(range(1, len(ordered) + 1))
        actual = tuple(_swap_leg_ordinal(leg).value for leg in ordered)
        if actual != expected:
            raise DerivativeContractValidationError(
                "swap leg ordinals must be contiguous from 1"
            )
        object.__setattr__(self, "legs", ordered)
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise DerivativeContractValidationError(
                "swap evidence_ref must be DerivativeEvidenceRef"
            )

    def _validate_leg_dates(self, leg: DerivativeSwapLeg) -> None:
        if isinstance(leg, ExchangeSwapLeg):
            if not self.effective_date <= leg.payment_date <= self.termination_date:
                raise DerivativeContractValidationError(
                    "exchange leg payment_date must fall within swap term"
                )
            return
        schedule = leg.notional_schedule
        if schedule.steps[0].effective_date != self.effective_date:
            raise DerivativeContractValidationError(
                "swap rate/reference/protection leg notional must start at effective_date"
            )
        if any(
            step.effective_date >= self.termination_date
            for step in schedule.steps[1:]
        ):
            raise DerivativeContractValidationError(
                "swap notional schedule changes must precede termination_date"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "swap",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.effective_date.isoformat(),
            self.termination_date.isoformat(),
            tuple(_swap_leg_logical_values(leg) for leg in self.legs),
            self.evidence_ref.logical_values(),
        )


class DerivativeCompositionSide(StrEnum):
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True, slots=True)
class DerivativeCompositionLeg:
    leg_id: DerivativeLegId
    ordinal: DerivativeLegOrdinal
    component_identity_id: EconomicIdentityId
    side: DerivativeCompositionSide
    ratio: Decimal
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.leg_id, DerivativeLegId):
            raise DerivativeContractValidationError(
                "composition leg_id must be DerivativeLegId"
            )
        if not isinstance(self.ordinal, DerivativeLegOrdinal):
            raise DerivativeContractValidationError(
                "composition ordinal must be DerivativeLegOrdinal"
            )
        _validate_identity(
            self.component_identity_id,
            field_name="composition component identity",
        )
        if not isinstance(self.side, DerivativeCompositionSide):
            raise DerivativeContractValidationError(
                "composition side must be DerivativeCompositionSide"
            )
        _validate_decimal(self.ratio, field_name="composition ratio", positive=True)
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise DerivativeContractValidationError(
                "composition evidence_ref must be DerivativeEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.leg_id.logical_values(),
            self.ordinal.logical_values(),
            self.component_identity_id.logical_values(),
            self.side.value,
            _canonical_decimal(self.ratio),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class DerivativeCompositionTerms:
    terms_id: DerivativeTermsId
    instrument_identity_id: EconomicIdentityId
    legs: tuple[DerivativeCompositionLeg, ...]
    evidence_ref: DerivativeEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, DerivativeTermsId):
            raise DerivativeContractValidationError(
                "composition terms_id must be DerivativeTermsId"
            )
        _validate_identity(
            self.instrument_identity_id,
            field_name="composition instrument identity",
        )
        if type(self.legs) is not tuple or len(self.legs) < 2:
            raise DerivativeContractValidationError(
                "composition legs must be an immutable tuple with at least two legs"
            )
        for leg in self.legs:
            if not isinstance(leg, DerivativeCompositionLeg):
                raise DerivativeContractValidationError(
                    "composition legs must contain DerivativeCompositionLeg"
                )
            if leg.component_identity_id == self.instrument_identity_id:
                raise DerivativeContractValidationError(
                    "composition instrument must not reference itself as a component"
                )
        leg_ids = tuple(leg.leg_id for leg in self.legs)
        if len(set(leg_ids)) != len(leg_ids):
            raise DerivativeContractValidationError(
                "composition leg ids must be unique"
            )
        component_ids = tuple(leg.component_identity_id for leg in self.legs)
        if len(set(component_ids)) != len(component_ids):
            raise DerivativeContractValidationError(
                "composition component identities must be unique"
            )
        ordinals = tuple(leg.ordinal.value for leg in self.legs)
        if len(set(ordinals)) != len(ordinals):
            raise DerivativeContractValidationError(
                "composition leg ordinals must be unique"
            )
        ordered = tuple(sorted(self.legs, key=lambda leg: leg.ordinal.value))
        expected = tuple(range(1, len(ordered) + 1))
        actual = tuple(leg.ordinal.value for leg in ordered)
        if actual != expected:
            raise DerivativeContractValidationError(
                "composition leg ordinals must be contiguous from 1"
            )
        object.__setattr__(self, "legs", ordered)
        if not isinstance(self.evidence_ref, DerivativeEvidenceRef):
            raise DerivativeContractValidationError(
                "composition evidence_ref must be DerivativeEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "derivative-composition",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            tuple(leg.logical_values() for leg in self.legs),
            self.evidence_ref.logical_values(),
        )
