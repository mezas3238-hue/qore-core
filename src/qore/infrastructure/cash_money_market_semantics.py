from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.derivative_contract_semantics import (
    DerivativePriceQuoteBasisCode,
    DerivativeStrike,
    DerivativeStrikeBasis,
)
from qore.infrastructure.fixed_income_economics import DayCountConventionCode, FinancialTenor
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class CashMoneyMarketSemanticsError(InfrastructureError):
    __slots__ = ()


class CashMoneyMarketValidationError(CashMoneyMarketSemanticsError):
    __slots__ = ()


def _fail(message: str) -> None:
    raise CashMoneyMarketValidationError(message)


def _uuid(value: UUID, name: str) -> None:
    if type(value) is not UUID:
        _fail(f"{name} must be UUID")


def _identity(value: EconomicIdentityId, name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        _fail(f"{name} must be EconomicIdentityId")


def _date(value: date, name: str) -> None:
    if type(value) is not date:
        _fail(f"{name} must be date")


def _decimal(value: Decimal, name: str, *, positive: bool = False) -> None:
    if type(value) is not Decimal or not value.is_finite():
        _fail(f"{name} must be a finite Decimal")
    if positive and value <= 0:
        _fail(f"{name} must be positive")


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    return "0" if normalized == 0 else format(normalized, "f")


def _dates(values: tuple[date, ...], name: str) -> tuple[date, ...]:
    if type(values) is not tuple or not values:
        _fail(f"{name} must be a non-empty tuple")
    for value in values:
        _date(value, f"{name} entry")
    if len(set(values)) != len(values):
        _fail(f"{name} must be unique")
    return tuple(sorted(values))


def _inside(values: tuple[date, ...], start: date, end: date, name: str) -> None:
    if any(value < start or value > end for value in values):
        _fail(f"{name} must lie within the contractual interval")


@dataclass(frozen=True, slots=True)
class CashMoneyMarketTermsId:
    value: UUID

    def __post_init__(self) -> None:
        _uuid(self.value, "cash/money-market terms id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CashMoneyMarketEvidenceRef:
    value: UUID

    def __post_init__(self) -> None:
        _uuid(self.value, "cash/money-market evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CashMoneyMarketDepositPrincipal:
    value: Decimal

    def __post_init__(self) -> None:
        _decimal(self.value, "deposit principal", positive=True)

    def logical_values(self) -> tuple[str, ...]:
        return (_decimal_text(self.value),)


@dataclass(frozen=True, slots=True)
class CashMoneyMarketCommercialPaperFaceAmount:
    value: Decimal

    def __post_init__(self) -> None:
        _decimal(self.value, "commercial-paper face amount", positive=True)

    def logical_values(self) -> tuple[str, ...]:
        return (_decimal_text(self.value),)


@dataclass(frozen=True, slots=True)
class CashMoneyMarketCommercialPaperIssuePrice:
    value: Decimal

    def __post_init__(self) -> None:
        _decimal(self.value, "commercial-paper issue price", positive=True)

    def logical_values(self) -> tuple[str, ...]:
        return (_decimal_text(self.value),)


@dataclass(frozen=True, slots=True)
class CashMoneyMarketContractualRate:
    value: Decimal

    def __post_init__(self) -> None:
        _decimal(self.value, "contractual rate")

    def logical_values(self) -> tuple[str, ...]:
        return (_decimal_text(self.value),)


@dataclass(frozen=True, slots=True)
class CashMoneyMarketFloatingSpread:
    value: Decimal

    def __post_init__(self) -> None:
        _decimal(self.value, "floating spread")

    def logical_values(self) -> tuple[str, ...]:
        return (_decimal_text(self.value),)


@dataclass(frozen=True, slots=True)
class CashMoneyMarketFloatingMultiplier:
    value: Decimal

    def __post_init__(self) -> None:
        _decimal(self.value, "floating multiplier", positive=True)

    def logical_values(self) -> tuple[str, ...]:
        return (_decimal_text(self.value),)


class DualCurrencyFxQuoteOrientation(StrEnum):
    ALTERNATE_PER_PRINCIPAL = "alternate-per-principal"
    PRINCIPAL_PER_ALTERNATE = "principal-per-alternate"


class DualCurrencyTriggerComparator(StrEnum):
    LESS_THAN = "less-than"
    LESS_THAN_OR_EQUAL = "less-than-or-equal"
    GREATER_THAN = "greater-than"
    GREATER_THAN_OR_EQUAL = "greater-than-or-equal"


@dataclass(frozen=True, slots=True)
class TermDepositDualCurrencyFeature:
    base_currency_identity_id: EconomicIdentityId
    alternate_currency_identity_id: EconomicIdentityId
    fx_fixing_identity_id: EconomicIdentityId
    fixing_date: date
    strike: DerivativeStrike
    orientation: DualCurrencyFxQuoteOrientation
    comparator: DualCurrencyTriggerComparator
    true_payout_identity_id: EconomicIdentityId
    false_payout_identity_id: EconomicIdentityId
    evidence_ref: CashMoneyMarketEvidenceRef

    def __post_init__(self) -> None:
        for value, name in (
            (self.base_currency_identity_id, "DCD base currency"),
            (self.alternate_currency_identity_id, "DCD alternate currency"),
            (self.fx_fixing_identity_id, "DCD FX fixing identity"),
            (self.true_payout_identity_id, "DCD true payout identity"),
            (self.false_payout_identity_id, "DCD false payout identity"),
        ):
            _identity(value, name)
        _date(self.fixing_date, "DCD fixing date")
        if not isinstance(self.strike, DerivativeStrike):
            _fail("DCD strike must be DerivativeStrike")
        if not isinstance(self.orientation, DualCurrencyFxQuoteOrientation):
            _fail("DCD orientation must be DualCurrencyFxQuoteOrientation")
        if not isinstance(self.comparator, DualCurrencyTriggerComparator):
            _fail("DCD comparator must be DualCurrencyTriggerComparator")
        if not isinstance(self.evidence_ref, CashMoneyMarketEvidenceRef):
            _fail("DCD evidence_ref must be CashMoneyMarketEvidenceRef")
        if self.base_currency_identity_id == self.alternate_currency_identity_id:
            _fail("DCD currencies must differ")
        if self.fx_fixing_identity_id in {
            self.base_currency_identity_id,
            self.alternate_currency_identity_id,
        }:
            _fail("DCD FX fixing identity must differ from both currencies")
        if self.strike.basis is not DerivativeStrikeBasis.PRICE or self.strike.value <= 0:
            _fail("DCD strike must be a positive PRICE strike")
        if self.strike.convention is not None:
            _fail("DCD PRICE strike must not carry convention")
        if self.strike.price_quote_basis != DerivativePriceQuoteBasisCode(
            "currency-per-unit"
        ):
            _fail("DCD PRICE strike must use currency-per-unit")
        expected_quote = (
            self.alternate_currency_identity_id
            if self.orientation is DualCurrencyFxQuoteOrientation.ALTERNATE_PER_PRINCIPAL
            else self.base_currency_identity_id
        )
        if self.strike.quote_identity_id != expected_quote:
            _fail("DCD strike quote identity must match orientation")
        if (
            self.true_payout_identity_id == self.false_payout_identity_id
            or {self.true_payout_identity_id, self.false_payout_identity_id}
            != {self.base_currency_identity_id, self.alternate_currency_identity_id}
        ):
            _fail("DCD payouts must be the two distinct DCD currencies")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "dual-currency",
            self.orientation.value,
            self.comparator.value,
            self.base_currency_identity_id.logical_values(),
            self.alternate_currency_identity_id.logical_values(),
            self.fx_fixing_identity_id.logical_values(),
            self.fixing_date.isoformat(),
            self.strike.logical_values(),
            self.true_payout_identity_id.logical_values(),
            self.false_payout_identity_id.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class TermDepositTerms:
    terms_id: CashMoneyMarketTermsId
    instrument_identity_id: EconomicIdentityId
    deposit_obligor_identity_id: EconomicIdentityId
    principal: CashMoneyMarketDepositPrincipal
    denomination_currency_identity_id: EconomicIdentityId
    start_date: date
    maturity_date: date
    contractual_rate: CashMoneyMarketContractualRate
    day_count: DayCountConventionCode
    evidence_ref: CashMoneyMarketEvidenceRef
    dual_currency_feature: TermDepositDualCurrencyFeature | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, CashMoneyMarketTermsId):
            _fail("term-deposit terms_id must be CashMoneyMarketTermsId")
        for value, name in (
            (self.instrument_identity_id, "term-deposit instrument"),
            (self.deposit_obligor_identity_id, "term-deposit obligor"),
            (self.denomination_currency_identity_id, "term-deposit currency"),
        ):
            _identity(value, name)
        if not isinstance(self.principal, CashMoneyMarketDepositPrincipal):
            _fail("term-deposit principal must be CashMoneyMarketDepositPrincipal")
        _date(self.start_date, "term-deposit start date")
        _date(self.maturity_date, "term-deposit maturity date")
        if not isinstance(self.contractual_rate, CashMoneyMarketContractualRate):
            _fail("term-deposit rate must be CashMoneyMarketContractualRate")
        if not isinstance(self.day_count, DayCountConventionCode):
            _fail("term-deposit day_count must be DayCountConventionCode")
        if not isinstance(self.evidence_ref, CashMoneyMarketEvidenceRef):
            _fail("term-deposit evidence_ref must be CashMoneyMarketEvidenceRef")
        if len(
            {
                self.instrument_identity_id,
                self.deposit_obligor_identity_id,
                self.denomination_currency_identity_id,
            }
        ) != 3:
            _fail("term-deposit instrument, obligor, and currency must differ")
        if self.maturity_date <= self.start_date:
            _fail("term-deposit maturity must be after start")
        feature = self.dual_currency_feature
        if feature is not None:
            if not isinstance(feature, TermDepositDualCurrencyFeature):
                _fail("dual_currency_feature must be TermDepositDualCurrencyFeature")
            if feature.base_currency_identity_id != self.denomination_currency_identity_id:
                _fail("DCD base currency must match term-deposit denomination")
            if not self.start_date <= feature.fixing_date <= self.maturity_date:
                _fail("DCD fixing date must lie within term-deposit interval")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "term-deposit",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.deposit_obligor_identity_id.logical_values(),
            self.principal.logical_values(),
            self.denomination_currency_identity_id.logical_values(),
            self.start_date.isoformat(),
            self.maturity_date.isoformat(),
            self.contractual_rate.logical_values(),
            self.day_count.logical_values(),
            self.dual_currency_feature.logical_values()
            if self.dual_currency_feature is not None
            else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CommercialPaperPaymentDateSchedule:
    dates: tuple[date, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "dates", _dates(self.dates, "CP payment dates"))

    def logical_values(self) -> tuple[tuple[str, ...]]:
        return (tuple(value.isoformat() for value in self.dates),)


@dataclass(frozen=True, slots=True)
class CommercialPaperResetDateSchedule:
    dates: tuple[date, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "dates", _dates(self.dates, "CP reset dates"))

    def logical_values(self) -> tuple[tuple[str, ...]]:
        return (tuple(value.isoformat() for value in self.dates),)


@dataclass(frozen=True, slots=True)
class CommercialPaperAtParPricing:
    def logical_values(self) -> tuple[str, ...]:
        return ("at-par",)


@dataclass(frozen=True, slots=True)
class CommercialPaperDiscountedPricing:
    issue_price: CashMoneyMarketCommercialPaperIssuePrice

    def __post_init__(self) -> None:
        if not isinstance(self.issue_price, CashMoneyMarketCommercialPaperIssuePrice):
            _fail("discounted CP issue_price must be CashMoneyMarketCommercialPaperIssuePrice")

    def logical_values(self) -> tuple[object, ...]:
        return ("discounted", self.issue_price.logical_values())


type CommercialPaperPricingTerms = (
    CommercialPaperAtParPricing | CommercialPaperDiscountedPricing
)


@dataclass(frozen=True, slots=True)
class CommercialPaperNoInterestTerms:
    def logical_values(self) -> tuple[str, ...]:
        return ("none",)


@dataclass(frozen=True, slots=True)
class CommercialPaperFixedInterestTerms:
    contractual_rate: CashMoneyMarketContractualRate
    day_count: DayCountConventionCode
    payment_dates: CommercialPaperPaymentDateSchedule

    def __post_init__(self) -> None:
        if not isinstance(self.contractual_rate, CashMoneyMarketContractualRate):
            _fail("fixed CP rate must be CashMoneyMarketContractualRate")
        if not isinstance(self.day_count, DayCountConventionCode):
            _fail("fixed CP day_count must be DayCountConventionCode")
        if not isinstance(self.payment_dates, CommercialPaperPaymentDateSchedule):
            _fail("fixed CP payment_dates must be CommercialPaperPaymentDateSchedule")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fixed",
            self.contractual_rate.logical_values(),
            self.day_count.logical_values(),
            self.payment_dates.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CommercialPaperFloatingInterestTerms:
    reference_identity_id: EconomicIdentityId
    reset_dates: CommercialPaperResetDateSchedule
    payment_dates: CommercialPaperPaymentDateSchedule
    day_count: DayCountConventionCode
    index_maturity: FinancialTenor | None = None
    spread: CashMoneyMarketFloatingSpread = field(
        default_factory=lambda: CashMoneyMarketFloatingSpread(Decimal("0"))
    )
    multiplier: CashMoneyMarketFloatingMultiplier = field(
        default_factory=lambda: CashMoneyMarketFloatingMultiplier(Decimal("1"))
    )

    def __post_init__(self) -> None:
        _identity(self.reference_identity_id, "floating CP reference")
        if not isinstance(self.reset_dates, CommercialPaperResetDateSchedule):
            _fail("floating CP reset_dates must be CommercialPaperResetDateSchedule")
        if not isinstance(self.payment_dates, CommercialPaperPaymentDateSchedule):
            _fail("floating CP payment_dates must be CommercialPaperPaymentDateSchedule")
        if not isinstance(self.day_count, DayCountConventionCode):
            _fail("floating CP day_count must be DayCountConventionCode")
        if self.index_maturity is not None and not isinstance(
            self.index_maturity, FinancialTenor
        ):
            _fail("floating CP index_maturity must be FinancialTenor or None")
        if not isinstance(self.spread, CashMoneyMarketFloatingSpread):
            _fail("floating CP spread must be CashMoneyMarketFloatingSpread")
        if not isinstance(self.multiplier, CashMoneyMarketFloatingMultiplier):
            _fail("floating CP multiplier must be CashMoneyMarketFloatingMultiplier")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "floating",
            self.reference_identity_id.logical_values(),
            self.index_maturity.logical_values() if self.index_maturity is not None else None,
            self.spread.logical_values(),
            self.multiplier.logical_values(),
            self.reset_dates.logical_values(),
            self.payment_dates.logical_values(),
            self.day_count.logical_values(),
        )


type CommercialPaperInterestTerms = (
    CommercialPaperNoInterestTerms
    | CommercialPaperFixedInterestTerms
    | CommercialPaperFloatingInterestTerms
)


@dataclass(frozen=True, slots=True)
class CommercialPaperTerms:
    terms_id: CashMoneyMarketTermsId
    instrument_identity_id: EconomicIdentityId
    issuer_obligor_identity_id: EconomicIdentityId
    denomination_currency_identity_id: EconomicIdentityId
    face_redemption_amount: CashMoneyMarketCommercialPaperFaceAmount
    issue_date: date
    maturity_date: date
    pricing: CommercialPaperPricingTerms
    interest: CommercialPaperInterestTerms
    evidence_ref: CashMoneyMarketEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, CashMoneyMarketTermsId):
            _fail("CP terms_id must be CashMoneyMarketTermsId")
        for value, name in (
            (self.instrument_identity_id, "CP instrument"),
            (self.issuer_obligor_identity_id, "CP issuer"),
            (self.denomination_currency_identity_id, "CP currency"),
        ):
            _identity(value, name)
        if not isinstance(self.face_redemption_amount, CashMoneyMarketCommercialPaperFaceAmount):
            _fail("CP face amount must be CashMoneyMarketCommercialPaperFaceAmount")
        _date(self.issue_date, "CP issue date")
        _date(self.maturity_date, "CP maturity date")
        if not isinstance(
            self.pricing, (CommercialPaperAtParPricing, CommercialPaperDiscountedPricing)
        ):
            _fail("CP pricing must be a typed pricing variant")
        if not isinstance(
            self.interest,
            (
                CommercialPaperNoInterestTerms,
                CommercialPaperFixedInterestTerms,
                CommercialPaperFloatingInterestTerms,
            ),
        ):
            _fail("CP interest must be a typed interest variant")
        if not isinstance(self.evidence_ref, CashMoneyMarketEvidenceRef):
            _fail("CP evidence_ref must be CashMoneyMarketEvidenceRef")
        identities = {
            self.instrument_identity_id,
            self.issuer_obligor_identity_id,
            self.denomination_currency_identity_id,
        }
        if len(identities) != 3:
            _fail("CP instrument, issuer, and currency must differ")
        if self.maturity_date <= self.issue_date:
            _fail("CP maturity must be after issue")
        if isinstance(self.pricing, CommercialPaperDiscountedPricing):
            if self.pricing.issue_price.value >= self.face_redemption_amount.value:
                _fail("discounted CP issue price must be below face amount")
        if isinstance(self.interest, CommercialPaperNoInterestTerms) and isinstance(
            self.pricing, CommercialPaperAtParPricing
        ):
            _fail("bounded CP rejects no-interest at-par issuance")
        if isinstance(self.interest, CommercialPaperFixedInterestTerms):
            _inside(
                self.interest.payment_dates.dates,
                self.issue_date,
                self.maturity_date,
                "CP payment dates",
            )
        elif isinstance(self.interest, CommercialPaperFloatingInterestTerms):
            if self.interest.reference_identity_id in identities:
                _fail("floating CP reference must differ from instrument, issuer, and currency")
            _inside(
                self.interest.reset_dates.dates,
                self.issue_date,
                self.maturity_date,
                "CP reset dates",
            )
            _inside(
                self.interest.payment_dates.dates,
                self.issue_date,
                self.maturity_date,
                "CP payment dates",
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "commercial-paper",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.issuer_obligor_identity_id.logical_values(),
            self.denomination_currency_identity_id.logical_values(),
            self.face_redemption_amount.logical_values(),
            self.issue_date.isoformat(),
            self.maturity_date.isoformat(),
            self.pricing.logical_values(),
            self.interest.logical_values(),
            self.evidence_ref.logical_values(),
        )


class CertificateOfDepositNegotiability(StrEnum):
    NEGOTIABLE = "negotiable"
    NON_NEGOTIABLE = "non-negotiable"


@dataclass(frozen=True, slots=True)
class CertificateOfDepositResetDateSchedule:
    dates: tuple[date, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "dates", _dates(self.dates, "CD reset dates"))

    def logical_values(self) -> tuple[tuple[str, ...]]:
        return (tuple(value.isoformat() for value in self.dates),)


@dataclass(frozen=True, slots=True)
class CertificateOfDepositFixedRateTerms:
    contractual_rate: CashMoneyMarketContractualRate
    day_count: DayCountConventionCode

    def __post_init__(self) -> None:
        if not isinstance(self.contractual_rate, CashMoneyMarketContractualRate):
            _fail("fixed CD rate must be CashMoneyMarketContractualRate")
        if not isinstance(self.day_count, DayCountConventionCode):
            _fail("fixed CD day_count must be DayCountConventionCode")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fixed-rate",
            self.contractual_rate.logical_values(),
            self.day_count.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CertificateOfDepositReferenceLinkedRateTerms:
    reference_identity_id: EconomicIdentityId
    spread: CashMoneyMarketFloatingSpread
    reset_schedule: CertificateOfDepositResetDateSchedule
    day_count: DayCountConventionCode

    def __post_init__(self) -> None:
        _identity(self.reference_identity_id, "reference-linked CD reference")
        if not isinstance(self.spread, CashMoneyMarketFloatingSpread):
            _fail("reference-linked CD spread must be CashMoneyMarketFloatingSpread")
        if not isinstance(self.reset_schedule, CertificateOfDepositResetDateSchedule):
            _fail(
                "reference-linked CD reset_schedule must be "
                "CertificateOfDepositResetDateSchedule"
            )
        if not isinstance(self.day_count, DayCountConventionCode):
            _fail("reference-linked CD day_count must be DayCountConventionCode")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "reference-linked",
            self.reference_identity_id.logical_values(),
            self.spread.logical_values(),
            self.reset_schedule.logical_values(),
            self.day_count.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CertificateOfDepositPresetRateStep:
    effective_date: date
    contractual_rate: CashMoneyMarketContractualRate

    def __post_init__(self) -> None:
        _date(self.effective_date, "preset CD effective date")
        if not isinstance(self.contractual_rate, CashMoneyMarketContractualRate):
            _fail("preset CD rate must be CashMoneyMarketContractualRate")

    def logical_values(self) -> tuple[object, ...]:
        return (self.effective_date.isoformat(), self.contractual_rate.logical_values())


@dataclass(frozen=True, slots=True)
class CertificateOfDepositPresetStepSchedule:
    steps: tuple[CertificateOfDepositPresetRateStep, ...]

    def __post_init__(self) -> None:
        if type(self.steps) is not tuple or not self.steps:
            _fail("preset CD steps must be a non-empty tuple")
        for step in self.steps:
            if not isinstance(step, CertificateOfDepositPresetRateStep):
                _fail("preset CD steps must contain CertificateOfDepositPresetRateStep")
        effective_dates = tuple(step.effective_date for step in self.steps)
        if len(set(effective_dates)) != len(effective_dates):
            _fail("preset CD effective dates must be unique")
        object.__setattr__(
            self, "steps", tuple(sorted(self.steps, key=lambda step: step.effective_date))
        )

    def logical_values(self) -> tuple[object, ...]:
        return (tuple(step.logical_values() for step in self.steps),)


@dataclass(frozen=True, slots=True)
class CertificateOfDepositPresetStepsRateTerms:
    steps: CertificateOfDepositPresetStepSchedule
    day_count: DayCountConventionCode

    def __post_init__(self) -> None:
        if not isinstance(self.steps, CertificateOfDepositPresetStepSchedule):
            _fail("preset CD steps must be CertificateOfDepositPresetStepSchedule")
        if not isinstance(self.day_count, DayCountConventionCode):
            _fail("preset CD day_count must be DayCountConventionCode")

    def logical_values(self) -> tuple[object, ...]:
        return ("preset-steps", self.steps.logical_values(), self.day_count.logical_values())


type CertificateOfDepositReturnTerms = (
    CertificateOfDepositFixedRateTerms
    | CertificateOfDepositReferenceLinkedRateTerms
    | CertificateOfDepositPresetStepsRateTerms
)


@dataclass(frozen=True, slots=True)
class CertificateOfDepositTerms:
    terms_id: CashMoneyMarketTermsId
    instrument_identity_id: EconomicIdentityId
    issuing_institution_identity_id: EconomicIdentityId
    denomination_currency_identity_id: EconomicIdentityId
    deposit_principal: CashMoneyMarketDepositPrincipal
    issue_start_date: date
    maturity_date: date
    negotiability: CertificateOfDepositNegotiability
    return_terms: CertificateOfDepositReturnTerms
    evidence_ref: CashMoneyMarketEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, CashMoneyMarketTermsId):
            _fail("CD terms_id must be CashMoneyMarketTermsId")
        for value, name in (
            (self.instrument_identity_id, "CD instrument"),
            (self.issuing_institution_identity_id, "CD institution"),
            (self.denomination_currency_identity_id, "CD currency"),
        ):
            _identity(value, name)
        if not isinstance(self.deposit_principal, CashMoneyMarketDepositPrincipal):
            _fail("CD deposit_principal must be CashMoneyMarketDepositPrincipal")
        _date(self.issue_start_date, "CD issue/start date")
        _date(self.maturity_date, "CD maturity date")
        if not isinstance(self.negotiability, CertificateOfDepositNegotiability):
            _fail("CD negotiability must be CertificateOfDepositNegotiability")
        if not isinstance(
            self.return_terms,
            (
                CertificateOfDepositFixedRateTerms,
                CertificateOfDepositReferenceLinkedRateTerms,
                CertificateOfDepositPresetStepsRateTerms,
            ),
        ):
            _fail("CD return_terms must be a typed return variant")
        if not isinstance(self.evidence_ref, CashMoneyMarketEvidenceRef):
            _fail("CD evidence_ref must be CashMoneyMarketEvidenceRef")
        identities = {
            self.instrument_identity_id,
            self.issuing_institution_identity_id,
            self.denomination_currency_identity_id,
        }
        if len(identities) != 3:
            _fail("CD instrument, institution, and currency must differ")
        if self.maturity_date <= self.issue_start_date:
            _fail("CD maturity must be after issue/start")
        if isinstance(self.return_terms, CertificateOfDepositReferenceLinkedRateTerms):
            if self.return_terms.reference_identity_id in identities:
                _fail(
                    "reference-linked CD reference must differ from "
                    "instrument/institution/currency"
                )
            _inside(
                self.return_terms.reset_schedule.dates,
                self.issue_start_date,
                self.maturity_date,
                "CD reset dates",
            )
        elif isinstance(self.return_terms, CertificateOfDepositPresetStepsRateTerms):
            _inside(
                tuple(step.effective_date for step in self.return_terms.steps.steps),
                self.issue_start_date,
                self.maturity_date,
                "CD preset step dates",
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "certificate-of-deposit",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.issuing_institution_identity_id.logical_values(),
            self.denomination_currency_identity_id.logical_values(),
            self.deposit_principal.logical_values(),
            self.issue_start_date.isoformat(),
            self.maturity_date.isoformat(),
            self.negotiability.value,
            self.return_terms.logical_values(),
            self.evidence_ref.logical_values(),
        )
