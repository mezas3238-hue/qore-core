"""Bounded Unit Investment Trust qualification over existing QORE identity.

This module does not own fund vehicle taxonomy, NAV values, NAV computation,
current holdings, redemption execution, listing authority, provider support,
or legal/regulatory eligibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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

_FUNDS_POOLED_VEHICLES_FAMILY = "funds-pooled-vehicles"


class UnitInvestmentTrustQualificationError(InfrastructureError):
    __slots__ = ()


class UnitInvestmentTrustQualificationValidationError(
    UnitInvestmentTrustQualificationError
):
    __slots__ = ()


def _fail(message: str) -> Never:
    raise UnitInvestmentTrustQualificationValidationError(message)


def _require_uuid(value: object, *, field_name: str) -> None:
    if type(value) is not UUID:
        _fail(f"{field_name} must be exact UUID")


def _require_local_uuid_wrapper(
    value: object,
    expected_type: type[object],
    *,
    field_name: str,
) -> None:
    if type(value) is not expected_type:
        _fail(f"{field_name} has invalid exact type")
    _require_uuid(getattr(value, "value", None), field_name=f"{field_name}.value")


def _validate_economic_identity(
    identity: object,
    *,
    require_fund_family: bool,
) -> None:
    if type(identity) is not EconomicIdentity:
        _fail("expected exact EconomicIdentity")

    if type(identity.identity_id) is not EconomicIdentityId:
        _fail("expected exact EconomicIdentityId")
    _require_uuid(identity.identity_id.value, field_name="economic identity id")

    if type(identity.kind) is not EconomicIdentityKind:
        _fail("expected exact EconomicIdentityKind")
    if identity.kind is not EconomicIdentityKind.TRADABLE_INSTRUMENT:
        _fail("UIT qualification requires TRADABLE_INSTRUMENT")

    if type(identity.family) is not IdentityFamilyCode:
        _fail("expected exact IdentityFamilyCode")
    if type(identity.family.value) is not str:
        _fail("family value must be exact str")
    identity.family.__post_init__()

    if type(identity.construction) is not IdentityConstructionKind:
        _fail("expected exact IdentityConstructionKind")
    if identity.construction is IdentityConstructionKind.CONTINUOUS_REFERENCE:
        _fail("tradable UIT material must not use continuous-reference construction")

    if type(identity.evidence_ref) is not IdentityEvidenceRef:
        _fail("expected exact IdentityEvidenceRef")
    _require_uuid(
        identity.evidence_ref.value,
        field_name="economic identity evidence ref",
    )

    if require_fund_family and identity.family.value != _FUNDS_POOLED_VEHICLES_FAMILY:
        _fail("UIT fund family must be funds-pooled-vehicles")


def _component_sort_key(
    component: UnitInvestmentTrustSpecifiedSecurity,
) -> str:
    return str(component.security_identity.identity_id.value)


@dataclass(frozen=True, slots=True)
class UnitInvestmentTrustQualificationId:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="qualification_id.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class UnitInvestmentTrustEvidenceRef:
    value: UUID

    def __post_init__(self) -> None:
        _require_uuid(self.value, field_name="evidence_ref.value")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class UnitInvestmentTrustSpecifiedSecurity:
    """One contractually specified security identity in a bounded UIT qualifier.

    This is not a current holding, position, quantity, weight, allocation,
    market value, or derivative payoff leg.
    """

    security_identity: EconomicIdentity
    evidence_ref: UnitInvestmentTrustEvidenceRef

    def __post_init__(self) -> None:
        _validate_economic_identity(
            self.security_identity,
            require_fund_family=False,
        )
        _require_local_uuid_wrapper(
            self.evidence_ref,
            UnitInvestmentTrustEvidenceRef,
            field_name="specified_security.evidence_ref",
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "specified-security",
            self.security_identity.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class UnitInvestmentTrustQualification:
    """Bounded US-style Unit Investment Trust qualification.

    Existence of this value means the bounded qualified instrument retains:

    - redeemable-security semantic;
    - undivided-interest semantic;
    - one or more contractually specified securities.

    It does not grant NAV value, NAV computation, current holdings,
    redemption execution, listing authority, legal eligibility, provider
    support, or settlement mutation.
    """

    qualification_id: UnitInvestmentTrustQualificationId
    fund_identity: EconomicIdentity
    specified_securities: tuple[UnitInvestmentTrustSpecifiedSecurity, ...]
    evidence_ref: UnitInvestmentTrustEvidenceRef
    contractual_termination_date: date | None = None

    def __post_init__(self) -> None:
        _require_local_uuid_wrapper(
            self.qualification_id,
            UnitInvestmentTrustQualificationId,
            field_name="qualification_id",
        )
        _require_local_uuid_wrapper(
            self.evidence_ref,
            UnitInvestmentTrustEvidenceRef,
            field_name="evidence_ref",
        )

        _validate_economic_identity(
            self.fund_identity,
            require_fund_family=True,
        )

        if type(self.specified_securities) is not tuple:
            _fail("specified securities must be an immutable tuple")
        if not self.specified_securities:
            _fail("specified securities tuple cannot be empty")

        root_id = str(self.fund_identity.identity_id.value)
        for component in self.specified_securities:
            if type(component) is not UnitInvestmentTrustSpecifiedSecurity:
                _fail(
                    "specified securities tuple must contain only exact "
                    "UnitInvestmentTrustSpecifiedSecurity"
                )
            component.__post_init__()
            if _component_sort_key(component) == root_id:
                _fail("specified security identity must differ from fund identity")

        canonical = tuple(sorted(self.specified_securities, key=_component_sort_key))

        seen_ids: set[str] = set()
        for component in canonical:
            key = _component_sort_key(component)
            if key in seen_ids:
                _fail("duplicate specified security identity")
            seen_ids.add(key)

        if self.specified_securities != canonical:
            object.__setattr__(self, "specified_securities", canonical)

        if self.contractual_termination_date is not None:
            if type(self.contractual_termination_date) is not date:
                _fail("contractual termination date must be exact date")

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "unit-investment-trust-qualification",
            self.qualification_id.logical_values(),
            self.fund_identity.logical_values(),
            "redeemable-security",
            "undivided-interest",
            tuple(
                component.logical_values()
                for component in self.specified_securities
            ),
            self.contractual_termination_date.isoformat()
            if self.contractual_termination_date is not None
            else None,
            self.evidence_ref.logical_values(),
        )