"""Bounded Sukuk / Shari'ah certificate structural qualification.

This module describes static certificate structure only. It does not determine
Shari'ah compliance, issue legal opinions, calculate distributions, value an
instrument, fetch market data, map providers, execute orders, mutate settlement,
or grant Risk/account/Production authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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

_ALLOWED_ROOT_FAMILIES = frozenset(
    {
        "fixed-income-credit",
        "structured-hybrid-products",
    }
)


class SukukStructuralSemanticsError(InfrastructureError):
    __slots__ = ()


class SukukStructuralSemanticsValidationError(SukukStructuralSemanticsError):
    __slots__ = ()


def _fail(message: str) -> Never:
    raise SukukStructuralSemanticsValidationError(message)


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


def _revalidate_economic_identity(
    identity: object,
    *,
    field_name: str,
    require_sukuk_root: bool,
) -> None:
    if type(identity) is not EconomicIdentity:
        _fail(f"{field_name} must be exact EconomicIdentity")

    if type(identity.identity_id) is not EconomicIdentityId:
        _fail(f"{field_name}.identity_id must be exact EconomicIdentityId")
    _require_uuid(identity.identity_id.value, field_name=f"{field_name}.identity_id.value")

    if type(identity.kind) is not EconomicIdentityKind:
        _fail(f"{field_name}.kind must be exact EconomicIdentityKind")

    if type(identity.family) is not IdentityFamilyCode:
        _fail(f"{field_name}.family must be exact IdentityFamilyCode")
    _require_code(identity.family.value, field_name=f"{field_name}.family.value")
    identity.family.__post_init__()

    if type(identity.construction) is not IdentityConstructionKind:
        _fail(f"{field_name}.construction must be exact IdentityConstructionKind")

    if type(identity.evidence_ref) is not IdentityEvidenceRef:
        _fail(f"{field_name}.evidence_ref must be exact IdentityEvidenceRef")
    _require_uuid(
        identity.evidence_ref.value,
        field_name=f"{field_name}.evidence_ref.value",
    )

    identity.__post_init__()

    if not require_sukuk_root:
        return
    if identity.kind is not EconomicIdentityKind.TRADABLE_INSTRUMENT:
        _fail("Sukuk certificate identity must be a tradable instrument")
    if identity.family.value not in _ALLOWED_ROOT_FAMILIES:
        _fail(
            "Sukuk certificate family must be fixed-income-credit or "
            "structured-hybrid-products"
        )


@dataclass(frozen=True, slots=True)
class SukukQualificationId:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="qualification_id.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class SukukUnderlyingBindingId:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="underlying_binding_id.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class SukukStructuralLegId:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="structural_leg_id.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class SukukEvidenceRef:
    """Opaque retained-evidence reference; never evidence content or credentials."""

    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="evidence_ref.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class SukukStructureCode:
    """Product-specific certificate structure code; never a compliance decision."""

    value: str

    def __post_init__(self) -> None:
        _require_code(self.value, field_name="structure_code.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class SukukCertificateInterestCode:
    """Economic interest represented by the certificate, expressed explicitly."""

    value: str

    def __post_init__(self) -> None:
        _require_code(self.value, field_name="certificate_interest_code.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class SukukUnderlyingRoleCode:
    value: str

    def __post_init__(self) -> None:
        _require_code(self.value, field_name="underlying_role_code.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class SukukUnderlyingInterestCode:
    value: str

    def __post_init__(self) -> None:
        _require_code(self.value, field_name="underlying_interest_code.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class SukukStructuralLegKindCode:
    value: str

    def __post_init__(self) -> None:
        _require_code(self.value, field_name="structural_leg_kind_code.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class SukukStructuralLegRoleCode:
    value: str

    def __post_init__(self) -> None:
        _require_code(self.value, field_name="structural_leg_role_code.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class SukukDistributionSourceCode:
    """Contractual source semantic; it is not a calculated cash-flow amount."""

    value: str

    def __post_init__(self) -> None:
        _require_code(self.value, field_name="distribution_source_code.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class SukukShariahFrameworkCode:
    """External framework/standard locator code; QORE does not adjudicate compliance."""

    value: str

    def __post_init__(self) -> None:
        _require_code(self.value, field_name="shariah_framework_code.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class SukukUnderlyingInterestBinding:
    """One explicit economic interest/reference retained by the Sukuk certificate."""

    binding_id: SukukUnderlyingBindingId
    underlying_identity: EconomicIdentity
    role: SukukUnderlyingRoleCode
    interest: SukukUnderlyingInterestCode
    evidence_ref: SukukEvidenceRef

    def __post_init__(self) -> None:
        _require_uuid_wrapper(
            self.binding_id,
            SukukUnderlyingBindingId,
            field_name="underlying.binding_id",
        )
        _revalidate_economic_identity(
            self.underlying_identity,
            field_name="underlying.identity",
            require_sukuk_root=False,
        )
        if type(self.role) is not SukukUnderlyingRoleCode:
            _fail("underlying.role must be exact SukukUnderlyingRoleCode")
        self.role.__post_init__()
        if type(self.interest) is not SukukUnderlyingInterestCode:
            _fail("underlying.interest must be exact SukukUnderlyingInterestCode")
        self.interest.__post_init__()
        _require_uuid_wrapper(
            self.evidence_ref,
            SukukEvidenceRef,
            field_name="underlying.evidence_ref",
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "sukuk-underlying-interest",
            self.binding_id.logical_values(),
            self.underlying_identity.logical_values(),
            self.role.logical_values(),
            self.interest.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class SukukStructuralLeg:
    """One ordered declarative structural leg; no agreement execution authority."""

    leg_id: SukukStructuralLegId
    ordinal: int
    kind: SukukStructuralLegKindCode
    role: SukukStructuralLegRoleCode
    evidence_ref: SukukEvidenceRef
    related_underlying_binding_id: SukukUnderlyingBindingId | None = None

    def __post_init__(self) -> None:
        _require_uuid_wrapper(
            self.leg_id,
            SukukStructuralLegId,
            field_name="leg.leg_id",
        )
        if type(self.ordinal) is not int or self.ordinal <= 0:
            _fail("leg.ordinal must be a positive exact int")
        if type(self.kind) is not SukukStructuralLegKindCode:
            _fail("leg.kind must be exact SukukStructuralLegKindCode")
        self.kind.__post_init__()
        if type(self.role) is not SukukStructuralLegRoleCode:
            _fail("leg.role must be exact SukukStructuralLegRoleCode")
        self.role.__post_init__()
        _require_uuid_wrapper(
            self.evidence_ref,
            SukukEvidenceRef,
            field_name="leg.evidence_ref",
        )
        if self.related_underlying_binding_id is not None:
            _require_uuid_wrapper(
                self.related_underlying_binding_id,
                SukukUnderlyingBindingId,
                field_name="leg.related_underlying_binding_id",
            )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "sukuk-structural-leg",
            self.leg_id.logical_values(),
            self.ordinal,
            self.kind.logical_values(),
            self.role.logical_values(),
            self.related_underlying_binding_id.logical_values()
            if self.related_underlying_binding_id is not None
            else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class SukukDistributionSource:
    """Static source qualification for distributions; it calculates no payment."""

    source: SukukDistributionSourceCode
    evidence_ref: SukukEvidenceRef
    related_underlying_binding_id: SukukUnderlyingBindingId | None = None

    def __post_init__(self) -> None:
        if type(self.source) is not SukukDistributionSourceCode:
            _fail("distribution.source must be exact SukukDistributionSourceCode")
        self.source.__post_init__()
        _require_uuid_wrapper(
            self.evidence_ref,
            SukukEvidenceRef,
            field_name="distribution.evidence_ref",
        )
        if self.related_underlying_binding_id is not None:
            _require_uuid_wrapper(
                self.related_underlying_binding_id,
                SukukUnderlyingBindingId,
                field_name="distribution.related_underlying_binding_id",
            )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "sukuk-distribution-source",
            self.source.logical_values(),
            self.related_underlying_binding_id.logical_values()
            if self.related_underlying_binding_id is not None
            else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class SukukExternalShariahEvidence:
    """Opaque external qualification evidence; never a QORE compliance verdict."""

    framework: SukukShariahFrameworkCode
    evidence_ref: SukukEvidenceRef
    effective_date: date | None = None

    def __post_init__(self) -> None:
        if type(self.framework) is not SukukShariahFrameworkCode:
            _fail("shariah_evidence.framework must be exact SukukShariahFrameworkCode")
        self.framework.__post_init__()
        _require_uuid_wrapper(
            self.evidence_ref,
            SukukEvidenceRef,
            field_name="shariah_evidence.evidence_ref",
        )
        if self.effective_date is not None:
            _require_date(
                self.effective_date,
                field_name="shariah_evidence.effective_date",
            )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "external-shariah-evidence",
            self.framework.logical_values(),
            self.effective_date.isoformat() if self.effective_date is not None else None,
            self.evidence_ref.logical_values(),
        )


def _underlying_semantic_key(
    value: SukukUnderlyingInterestBinding,
) -> tuple[str, str, str]:
    return (
        str(value.underlying_identity.identity_id.value),
        value.role.value,
        value.interest.value,
    )


def _underlying_sort_key(
    value: SukukUnderlyingInterestBinding,
) -> tuple[str, str, str, str]:
    return (*_underlying_semantic_key(value), str(value.binding_id.value))


def _leg_sort_key(value: SukukStructuralLeg) -> tuple[int, str]:
    return (value.ordinal, str(value.leg_id.value))


@dataclass(frozen=True, slots=True)
class SukukStructuralQualification:
    """Static Sukuk certificate structure over one existing UMI-02 identity.

    The value proves only that the retained certificate declaration contains
    explicit product structure, underlying-interest, ordered-leg, distribution
    source, and external Shari'ah-framework evidence. It is not a legal or
    religious compliance determination.
    """

    qualification_id: SukukQualificationId
    certificate_identity: EconomicIdentity
    structure: SukukStructureCode
    certificate_interest: SukukCertificateInterestCode
    underlying_interests: tuple[SukukUnderlyingInterestBinding, ...]
    structural_legs: tuple[SukukStructuralLeg, ...]
    distribution_source: SukukDistributionSource
    shariah_evidence: SukukExternalShariahEvidence
    issue_date: date
    evidence_ref: SukukEvidenceRef
    maturity_date: date | None = None

    def __post_init__(self) -> None:
        _require_uuid_wrapper(
            self.qualification_id,
            SukukQualificationId,
            field_name="qualification_id",
        )
        _revalidate_economic_identity(
            self.certificate_identity,
            field_name="certificate_identity",
            require_sukuk_root=True,
        )
        if type(self.structure) is not SukukStructureCode:
            _fail("structure must be exact SukukStructureCode")
        self.structure.__post_init__()
        if type(self.certificate_interest) is not SukukCertificateInterestCode:
            _fail("certificate_interest must be exact SukukCertificateInterestCode")
        self.certificate_interest.__post_init__()

        if type(self.underlying_interests) is not tuple:
            _fail("underlying_interests must be an immutable tuple")
        if not self.underlying_interests:
            _fail("underlying_interests cannot be empty")

        certificate_id = str(self.certificate_identity.identity_id.value)
        seen_binding_ids: set[str] = set()
        seen_semantic_bindings: set[tuple[str, str, str]] = set()
        for binding in self.underlying_interests:
            if type(binding) is not SukukUnderlyingInterestBinding:
                _fail(
                    "underlying_interests must contain exact "
                    "SukukUnderlyingInterestBinding values"
                )
            binding.__post_init__()
            binding_id = str(binding.binding_id.value)
            if binding_id in seen_binding_ids:
                _fail("duplicate Sukuk underlying binding id")
            seen_binding_ids.add(binding_id)
            if str(binding.underlying_identity.identity_id.value) == certificate_id:
                _fail("Sukuk underlying identity must differ from certificate identity")
            semantic_key = _underlying_semantic_key(binding)
            if semantic_key in seen_semantic_bindings:
                _fail("duplicate Sukuk underlying semantic binding")
            seen_semantic_bindings.add(semantic_key)

        canonical_underlyings = tuple(
            sorted(self.underlying_interests, key=_underlying_sort_key)
        )
        if self.underlying_interests != canonical_underlyings:
            object.__setattr__(
                self,
                "underlying_interests",
                canonical_underlyings,
            )

        if type(self.structural_legs) is not tuple:
            _fail("structural_legs must be an immutable tuple")
        if not self.structural_legs:
            _fail("structural_legs cannot be empty")

        seen_leg_ids: set[str] = set()
        seen_ordinals: set[int] = set()
        for leg in self.structural_legs:
            if type(leg) is not SukukStructuralLeg:
                _fail("structural_legs must contain exact SukukStructuralLeg values")
            leg.__post_init__()
            leg_id = str(leg.leg_id.value)
            if leg_id in seen_leg_ids:
                _fail("duplicate Sukuk structural leg id")
            seen_leg_ids.add(leg_id)
            if leg.ordinal in seen_ordinals:
                _fail("duplicate Sukuk structural leg ordinal")
            seen_ordinals.add(leg.ordinal)
            if (
                leg.related_underlying_binding_id is not None
                and str(leg.related_underlying_binding_id.value) not in seen_binding_ids
            ):
                _fail("structural leg references undeclared underlying binding")

        canonical_legs = tuple(sorted(self.structural_legs, key=_leg_sort_key))
        if self.structural_legs != canonical_legs:
            object.__setattr__(self, "structural_legs", canonical_legs)

        if type(self.distribution_source) is not SukukDistributionSource:
            _fail("distribution_source must be exact SukukDistributionSource")
        self.distribution_source.__post_init__()
        if (
            self.distribution_source.related_underlying_binding_id is not None
            and str(self.distribution_source.related_underlying_binding_id.value)
            not in seen_binding_ids
        ):
            _fail("distribution source references undeclared underlying binding")

        if type(self.shariah_evidence) is not SukukExternalShariahEvidence:
            _fail("shariah_evidence must be exact SukukExternalShariahEvidence")
        self.shariah_evidence.__post_init__()

        _require_date(self.issue_date, field_name="issue_date")
        if self.maturity_date is not None:
            _require_date(self.maturity_date, field_name="maturity_date")
            if self.maturity_date <= self.issue_date:
                _fail("maturity_date must be after issue_date when present")

        _require_uuid_wrapper(
            self.evidence_ref,
            SukukEvidenceRef,
            field_name="evidence_ref",
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "sukuk-structural-qualification",
            self.qualification_id.logical_values(),
            self.certificate_identity.logical_values(),
            self.structure.logical_values(),
            self.certificate_interest.logical_values(),
            tuple(value.logical_values() for value in self.underlying_interests),
            tuple(value.logical_values() for value in self.structural_legs),
            self.distribution_source.logical_values(),
            self.shariah_evidence.logical_values(),
            self.issue_date.isoformat(),
            self.maturity_date.isoformat() if self.maturity_date is not None else None,
            self.evidence_ref.logical_values(),
        )
