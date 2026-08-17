from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import date, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.equity_fund_corporate_action_semantics import (
    EquityFundEvidenceRef,
    EquityFundTermsId,
    FundVehicleKind,
    FundVehicleTerms,
)
from qore.infrastructure.structured_hybrid_synthetic_semantics import (
    StructuredComponentBinding,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentity,
    EconomicIdentityId,
    EconomicIdentityKind,
    IdentityConstructionKind,
    IdentityEvidenceRef,
    IdentityFamilyCode,
    IdentityLifecycleEvent,
)
from qore.infrastructure.uit_contract_qualification import (
    UnitInvestmentTrustEvidenceRef,
    UnitInvestmentTrustQualification,
    UnitInvestmentTrustQualificationId,
    UnitInvestmentTrustQualificationValidationError,
    UnitInvestmentTrustSpecifiedSecurity,
)


def _uuid(i: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{i:012d}")


def _economic_identity_id(i: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(i))


def _identity_evidence(i: int) -> IdentityEvidenceRef:
    return IdentityEvidenceRef(_uuid(i))


def _uit_id(i: int) -> UnitInvestmentTrustQualificationId:
    return UnitInvestmentTrustQualificationId(_uuid(i))


def _uit_evidence(i: int) -> UnitInvestmentTrustEvidenceRef:
    return UnitInvestmentTrustEvidenceRef(_uuid(i))


def _fund_identity_with_evidence(
    identity_index: int,
    evidence_index: int,
) -> EconomicIdentity:
    return EconomicIdentity(
        identity_id=_economic_identity_id(identity_index),
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=IdentityFamilyCode("funds-pooled-vehicles"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=_identity_evidence(evidence_index),
    )


def _fund_identity(i: int) -> EconomicIdentity:
    return _fund_identity_with_evidence(i, i)


def _security_identity(
    security_index: int,
    identity_evidence_index: int,
) -> EconomicIdentity:
    return EconomicIdentity(
        identity_id=_economic_identity_id(security_index),
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=IdentityFamilyCode("equities"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=_identity_evidence(identity_evidence_index),
    )


def _component_with_evidence(
    security_index: int,
    *,
    identity_evidence_index: int,
    local_evidence_index: int,
) -> UnitInvestmentTrustSpecifiedSecurity:
    return UnitInvestmentTrustSpecifiedSecurity(
        security_identity=_security_identity(
            security_index,
            identity_evidence_index,
        ),
        evidence_ref=_uit_evidence(local_evidence_index),
    )


def _component(
    security_index: int,
    evidence_index: int,
) -> UnitInvestmentTrustSpecifiedSecurity:
    return _component_with_evidence(
        security_index,
        identity_evidence_index=evidence_index,
        local_evidence_index=evidence_index,
    )


def _qualification(
    *,
    fund_identity: EconomicIdentity,
    components: tuple[UnitInvestmentTrustSpecifiedSecurity, ...],
    termination: date | None = None,
) -> UnitInvestmentTrustQualification:
    return UnitInvestmentTrustQualification(
        qualification_id=_uit_id(3),
        fund_identity=fund_identity,
        specified_securities=components,
        evidence_ref=_uit_evidence(4),
        contractual_termination_date=termination,
    )


def test_local_id_wrappers_reject_non_uuid_runtime_values() -> None:
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        UnitInvestmentTrustQualificationId(cast(UUID, "not-a-uuid"))
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        UnitInvestmentTrustEvidenceRef(cast(UUID, object()))


def test_valid_non_etf_uit() -> None:
    q = _qualification(
        fund_identity=_fund_identity(1),
        components=(_component(10, 10),),
    )
    assert q.logical_values()[0] == "unit-investment-trust-qualification"


def test_etf_plus_uit_composition() -> None:
    fund_identity = _fund_identity(1)
    etf_terms = FundVehicleTerms(
        terms_id=EquityFundTermsId(_uuid(500)),
        instrument_identity_id=fund_identity.identity_id,
        vehicle_kind=FundVehicleKind.ETF,
        evidence_ref=EquityFundEvidenceRef(_uuid(501)),
        share_class=None,
        nav_basis=None,
    )
    uit = _qualification(
        fund_identity=fund_identity,
        components=(_component(10, 10),),
    )
    assert etf_terms.instrument_identity_id == uit.fund_identity.identity_id


def test_etf_terms_alone_is_not_uit() -> None:
    fund_identity = _fund_identity(1)
    etf_terms = FundVehicleTerms(
        terms_id=EquityFundTermsId(_uuid(500)),
        instrument_identity_id=fund_identity.identity_id,
        vehicle_kind=FundVehicleKind.ETF,
        evidence_ref=EquityFundEvidenceRef(_uuid(501)),
    )
    assert not isinstance(etf_terms, UnitInvestmentTrustQualification)


def test_wrong_root_family_rejected() -> None:
    bad = EconomicIdentity(
        identity_id=_economic_identity_id(1),
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=IdentityFamilyCode("equities"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=_identity_evidence(1),
    )
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=bad,
            components=(_component(10, 10),),
        )


def test_root_reference_object_rejected() -> None:
    bad = EconomicIdentity(
        identity_id=_economic_identity_id(1),
        kind=EconomicIdentityKind.REFERENCE_OBJECT,
        family=IdentityFamilyCode("funds-pooled-vehicles"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=_identity_evidence(1),
    )
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=bad,
            components=(_component(10, 10),),
        )


class DeceptiveEconomicIdentity(EconomicIdentity):
    pass


class DeceptiveEconomicIdentityId(EconomicIdentityId):
    pass


class DeceptiveFamily(IdentityFamilyCode):
    pass


class DeceptiveIdentityEvidenceRef(IdentityEvidenceRef):
    pass


class DeceptiveString(str):
    pass


def test_root_economic_identity_subclass_rejected() -> None:
    bad = DeceptiveEconomicIdentity(
        identity_id=_economic_identity_id(1),
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=IdentityFamilyCode("funds-pooled-vehicles"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=_identity_evidence(1),
    )
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=bad,
            components=(_component(10, 10),),
        )


def test_root_economic_identity_id_subclass_rejected() -> None:
    deceptive_id = DeceptiveEconomicIdentityId(_uuid(1))
    bad = EconomicIdentity(
        identity_id=deceptive_id,
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=IdentityFamilyCode("funds-pooled-vehicles"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=_identity_evidence(1),
    )
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=bad,
            components=(_component(10, 10),),
        )


def test_root_family_subclass_rejected() -> None:
    bad = EconomicIdentity(
        identity_id=_economic_identity_id(1),
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=DeceptiveFamily("funds-pooled-vehicles"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=_identity_evidence(1),
    )
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=bad,
            components=(_component(10, 10),),
        )


def test_root_family_value_string_subclass_rejected() -> None:
    bad = EconomicIdentity(
        identity_id=_economic_identity_id(1),
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=IdentityFamilyCode(
            cast(str, DeceptiveString("funds-pooled-vehicles"))
        ),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=_identity_evidence(1),
    )
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=bad,
            components=(_component(10, 10),),
        )


def test_root_identity_evidence_subclass_rejected() -> None:
    bad = EconomicIdentity(
        identity_id=_economic_identity_id(1),
        kind=EconomicIdentityKind.TRADABLE_INSTRUMENT,
        family=IdentityFamilyCode("funds-pooled-vehicles"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=DeceptiveIdentityEvidenceRef(_uuid(1)),
    )
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=bad,
            components=(_component(10, 10),),
        )


def test_same_root_id_different_identity_evidence_changes_logical_material() -> None:
    a = _fund_identity_with_evidence(1, 100)
    b = _fund_identity_with_evidence(1, 200)
    qa = _qualification(fund_identity=a, components=(_component(10, 10),))
    qb = _qualification(fund_identity=b, components=(_component(10, 10),))
    assert qa.logical_values() != qb.logical_values()


def test_one_valid_component_accepted() -> None:
    q = _qualification(
        fund_identity=_fund_identity(1),
        components=(_component(10, 10),),
    )
    assert len(q.specified_securities) == 1


def test_multiple_valid_components_accepted() -> None:
    q = _qualification(
        fund_identity=_fund_identity(1),
        components=(_component(10, 10), _component(11, 11)),
    )
    assert len(q.specified_securities) == 2


def test_empty_tuple_rejected() -> None:
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=_fund_identity(1),
            components=(),
        )


def test_list_instead_of_tuple_rejected() -> None:
    bad_components = cast(
        tuple[UnitInvestmentTrustSpecifiedSecurity, ...],
        [_component(10, 10)],
    )
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        UnitInvestmentTrustQualification(
            qualification_id=_uit_id(3),
            fund_identity=_fund_identity(1),
            specified_securities=bad_components,
            evidence_ref=_uit_evidence(4),
        )


def test_raw_economic_identity_rejected_as_component() -> None:
    bad = cast(UnitInvestmentTrustSpecifiedSecurity, _fund_identity(10))
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=_fund_identity(1),
            components=(bad,),
        )


def test_raw_economic_identity_id_rejected_as_component() -> None:
    bad = cast(
        UnitInvestmentTrustSpecifiedSecurity,
        _economic_identity_id(10),
    )
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=_fund_identity(1),
            components=(bad,),
        )


def test_wrong_component_type_rejected() -> None:
    bad = cast(
        UnitInvestmentTrustSpecifiedSecurity,
        object(),
    )
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=_fund_identity(1),
            components=(bad,),
        )


def test_component_reference_object_rejected() -> None:
    bad_security = EconomicIdentity(
        identity_id=_economic_identity_id(10),
        kind=EconomicIdentityKind.REFERENCE_OBJECT,
        family=IdentityFamilyCode("equities"),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=_identity_evidence(10),
    )
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        UnitInvestmentTrustSpecifiedSecurity(
            security_identity=bad_security,
            evidence_ref=_uit_evidence(10),
        )


def test_component_wrong_local_evidence_type_rejected() -> None:
    bad_evidence = cast(
        UnitInvestmentTrustEvidenceRef,
        _identity_evidence(10),
    )
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        UnitInvestmentTrustSpecifiedSecurity(
            security_identity=_security_identity(10, 10),
            evidence_ref=bad_evidence,
        )


def test_duplicate_component_identity_rejected_even_with_different_evidence() -> None:
    c1 = _component(10, 100)
    c2 = _component(10, 200)
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=_fund_identity(1),
            components=(c1, c2),
        )


def test_reversed_component_order_canonicalizes_identically() -> None:
    c1 = _component(10, 10)
    c2 = _component(11, 11)
    qa = _qualification(
        fund_identity=_fund_identity(1),
        components=(c1, c2),
    )
    qb = _qualification(
        fund_identity=_fund_identity(1),
        components=(c2, c1),
    )
    assert qa.specified_securities == qb.specified_securities
    assert qa.logical_values() == qb.logical_values()


def test_different_component_identity_changes_logical_material() -> None:
    qa = _qualification(
        fund_identity=_fund_identity(1),
        components=(_component(10, 10),),
    )
    qb = _qualification(
        fund_identity=_fund_identity(1),
        components=(_component(11, 11),),
    )
    assert qa.logical_values() != qb.logical_values()


def test_same_component_id_different_identity_evidence_changes_component() -> None:
    a = _component_with_evidence(
        10,
        identity_evidence_index=100,
        local_evidence_index=300,
    )
    b = _component_with_evidence(
        10,
        identity_evidence_index=200,
        local_evidence_index=300,
    )
    assert a.logical_values() != b.logical_values()


def test_different_local_component_evidence_changes_logical_material() -> None:
    a = _component_with_evidence(
        10,
        identity_evidence_index=10,
        local_evidence_index=100,
    )
    b = _component_with_evidence(
        10,
        identity_evidence_index=10,
        local_evidence_index=200,
    )
    assert a.logical_values() != b.logical_values()


def test_wrong_qualification_id_type_rejected() -> None:
    bad_id = cast(UnitInvestmentTrustQualificationId, _economic_identity_id(3))
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        UnitInvestmentTrustQualification(
            qualification_id=bad_id,
            fund_identity=_fund_identity(1),
            specified_securities=(_component(10, 10),),
            evidence_ref=_uit_evidence(4),
        )


def test_wrong_qualification_evidence_type_rejected() -> None:
    bad_evidence = cast(UnitInvestmentTrustEvidenceRef, _identity_evidence(4))
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        UnitInvestmentTrustQualification(
            qualification_id=_uit_id(3),
            fund_identity=_fund_identity(1),
            specified_securities=(_component(10, 10),),
            evidence_ref=bad_evidence,
        )


def test_termination_none_accepted() -> None:
    q = _qualification(
        fund_identity=_fund_identity(1),
        components=(_component(10, 10),),
        termination=None,
    )
    assert q.logical_values()[6] is None


def test_termination_exact_date_accepted() -> None:
    q = _qualification(
        fund_identity=_fund_identity(1),
        components=(_component(10, 10),),
        termination=date(2026, 12, 31),
    )
    assert q.logical_values()[6] == "2026-12-31"


def test_datetime_masquerading_as_date_rejected() -> None:
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=_fund_identity(1),
            components=(_component(10, 10),),
            termination=datetime(2026, 12, 31),
        )


def test_wrong_termination_type_rejected() -> None:
    bad_termination = cast(date, "2026-12-31")
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=_fund_identity(1),
            components=(_component(10, 10),),
            termination=bad_termination,
        )


def test_termination_date_changes_logical_material() -> None:
    qa = _qualification(
        fund_identity=_fund_identity(1),
        components=(_component(10, 10),),
        termination=date(2026, 12, 31),
    )
    qb = _qualification(
        fund_identity=_fund_identity(1),
        components=(_component(10, 10),),
        termination=None,
    )
    assert qa.logical_values() != qb.logical_values()


def test_qualification_evidence_changes_logical_material() -> None:
    a = UnitInvestmentTrustQualification(
        qualification_id=_uit_id(3),
        fund_identity=_fund_identity(1),
        specified_securities=(_component(10, 10),),
        evidence_ref=_uit_evidence(4),
    )
    b = UnitInvestmentTrustQualification(
        qualification_id=_uit_id(3),
        fund_identity=_fund_identity(1),
        specified_securities=(_component(10, 10),),
        evidence_ref=_uit_evidence(5),
    )
    assert a.logical_values() != b.logical_values()


def test_exact_qualification_field_surface() -> None:
    assert tuple(
        field.name for field in fields(UnitInvestmentTrustQualification)
    ) == (
        "qualification_id",
        "fund_identity",
        "specified_securities",
        "evidence_ref",
        "contractual_termination_date",
    )


def test_exact_component_field_surface() -> None:
    assert tuple(
        field.name for field in fields(UnitInvestmentTrustSpecifiedSecurity)
    ) == (
        "security_identity",
        "evidence_ref",
    )


def test_exact_qualification_logical_tuple() -> None:
    q = _qualification(
        fund_identity=_fund_identity(1),
        components=(_component(11, 11), _component(10, 10)),
        termination=date(2026, 12, 31),
    )
    assert q.logical_values() == (
        "unit-investment-trust-qualification",
        q.qualification_id.logical_values(),
        q.fund_identity.logical_values(),
        "redeemable-security",
        "undivided-interest",
        tuple(component.logical_values() for component in q.specified_securities),
        "2026-12-31",
        q.evidence_ref.logical_values(),
    )


def test_exact_component_logical_tuple() -> None:
    c = _component(10, 10)
    assert c.logical_values() == (
        "specified-security",
        c.security_identity.logical_values(),
        c.evidence_ref.logical_values(),
    )


def test_no_fund_vehicle_terms_dependency() -> None:
    field_names = {
        field.name for field in fields(UnitInvestmentTrustQualification)
    }
    assert "fund_vehicle_terms" not in field_names


def test_no_unit_investment_trust_enum_member_added() -> None:
    assert not hasattr(FundVehicleKind, "UNIT_INVESTMENT_TRUST")


def test_listing_negative_space() -> None:
    q = _qualification(
        fund_identity=_fund_identity(1),
        components=(_component(10, 10),),
    )
    assert not hasattr(q, "listing")
    assert not hasattr(q, "venue")
    assert not hasattr(q, "listed")


def test_nav_negative_space() -> None:
    q = _qualification(
        fund_identity=_fund_identity(1),
        components=(_component(10, 10),),
    )
    for attr in (
        "nav",
        "nav_basis",
        "nav_value",
        "calculate_nav",
        "calculate",
        "observe",
    ):
        assert not hasattr(q, attr)


def test_lifecycle_event_cannot_substitute_termination() -> None:
    bad = cast(date, object.__new__(IdentityLifecycleEvent))
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=_fund_identity(1),
            components=(_component(10, 10),),
            termination=bad,
        )


def test_structured_component_cannot_substitute_specified_security() -> None:
    bad = cast(
        UnitInvestmentTrustSpecifiedSecurity,
        object.__new__(StructuredComponentBinding),
    )
    with pytest.raises(UnitInvestmentTrustQualificationValidationError):
        _qualification(
            fund_identity=_fund_identity(1),
            components=(bad,),
        )


_FORBIDDEN_AUTHORITY_FIELDS = {
    "current_nav",
    "nav_value",
    "nav_calculation",
    "current_holdings",
    "quantity",
    "portfolio_weight",
    "allocation",
    "market_value",
    "redemption_price",
    "redemption_request",
    "redemption_execution",
    "cash_distribution",
    "in_kind_settlement",
    "liquidation_execution",
    "provider_symbol",
    "provider_capability",
    "board",
    "trustee_regulatory_status",
    "custodian_regulatory_status",
    "SEC_registration",
    "legal_eligibility",
    "fees",
    "sales_charge",
    "secondary_market_support",
    "order",
    "trade",
    "receipt",
    "settlement_mutation",
    "redeemable",
    "undivided_interest",
}

_FORBIDDEN_OPERATIONAL_METHODS = {
    "calculate",
    "calculate_nav",
    "observe",
    "redeem",
    "execute",
    "settle",
    "liquidate",
    "schedule",
    "terminate",
    "roll",
    "sleep",
    "thread",
    "timer",
}


def test_qualification_field_names_disjoint_forbidden_authority_fields() -> None:
    actual = {
        field.name for field in fields(UnitInvestmentTrustQualification)
    }
    assert actual.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)


def test_component_field_names_disjoint_forbidden_authority_fields() -> None:
    actual = {
        field.name for field in fields(UnitInvestmentTrustSpecifiedSecurity)
    }
    assert actual.isdisjoint(_FORBIDDEN_AUTHORITY_FIELDS)


def test_qualification_has_no_forbidden_operational_methods() -> None:
    q = _qualification(
        fund_identity=_fund_identity(1),
        components=(_component(10, 10),),
    )
    for method in _FORBIDDEN_OPERATIONAL_METHODS:
        assert not hasattr(q, method)


def test_component_has_no_forbidden_operational_methods() -> None:
    c = _component(10, 10)
    for method in _FORBIDDEN_OPERATIONAL_METHODS:
        assert not hasattr(c, method)


def test_mandatory_semantic_tags_present_in_logical_values() -> None:
    q = _qualification(
        fund_identity=_fund_identity(1),
        components=(_component(10, 10),),
    )
    assert "redeemable-security" in q.logical_values()
    assert "undivided-interest" in q.logical_values()


def test_qualification_is_frozen_and_slotted() -> None:
    q = _qualification(
        fund_identity=_fund_identity(1),
        components=(_component(10, 10),),
    )
    with pytest.raises(FrozenInstanceError):
        setattr(q, "evidence_ref", _uit_evidence(99))
    assert not hasattr(q, "__dict__")


def test_component_is_frozen_and_slotted() -> None:
    c = _component(10, 10)
    with pytest.raises(FrozenInstanceError):
        setattr(c, "evidence_ref", _uit_evidence(99))
    assert not hasattr(c, "__dict__")
