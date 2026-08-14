from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class FixedIncomeEconomicsError(InfrastructureError):
    """Base error for fixed-income economic contracts."""

    __slots__ = ()


class FixedIncomeEconomicsValidationError(FixedIncomeEconomicsError):
    """Violation of a fixed-income economic invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise FixedIncomeEconomicsValidationError(f"{field_name} must be UUID")


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        raise FixedIncomeEconomicsValidationError(
            f"{field_name} must be EconomicIdentityId"
        )


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        raise FixedIncomeEconomicsValidationError(f"{field_name} must be date")


def _validate_code(value: str, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 64
        or fullmatch(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise FixedIncomeEconomicsValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


def _validate_decimal(
    value: Decimal,
    *,
    field_name: str,
    positive: bool = False,
) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise FixedIncomeEconomicsValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if positive and value <= 0:
        raise FixedIncomeEconomicsValidationError(f"{field_name} must be positive")


def _canonical_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class FixedIncomeTermsId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="fixed-income terms id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FixedIncomeCashFlowId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="fixed-income cash-flow id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FixedIncomeEvidenceRef:
    """Opaque reference to retained evidence; never evidence content or a secret."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="fixed-income evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class FinancialTenorUnit(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


@dataclass(frozen=True, slots=True)
class FinancialTenor:
    """Calendar/financial horizon. It intentionally has no fixed-seconds meaning."""

    value: int
    unit: FinancialTenorUnit

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value <= 0:
            raise FixedIncomeEconomicsValidationError(
                "financial tenor value must be a positive int"
            )
        if not isinstance(self.unit, FinancialTenorUnit):
            raise FixedIncomeEconomicsValidationError(
                "financial tenor unit must be FinancialTenorUnit"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.value, self.unit.value)


@dataclass(frozen=True, slots=True)
class DayCountConventionCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="day-count convention code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class BusinessDayConventionCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="business-day convention code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class BusinessCalendarRef:
    """Reference to D06-governed calendar semantics; this type grants no authority."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="business calendar ref")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class CompoundingConventionCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="compounding convention code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class FixedIncomePriceBasisCode:
    """Quote-basis semantic such as percent-of-par; never inferred from magnitude."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="fixed-income price basis code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class FixedIncomeYieldCode:
    """Extensible yield semantic such as yield-to-maturity."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="fixed-income yield code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class FixedIncomeReferenceRoleCode:
    """Bounded role for a benchmark/curve reference; not curve authority."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="fixed-income reference role code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class FaceAmount:
    """Positive face/par principal magnitude in the separately bound denomination."""

    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="face amount", positive=True)

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class FixedIncomeCashAmount:
    """Positive contractual cash-flow magnitude; currency identity is separate."""

    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(
            self.value,
            field_name="fixed-income cash amount",
            positive=True,
        )

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class CouponRate:
    """Coupon-rate magnitude encoded as a decimal fraction; semantic != yield/spread."""

    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="coupon rate")

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class FixedIncomeYield:
    """Yield magnitude encoded as a decimal fraction; semantic != rate/spread."""

    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="fixed-income yield")

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class FixedIncomeSpread:
    """Spread magnitude encoded as a decimal fraction; semantic != rate/yield."""

    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="fixed-income spread")

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


class FixedIncomePriceKind(StrEnum):
    CLEAN = "clean"
    DIRTY = "dirty"


@dataclass(frozen=True, slots=True)
class FixedIncomePrice:
    """Fixed-income price semantic; not MoneyAmount or a valuation authority."""

    value: Decimal
    kind: FixedIncomePriceKind
    basis: FixedIncomePriceBasisCode

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="fixed-income price")
        if not isinstance(self.kind, FixedIncomePriceKind):
            raise FixedIncomeEconomicsValidationError(
                "fixed-income price kind must be FixedIncomePriceKind"
            )
        if not isinstance(self.basis, FixedIncomePriceBasisCode):
            raise FixedIncomeEconomicsValidationError(
                "fixed-income price basis must be FixedIncomePriceBasisCode"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            _canonical_decimal(self.value),
            self.kind.value,
            self.basis.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FixedIncomeBenchmarkReference:
    """Reference-object attachment only; UMI-04 retains curve construction authority."""

    reference_identity_id: EconomicIdentityId
    role: FixedIncomeReferenceRoleCode
    tenor: FinancialTenor | None = None

    def __post_init__(self) -> None:
        _validate_identity(
            self.reference_identity_id,
            field_name="fixed-income benchmark reference identity",
        )
        if not isinstance(self.role, FixedIncomeReferenceRoleCode):
            raise FixedIncomeEconomicsValidationError(
                "fixed-income benchmark role must be FixedIncomeReferenceRoleCode"
            )
        if self.tenor is not None and not isinstance(self.tenor, FinancialTenor):
            raise FixedIncomeEconomicsValidationError(
                "fixed-income benchmark tenor must be FinancialTenor or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.reference_identity_id.logical_values(),
            self.role.logical_values(),
            self.tenor.logical_values() if self.tenor is not None else None,
        )


@dataclass(frozen=True, slots=True)
class FixedCouponTerms:
    rate: CouponRate
    day_count: DayCountConventionCode
    payment_tenor: FinancialTenor

    def __post_init__(self) -> None:
        if not isinstance(self.rate, CouponRate):
            raise FixedIncomeEconomicsValidationError(
                "fixed coupon rate must be CouponRate"
            )
        if not isinstance(self.day_count, DayCountConventionCode):
            raise FixedIncomeEconomicsValidationError(
                "fixed coupon day_count must be DayCountConventionCode"
            )
        if not isinstance(self.payment_tenor, FinancialTenor):
            raise FixedIncomeEconomicsValidationError(
                "fixed coupon payment_tenor must be FinancialTenor"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fixed",
            self.rate.logical_values(),
            self.day_count.logical_values(),
            self.payment_tenor.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FloatingCouponTerms:
    benchmark: FixedIncomeBenchmarkReference
    spread: FixedIncomeSpread
    day_count: DayCountConventionCode
    payment_tenor: FinancialTenor
    reset_tenor: FinancialTenor

    def __post_init__(self) -> None:
        if not isinstance(self.benchmark, FixedIncomeBenchmarkReference):
            raise FixedIncomeEconomicsValidationError(
                "floating coupon benchmark must be FixedIncomeBenchmarkReference"
            )
        if not isinstance(self.spread, FixedIncomeSpread):
            raise FixedIncomeEconomicsValidationError(
                "floating coupon spread must be FixedIncomeSpread"
            )
        if not isinstance(self.day_count, DayCountConventionCode):
            raise FixedIncomeEconomicsValidationError(
                "floating coupon day_count must be DayCountConventionCode"
            )
        if not isinstance(self.payment_tenor, FinancialTenor):
            raise FixedIncomeEconomicsValidationError(
                "floating coupon payment_tenor must be FinancialTenor"
            )
        if not isinstance(self.reset_tenor, FinancialTenor):
            raise FixedIncomeEconomicsValidationError(
                "floating coupon reset_tenor must be FinancialTenor"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "floating",
            self.benchmark.logical_values(),
            self.spread.logical_values(),
            self.day_count.logical_values(),
            self.payment_tenor.logical_values(),
            self.reset_tenor.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ZeroCouponTerms:
    day_count: DayCountConventionCode

    def __post_init__(self) -> None:
        if not isinstance(self.day_count, DayCountConventionCode):
            raise FixedIncomeEconomicsValidationError(
                "zero coupon day_count must be DayCountConventionCode"
            )

    def logical_values(self) -> tuple[object, ...]:
        return ("zero", self.day_count.logical_values())


type FixedIncomeCouponTerms = FixedCouponTerms | FloatingCouponTerms | ZeroCouponTerms


@dataclass(frozen=True, slots=True)
class AccrualPeriod:
    start_date: date
    end_date: date
    payment_date: date
    day_count: DayCountConventionCode

    def __post_init__(self) -> None:
        _validate_date(self.start_date, field_name="accrual start_date")
        _validate_date(self.end_date, field_name="accrual end_date")
        _validate_date(self.payment_date, field_name="accrual payment_date")
        if self.end_date <= self.start_date:
            raise FixedIncomeEconomicsValidationError(
                "accrual end_date must be after start_date"
            )
        if self.payment_date < self.end_date:
            raise FixedIncomeEconomicsValidationError(
                "accrual payment_date must not predate end_date"
            )
        if not isinstance(self.day_count, DayCountConventionCode):
            raise FixedIncomeEconomicsValidationError(
                "accrual day_count must be DayCountConventionCode"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.start_date.isoformat(),
            self.end_date.isoformat(),
            self.payment_date.isoformat(),
            self.day_count.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class SettlementConvention:
    business_day_lag: int
    calendar_ref: BusinessCalendarRef
    business_day_convention: BusinessDayConventionCode

    def __post_init__(self) -> None:
        if type(self.business_day_lag) is not int or self.business_day_lag < 0:
            raise FixedIncomeEconomicsValidationError(
                "settlement business_day_lag must be a non-negative int"
            )
        if not isinstance(self.calendar_ref, BusinessCalendarRef):
            raise FixedIncomeEconomicsValidationError(
                "settlement calendar_ref must be BusinessCalendarRef"
            )
        if not isinstance(self.business_day_convention, BusinessDayConventionCode):
            raise FixedIncomeEconomicsValidationError(
                "settlement business_day_convention must be BusinessDayConventionCode"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.business_day_lag,
            self.calendar_ref.logical_values(),
            self.business_day_convention.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class YieldConvention:
    yield_code: FixedIncomeYieldCode
    day_count: DayCountConventionCode
    compounding: CompoundingConventionCode
    compounding_tenor: FinancialTenor | None = None
    reference: FixedIncomeBenchmarkReference | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.yield_code, FixedIncomeYieldCode):
            raise FixedIncomeEconomicsValidationError(
                "yield convention yield_code must be FixedIncomeYieldCode"
            )
        if not isinstance(self.day_count, DayCountConventionCode):
            raise FixedIncomeEconomicsValidationError(
                "yield convention day_count must be DayCountConventionCode"
            )
        if not isinstance(self.compounding, CompoundingConventionCode):
            raise FixedIncomeEconomicsValidationError(
                "yield convention compounding must be CompoundingConventionCode"
            )
        if self.compounding_tenor is not None and not isinstance(
            self.compounding_tenor, FinancialTenor
        ):
            raise FixedIncomeEconomicsValidationError(
                "yield convention compounding_tenor must be FinancialTenor or None"
            )
        if self.compounding.value == "periodic" and self.compounding_tenor is None:
            raise FixedIncomeEconomicsValidationError(
                "periodic yield compounding requires compounding_tenor"
            )
        if self.reference is not None and not isinstance(
            self.reference, FixedIncomeBenchmarkReference
        ):
            raise FixedIncomeEconomicsValidationError(
                "yield convention reference must be "
                "FixedIncomeBenchmarkReference or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.yield_code.logical_values(),
            self.day_count.logical_values(),
            self.compounding.logical_values(),
            self.compounding_tenor.logical_values()
            if self.compounding_tenor is not None
            else None,
            self.reference.logical_values() if self.reference is not None else None,
        )


class FixedIncomeCashFlowKind(StrEnum):
    COUPON = "coupon"
    PRINCIPAL = "principal"
    REDEMPTION = "redemption"


class FixedIncomeCashFlowDirection(StrEnum):
    RECEIVABLE = "receivable"
    PAYABLE = "payable"


@dataclass(frozen=True, slots=True)
class FixedIncomeCashFlow:
    cash_flow_id: FixedIncomeCashFlowId
    instrument_identity_id: EconomicIdentityId
    kind: FixedIncomeCashFlowKind
    direction: FixedIncomeCashFlowDirection
    amount: FixedIncomeCashAmount
    currency_identity_id: EconomicIdentityId
    payment_date: date
    evidence_ref: FixedIncomeEvidenceRef
    accrual_period: AccrualPeriod | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.cash_flow_id, FixedIncomeCashFlowId):
            raise FixedIncomeEconomicsValidationError(
                "cash flow cash_flow_id must be FixedIncomeCashFlowId"
            )
        _validate_identity(
            self.instrument_identity_id,
            field_name="cash flow instrument identity",
        )
        if not isinstance(self.kind, FixedIncomeCashFlowKind):
            raise FixedIncomeEconomicsValidationError(
                "cash flow kind must be FixedIncomeCashFlowKind"
            )
        if not isinstance(self.direction, FixedIncomeCashFlowDirection):
            raise FixedIncomeEconomicsValidationError(
                "cash flow direction must be FixedIncomeCashFlowDirection"
            )
        if not isinstance(self.amount, FixedIncomeCashAmount):
            raise FixedIncomeEconomicsValidationError(
                "cash flow amount must be FixedIncomeCashAmount"
            )
        _validate_identity(
            self.currency_identity_id,
            field_name="cash flow currency identity",
        )
        _validate_date(self.payment_date, field_name="cash flow payment_date")
        if not isinstance(self.evidence_ref, FixedIncomeEvidenceRef):
            raise FixedIncomeEconomicsValidationError(
                "cash flow evidence_ref must be FixedIncomeEvidenceRef"
            )
        if self.accrual_period is not None and not isinstance(
            self.accrual_period, AccrualPeriod
        ):
            raise FixedIncomeEconomicsValidationError(
                "cash flow accrual_period must be AccrualPeriod or None"
            )
        if self.kind is FixedIncomeCashFlowKind.COUPON:
            if self.accrual_period is None:
                raise FixedIncomeEconomicsValidationError(
                    "coupon cash flow requires accrual_period"
                )
            if self.payment_date != self.accrual_period.payment_date:
                raise FixedIncomeEconomicsValidationError(
                    "coupon cash flow payment_date must match accrual payment_date"
                )
        elif self.accrual_period is not None:
            raise FixedIncomeEconomicsValidationError(
                "non-coupon cash flow must not carry accrual_period"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.cash_flow_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.kind.value,
            self.direction.value,
            self.amount.logical_values(),
            self.currency_identity_id.logical_values(),
            self.payment_date.isoformat(),
            self.evidence_ref.logical_values(),
            self.accrual_period.logical_values()
            if self.accrual_period is not None
            else None,
        )


@dataclass(frozen=True, slots=True)
class FixedIncomeCashFlowSchedule:
    instrument_identity_id: EconomicIdentityId
    cash_flows: tuple[FixedIncomeCashFlow, ...]

    def __post_init__(self) -> None:
        _validate_identity(
            self.instrument_identity_id,
            field_name="cash-flow schedule instrument identity",
        )
        if type(self.cash_flows) is not tuple or not self.cash_flows:
            raise FixedIncomeEconomicsValidationError(
                "cash-flow schedule cash_flows must be a non-empty tuple"
            )
        for cash_flow in self.cash_flows:
            if not isinstance(cash_flow, FixedIncomeCashFlow):
                raise FixedIncomeEconomicsValidationError(
                    "cash-flow schedule entries must be FixedIncomeCashFlow"
                )
            if cash_flow.instrument_identity_id != self.instrument_identity_id:
                raise FixedIncomeEconomicsValidationError(
                    "cash-flow schedule entries must reference the schedule instrument"
                )
        cash_flow_ids = [item.cash_flow_id for item in self.cash_flows]
        if len(cash_flow_ids) != len(set(cash_flow_ids)):
            raise FixedIncomeEconomicsValidationError(
                "cash-flow schedule cash_flow_id values must be unique"
            )
        ordered = tuple(
            sorted(
                self.cash_flows,
                key=lambda item: (item.payment_date, str(item.cash_flow_id.value)),
            )
        )
        object.__setattr__(self, "cash_flows", ordered)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.instrument_identity_id.logical_values(),
            tuple(item.logical_values() for item in self.cash_flows),
        )


@dataclass(frozen=True, slots=True)
class FixedIncomeInstrumentTerms:
    terms_id: FixedIncomeTermsId
    instrument_identity_id: EconomicIdentityId
    denomination_currency_identity_id: EconomicIdentityId
    face_amount: FaceAmount
    issue_date: date
    maturity_date: date | None
    coupon: FixedIncomeCouponTerms
    settlement: SettlementConvention
    yield_convention: YieldConvention
    evidence_ref: FixedIncomeEvidenceRef
    redemption_amount: FixedIncomeCashAmount | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, FixedIncomeTermsId):
            raise FixedIncomeEconomicsValidationError(
                "fixed-income terms_id must be FixedIncomeTermsId"
            )
        _validate_identity(
            self.instrument_identity_id,
            field_name="fixed-income instrument identity",
        )
        _validate_identity(
            self.denomination_currency_identity_id,
            field_name="fixed-income denomination currency identity",
        )
        if self.instrument_identity_id == self.denomination_currency_identity_id:
            raise FixedIncomeEconomicsValidationError(
                "instrument identity and denomination currency identity must differ"
            )
        if not isinstance(self.face_amount, FaceAmount):
            raise FixedIncomeEconomicsValidationError(
                "fixed-income face_amount must be FaceAmount"
            )
        _validate_date(self.issue_date, field_name="fixed-income issue_date")
        if self.maturity_date is not None:
            _validate_date(self.maturity_date, field_name="fixed-income maturity_date")
            if self.maturity_date <= self.issue_date:
                raise FixedIncomeEconomicsValidationError(
                    "fixed-income maturity_date must be after issue_date"
                )
        if not isinstance(
            self.coupon, (FixedCouponTerms, FloatingCouponTerms, ZeroCouponTerms)
        ):
            raise FixedIncomeEconomicsValidationError(
                "fixed-income coupon must be a certified coupon terms type"
            )
        if isinstance(self.coupon, ZeroCouponTerms) and self.maturity_date is None:
            raise FixedIncomeEconomicsValidationError(
                "zero-coupon fixed income requires maturity_date"
            )
        if not isinstance(self.settlement, SettlementConvention):
            raise FixedIncomeEconomicsValidationError(
                "fixed-income settlement must be SettlementConvention"
            )
        if not isinstance(self.yield_convention, YieldConvention):
            raise FixedIncomeEconomicsValidationError(
                "fixed-income yield_convention must be YieldConvention"
            )
        if not isinstance(self.evidence_ref, FixedIncomeEvidenceRef):
            raise FixedIncomeEconomicsValidationError(
                "fixed-income evidence_ref must be FixedIncomeEvidenceRef"
            )
        if self.redemption_amount is not None and not isinstance(
            self.redemption_amount, FixedIncomeCashAmount
        ):
            raise FixedIncomeEconomicsValidationError(
                "fixed-income redemption_amount must be FixedIncomeCashAmount or None"
            )
        if self.redemption_amount is not None and self.maturity_date is None:
            raise FixedIncomeEconomicsValidationError(
                "redemption_amount requires maturity_date"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.denomination_currency_identity_id.logical_values(),
            self.face_amount.logical_values(),
            self.issue_date.isoformat(),
            self.maturity_date.isoformat() if self.maturity_date is not None else None,
            self.coupon.logical_values(),
            self.settlement.logical_values(),
            self.yield_convention.logical_values(),
            self.evidence_ref.logical_values(),
            self.redemption_amount.logical_values()
            if self.redemption_amount is not None
            else None,
        )


def _coupon_day_count(
    coupon: FixedIncomeCouponTerms,
) -> DayCountConventionCode:
    return coupon.day_count


@dataclass(frozen=True, slots=True)
class FixedIncomeEconomicProfile:
    """Immutable composition of terms and optional retained contractual cash flows."""

    terms: FixedIncomeInstrumentTerms
    cash_flow_schedule: FixedIncomeCashFlowSchedule | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms, FixedIncomeInstrumentTerms):
            raise FixedIncomeEconomicsValidationError(
                "fixed-income profile terms must be FixedIncomeInstrumentTerms"
            )
        if self.cash_flow_schedule is not None:
            if not isinstance(self.cash_flow_schedule, FixedIncomeCashFlowSchedule):
                raise FixedIncomeEconomicsValidationError(
                    "fixed-income profile cash_flow_schedule must be "
                    "FixedIncomeCashFlowSchedule or None"
                )
            if (
                self.cash_flow_schedule.instrument_identity_id
                != self.terms.instrument_identity_id
            ):
                raise FixedIncomeEconomicsValidationError(
                    "fixed-income profile schedule must reference terms instrument"
                )
            for cash_flow in self.cash_flow_schedule.cash_flows:
                if cash_flow.payment_date < self.terms.issue_date:
                    raise FixedIncomeEconomicsValidationError(
                        "fixed-income cash flow must not predate issue_date"
                    )
                if cash_flow.kind is FixedIncomeCashFlowKind.COUPON:
                    if isinstance(self.terms.coupon, ZeroCouponTerms):
                        raise FixedIncomeEconomicsValidationError(
                            "zero-coupon terms must not carry coupon cash flows"
                        )
                    if cash_flow.accrual_period is None:
                        raise FixedIncomeEconomicsValidationError(
                            "coupon cash flow requires accrual_period"
                        )
                    if (
                        cash_flow.accrual_period.day_count
                        != _coupon_day_count(self.terms.coupon)
                    ):
                        raise FixedIncomeEconomicsValidationError(
                            "coupon cash-flow day_count must match coupon terms"
                        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.terms.logical_values(),
            self.cash_flow_schedule.logical_values()
            if self.cash_flow_schedule is not None
            else None,
        )
