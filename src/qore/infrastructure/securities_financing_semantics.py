from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from typing import Never
from uuid import UUID

from qore.infrastructure.fixed_income_economics import (
    DayCountConventionCode,
    FinancialTenor,
    FinancialTenorUnit,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class SecuritiesFinancingSemanticsError(InfrastructureError):
    """Base error for bounded securities-financing contract semantics."""

    __slots__ = ()


class SecuritiesFinancingValidationError(SecuritiesFinancingSemanticsError):
    """Violation of a static securities-financing semantic invariant."""

    __slots__ = ()


def _fail(message: str) -> Never:
    raise SecuritiesFinancingValidationError(message)


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if type(value) is not UUID:
        _fail(f"{field_name} must be exact UUID")


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if type(value) is not EconomicIdentityId:
        _fail(f"{field_name} must be exact EconomicIdentityId")
    _validate_uuid(value.value, field_name=f"{field_name}.value")


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        _fail(f"{field_name} must be exact date")


def _validate_code(value: str, *, field_name: str) -> None:
    valid = (
        type(value) is str
        and bool(value)
        and len(value) <= 64
        and fullmatch(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", value) is not None
    )
    if not valid:
        _fail(f"{field_name} must use canonical lowercase code syntax")


def _validate_day_count(value: DayCountConventionCode) -> None:
    if type(value) is not DayCountConventionCode:
        _fail("SFT day_count must be exact DayCountConventionCode")
    _validate_code(value.value, field_name="SFT day-count convention code")


def _validate_financial_tenor(value: FinancialTenor, *, field_name: str) -> None:
    if type(value) is not FinancialTenor:
        _fail(f"{field_name} must be exact FinancialTenor")
    if type(value.value) is not int or value.value <= 0:
        _fail(f"{field_name}.value must be positive int")
    if type(value.unit) is not FinancialTenorUnit:
        _fail(f"{field_name}.unit must be exact FinancialTenorUnit")


def _validate_decimal(
    value: Decimal,
    *,
    field_name: str,
    positive: bool = False,
    non_negative: bool = False,
) -> None:
    if type(value) is not Decimal or not value.is_finite():
        _fail(f"{field_name} must be a finite exact Decimal")
    if positive and value <= 0:
        _fail(f"{field_name} must be positive")
    if non_negative and value < 0:
        _fail(f"{field_name} must be non-negative")


def _canonical_decimal(value: Decimal) -> str:
    """Context-independent compact finite-Decimal representation."""

    parts = value.as_tuple()
    digits = list(parts.digits)
    if not any(digits):
        return "0"

    exponent = int(parts.exponent)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1

    digit_text = "".join(str(digit) for digit in digits)
    sign = "-" if parts.sign else ""
    adjusted_exponent = exponent + len(digits) - 1
    mantissa = digit_text[0]
    if len(digit_text) > 1:
        mantissa += "." + digit_text[1:]
    exponent_sign = "+" if adjusted_exponent >= 0 else ""
    compact = f"{sign}{mantissa}e{exponent_sign}{adjusted_exponent}"

    if exponent >= 0:
        fixed_length = len(sign) + len(digit_text) + exponent
    else:
        point = len(digit_text) + exponent
        if point > 0:
            fixed_length = len(sign) + len(digit_text) + 1
        else:
            fixed_length = len(sign) + 2 + (-point) + len(digit_text)

    if fixed_length > len(compact) + 1:
        return compact

    if exponent >= 0:
        fixed = digit_text + ("0" * exponent)
    else:
        point = len(digit_text) + exponent
        if point > 0:
            fixed = digit_text[:point] + "." + digit_text[point:]
        else:
            fixed = "0." + ("0" * (-point)) + digit_text
    return sign + fixed


def _identity_values(value: EconomicIdentityId, *, field_name: str) -> tuple[str, ...]:
    _validate_identity(value, field_name=field_name)
    return (str(value.value),)


def _tenor_values(value: FinancialTenor, *, field_name: str) -> tuple[object, ...]:
    _validate_financial_tenor(value, field_name=field_name)
    return (value.value, value.unit.value)


@dataclass(frozen=True, slots=True)
class SftTermsId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="SFT terms ID")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class SftEvidenceRef:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="SFT evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class SftPartyReferenceId:
    """Opaque contractual party reference; not a legal-identity registry claim."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="SFT party reference ID")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class SftScheduleReferenceId:
    """Opaque static schedule/terms reference; never a generated calendar."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="SFT schedule reference ID")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class SftCollateralEligibilityCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="SFT collateral eligibility code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class SftSecurityQuantityBasisCode:
    """Provider-neutral contractual quantity basis such as units or nominal-amount."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="SFT security quantity basis code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class SftCompensationAccrualBasisCode:
    """Static compensation accrual-base qualification; never an observed valuation."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="SFT compensation accrual basis code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


class SftDurationMode(StrEnum):
    TERM = "term"
    OPEN = "open"
    CALLABLE = "callable"


class SftRateKind(StrEnum):
    FIXED = "fixed"
    FLOATING = "floating"


class SftArrangementMode(StrEnum):
    BILATERAL = "bilateral"
    TRI_PARTY = "tri-party"


class SftCollateralizationMode(StrEnum):
    UNCOLLATERALIZED = "uncollateralized"
    EXPLICIT = "explicit"
    EXTERNAL_SCHEDULE = "external-schedule"


class SftCompensationPaymentMode(StrEnum):
    PERIODIC = "periodic"
    AT_TERMINATION = "at-termination"
    EXTERNAL_SCHEDULE = "external-schedule"


class SftCompensationResetMode(StrEnum):
    PERIODIC = "periodic"
    AT_PAYMENT = "at-payment"
    EXTERNAL_SCHEDULE = "external-schedule"
    REFERENCE_CONVENTION = "reference-convention"


class SftFinancingPaymentMode(StrEnum):
    PERIODIC = "periodic"
    AT_TERMINATION = "at-termination"
    EXTERNAL_SCHEDULE = "external-schedule"


class SftFinancingResetMode(StrEnum):
    PERIODIC = "periodic"
    AT_PAYMENT = "at-payment"
    EXTERNAL_SCHEDULE = "external-schedule"
    REFERENCE_CONVENTION = "reference-convention"


class SftFinancingFixingTiming(StrEnum):
    """Static placement of a periodic floating fixing relative to its accrual period."""

    IN_ADVANCE = "in-advance"
    IN_ARREARS = "in-arrears"
    REFERENCE_CONVENTION = "reference-convention"


@dataclass(frozen=True, slots=True)
class SftCashAmount:
    amount: Decimal
    currency_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        _validate_decimal(self.amount, field_name="SFT cash amount", positive=True)
        _validate_identity(
            self.currency_identity_id,
            field_name="SFT cash currency identity",
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            _canonical_decimal(self.amount),
            _identity_values(
                self.currency_identity_id,
                field_name="SFT cash currency identity",
            ),
        )


@dataclass(frozen=True, slots=True)
class SftSecurityQuantity:
    security_identity_id: EconomicIdentityId
    quantity: Decimal
    quantity_basis: SftSecurityQuantityBasisCode

    def __post_init__(self) -> None:
        _validate_identity(
            self.security_identity_id,
            field_name="SFT security identity",
        )
        _validate_decimal(
            self.quantity,
            field_name="SFT security quantity",
            positive=True,
        )
        _validate_security_quantity_basis_child(self.quantity_basis)

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            _identity_values(
                self.security_identity_id,
                field_name="SFT security identity",
            ),
            _canonical_decimal(self.quantity),
            self.quantity_basis.logical_values(),
        )


SftCollateralItem = SftCashAmount | SftSecurityQuantity


def _validate_terms_id_child(value: SftTermsId) -> None:
    if type(value) is not SftTermsId:
        _fail("SFT terms_id must be exact SftTermsId")
    _validate_uuid(value.value, field_name="SFT terms_id.value")


def _validate_evidence_child(value: SftEvidenceRef) -> None:
    if type(value) is not SftEvidenceRef:
        _fail("SFT evidence_ref must be exact SftEvidenceRef")
    _validate_uuid(value.value, field_name="SFT evidence_ref.value")


def _validate_party_child(value: SftPartyReferenceId, *, field_name: str) -> None:
    if type(value) is not SftPartyReferenceId:
        _fail(f"{field_name} must be exact SftPartyReferenceId")
    _validate_uuid(value.value, field_name=f"{field_name}.value")


def _validate_schedule_ref_child(value: SftScheduleReferenceId, *, field_name: str) -> None:
    if type(value) is not SftScheduleReferenceId:
        _fail(f"{field_name} must be exact SftScheduleReferenceId")
    _validate_uuid(value.value, field_name=f"{field_name}.value")


def _validate_security_quantity_basis_child(value: SftSecurityQuantityBasisCode) -> None:
    if type(value) is not SftSecurityQuantityBasisCode:
        _fail("SFT security quantity_basis must be exact SftSecurityQuantityBasisCode")
    _validate_code(value.value, field_name="SFT security quantity basis code")


def _validate_compensation_basis_child(value: SftCompensationAccrualBasisCode) -> None:
    if type(value) is not SftCompensationAccrualBasisCode:
        _fail(
            "SFT compensation accrual_basis must be exact "
            "SftCompensationAccrualBasisCode"
        )
    _validate_code(value.value, field_name="SFT compensation accrual basis code")


def _validate_cash_child(value: SftCashAmount, *, field_name: str) -> None:
    if type(value) is not SftCashAmount:
        _fail(f"{field_name} must be exact SftCashAmount")
    _validate_decimal(value.amount, field_name=f"{field_name}.amount", positive=True)
    _validate_identity(
        value.currency_identity_id,
        field_name=f"{field_name}.currency_identity_id",
    )


def _validate_security_child(value: SftSecurityQuantity, *, field_name: str) -> None:
    if type(value) is not SftSecurityQuantity:
        _fail(f"{field_name} must be exact SftSecurityQuantity")
    _validate_identity(
        value.security_identity_id,
        field_name=f"{field_name}.security_identity_id",
    )
    _validate_decimal(
        value.quantity,
        field_name=f"{field_name}.quantity",
        positive=True,
    )
    _validate_security_quantity_basis_child(value.quantity_basis)


@dataclass(frozen=True, slots=True)
class SftRateTerms:
    """Contractual financing-rate material; performs no accrual computation."""

    kind: SftRateKind
    contractual_rate_or_spread: Decimal
    day_count: DayCountConventionCode
    floating_reference_identity_id: EconomicIdentityId | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not SftRateKind:
            _fail("SFT rate kind must be exact SftRateKind")
        _validate_decimal(
            self.contractual_rate_or_spread,
            field_name="SFT contractual rate or spread",
        )
        _validate_day_count(self.day_count)
        if self.kind is SftRateKind.FIXED:
            if self.floating_reference_identity_id is not None:
                _fail("fixed SFT rate must not carry floating reference identity")
            return
        if self.floating_reference_identity_id is None:
            _fail("floating SFT rate requires reference identity")
        _validate_identity(
            self.floating_reference_identity_id,
            field_name="floating SFT rate reference identity",
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.kind.value,
            _canonical_decimal(self.contractual_rate_or_spread),
            (self.day_count.value,),
            _identity_values(
                self.floating_reference_identity_id,
                field_name="floating SFT rate reference identity",
            )
            if self.floating_reference_identity_id is not None
            else None,
        )


def _validate_rate_child(value: SftRateTerms, *, field_name: str) -> None:
    if type(value) is not SftRateTerms:
        _fail(f"{field_name} must be exact SftRateTerms")
    value.__post_init__()


@dataclass(frozen=True, slots=True)
class SftDurationTerms:
    """Static duration/notice terms; never live termination or notice state."""

    mode: SftDurationMode
    start_date: date
    termination_date: date | None = None
    notice_days: int | None = None

    def __post_init__(self) -> None:
        if type(self.mode) is not SftDurationMode:
            _fail("SFT duration mode must be exact SftDurationMode")
        _validate_date(self.start_date, field_name="SFT duration start date")
        if self.termination_date is not None:
            _validate_date(
                self.termination_date,
                field_name="SFT duration termination date",
            )
            if self.termination_date <= self.start_date:
                _fail("SFT termination date must be after start date")
        if self.notice_days is not None and (
            type(self.notice_days) is not int or self.notice_days <= 0
        ):
            _fail("SFT notice_days must be positive int or None")
        if self.mode is SftDurationMode.TERM:
            if self.termination_date is None or self.notice_days is not None:
                _fail("term SFT requires termination date and no notice period")
            return
        if self.mode is SftDurationMode.OPEN:
            if self.termination_date is not None:
                _fail("open SFT must not invent termination date")
            return
        if self.notice_days is None:
            _fail("callable SFT requires positive contractual notice days")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.mode.value,
            self.start_date.isoformat(),
            self.termination_date.isoformat()
            if self.termination_date is not None
            else None,
            self.notice_days,
        )


def _validate_duration_child(value: SftDurationTerms, *, field_name: str) -> None:
    if type(value) is not SftDurationTerms:
        _fail(f"{field_name} must be exact SftDurationTerms")
    value.__post_init__()


@dataclass(frozen=True, slots=True)
class SftArrangementTerms:
    mode: SftArrangementMode
    tri_party_agent_reference_id: SftPartyReferenceId | None = None

    def __post_init__(self) -> None:
        if type(self.mode) is not SftArrangementMode:
            _fail("SFT arrangement mode must be exact SftArrangementMode")
        if self.mode is SftArrangementMode.BILATERAL:
            if self.tri_party_agent_reference_id is not None:
                _fail("bilateral SFT must not carry tri-party agent")
            return
        if self.tri_party_agent_reference_id is None:
            _fail("tri-party SFT requires agent reference")
        _validate_party_child(
            self.tri_party_agent_reference_id,
            field_name="tri-party agent reference",
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.mode.value,
            self.tri_party_agent_reference_id.logical_values()
            if self.tri_party_agent_reference_id is not None
            else None,
        )


def _validate_arrangement_child(
    value: SftArrangementTerms,
    *,
    field_name: str,
) -> None:
    if type(value) is not SftArrangementTerms:
        _fail(f"{field_name} must be exact SftArrangementTerms")
    value.__post_init__()


@dataclass(frozen=True, slots=True)
class SftMarginTerms:
    """Static contractual margin/haircut ratios; not live margin state."""

    initial_margin_ratio: Decimal | None = None
    haircut_ratio: Decimal | None = None

    def __post_init__(self) -> None:
        if self.initial_margin_ratio is None and self.haircut_ratio is None:
            _fail("SFT margin terms require initial margin or haircut material")
        if self.initial_margin_ratio is not None:
            _validate_decimal(
                self.initial_margin_ratio,
                field_name="SFT initial margin ratio",
                non_negative=True,
            )
        if self.haircut_ratio is not None:
            _validate_decimal(
                self.haircut_ratio,
                field_name="SFT haircut ratio",
                non_negative=True,
            )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            _canonical_decimal(self.initial_margin_ratio)
            if self.initial_margin_ratio is not None
            else None,
            _canonical_decimal(self.haircut_ratio)
            if self.haircut_ratio is not None
            else None,
        )


def _validate_margin_child(value: SftMarginTerms, *, field_name: str) -> None:
    if type(value) is not SftMarginTerms:
        _fail(f"{field_name} must be exact SftMarginTerms")
    value.__post_init__()


@dataclass(frozen=True, slots=True)
class RepoFarLegTerms:
    """Contractual far-leg date and optional supplied cash; no rate computation."""

    repurchase_date: date
    repurchase_cash: SftCashAmount | None = None

    def __post_init__(self) -> None:
        _validate_date(self.repurchase_date, field_name="repo repurchase date")
        if self.repurchase_cash is not None:
            _validate_cash_child(
                self.repurchase_cash,
                field_name="repo repurchase cash",
            )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.repurchase_date.isoformat(),
            self.repurchase_cash.logical_values()
            if self.repurchase_cash is not None
            else None,
        )


def _validate_far_leg_child(value: RepoFarLegTerms) -> None:
    if type(value) is not RepoFarLegTerms:
        _fail("repo far_leg must be exact RepoFarLegTerms")
    value.__post_init__()


def _payment_values(
    mode: SftCompensationPaymentMode,
    tenor: FinancialTenor | None,
    schedule_ref: SftScheduleReferenceId | None,
) -> tuple[object, ...]:
    return (
        mode.value,
        _tenor_values(tenor, field_name="securities-lending payment tenor")
        if tenor is not None
        else None,
        schedule_ref.logical_values() if schedule_ref is not None else None,
    )


def _reset_values(
    mode: SftCompensationResetMode,
    tenor: FinancialTenor | None,
    schedule_ref: SftScheduleReferenceId | None,
) -> tuple[object, ...]:
    return (
        mode.value,
        _tenor_values(tenor, field_name="securities-lending reset tenor")
        if tenor is not None
        else None,
        schedule_ref.logical_values() if schedule_ref is not None else None,
    )


def _validate_financing_payment_timing(
    mode: SftFinancingPaymentMode,
    tenor: FinancialTenor | None,
    schedule_ref: SftScheduleReferenceId | None,
) -> None:
    if type(mode) is not SftFinancingPaymentMode:
        _fail("margin-lending financing payment requires exact mode")
    if mode is SftFinancingPaymentMode.PERIODIC:
        if tenor is None or schedule_ref is not None:
            _fail("periodic margin-lending financing payment requires tenor only")
        _validate_financial_tenor(
            tenor,
            field_name="margin-lending financing payment tenor",
        )
        return
    if mode is SftFinancingPaymentMode.AT_TERMINATION:
        if tenor is not None or schedule_ref is not None:
            _fail("at-termination margin-lending payment must not carry timing material")
        return
    if tenor is not None or schedule_ref is None:
        _fail("external-schedule margin-lending payment requires schedule ref only")
    _validate_schedule_ref_child(
        schedule_ref,
        field_name="margin-lending financing payment schedule reference",
    )


def _financing_payment_values(
    mode: SftFinancingPaymentMode,
    tenor: FinancialTenor | None,
    schedule_ref: SftScheduleReferenceId | None,
) -> tuple[object, ...]:
    _validate_financing_payment_timing(mode, tenor, schedule_ref)
    return (
        mode.value,
        _tenor_values(tenor, field_name="margin-lending financing payment tenor")
        if tenor is not None
        else None,
        schedule_ref.logical_values() if schedule_ref is not None else None,
    )


def _validate_financing_reset_timing(
    rate: SftRateTerms,
    mode: SftFinancingResetMode | None,
    tenor: FinancialTenor | None,
    schedule_ref: SftScheduleReferenceId | None,
    fixing_timing: SftFinancingFixingTiming | None,
) -> None:
    if rate.kind is SftRateKind.FIXED:
        if (
            mode is not None
            or tenor is not None
            or schedule_ref is not None
            or fixing_timing is not None
        ):
            _fail("fixed margin-lending financing rate must not carry reset/fixing timing")
        return
    if type(mode) is not SftFinancingResetMode:
        _fail("floating margin-lending financing rate requires exact reset mode")
    if mode is SftFinancingResetMode.PERIODIC:
        if tenor is None or schedule_ref is not None:
            _fail("periodic margin-lending financing reset requires tenor only")
        _validate_financial_tenor(
            tenor,
            field_name="margin-lending financing reset tenor",
        )
        if type(fixing_timing) is not SftFinancingFixingTiming:
            _fail("periodic margin-lending financing reset requires exact fixing timing")
        return
    if mode in {
        SftFinancingResetMode.AT_PAYMENT,
        SftFinancingResetMode.REFERENCE_CONVENTION,
    }:
        if tenor is not None or schedule_ref is not None or fixing_timing is not None:
            _fail("non-scheduled margin-lending financing reset must not carry timing material")
        return
    if tenor is not None or schedule_ref is None or fixing_timing is not None:
        _fail("external-schedule margin-lending financing reset requires schedule ref only")
    _validate_schedule_ref_child(
        schedule_ref,
        field_name="margin-lending financing reset schedule reference",
    )


def _financing_reset_values(
    mode: SftFinancingResetMode,
    tenor: FinancialTenor | None,
    schedule_ref: SftScheduleReferenceId | None,
    fixing_timing: SftFinancingFixingTiming | None,
) -> tuple[object, ...]:
    return (
        mode.value,
        _tenor_values(tenor, field_name="margin-lending financing reset tenor")
        if tenor is not None
        else None,
        schedule_ref.logical_values() if schedule_ref is not None else None,
        fixing_timing.value if fixing_timing is not None else None,
    )


@dataclass(frozen=True, slots=True)
class SecuritiesLendingCompensationLegTerms:
    """One static fee/rebate leg; retains convention but computes no cashflow."""

    rate: SftRateTerms
    currency_identity_id: EconomicIdentityId
    accrual_basis: SftCompensationAccrualBasisCode
    payment_mode: SftCompensationPaymentMode | None = None
    payment_tenor: FinancialTenor | None = None
    payment_schedule_reference: SftScheduleReferenceId | None = None
    reset_mode: SftCompensationResetMode | None = None
    reset_tenor: FinancialTenor | None = None
    reset_schedule_reference: SftScheduleReferenceId | None = None

    def __post_init__(self) -> None:
        _validate_rate_child(self.rate, field_name="securities-lending compensation rate")
        _validate_identity(
            self.currency_identity_id,
            field_name="securities-lending compensation currency identity",
        )
        _validate_compensation_basis_child(self.accrual_basis)
        self._validate_payment_timing()
        self._validate_reset_timing()

    def _validate_payment_timing(self) -> None:
        if type(self.payment_mode) is not SftCompensationPaymentMode:
            _fail("securities-lending compensation requires exact payment mode")
        if self.payment_mode is SftCompensationPaymentMode.PERIODIC:
            if self.payment_tenor is None or self.payment_schedule_reference is not None:
                _fail("periodic compensation payment requires tenor and no schedule ref")
            _validate_financial_tenor(
                self.payment_tenor,
                field_name="securities-lending compensation payment tenor",
            )
            return
        if self.payment_mode is SftCompensationPaymentMode.AT_TERMINATION:
            if self.payment_tenor is not None or self.payment_schedule_reference is not None:
                _fail("at-termination payment must not carry tenor or schedule ref")
            return
        if self.payment_tenor is not None or self.payment_schedule_reference is None:
            _fail("external-schedule payment requires schedule ref and no tenor")
        _validate_schedule_ref_child(
            self.payment_schedule_reference,
            field_name="securities-lending payment schedule reference",
        )

    def _validate_reset_timing(self) -> None:
        if self.rate.kind is SftRateKind.FIXED:
            if (
                self.reset_mode is not None
                or self.reset_tenor is not None
                or self.reset_schedule_reference is not None
            ):
                _fail("fixed securities-lending compensation must not carry reset timing")
            return
        if type(self.reset_mode) is not SftCompensationResetMode:
            _fail("floating securities-lending compensation requires exact reset mode")
        if self.reset_mode is SftCompensationResetMode.PERIODIC:
            if self.reset_tenor is None or self.reset_schedule_reference is not None:
                _fail("periodic compensation reset requires tenor and no schedule ref")
            _validate_financial_tenor(
                self.reset_tenor,
                field_name="securities-lending compensation reset tenor",
            )
            return
        if self.reset_mode in {
            SftCompensationResetMode.AT_PAYMENT,
            SftCompensationResetMode.REFERENCE_CONVENTION,
        }:
            if self.reset_tenor is not None or self.reset_schedule_reference is not None:
                _fail("non-scheduled reset mode must not carry tenor or schedule ref")
            return
        if self.reset_tenor is not None or self.reset_schedule_reference is None:
            _fail("external-schedule reset requires schedule ref and no tenor")
        _validate_schedule_ref_child(
            self.reset_schedule_reference,
            field_name="securities-lending reset schedule reference",
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        assert self.payment_mode is not None
        return (
            self.rate.logical_values(),
            _identity_values(
                self.currency_identity_id,
                field_name="securities-lending compensation currency identity",
            ),
            self.accrual_basis.logical_values(),
            _payment_values(
                self.payment_mode,
                self.payment_tenor,
                self.payment_schedule_reference,
            ),
            _reset_values(
                self.reset_mode,
                self.reset_tenor,
                self.reset_schedule_reference,
            )
            if self.reset_mode is not None
            else None,
        )


def _validate_compensation_leg_child(
    value: SecuritiesLendingCompensationLegTerms,
    *,
    field_name: str,
) -> None:
    if type(value) is not SecuritiesLendingCompensationLegTerms:
        _fail(f"{field_name} must be exact SecuritiesLendingCompensationLegTerms")
    value.__post_init__()


@dataclass(frozen=True, slots=True)
class SecuritiesLendingCompensationTerms:
    """Fee and cash-collateral rebate remain distinct contractual legs."""

    lending_fee: SecuritiesLendingCompensationLegTerms | None = None
    cash_collateral_rebate: SecuritiesLendingCompensationLegTerms | None = None

    def __post_init__(self) -> None:
        if self.lending_fee is None and self.cash_collateral_rebate is None:
            _fail("securities-lending compensation requires fee or rebate material")
        if self.lending_fee is not None:
            _validate_compensation_leg_child(
                self.lending_fee,
                field_name="securities-lending fee",
            )
            if (
                self.lending_fee.rate.kind is SftRateKind.FIXED
                and self.lending_fee.rate.contractual_rate_or_spread < 0
            ):
                _fail("fixed securities-lending fee rate must be non-negative")
        if self.cash_collateral_rebate is not None:
            _validate_compensation_leg_child(
                self.cash_collateral_rebate,
                field_name="securities-lending cash-collateral rebate",
            )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.lending_fee.logical_values() if self.lending_fee is not None else None,
            self.cash_collateral_rebate.logical_values()
            if self.cash_collateral_rebate is not None
            else None,
        )


def _validate_compensation_child(value: SecuritiesLendingCompensationTerms) -> None:
    if type(value) is not SecuritiesLendingCompensationTerms:
        _fail(
            "securities-lending compensation must be exact "
            "SecuritiesLendingCompensationTerms"
        )
    value.__post_init__()


def _validate_eligibility_child(value: SftCollateralEligibilityCode) -> None:
    if type(value) is not SftCollateralEligibilityCode:
        _fail(
            "margin-lending collateral_eligibility must be exact "
            "SftCollateralEligibilityCode"
        )
    _validate_code(value.value, field_name="SFT collateral eligibility code")


def _validate_parties(
    first: SftPartyReferenceId,
    second: SftPartyReferenceId,
    *,
    first_name: str,
    second_name: str,
) -> None:
    _validate_party_child(first, field_name=first_name)
    _validate_party_child(second, field_name=second_name)
    if first.value == second.value:
        _fail(f"{first_name} and {second_name} must differ")


def _security_sort_key(value: SftSecurityQuantity) -> tuple[str, str, str]:
    _validate_security_child(value, field_name="SFT security basket item")
    return (
        str(value.security_identity_id.value),
        value.quantity_basis.value,
        _canonical_decimal(value.quantity),
    )


def _canonicalize_security_basket(
    securities: tuple[SftSecurityQuantity, ...],
    *,
    field_name: str,
) -> tuple[SftSecurityQuantity, ...]:
    if type(securities) is not tuple or not securities:
        _fail(f"{field_name} must be a non-empty exact tuple")
    for security in securities:
        _validate_security_child(security, field_name=field_name)
    identity_values = tuple(item.security_identity_id.value for item in securities)
    if len(set(identity_values)) != len(identity_values):
        _fail(f"{field_name} must not duplicate security identities")
    return tuple(sorted(securities, key=_security_sort_key))


def _collateral_key(value: SftCollateralItem) -> tuple[str, str, str, str]:
    if type(value) is SftCashAmount:
        cash = value
        _validate_cash_child(cash, field_name="SFT collateral cash")
        return (
            "cash",
            str(cash.currency_identity_id.value),
            "cash",
            _canonical_decimal(cash.amount),
        )
    if type(value) is SftSecurityQuantity:
        security = value
        _validate_security_child(security, field_name="SFT collateral security")
        return (
            "security",
            str(security.security_identity_id.value),
            security.quantity_basis.value,
            _canonical_decimal(security.quantity),
        )
    _fail("SFT collateral contains unsupported item")


def _canonicalize_collateral(
    collateral: tuple[SftCollateralItem, ...],
    *,
    field_name: str,
) -> tuple[SftCollateralItem, ...]:
    if type(collateral) is not tuple:
        _fail(f"{field_name} must be exact tuple")
    role_identity_keys: list[tuple[str, UUID]] = []
    for item in collateral:
        if type(item) is SftCashAmount:
            cash = item
            _validate_cash_child(cash, field_name=field_name)
            role_identity_keys.append(("cash", cash.currency_identity_id.value))
        elif type(item) is SftSecurityQuantity:
            security = item
            _validate_security_child(security, field_name=field_name)
            role_identity_keys.append(("security", security.security_identity_id.value))
        else:
            _fail(f"{field_name} contains unsupported collateral item")
    if len(set(role_identity_keys)) != len(role_identity_keys):
        _fail(f"{field_name} must not duplicate role/identity entries")
    return tuple(sorted(collateral, key=_collateral_key))


def _canonicalize_identity_tuple(
    identities: tuple[EconomicIdentityId, ...],
) -> tuple[EconomicIdentityId, ...]:
    if type(identities) is not tuple:
        _fail("eligible collateral identities must be exact tuple")
    for identity in identities:
        _validate_identity(identity, field_name="eligible collateral identity")
    values = tuple(identity.value for identity in identities)
    if len(set(values)) != len(values):
        _fail("eligible collateral identities must be unique")
    return tuple(sorted(identities, key=lambda identity: str(identity.value)))


@dataclass(frozen=True, slots=True)
class RepoTerms:
    """Static repo transfer/financing terms, not settlement or collateral state."""

    terms_id: SftTermsId
    instrument_identity_id: EconomicIdentityId
    seller_reference_id: SftPartyReferenceId
    buyer_reference_id: SftPartyReferenceId
    duration: SftDurationTerms
    near_cash: SftCashAmount
    transferred_securities: tuple[SftSecurityQuantity, ...]
    financing_rate: SftRateTerms
    arrangement: SftArrangementTerms
    evidence_ref: SftEvidenceRef
    far_leg: RepoFarLegTerms | None = None
    margin_terms: SftMarginTerms | None = None

    def __post_init__(self) -> None:
        _validate_terms_id_child(self.terms_id)
        _validate_identity(self.instrument_identity_id, field_name="repo instrument identity")
        _validate_parties(
            self.seller_reference_id,
            self.buyer_reference_id,
            first_name="repo seller reference",
            second_name="repo buyer reference",
        )
        _validate_duration_child(self.duration, field_name="repo duration")
        _validate_cash_child(self.near_cash, field_name="repo near cash")
        canonical_securities = _canonicalize_security_basket(
            self.transferred_securities,
            field_name="repo transferred securities",
        )
        object.__setattr__(self, "transferred_securities", canonical_securities)
        if self.instrument_identity_id.value in {
            item.security_identity_id.value for item in canonical_securities
        }:
            _fail("repo instrument identity must not equal transferred security identity")
        _validate_rate_child(self.financing_rate, field_name="repo financing_rate")
        _validate_arrangement_child(self.arrangement, field_name="repo arrangement")
        _validate_evidence_child(self.evidence_ref)
        if self.margin_terms is not None:
            _validate_margin_child(self.margin_terms, field_name="repo margin_terms")
        if self.duration.mode is SftDurationMode.TERM:
            if self.far_leg is None:
                _fail("term repo requires contractual far leg")
            _validate_far_leg_child(self.far_leg)
            if self.far_leg.repurchase_date != self.duration.termination_date:
                _fail("term repo far date must equal contractual termination date")
        elif self.duration.mode is SftDurationMode.OPEN:
            if self.far_leg is not None:
                _fail("open repo must not invent contractual far leg")
        elif self.far_leg is not None:
            _validate_far_leg_child(self.far_leg)
            if self.duration.termination_date is None:
                _fail("callable repo far leg requires contractual termination date")
            if self.far_leg.repurchase_date != self.duration.termination_date:
                _fail("callable repo far date must equal contractual termination date")
        if self.far_leg is not None and self.far_leg.repurchase_cash is not None:
            if (
                self.far_leg.repurchase_cash.currency_identity_id.value
                != self.near_cash.currency_identity_id.value
            ):
                _fail("repo near and supplied far cash currencies must match")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "repo",
            self.terms_id.logical_values(),
            _identity_values(self.instrument_identity_id, field_name="repo instrument identity"),
            self.seller_reference_id.logical_values(),
            self.buyer_reference_id.logical_values(),
            self.duration.logical_values(),
            self.near_cash.logical_values(),
            tuple(item.logical_values() for item in self.transferred_securities),
            self.financing_rate.logical_values(),
            self.arrangement.logical_values(),
            self.far_leg.logical_values() if self.far_leg is not None else None,
            self.margin_terms.logical_values() if self.margin_terms is not None else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class SecuritiesLendingTerms:
    terms_id: SftTermsId
    instrument_identity_id: EconomicIdentityId
    lender_reference_id: SftPartyReferenceId
    borrower_reference_id: SftPartyReferenceId
    duration: SftDurationTerms
    principal_security: SftSecurityQuantity
    compensation: SecuritiesLendingCompensationTerms
    collateral: tuple[SftCollateralItem, ...]
    arrangement: SftArrangementTerms
    evidence_ref: SftEvidenceRef
    collateralization_mode: SftCollateralizationMode = SftCollateralizationMode.EXPLICIT
    collateral_schedule_reference: SftScheduleReferenceId | None = None
    margin_terms: SftMarginTerms | None = None

    def __post_init__(self) -> None:
        _validate_terms_id_child(self.terms_id)
        _validate_identity(
            self.instrument_identity_id,
            field_name="securities-lending instrument identity",
        )
        _validate_parties(
            self.lender_reference_id,
            self.borrower_reference_id,
            first_name="securities-lending lender reference",
            second_name="securities-lending borrower reference",
        )
        _validate_duration_child(self.duration, field_name="securities-lending duration")
        _validate_security_child(
            self.principal_security,
            field_name="securities-lending principal security",
        )
        if self.principal_security.security_identity_id.value == self.instrument_identity_id.value:
            _fail("securities-lending instrument must differ from principal security")
        _validate_compensation_child(self.compensation)
        canonical_collateral = _canonicalize_collateral(
            self.collateral,
            field_name="securities-lending collateral",
        )
        object.__setattr__(self, "collateral", canonical_collateral)
        self._validate_collateralization()
        _validate_arrangement_child(self.arrangement, field_name="securities-lending arrangement")
        _validate_evidence_child(self.evidence_ref)
        if self.margin_terms is not None:
            _validate_margin_child(self.margin_terms, field_name="securities-lending margin_terms")

    def _validate_collateralization(self) -> None:
        if type(self.collateralization_mode) is not SftCollateralizationMode:
            _fail("securities-lending collateralization_mode must be exact mode")
        if self.collateralization_mode is SftCollateralizationMode.UNCOLLATERALIZED:
            if self.collateral or self.collateral_schedule_reference is not None:
                _fail("uncollateralized securities lending must not carry collateral material")
            return
        if self.collateralization_mode is SftCollateralizationMode.EXPLICIT:
            if not self.collateral or self.collateral_schedule_reference is not None:
                _fail("explicit securities-lending collateral requires non-empty tuple only")
            return
        if self.collateral_schedule_reference is None:
            _fail("external collateral schedule requires schedule reference")
        _validate_schedule_ref_child(
            self.collateral_schedule_reference,
            field_name="securities-lending collateral schedule reference",
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "securities-lending",
            self.terms_id.logical_values(),
            _identity_values(
                self.instrument_identity_id,
                field_name="securities-lending instrument identity",
            ),
            self.lender_reference_id.logical_values(),
            self.borrower_reference_id.logical_values(),
            self.duration.logical_values(),
            self.principal_security.logical_values(),
            self.compensation.logical_values(),
            (
                self.collateralization_mode.value,
                self.collateral_schedule_reference.logical_values()
                if self.collateral_schedule_reference is not None
                else None,
            ),
            tuple(item.logical_values() for item in self.collateral),
            self.arrangement.logical_values(),
            self.margin_terms.logical_values() if self.margin_terms is not None else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class MarginLendingTerms:
    """Static margin-credit facility terms, not utilization or margin state."""

    terms_id: SftTermsId
    instrument_identity_id: EconomicIdentityId
    lender_reference_id: SftPartyReferenceId
    borrower_reference_id: SftPartyReferenceId
    duration: SftDurationTerms
    credit_limit: SftCashAmount
    financing_rate: SftRateTerms
    financing_payment_mode: SftFinancingPaymentMode
    collateral_eligibility: SftCollateralEligibilityCode
    eligible_collateral_identity_ids: tuple[EconomicIdentityId, ...]
    arrangement: SftArrangementTerms
    evidence_ref: SftEvidenceRef
    financing_payment_tenor: FinancialTenor | None = None
    financing_payment_schedule_reference: SftScheduleReferenceId | None = None
    financing_reset_mode: SftFinancingResetMode | None = None
    financing_reset_tenor: FinancialTenor | None = None
    financing_reset_schedule_reference: SftScheduleReferenceId | None = None
    financing_fixing_timing: SftFinancingFixingTiming | None = None
    margin_terms: SftMarginTerms | None = None

    def __post_init__(self) -> None:
        _validate_terms_id_child(self.terms_id)
        _validate_identity(
            self.instrument_identity_id,
            field_name="margin-lending instrument identity",
        )
        _validate_parties(
            self.lender_reference_id,
            self.borrower_reference_id,
            first_name="margin-lending lender reference",
            second_name="margin-lending borrower reference",
        )
        _validate_duration_child(self.duration, field_name="margin-lending duration")
        _validate_cash_child(self.credit_limit, field_name="margin-lending credit_limit")
        _validate_rate_child(self.financing_rate, field_name="margin-lending financing_rate")
        _validate_financing_payment_timing(
            self.financing_payment_mode,
            self.financing_payment_tenor,
            self.financing_payment_schedule_reference,
        )
        _validate_financing_reset_timing(
            self.financing_rate,
            self.financing_reset_mode,
            self.financing_reset_tenor,
            self.financing_reset_schedule_reference,
            self.financing_fixing_timing,
        )
        _validate_eligibility_child(self.collateral_eligibility)
        canonical_identities = _canonicalize_identity_tuple(self.eligible_collateral_identity_ids)
        object.__setattr__(self, "eligible_collateral_identity_ids", canonical_identities)
        if self.instrument_identity_id.value in {
            identity.value for identity in canonical_identities
        }:
            _fail("margin-lending facility instrument must not be eligible collateral")
        _validate_arrangement_child(self.arrangement, field_name="margin-lending arrangement")
        _validate_evidence_child(self.evidence_ref)
        if self.margin_terms is not None:
            _validate_margin_child(self.margin_terms, field_name="margin-lending margin_terms")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "margin-lending",
            self.terms_id.logical_values(),
            _identity_values(
                self.instrument_identity_id,
                field_name="margin-lending instrument identity",
            ),
            self.lender_reference_id.logical_values(),
            self.borrower_reference_id.logical_values(),
            self.duration.logical_values(),
            self.credit_limit.logical_values(),
            self.financing_rate.logical_values(),
            _financing_payment_values(
                self.financing_payment_mode,
                self.financing_payment_tenor,
                self.financing_payment_schedule_reference,
            ),
            _financing_reset_values(
                self.financing_reset_mode,
                self.financing_reset_tenor,
                self.financing_reset_schedule_reference,
                self.financing_fixing_timing,
            )
            if self.financing_reset_mode is not None
            else None,
            self.collateral_eligibility.logical_values(),
            tuple(
                _identity_values(identity, field_name="eligible collateral identity")
                for identity in self.eligible_collateral_identity_ids
            ),
            self.arrangement.logical_values(),
            self.margin_terms.logical_values() if self.margin_terms is not None else None,
            self.evidence_ref.logical_values(),
        )
