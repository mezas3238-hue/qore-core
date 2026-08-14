from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeStrike,
    DerivativeStrikeBasis,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentityId,
    IdentityRelationshipId,
)
from qore.kernel.errors import InfrastructureError


class EquityFundCorporateActionError(InfrastructureError):
    """Base error for provider-neutral equity/fund/corporate-action semantics."""

    __slots__ = ()


class EquityFundCorporateActionValidationError(EquityFundCorporateActionError):
    """Violation of an equity/fund/corporate-action semantic invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise EquityFundCorporateActionValidationError(f"{field_name} must be UUID")


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        raise EquityFundCorporateActionValidationError(
            f"{field_name} must be EconomicIdentityId"
        )


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        raise EquityFundCorporateActionValidationError(f"{field_name} must be date")


def _validate_code(value: str, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) > 64
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        raise EquityFundCorporateActionValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )


def _validate_positive_decimal(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise EquityFundCorporateActionValidationError(
            f"{field_name} must be a positive finite Decimal"
        )


def _canonical_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class EquityFundTermsId:
    """Local immutable terms identity; never an economic instrument identity."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="equity/fund terms id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CorporateActionId:
    """Stable local identity for one corporate action across immutable revisions."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="corporate action id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class CorporateActionRevision:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value <= 0:
            raise EquityFundCorporateActionValidationError(
                "corporate action revision must be a positive int"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class EquityFundEvidenceRef:
    """Opaque reference to retained evidence; never evidence content."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="equity/fund evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class EquityShareClassCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="equity share-class code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class DepositaryReceiptProgramCode:
    """Program semantic such as adr/gdr; never a provider symbol or listing ID."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="depositary receipt program code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class FundBenchmarkRoleCode:
    """Relationship role such as primary-benchmark or tracking-index."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="fund benchmark role code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class BenchmarkReturnBasisCode:
    """Return semantic such as price-return, gross-total-return or net-total-return."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="benchmark return-basis code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class FundNavBasisCode:
    """NAV denominator semantic such as per-share or per-unit; no valuation engine."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="fund NAV basis code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class EquitySecurityKind(StrEnum):
    COMMON = "common"
    PREFERRED = "preferred"


class FundVehicleKind(StrEnum):
    ETF = "etf"
    MUTUAL_FUND = "mutual-fund"
    CLOSED_END_FUND = "closed-end-fund"
    MONEY_MARKET_FUND = "money-market-fund"
    LISTED_TRUST = "listed-trust"
    REIT = "reit"


@dataclass(frozen=True, slots=True)
class EquityUnitRatio:
    """Positive exact unit ratio; semantic is supplied by its containing field."""

    value: Decimal

    def __post_init__(self) -> None:
        _validate_positive_decimal(self.value, field_name="equity unit ratio")

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class CorporateActionCashAmount:
    """Positive declared cash amount with explicit canonical currency identity."""

    amount: Decimal
    currency_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        _validate_positive_decimal(
            self.amount,
            field_name="corporate action cash amount",
        )
        _validate_identity(
            self.currency_identity_id,
            field_name="corporate action cash currency identity",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            _canonical_decimal(self.amount),
            self.currency_identity_id.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FundNavBasis:
    """Structural NAV basis only; contains no NAV value or calculation authority."""

    currency_identity_id: EconomicIdentityId
    unit_identity_id: EconomicIdentityId
    basis: FundNavBasisCode
    evidence_ref: EquityFundEvidenceRef

    def __post_init__(self) -> None:
        _validate_identity(
            self.currency_identity_id,
            field_name="fund NAV currency identity",
        )
        _validate_identity(
            self.unit_identity_id,
            field_name="fund NAV unit identity",
        )
        if self.currency_identity_id == self.unit_identity_id:
            raise EquityFundCorporateActionValidationError(
                "fund NAV currency and unit identities must differ"
            )
        if not isinstance(self.basis, FundNavBasisCode):
            raise EquityFundCorporateActionValidationError(
                "fund NAV basis must be FundNavBasisCode"
            )
        if not isinstance(self.evidence_ref, EquityFundEvidenceRef):
            raise EquityFundCorporateActionValidationError(
                "fund NAV evidence_ref must be EquityFundEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.currency_identity_id.logical_values(),
            self.unit_identity_id.logical_values(),
            self.basis.logical_values(),
            self.evidence_ref.logical_values(),
        )


def _validate_terms_header(
    terms_id: EquityFundTermsId,
    instrument_identity_id: EconomicIdentityId,
    evidence_ref: EquityFundEvidenceRef,
    *,
    field_prefix: str,
) -> None:
    if not isinstance(terms_id, EquityFundTermsId):
        raise EquityFundCorporateActionValidationError(
            f"{field_prefix} terms_id must be EquityFundTermsId"
        )
    _validate_identity(
        instrument_identity_id,
        field_name=f"{field_prefix} instrument identity",
    )
    if not isinstance(evidence_ref, EquityFundEvidenceRef):
        raise EquityFundCorporateActionValidationError(
            f"{field_prefix} evidence_ref must be EquityFundEvidenceRef"
        )


def _validate_action_header(
    action_id: CorporateActionId,
    revision: CorporateActionRevision,
    instrument_identity_id: EconomicIdentityId,
    evidence_ref: EquityFundEvidenceRef,
    *,
    field_prefix: str,
) -> None:
    if not isinstance(action_id, CorporateActionId):
        raise EquityFundCorporateActionValidationError(
            f"{field_prefix} action_id must be CorporateActionId"
        )
    if not isinstance(revision, CorporateActionRevision):
        raise EquityFundCorporateActionValidationError(
            f"{field_prefix} revision must be CorporateActionRevision"
        )
    _validate_identity(
        instrument_identity_id,
        field_name=f"{field_prefix} instrument identity",
    )
    if not isinstance(evidence_ref, EquityFundEvidenceRef):
        raise EquityFundCorporateActionValidationError(
            f"{field_prefix} evidence_ref must be EquityFundEvidenceRef"
        )


@dataclass(frozen=True, slots=True)
class EquitySecurityTerms:
    terms_id: EquityFundTermsId
    instrument_identity_id: EconomicIdentityId
    issuer_identity_id: EconomicIdentityId
    security_kind: EquitySecurityKind
    evidence_ref: EquityFundEvidenceRef
    share_class: EquityShareClassCode | None = None

    def __post_init__(self) -> None:
        _validate_terms_header(
            self.terms_id,
            self.instrument_identity_id,
            self.evidence_ref,
            field_prefix="equity security",
        )
        _validate_identity(
            self.issuer_identity_id,
            field_name="equity issuer identity",
        )
        if self.instrument_identity_id == self.issuer_identity_id:
            raise EquityFundCorporateActionValidationError(
                "equity instrument and issuer identities must differ"
            )
        if not isinstance(self.security_kind, EquitySecurityKind):
            raise EquityFundCorporateActionValidationError(
                "equity security_kind must be EquitySecurityKind"
            )
        if self.share_class is not None and not isinstance(
            self.share_class,
            EquityShareClassCode,
        ):
            raise EquityFundCorporateActionValidationError(
                "equity share_class must be EquityShareClassCode or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "equity-security",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.issuer_identity_id.logical_values(),
            self.security_kind.value,
            self.share_class.logical_values() if self.share_class is not None else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class DepositaryReceiptTerms:
    terms_id: EquityFundTermsId
    receipt_identity_id: EconomicIdentityId
    underlying_identity_id: EconomicIdentityId
    program: DepositaryReceiptProgramCode
    underlying_units_per_receipt: EquityUnitRatio
    evidence_ref: EquityFundEvidenceRef

    def __post_init__(self) -> None:
        _validate_terms_header(
            self.terms_id,
            self.receipt_identity_id,
            self.evidence_ref,
            field_prefix="depositary receipt",
        )
        _validate_identity(
            self.underlying_identity_id,
            field_name="depositary receipt underlying identity",
        )
        if self.receipt_identity_id == self.underlying_identity_id:
            raise EquityFundCorporateActionValidationError(
                "depositary receipt and underlying identities must differ"
            )
        if not isinstance(self.program, DepositaryReceiptProgramCode):
            raise EquityFundCorporateActionValidationError(
                "depositary receipt program must be DepositaryReceiptProgramCode"
            )
        if not isinstance(self.underlying_units_per_receipt, EquityUnitRatio):
            raise EquityFundCorporateActionValidationError(
                "depositary receipt ratio must be EquityUnitRatio"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "depositary-receipt",
            self.terms_id.logical_values(),
            self.receipt_identity_id.logical_values(),
            self.underlying_identity_id.logical_values(),
            self.program.logical_values(),
            self.underlying_units_per_receipt.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FundVehicleTerms:
    terms_id: EquityFundTermsId
    instrument_identity_id: EconomicIdentityId
    vehicle_kind: FundVehicleKind
    evidence_ref: EquityFundEvidenceRef
    share_class: EquityShareClassCode | None = None
    nav_basis: FundNavBasis | None = None

    def __post_init__(self) -> None:
        _validate_terms_header(
            self.terms_id,
            self.instrument_identity_id,
            self.evidence_ref,
            field_prefix="fund vehicle",
        )
        if not isinstance(self.vehicle_kind, FundVehicleKind):
            raise EquityFundCorporateActionValidationError(
                "fund vehicle_kind must be FundVehicleKind"
            )
        if self.share_class is not None and not isinstance(
            self.share_class,
            EquityShareClassCode,
        ):
            raise EquityFundCorporateActionValidationError(
                "fund share_class must be EquityShareClassCode or None"
            )
        if self.nav_basis is not None and not isinstance(self.nav_basis, FundNavBasis):
            raise EquityFundCorporateActionValidationError(
                "fund nav_basis must be FundNavBasis or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fund-vehicle",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.vehicle_kind.value,
            self.share_class.logical_values() if self.share_class is not None else None,
            self.nav_basis.logical_values() if self.nav_basis is not None else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FundBenchmarkRelationshipTerms:
    """UMI-06 semantic enrichment of one existing UMI-02 identity relationship."""

    terms_id: EquityFundTermsId
    relationship_id: IdentityRelationshipId
    role: FundBenchmarkRoleCode
    return_basis: BenchmarkReturnBasisCode
    evidence_ref: EquityFundEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, EquityFundTermsId):
            raise EquityFundCorporateActionValidationError(
                "fund benchmark terms_id must be EquityFundTermsId"
            )
        if not isinstance(self.relationship_id, IdentityRelationshipId):
            raise EquityFundCorporateActionValidationError(
                "fund benchmark relationship_id must be IdentityRelationshipId"
            )
        if not isinstance(self.role, FundBenchmarkRoleCode):
            raise EquityFundCorporateActionValidationError(
                "fund benchmark role must be FundBenchmarkRoleCode"
            )
        if not isinstance(self.return_basis, BenchmarkReturnBasisCode):
            raise EquityFundCorporateActionValidationError(
                "fund benchmark return_basis must be BenchmarkReturnBasisCode"
            )
        if not isinstance(self.evidence_ref, EquityFundEvidenceRef):
            raise EquityFundCorporateActionValidationError(
                "fund benchmark evidence_ref must be EquityFundEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fund-benchmark-relationship",
            self.terms_id.logical_values(),
            self.relationship_id.logical_values(),
            self.role.logical_values(),
            self.return_basis.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CashDividendTerms:
    action_id: CorporateActionId
    revision: CorporateActionRevision
    instrument_identity_id: EconomicIdentityId
    amount: CorporateActionCashAmount
    declared_date: date
    ex_date: date
    record_date: date
    payable_date: date
    evidence_ref: EquityFundEvidenceRef

    def __post_init__(self) -> None:
        _validate_action_header(
            self.action_id,
            self.revision,
            self.instrument_identity_id,
            self.evidence_ref,
            field_prefix="cash dividend",
        )
        if not isinstance(self.amount, CorporateActionCashAmount):
            raise EquityFundCorporateActionValidationError(
                "cash dividend amount must be CorporateActionCashAmount"
            )
        _validate_date(self.declared_date, field_name="cash dividend declared_date")
        _validate_date(self.ex_date, field_name="cash dividend ex_date")
        _validate_date(self.record_date, field_name="cash dividend record_date")
        _validate_date(self.payable_date, field_name="cash dividend payable_date")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "cash-dividend",
            self.action_id.logical_values(),
            self.revision.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.amount.logical_values(),
            self.declared_date.isoformat(),
            self.ex_date.isoformat(),
            self.record_date.isoformat(),
            self.payable_date.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class StockDividendTerms:
    action_id: CorporateActionId
    revision: CorporateActionRevision
    instrument_identity_id: EconomicIdentityId
    distribution_identity_id: EconomicIdentityId
    units_per_existing_unit: EquityUnitRatio
    ex_date: date
    record_date: date
    payable_date: date
    evidence_ref: EquityFundEvidenceRef

    def __post_init__(self) -> None:
        _validate_action_header(
            self.action_id,
            self.revision,
            self.instrument_identity_id,
            self.evidence_ref,
            field_prefix="stock dividend",
        )
        _validate_identity(
            self.distribution_identity_id,
            field_name="stock dividend distribution identity",
        )
        if not isinstance(self.units_per_existing_unit, EquityUnitRatio):
            raise EquityFundCorporateActionValidationError(
                "stock dividend ratio must be EquityUnitRatio"
            )
        _validate_date(self.ex_date, field_name="stock dividend ex_date")
        _validate_date(self.record_date, field_name="stock dividend record_date")
        _validate_date(self.payable_date, field_name="stock dividend payable_date")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "stock-dividend",
            self.action_id.logical_values(),
            self.revision.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.distribution_identity_id.logical_values(),
            self.units_per_existing_unit.logical_values(),
            self.ex_date.isoformat(),
            self.record_date.isoformat(),
            self.payable_date.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class SplitTerms:
    action_id: CorporateActionId
    revision: CorporateActionRevision
    instrument_identity_id: EconomicIdentityId
    new_units_per_old_unit: EquityUnitRatio
    effective_date: date
    evidence_ref: EquityFundEvidenceRef

    def __post_init__(self) -> None:
        _validate_action_header(
            self.action_id,
            self.revision,
            self.instrument_identity_id,
            self.evidence_ref,
            field_prefix="split",
        )
        if not isinstance(self.new_units_per_old_unit, EquityUnitRatio):
            raise EquityFundCorporateActionValidationError(
                "split ratio must be EquityUnitRatio"
            )
        _validate_date(self.effective_date, field_name="split effective_date")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "split",
            self.action_id.logical_values(),
            self.revision.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.new_units_per_old_unit.logical_values(),
            self.effective_date.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class RightsDistributionTerms:
    action_id: CorporateActionId
    revision: CorporateActionRevision
    instrument_identity_id: EconomicIdentityId
    rights_identity_id: EconomicIdentityId
    entitlement_units_per_source_unit: EquityUnitRatio
    subscription_strike: DerivativeStrike
    ex_date: date
    record_date: date
    expiration_date: date
    evidence_ref: EquityFundEvidenceRef

    def __post_init__(self) -> None:
        _validate_action_header(
            self.action_id,
            self.revision,
            self.instrument_identity_id,
            self.evidence_ref,
            field_prefix="rights distribution",
        )
        _validate_identity(
            self.rights_identity_id,
            field_name="rights distribution rights identity",
        )
        if self.instrument_identity_id == self.rights_identity_id:
            raise EquityFundCorporateActionValidationError(
                "rights instrument and source instrument identities must differ"
            )
        if not isinstance(
            self.entitlement_units_per_source_unit,
            EquityUnitRatio,
        ):
            raise EquityFundCorporateActionValidationError(
                "rights entitlement ratio must be EquityUnitRatio"
            )
        if not isinstance(self.subscription_strike, DerivativeStrike):
            raise EquityFundCorporateActionValidationError(
                "rights subscription_strike must be DerivativeStrike"
            )
        if self.subscription_strike.basis is not DerivativeStrikeBasis.PRICE:
            raise EquityFundCorporateActionValidationError(
                "rights subscription_strike must use PRICE strike semantics"
            )
        _validate_date(self.ex_date, field_name="rights distribution ex_date")
        _validate_date(self.record_date, field_name="rights distribution record_date")
        _validate_date(
            self.expiration_date,
            field_name="rights distribution expiration_date",
        )
        if self.expiration_date < self.record_date:
            raise EquityFundCorporateActionValidationError(
                "rights expiration_date must not be before record_date"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "rights-distribution",
            self.action_id.logical_values(),
            self.revision.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.rights_identity_id.logical_values(),
            self.entitlement_units_per_source_unit.logical_values(),
            self.subscription_strike.logical_values(),
            self.ex_date.isoformat(),
            self.record_date.isoformat(),
            self.expiration_date.isoformat(),
            self.evidence_ref.logical_values(),
        )


type EquityFundTerms = (
    EquitySecurityTerms
    | DepositaryReceiptTerms
    | FundVehicleTerms
    | FundBenchmarkRelationshipTerms
)

type CorporateActionTerms = (
    CashDividendTerms | StockDividendTerms | SplitTerms | RightsDistributionTerms
)
