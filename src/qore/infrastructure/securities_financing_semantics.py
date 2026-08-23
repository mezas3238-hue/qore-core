from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from typing import Never, cast
from uuid import UUID

from qore.infrastructure.fixed_income_economics import DayCountConventionCode
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
class SftCollateralEligibilityCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="SFT collateral eligibility code")

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
        self.__post_init__()
        return (
            _identity_values(
                self.security_identity_id,
                field_name="SFT security identity",
            ),
            _canonical_decimal(self.quantity),
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


@dataclass(frozen=True, slots=True)
class SftRateTerms:
    """Contractual financing-rate material; performs no accrual calculation."""

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
    """Static duration/notice terms; never current termination or notice state."""

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
    """Static contractual margin/haircut ratios; not current margin state."""

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
    """Contractual far-leg date and optional supplied cash; no rate calculation."""

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


@dataclass(frozen=True, slots=True)
class SecuritiesLendingCompensationTerms:
    """Fee and cash-collateral rebate remain distinct contractual quantities."""

    lending_fee_rate: Decimal | None = None
    cash_collateral_rebate_rate: Decimal | None = None

    def __post_init__(self) -> None:
        if self.lending_fee_rate is None and self.cash_collateral_rebate_rate is None:
            _fail("securities-lending compensation requires fee or rebate material")
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
        self.__post_init__()
        return (
            _canonical_decimal(self.lending_fee_rate)
            if self.lending_fee_rate is not None
            else None,
            _canonical_decimal(self.cash_collateral_rebate_rate)
            if self.cash_collateral_rebate_rate is not None
            else None,
        )


def _validate_compensation_child(
    value: SecuritiesLendingCompensationTerms,
) -> None:
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


def _security_sort_key(value: SftSecurityQuantity) -> tuple[str, str]:
    _validate_security_child(value, field_name="SFT security basket item")
    return (str(value.security_identity_id.value), _canonical_decimal(value.quantity))


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


def _collateral_key(value: SftCollateralItem) -> tuple[str, str, str]:
    if type(value) is SftCashAmount:
        cash = cast(SftCashAmount, value)
        _validate_cash_child(cash, field_name="SFT collateral cash")
        return (
            "cash",
            str(cash.currency_identity_id.value),
            _canonical_decimal(cash.amount),
        )
    if type(value) is SftSecurityQuantity:
        security = cast(SftSecurityQuantity, value)
        _validate_security_child(security, field_name="SFT collateral security")
        return (
            "security",
            str(security.security_identity_id.value),
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
            cash = cast(SftCashAmount, item)
            _validate_cash_child(cash, field_name=field_name)
            role_identity_keys.append(("cash", cash.currency_identity_id.value))
        elif type(item) is SftSecurityQuantity:
            security = cast(SftSecurityQuantity, item)
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
            _identity_values(
                self.instrument_identity_id,
                field_name="repo instrument identity",
            ),
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
        _validate_duration_child(
            self.duration,
            field_name="securities-lending duration",
        )
        _validate_security_child(
            self.principal_security,
            field_name="securities-lending principal security",
        )
        if (
            self.principal_security.security_identity_id.value
            == self.instrument_identity_id.value
        ):
            _fail("securities-lending instrument must differ from principal security")
        _validate_compensation_child(self.compensation)
        canonical_collateral = _canonicalize_collateral(
            self.collateral,
            field_name="securities-lending collateral",
        )
        object.__setattr__(self, "collateral", canonical_collateral)
        _validate_arrangement_child(
            self.arrangement,
            field_name="securities-lending arrangement",
        )
        _validate_evidence_child(self.evidence_ref)
        if self.margin_terms is not None:
            _validate_margin_child(
                self.margin_terms,
                field_name="securities-lending margin_terms",
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
    arrangement: SftArrangementTerms
    evidence_ref: SftEvidenceRef
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
        _validate_rate_child(
            self.financing_rate,
            field_name="margin-lending financing_rate",
        )
        _validate_eligibility_child(self.collateral_eligibility)
        canonical_identities = _canonicalize_identity_tuple(
            self.eligible_collateral_identity_ids
        )
        object.__setattr__(
            self,
            "eligible_collateral_identity_ids",
            canonical_identities,
        )
        if self.instrument_identity_id.value in {
            identity.value for identity in canonical_identities
        }:
            _fail("margin-lending facility instrument must not be eligible collateral")
        _validate_arrangement_child(
            self.arrangement,
            field_name="margin-lending arrangement",
        )
        _validate_evidence_child(self.evidence_ref)
        if self.margin_terms is not None:
            _validate_margin_child(
                self.margin_terms,
                field_name="margin-lending margin_terms",
            )

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
            self.collateral_eligibility.logical_values(),
            tuple(
                _identity_values(
                    identity,
                    field_name="eligible collateral identity",
                )
                for identity in self.eligible_collateral_identity_ids
            ),
            self.arrangement.logical_values(),
            self.margin_terms.logical_values()
            if self.margin_terms is not None
            else None,
            self.evidence_ref.logical_values(),
        )
