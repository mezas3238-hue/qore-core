"""Bounded Shari'ah cross-family financing, liquidity and hedging qualification.

This module retains static contractual qualification only. It does not determine
religious or legal compliance, calculate price/PV/rates, move cash or assets,
query providers, execute or settle transactions, mutate Risk/accounts, or grant
Production/real-capital authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from re import fullmatch
from typing import Never
from uuid import UUID

from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentity,
    EconomicIdentityId,
    EconomicIdentityKind,
    IdentityConstructionKind,
    IdentityEvidenceRef,
    IdentityFamilyCode,
)
from qore.kernel.errors import InfrastructureError

_FINANCING_LIQUIDITY_FAMILIES = frozenset(
    {
        "cash-money-market",
        "fixed-income-credit",
        "structured-hybrid-products",
        "loans-credit-facilities",
    }
)
_HEDGING_FAMILIES = frozenset({"forwards-swaps-otc"})
_SYNDICATED_FAMILIES = frozenset({"loans-credit-facilities"})


class ShariahCrossFamilySemanticsError(InfrastructureError):
    __slots__ = ()


class ShariahCrossFamilyValidationError(ShariahCrossFamilySemanticsError):
    __slots__ = ()


def _fail(message: str) -> Never:
    raise ShariahCrossFamilyValidationError(message)


def _require_uuid(value: object, *, field_name: str) -> None:
    if type(value) is not UUID:
        _fail(f"{field_name} must be exact UUID")


def _require_code(value: object, *, field_name: str) -> None:
    if (
        type(value) is not str
        or len(value) > 96
        or fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", value) is None
    ):
        _fail(f"{field_name} must use exact canonical lowercase code syntax")


def _require_date(value: object, *, field_name: str) -> None:
    if type(value) is not date:
        _fail(f"{field_name} must be exact date")


def _require_uuid_wrapper(
    value: object,
    expected_type: type[object],
    *,
    field_name: str,
) -> None:
    if type(value) is not expected_type:
        _fail(f"{field_name} has invalid exact type")
    _require_uuid(getattr(value, "value", None), field_name=f"{field_name}.value")


def _require_economic_identity_id(value: object, *, field_name: str) -> None:
    if type(value) is not EconomicIdentityId:
        _fail(f"{field_name} must be exact EconomicIdentityId")
    _require_uuid(value.value, field_name=f"{field_name}.value")


def _require_economic_identity(
    value: object,
    *,
    field_name: str,
    allowed_families: frozenset[str],
) -> None:
    if type(value) is not EconomicIdentity:
        _fail(f"{field_name} must be exact EconomicIdentity")
    if type(value.identity_id) is not EconomicIdentityId:
        _fail(f"{field_name}.identity_id must be exact EconomicIdentityId")
    _require_uuid(value.identity_id.value, field_name=f"{field_name}.identity_id.value")
    if type(value.kind) is not EconomicIdentityKind:
        _fail(f"{field_name}.kind must be exact EconomicIdentityKind")
    if type(value.family) is not IdentityFamilyCode:
        _fail(f"{field_name}.family must be exact IdentityFamilyCode")
    _require_code(value.family.value, field_name=f"{field_name}.family.value")
    value.family.__post_init__()
    if value.family.value not in allowed_families:
        _fail(f"{field_name}.family is not allowed for this Shari'ah qualification")
    if type(value.construction) is not IdentityConstructionKind:
        _fail(f"{field_name}.construction must be exact IdentityConstructionKind")
    if type(value.evidence_ref) is not IdentityEvidenceRef:
        _fail(f"{field_name}.evidence_ref must be exact IdentityEvidenceRef")
    _require_uuid(value.evidence_ref.value, field_name=f"{field_name}.evidence_ref.value")
    if (
        value.construction is IdentityConstructionKind.CONTINUOUS_REFERENCE
        and value.kind is not EconomicIdentityKind.REFERENCE_OBJECT
    ):
        _fail(f"{field_name} continuous-reference must be a reference object")
    value.__post_init__()


def _canonical_ids(
    values: object,
    *,
    field_name: str,
) -> tuple[EconomicIdentityId, ...]:
    if type(values) is not tuple:
        _fail(f"{field_name} must be exact tuple")
    checked: list[EconomicIdentityId] = []
    for index, value in enumerate(values):
        _require_economic_identity_id(value, field_name=f"{field_name}[{index}]")
        checked.append(value)
    ids = [value.value for value in checked]
    if len(set(ids)) != len(ids):
        _fail(f"{field_name} must not contain duplicate economic identities")
    return tuple(sorted(checked, key=lambda item: str(item.value)))


@dataclass(frozen=True, slots=True)
class ShariahCrossFamilyQualificationId:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="qualification_id.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ShariahEvidenceRef:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="evidence_ref.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ShariahPartyReferenceId:
    """Contract-local party reference; never legal-identity or KYC authority."""

    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="party_reference_id.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ShariahParticipantBindingId:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="participant_binding_id.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ShariahFrameworkCode:
    value: str

    def __post_init__(self) -> None:
        _require_code(self.value, field_name="framework.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ShariahPartyRoleCode:
    value: str

    def __post_init__(self) -> None:
        _require_code(self.value, field_name="party_role.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


class ShariahCrossFamilyCategory(StrEnum):
    FINANCING_LIQUIDITY = "financing-liquidity"
    HEDGING = "hedging"
    SYNDICATED_FINANCING = "syndicated-financing"


class ShariahFinancingLiquidityKind(StrEnum):
    MURABAHAH = "murabahah"
    WAKALAH_AGENCY = "wakalah-agency"
    COLLATERALIZED_MURABAHAH = "collateralized-murabahah"


class ShariahHedgingKind(StrEnum):
    PROFIT_RATE_HEDGING = "profit-rate-hedging"
    CROSS_CURRENCY_HEDGING = "cross-currency-hedging"
    ISLAMIC_FX_FORWARD = "islamic-fx-forward"


class ShariahSyndicatedFinancingKind(StrEnum):
    IJARAH = "ijarah"
    MURABAHAH = "murabahah"


@dataclass(frozen=True, slots=True)
class ShariahParticipantBinding:
    binding_id: ShariahParticipantBindingId
    party_reference_id: ShariahPartyReferenceId
    role: ShariahPartyRoleCode
    evidence_ref: ShariahEvidenceRef

    def __post_init__(self) -> None:
        _require_uuid_wrapper(
            self.binding_id,
            ShariahParticipantBindingId,
            field_name="participant.binding_id",
        )
        _require_uuid_wrapper(
            self.party_reference_id,
            ShariahPartyReferenceId,
            field_name="participant.party_reference_id",
        )
        if type(self.role) is not ShariahPartyRoleCode:
            _fail("participant.role must be exact ShariahPartyRoleCode")
        self.role.__post_init__()
        _require_uuid_wrapper(
            self.evidence_ref,
            ShariahEvidenceRef,
            field_name="participant.evidence_ref",
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.binding_id.logical_values(),
            self.party_reference_id.logical_values(),
            self.role.logical_values(),
            self.evidence_ref.logical_values(),
        )


def _canonical_participants(
    values: object,
    *,
    field_name: str,
) -> tuple[ShariahParticipantBinding, ...]:
    if type(values) is not tuple or not values:
        _fail(f"{field_name} must be non-empty exact tuple")
    checked: list[ShariahParticipantBinding] = []
    for index, value in enumerate(values):
        if type(value) is not ShariahParticipantBinding:
            _fail(f"{field_name}[{index}] must be exact ShariahParticipantBinding")
        value.__post_init__()
        checked.append(value)
    binding_ids = [value.binding_id.value for value in checked]
    if len(set(binding_ids)) != len(binding_ids):
        _fail(f"{field_name} binding ids must be unique")
    party_roles = [(value.party_reference_id.value, value.role.value) for value in checked]
    if len(set(party_roles)) != len(party_roles):
        _fail(f"{field_name} must not duplicate party-role bindings")
    return tuple(
        sorted(
            checked,
            key=lambda item: (
                str(item.party_reference_id.value),
                item.role.value,
                str(item.binding_id.value),
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class ShariahFinancingLiquidityTerms:
    structure: ShariahFinancingLiquidityKind
    primary_identity: EconomicIdentity
    participants: tuple[ShariahParticipantBinding, ...]
    start_date: date
    evidence_ref: ShariahEvidenceRef
    related_identity_ids: tuple[EconomicIdentityId, ...] = ()
    end_date: date | None = None

    def __post_init__(self) -> None:
        if type(self.structure) is not ShariahFinancingLiquidityKind:
            _fail("financing structure must be exact ShariahFinancingLiquidityKind")
        _require_economic_identity(
            self.primary_identity,
            field_name="financing.primary_identity",
            allowed_families=_FINANCING_LIQUIDITY_FAMILIES,
        )
        canonical_participants = _canonical_participants(
            self.participants,
            field_name="financing.participants",
        )
        canonical_related = _canonical_ids(
            self.related_identity_ids,
            field_name="financing.related_identity_ids",
        )
        _require_date(self.start_date, field_name="financing.start_date")
        if self.end_date is not None:
            _require_date(self.end_date, field_name="financing.end_date")
            if self.end_date < self.start_date:
                _fail("financing.end_date must not precede start_date")
        _require_uuid_wrapper(
            self.evidence_ref,
            ShariahEvidenceRef,
            field_name="financing.evidence_ref",
        )
        object.__setattr__(self, "participants", canonical_participants)
        object.__setattr__(self, "related_identity_ids", canonical_related)

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "shariah-financing-liquidity",
            self.structure.value,
            self.primary_identity.logical_values(),
            tuple(item.logical_values() for item in self.participants),
            tuple(item.logical_values() for item in self.related_identity_ids),
            self.start_date.isoformat(),
            self.end_date.isoformat() if self.end_date is not None else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ShariahHedgingQualificationTerms:
    structure: ShariahHedgingKind
    hedged_identity: EconomicIdentity
    evidence_ref: ShariahEvidenceRef
    related_identity_ids: tuple[EconomicIdentityId, ...] = ()

    def __post_init__(self) -> None:
        if type(self.structure) is not ShariahHedgingKind:
            _fail("hedging structure must be exact ShariahHedgingKind")
        _require_economic_identity(
            self.hedged_identity,
            field_name="hedging.hedged_identity",
            allowed_families=_HEDGING_FAMILIES,
        )
        canonical_related = _canonical_ids(
            self.related_identity_ids,
            field_name="hedging.related_identity_ids",
        )
        _require_uuid_wrapper(
            self.evidence_ref,
            ShariahEvidenceRef,
            field_name="hedging.evidence_ref",
        )
        object.__setattr__(self, "related_identity_ids", canonical_related)

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "shariah-hedging",
            self.structure.value,
            self.hedged_identity.logical_values(),
            tuple(item.logical_values() for item in self.related_identity_ids),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ShariahSyndicatedFinancingTerms:
    structure: ShariahSyndicatedFinancingKind
    primary_identity: EconomicIdentity
    participants: tuple[ShariahParticipantBinding, ...]
    evidence_ref: ShariahEvidenceRef

    def __post_init__(self) -> None:
        if type(self.structure) is not ShariahSyndicatedFinancingKind:
            _fail("syndicated structure must be exact ShariahSyndicatedFinancingKind")
        _require_economic_identity(
            self.primary_identity,
            field_name="syndicated.primary_identity",
            allowed_families=_SYNDICATED_FAMILIES,
        )
        canonical_participants = _canonical_participants(
            self.participants,
            field_name="syndicated.participants",
        )
        _require_uuid_wrapper(
            self.evidence_ref,
            ShariahEvidenceRef,
            field_name="syndicated.evidence_ref",
        )
        object.__setattr__(self, "participants", canonical_participants)

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "shariah-syndicated-financing",
            self.structure.value,
            self.primary_identity.logical_values(),
            tuple(item.logical_values() for item in self.participants),
            self.evidence_ref.logical_values(),
        )


ShariahCrossFamilyTerms = (
    ShariahFinancingLiquidityTerms
    | ShariahHedgingQualificationTerms
    | ShariahSyndicatedFinancingTerms
)


@dataclass(frozen=True, slots=True)
class ShariahCrossFamilyQualification:
    qualification_id: ShariahCrossFamilyQualificationId
    category: ShariahCrossFamilyCategory
    terms: ShariahCrossFamilyTerms
    effective_date: date
    framework: ShariahFrameworkCode
    evidence_ref: ShariahEvidenceRef
    end_date: date | None = None

    def __post_init__(self) -> None:
        _require_uuid_wrapper(
            self.qualification_id,
            ShariahCrossFamilyQualificationId,
            field_name="qualification.qualification_id",
        )
        if type(self.category) is not ShariahCrossFamilyCategory:
            _fail("qualification.category must be exact ShariahCrossFamilyCategory")
        expected_type: type[object]
        if self.category is ShariahCrossFamilyCategory.FINANCING_LIQUIDITY:
            expected_type = ShariahFinancingLiquidityTerms
        elif self.category is ShariahCrossFamilyCategory.HEDGING:
            expected_type = ShariahHedgingQualificationTerms
        else:
            expected_type = ShariahSyndicatedFinancingTerms
        if type(self.terms) is not expected_type:
            _fail("qualification category and terms variant must match exactly")
        self.terms.__post_init__()
        _require_date(self.effective_date, field_name="qualification.effective_date")
        if self.end_date is not None:
            _require_date(self.end_date, field_name="qualification.end_date")
            if self.end_date < self.effective_date:
                _fail("qualification.end_date must not precede effective_date")
        if type(self.framework) is not ShariahFrameworkCode:
            _fail("qualification.framework must be exact ShariahFrameworkCode")
        self.framework.__post_init__()
        _require_uuid_wrapper(
            self.evidence_ref,
            ShariahEvidenceRef,
            field_name="qualification.evidence_ref",
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.qualification_id.logical_values(),
            self.category.value,
            self.terms.logical_values(),
            self.effective_date.isoformat(),
            self.end_date.isoformat() if self.end_date is not None else None,
            self.framework.logical_values(),
            self.evidence_ref.logical_values(),
        )
