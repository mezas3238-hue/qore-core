from __future__ import annotations

from uuid import UUID

import pytest

from qore.infrastructure.uit_contract_qualification import (
    UnitInvestmentTrustEvidenceRef,
    UnitInvestmentTrustQualification,
    UnitInvestmentTrustQualificationId,
    UnitInvestmentTrustQualificationValidationError,
    UnitInvestmentTrustSpecifiedSecurity,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentity,
    EconomicIdentityId,
    EconomicIdentityKind,
    IdentityConstructionKind,
    IdentityEvidenceRef,
    IdentityFamilyCode,
)


def _uuid(i: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{i:012d}")


def _identity(
    identity_index: int,
    *,
    family: str,
    evidence_index: int,
) -> EconomicIdentity:
    return EconomicIdentity(
        identity_id=EconomicIdentityId(_uuid(identity_index)),
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=IdentityFamilyCode(family),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=IdentityEvidenceRef(_uuid(evidence_index)),
    )


def _component(
    identity: EconomicIdentity,
    evidence_index: int,
) -> UnitInvestmentTrustSpecifiedSecurity:
    return UnitInvestmentTrustSpecifiedSecurity(
        security_identity=identity,
        evidence_ref=UnitInvestmentTrustEvidenceRef(_uuid(evidence_index)),
    )


def _qualification(
    fund_identity: EconomicIdentity,
    component: UnitInvestmentTrustSpecifiedSecurity,
) -> UnitInvestmentTrustQualification:
    return UnitInvestmentTrustQualification(
        qualification_id=UnitInvestmentTrustQualificationId(_uuid(900)),
        fund_identity=fund_identity,
        specified_securities=(component,),
        evidence_ref=UnitInvestmentTrustEvidenceRef(_uuid(901)),
    )


def test_same_root_economic_identity_rejected_as_specified_security() -> None:
    fund = _identity(1, family="funds-pooled-vehicles", evidence_index=10)
    self_component = _component(fund, 20)

    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(fund, self_component)


def test_same_root_id_with_different_projection_rejected() -> None:
    fund = _identity(1, family="funds-pooled-vehicles", evidence_index=10)
    colliding_security = _identity(1, family="equities", evidence_index=11)

    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(fund, _component(colliding_security, 20))


def test_distinct_fund_component_identity_is_accepted() -> None:
    fund = _identity(1, family="funds-pooled-vehicles", evidence_index=10)
    nested_fund = _identity(2, family="funds-pooled-vehicles", evidence_index=11)

    qualification = _qualification(fund, _component(nested_fund, 20))

    assert (
        qualification.fund_identity.identity_id
        != qualification.specified_securities[0].security_identity.identity_id
    )
