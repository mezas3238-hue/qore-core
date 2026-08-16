from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class SecuritiesFinancingSemanticsError(InfrastructureError):
    """Base error for bounded securities-financing contract semantics."""

    __slots__ = ()


class SecuritiesFinancingValidationError(SecuritiesFinancingSemanticsError):
    """Violation of a static securities-financing semantic invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise SecuritiesFinancingValidationError(f"{field_name} must be UUID")


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        raise SecuritiesFinancingValidationError(
            f"{field_name} must be EconomicIdentityId"
        )


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        raise SecuritiesFinancingValidationError(f"{field_name} must be date")


def _validate_code(value: str, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise SecuritiesFinancingValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


def _validate_decimal(
    value: Decimal,
    *,
    field_name: str,
    positive: bool = False,
    non_negative: bool = False,
) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise SecuritiesFinancingValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if positive and value <= 0:
        raise SecuritiesFinancingValidationError(f"{field_name} must be positive")
    if non_negative and value < 0:
        raise SecuritiesFinancingValidationError(
            f"{field_name} must be non-negative"
        )


def _canonical_decimal(value: Decimal) -> str:
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class SftTermsId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="SFT terms ID")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class SftEvidenceRef:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="SFT evidence reference")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class SftPartyReferenceId:
    """Opaque contractual party reference; not a legal-identity registry claim."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="SFT party reference ID")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class SftDayCountCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="SFT day-count code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class SftCollateralEligibilityCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="SFT collateral eligibility code")

    def logical_values(self) -> tuple[str, ...]:
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
        return (
            _canonical_decimal(self.amount),
            self.currency_identity_id.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class SftSecurityQuantity:
    security_identity_id: EconomicIdentityId
    quantity: Decimal

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

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.security_identity_id.logical_values(),
            _canonical_decimal(self.quantity),
        )


SftCollateralItem = SftCashAmount | SftSecurityQuantity


@dataclass(frozen=True, slots=True)
class SftRateTerms:
    """Contractual financing-rate material; performs no accrual calculation."""

    kind: SftRateKind
    contractual_rate_or_spread: Decimal
    day_count: SftDayCountCode
    floating_reference_identity_id: EconomicIdentityId | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, SftRateKind):
            raise SecuritiesFinancingValidationError(
                "SFT rate kind must be SftRateKind"
            )
        _validate_decimal(
            self.contractual_rate_or_spread,
            field_name="SFT contractual rate or spread",
        )
        if not isinstance(self.day_count, SftDayCountCode):
            raise SecuritiesFinancingValidationError(
                "SFT day_count must be SftDayCountCode"
            )
        if self.kind is SftRateKind.FIXED:
            if self.floating_reference_identity_id is not None:
                raise SecuritiesFinancingValidationError(
                    "fixed SFT rate must not carry floating reference identity"
                )
            return
        if not isinstance(
            self.floating_reference_identity_id,
            EconomicIdentityId,
        ):
            raise SecuritiesFinancingValidationError(
                "floating SFT rate requires typed reference identity"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.kind.value,
            _canonical_decimal(self.contractual_rate_or_spread),
            self.day_count.logical_values(),
            self.floating_reference_identity_id.logical_values()
            if self.floating_reference_identity_id is not None
            else None,
        )


@dataclass(frozen=True, slots=True)
class SftDurationTerms:
    """Static duration/notice terms; never current termination or notice state."""

    mode: SftDurationMode
    start_date: date
    termination_date: date | None = None
    notice_days: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, SftDurationMode):
            raise SecuritiesFinancingValidationError(
                "SFT duration mode must be SftDurationMode"
            )
        _validate_date(self.start_date, field_name="SFT duration start date")
        if self.termination_date is not None:
            _validate_date(
                self.termination_date,
                field_name="SFT duration termination date",
            )
            if self.termination_date <= self.start_date:
                raise SecuritiesFinancingValidationError(
                    "SFT termination date must be after start date"
                )
        if self.notice_days is not None and (
            type(self.notice_days) is not int or self.notice_days <= 0
        ):
            raise SecuritiesFinancingValidationError(
                "SFT notice_days must be positive int or None"
            )
        if self.mode is SftDurationMode.TERM:
            if self.termination_date is None or self.notice_days is not None:
                raise SecuritiesFinancingValidationError(
                    "term SFT requires termination date and no notice period"
                )
            return
        if self.mode is SftDurationMode.OPEN:
            if self.termination_date is not None:
                raise SecuritiesFinancingValidationError(
                    "open SFT must not invent termination date"
                )
            return
        if self.notice_days is None:
            raise SecuritiesFinancingValidationError(
                "callable SFT requires positive contractual notice days"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mode.value,
            self.start_date.isoformat(),
            self.termination_date.isoformat()
            if self.termination_date is not None
            else None,
            self.notice_days,
        )


@dataclass(frozen=True, slots=True)
class SftArrangementTerms:
    mode: SftArrangementMode
    tri_party_agent_reference_id: SftPartyReferenceId | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, SftArrangementMode):
            raise SecuritiesFinancingValidationError(
                "SFT arrangement mode must be SftArrangementMode"
            )
        if self.mode is SftArrangementMode.BILATERAL:
            if self.tri_party_agent_reference_id is not None:
                raise SecuritiesFinancingValidationError(
                    "bilateral SFT must not carry tri-party agent"
                )
            return
        if not isinstance(
            self.tri_party_agent_reference_id,
            SftPartyReferenceId,
        ):
            raise SecuritiesFinancingValidationError(
                "tri-party SFT requires typed agent reference"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mode.value,
            self.tri_party_agent_reference_id.logical_values()
            if self.tri_party_agent_reference_id is not None
            else None,
        )


@dataclass(frozen=True, slots=True)
class SftMarginTerms:
    """Static contractual margin/haircut ratios; not current margin state."""

    initial_margin_ratio: Decimal | None = None
    haircut_ratio: Decimal | None = None

    def __post_init__(self) -> None:
        if self.initial_margin_ratio is None and self.haircut_ratio is None:
            raise SecuritiesFinancingValidationError(
                "SFT margin terms require initial margin or haircut material"
            )
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
        return (
            _canonical_decimal(self.initial_margin_ratio)
            if self.initial_margin_ratio is not None
            else None,
            _canonical_decimal(self.haircut_ratio)
            if self.haircut_ratio is not None
            else None,
        )


@dataclass(frozen=True, slots=True)
class RepoFarLegTerms:
    """Contractual far-leg date and optional supplied cash; no rate calculation."""

    repurchase_date: date
    repurchase_cash: SftCashAmount | None = None

    def __post_init__(self) -> None:
        _validate_date(self.repurchase_date, field_name="repo repurchase date")
        if self.repurchase_cash is not None and not isinstance(
            self.repurchase_cash,
            SftCashAmount,
        ):
            raise SecuritiesFinancingValidationError(
                "repo repurchase_cash must be SftCashAmount or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.repurchase_date.isoformat(),
            self.repurchase_cash.logical_values()
            if self.repurchase_cash is not None
            else None,
        )


def _validate_parties(
    first: SftPartyReferenceId,
    second: SftPartyReferenceId,
    *,
    first_name: str,
    second_name: str,
) -> None:
    if not isinstance(first, SftPartyReferenceId):
        raise SecuritiesFinancingValidationError(
            f"{first_name} must be SftPartyReferenceId"
        )
    if not isinstance(second, SftPartyReferenceId):
        raise SecuritiesFinancingValidationError(
            f"{second_name} must be SftPartyReferenceId"
        )
    if first == second:
        raise SecuritiesFinancingValidationError(
            f"{first_name} and {second_name} must differ"
        )


def _validate_security_basket(
    securities: tuple[SftSecurityQuantity, ...],
    *,
    field_name: str,
    allow_empty: bool = False,
) -> None:
    if type(securities) is not tuple:
        raise SecuritiesFinancingValidationError(f"{field_name} must be tuple")
    if not securities and not allow_empty:
        raise SecuritiesFinancingValidationError(f"{field_name} must not be empty")
    for security in securities:
        if not isinstance(security, SftSecurityQuantity):
            raise SecuritiesFinancingValidationError(
                f"{field_name} must contain SftSecurityQuantity"
            )
    identities = tuple(item.security_identity_id for item in securities)
    if len(set(identities)) != len(identities):
        raise SecuritiesFinancingValidationError(
            f"{field_name} must not duplicate security identities"
        )


def _validate_collateral(
    collateral: tuple[SftCollateralItem, ...],
    *,
    field_name: str,
) -> None:
    if type(collateral) is not tuple:
        raise SecuritiesFinancingValidationError(f"{field_name} must be tuple")
    for item in collateral:
        if not isinstance(item, (SftCashAmount, SftSecurityQuantity)):
            raise SecuritiesFinancingValidationError(
                f"{field_name} contains unsupported collateral item"
            )


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
        if not isinstance(self.terms_id, SftTermsId):
            raise SecuritiesFinancingValidationError(
                "repo terms_id must be SftTermsId"
            )
        _validate_identity(
            self.instrument_identity_id,
            field_name="repo instrument identity",
        )
        _validate_parties(
            self.seller_reference_id,
            self.buyer_reference_id,
            first_name="repo seller reference",
            second_name="repo buyer reference",
        )
        if not isinstance(self.duration, SftDurationTerms):
            raise SecuritiesFinancingValidationError(
                "repo duration must be SftDurationTerms"
            )
        if not isinstance(self.near_cash, SftCashAmount):
            raise SecuritiesFinancingValidationError(
                "repo near_cash must be SftCashAmount"
            )
        _validate_security_basket(
            self.transferred_securities,
            field_name="repo transferred securities",
        )
        if self.instrument_identity_id in {
            item.security_identity_id for item in self.transferred_securities
        }:
            raise SecuritiesFinancingValidationError(
                "repo instrument identity must not equal transferred security identity"
            )
        if not isinstance(self.financing_rate, SftRateTerms):
            raise SecuritiesFinancingValidationError(
                "repo financing_rate must be SftRateTerms"
            )
        if not isinstance(self.arrangement, SftArrangementTerms):
            raise SecuritiesFinancingValidationError(
                "repo arrangement must be SftArrangementTerms"
            )
        if not isinstance(self.evidence_ref, SftEvidenceRef):
            raise SecuritiesFinancingValidationError(
                "repo evidence_ref must be SftEvidenceRef"
            )
        if self.margin_terms is not None and not isinstance(
            self.margin_terms,
            SftMarginTerms,
        ):
            raise SecuritiesFinancingValidationError(
                "repo margin_terms must be SftMarginTerms or None"
            )
        if self.duration.mode is SftDurationMode.TERM:
            if not isinstance(self.far_leg, RepoFarLegTerms):
                raise SecuritiesFinancingValidationError(
                    "term repo requires contractual far leg"
                )
            if self.far_leg.repurchase_date != self.duration.termination_date:
                raise SecuritiesFinancingValidationError(
                    "term repo far date must equal contractual termination date"
                )
            return
        if self.duration.mode is SftDurationMode.OPEN:
            if self.far_leg is not None:
                raise SecuritiesFinancingValidationError(
                    "open repo must not invent contractual far leg"
                )
            return
        if self.far_leg is not None:
            if self.duration.termination_date is None:
                raise SecuritiesFinancingValidationError(
                    "callable repo far leg requires contractual termination date"
                )
            if self.far_leg.repurchase_date != self.duration.termination_date:
                raise SecuritiesFinancingValidationError(
                    "callable repo far date must equal contractual termination date"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "repo",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.seller_reference_id.logical_values(),
            self.buyer_reference_id.logical_values(),
            self.duration.logical_values(),
            self.near_cash.logical_values(),
            tuple(item.logical_values() for item in self.transferred_securities),
            self.financing_rate.logical_values(),
            self.arrangement.logical_values(),
            self.far_leg.logical_values() if self.far_leg is not None else None,
            self.margin_terms.logical_values()
            if self.margin_terms is not None
            else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class SecuritiesLendingCompensationTerms:
    """Fee and cash-collateral rebate remain distinct contractual quantities."""

    lending_fee_rate: Decimal | None = None
    cash_collateral_rebate_rate: Decimal | None = None

    def __post_init__(self) -> None:
        if (
            self.lending_fee_rate is None
            and self.cash_collateral_rebate_rate is None
        ):
            raise SecuritiesFinancingValidationError(
                "securities-lending compensation requires fee or rebate material"
            )
        if self.lending_fee_rate is not None:
            _validate_decimal(
                self.lending_fee_rate,
                field_name="securities-lending fee rate",
                non_negative=True,
            )
        if self.cash_collateral_rebate_rate is not None:
            _validate_decimal(
                self.cash_collateral_rebate_rate,
                field_name="securities-lending rebate rate",
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            _canonical_decimal(self.lending_fee_rate)
            if self.lending_fee_rate is not None
            else None,
            _canonical_decimal(self.cash_collateral_rebate_rate)
            if self.cash_collateral_rebate_rate is not None
            else None,
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
    margin_terms: SftMarginTerms | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, SftTermsId):
            raise SecuritiesFinancingValidationError(
                "securities-lending terms_id must be SftTermsId"
            )
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
        if not isinstance(self.duration, SftDurationTerms):
            raise SecuritiesFinancingValidationError(
                "securities-lending duration must be SftDurationTerms"
            )
        if not isinstance(self.principal_security, SftSecurityQuantity):
            raise SecuritiesFinancingValidationError(
                "principal_security must be SftSecurityQuantity"
            )
        if self.principal_security.security_identity_id == self.instrument_identity_id:
            raise SecuritiesFinancingValidationError(
                "securities-lending instrument must differ from principal security"
            )
        if not isinstance(
            self.compensation,
            SecuritiesLendingCompensationTerms,
        ):
            raise SecuritiesFinancingValidationError(
                "securities-lending compensation must be typed"
            )
        _validate_collateral(
            self.collateral,
            field_name="securities-lending collateral",
        )
        if not isinstance(self.arrangement, SftArrangementTerms):
            raise SecuritiesFinancingValidationError(
                "securities-lending arrangement must be typed"
            )
        if not isinstance(self.evidence_ref, SftEvidenceRef):
            raise SecuritiesFinancingValidationError(
                "securities-lending evidence_ref must be typed"
            )
        if self.margin_terms is not None and not isinstance(
            self.margin_terms,
            SftMarginTerms,
        ):
            raise SecuritiesFinancingValidationError(
                "securities-lending margin_terms must be typed or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "securities-lending",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.lender_reference_id.logical_values(),
            self.borrower_reference_id.logical_values(),
            self.duration.logical_values(),
            self.principal_security.logical_values(),
            self.compensation.logical_values(),
            tuple(item.logical_values() for item in self.collateral),
            self.arrangement.logical_values(),
            self.margin_terms.logical_values()
            if self.margin_terms is not None
            else None,
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
    collateral_eligibility: SftCollateralEligibilityCode
    eligible_collateral_identity_ids: tuple[EconomicIdentityId, ...]
    evidence_ref: SftEvidenceRef
    margin_terms: SftMarginTerms | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, SftTermsId):
            raise SecuritiesFinancingValidationError(
                "margin-lending terms_id must be SftTermsId"
            )
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
        if not isinstance(self.duration, SftDurationTerms):
            raise SecuritiesFinancingValidationError(
                "margin-lending duration must be SftDurationTerms"
            )
        if not isinstance(self.credit_limit, SftCashAmount):
            raise SecuritiesFinancingValidationError(
                "margin-lending credit_limit must be SftCashAmount"
            )
        if not isinstance(self.financing_rate, SftRateTerms):
            raise SecuritiesFinancingValidationError(
                "margin-lending financing_rate must be SftRateTerms"
            )
        if not isinstance(
            self.collateral_eligibility,
            SftCollateralEligibilityCode,
        ):
            raise SecuritiesFinancingValidationError(
                "margin-lending collateral_eligibility must be typed"
            )
        if type(self.eligible_collateral_identity_ids) is not tuple:
            raise SecuritiesFinancingValidationError(
                "eligible collateral identities must be tuple"
            )
        for identity in self.eligible_collateral_identity_ids:
            _validate_identity(
                identity,
                field_name="eligible collateral identity",
            )
        if len(set(self.eligible_collateral_identity_ids)) != len(
            self.eligible_collateral_identity_ids
        ):
            raise SecuritiesFinancingValidationError(
                "eligible collateral identities must be unique"
            )
        if self.instrument_identity_id in self.eligible_collateral_identity_ids:
            raise SecuritiesFinancingValidationError(
                "margin-lending facility instrument must not be eligible collateral"
            )
        if not isinstance(self.evidence_ref, SftEvidenceRef):
            raise SecuritiesFinancingValidationError(
                "margin-lending evidence_ref must be typed"
            )
        if self.margin_terms is not None and not isinstance(
            self.margin_terms,
            SftMarginTerms,
        ):
            raise SecuritiesFinancingValidationError(
                "margin-lending margin_terms must be typed or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "margin-lending",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.lender_reference_id.logical_values(),
            self.borrower_reference_id.logical_values(),
            self.duration.logical_values(),
            self.credit_limit.logical_values(),
            self.financing_rate.logical_values(),
            self.collateral_eligibility.logical_values(),
            tuple(
                identity.logical_values()
                for identity in self.eligible_collateral_identity_ids
            ),
            self.margin_terms.logical_values()
            if self.margin_terms is not None
            else None,
            self.evidence_ref.logical_values(),
        )
