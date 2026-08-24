from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from datetime import date, datetime
from typing import cast
from uuid import UUID

import pytest

import qore.infrastructure.sukuk_structural_semantics as sukuk_module
from qore.infrastructure.sukuk_structural_semantics import (
    SukukCertificateInterestCode,
    SukukDistributionSource,
    SukukDistributionSourceCode,
    SukukEvidenceRef,
    SukukExternalShariahEvidence,
    SukukQualificationId,
    SukukShariahFrameworkCode,
    SukukStructuralLeg,
    SukukStructuralLegId,
    SukukStructuralLegKindCode,
    SukukStructuralLegRoleCode,
    SukukStructuralQualification,
    SukukStructuralSemanticsValidationError,
    SukukStructureCode,
    SukukUnderlyingBindingId,
    SukukUnderlyingInterestBinding,
    SukukUnderlyingInterestCode,
    SukukUnderlyingRoleCode,
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
    i: int,
    *,
    family: str = "fixed-income-credit",
    kind: EconomicIdentityKind = EconomicIdentityKind.TRADABLE_INSTRUMENT,
) -> EconomicIdentity:
    return EconomicIdentity(
        identity_id=EconomicIdentityId(_uuid(i)),
        kind=kind,
        family=IdentityFamilyCode(family),
        construction=IdentityConstructionKind.NATIVE,
        evidence_ref=IdentityEvidenceRef(_uuid(1000 + i)),
    )


def _binding(
    binding_index: int,
    identity_index: int,
    *,
    role: str = "leased-asset",
    interest: str = "usufruct-interest",
    family: str = "real-asset-reference",
    kind: EconomicIdentityKind = EconomicIdentityKind.REFERENCE_OBJECT,
) -> SukukUnderlyingInterestBinding:
    return SukukUnderlyingInterestBinding(
        binding_id=SukukUnderlyingBindingId(_uuid(2000 + binding_index)),
        underlying_identity=_identity(
            identity_index,
            family=family,
            kind=kind,
        ),
        role=SukukUnderlyingRoleCode(role),
        interest=SukukUnderlyingInterestCode(interest),
        evidence_ref=SukukEvidenceRef(_uuid(3000 + binding_index)),
    )


def _leg(
    leg_index: int,
    ordinal: int,
    *,
    kind: str,
    role: str,
    related: SukukUnderlyingBindingId | None = None,
) -> SukukStructuralLeg:
    return SukukStructuralLeg(
        leg_id=SukukStructuralLegId(_uuid(4000 + leg_index)),
        ordinal=ordinal,
        kind=SukukStructuralLegKindCode(kind),
        role=SukukStructuralLegRoleCode(role),
        evidence_ref=SukukEvidenceRef(_uuid(5000 + leg_index)),
        related_underlying_binding_id=related,
    )


def _qualification(
    *,
    certificate: EconomicIdentity | None = None,
    structure: str = "ijarah",
    certificate_interest: str = "undivided-beneficial-interest",
    underlyings: tuple[SukukUnderlyingInterestBinding, ...] | None = None,
    legs: tuple[SukukStructuralLeg, ...] | None = None,
    distribution_source: str = "lease-rental",
    distribution_related: SukukUnderlyingBindingId | None = None,
    framework: str = "iifm-sukuk-al-ijarah",
    maturity: date | None = date(2030, 1, 1),
) -> SukukStructuralQualification:
    root = certificate or _identity(1)
    default_binding = _binding(1, 10)
    selected_underlyings = (
        underlyings if underlyings is not None else (default_binding,)
    )
    default_related = (
        min(
            selected_underlyings,
            key=lambda binding: str(binding.binding_id.value),
        ).binding_id
        if selected_underlyings
        else None
    )
    selected_legs = (
        legs
        if legs is not None
        else (
            _leg(
                1,
                1,
                kind="sale-purchase",
                role="asset-transfer",
                related=default_related,
            ),
            _leg(
                2,
                2,
                kind="lease",
                role="usufruct-generation",
                related=default_related,
            ),
            _leg(
                3,
                3,
                kind="declaration-of-trust",
                role="certificate-trust",
            ),
        )
    )
    return SukukStructuralQualification(
        qualification_id=SukukQualificationId(_uuid(6001)),
        certificate_identity=root,
        structure=SukukStructureCode(structure),
        certificate_interest=SukukCertificateInterestCode(certificate_interest),
        underlying_interests=selected_underlyings,
        structural_legs=selected_legs,
        distribution_source=SukukDistributionSource(
            source=SukukDistributionSourceCode(distribution_source),
            related_underlying_binding_id=(
                distribution_related
                if distribution_related is not None
                else default_related
            ),
            evidence_ref=SukukEvidenceRef(_uuid(6002)),
        ),
        shariah_evidence=SukukExternalShariahEvidence(
            framework=SukukShariahFrameworkCode(framework),
            evidence_ref=SukukEvidenceRef(_uuid(6003)),
            effective_date=date(2026, 8, 15),
        ),
        issue_date=date(2026, 8, 15),
        maturity_date=maturity,
        evidence_ref=SukukEvidenceRef(_uuid(6004)),
    )


def test_valid_ijarah_qualification_retains_non_debt_structure() -> None:
    value = _qualification()
    logical = value.logical_values()
    distribution = cast(tuple[object, ...], logical[7])
    shariah = cast(tuple[object, ...], logical[8])

    assert logical[0] == "sukuk-structural-qualification"
    assert logical[3] == ("ijarah",)
    assert logical[4] == ("undivided-beneficial-interest",)
    assert distribution[1] == ("lease-rental",)
    assert shariah[1] == ("iifm-sukuk-al-ijarah",)


def test_valid_perpetual_mudarabah_certificate() -> None:
    partnership = _binding(
        1,
        20,
        role="mudarabah-venture",
        interest="partnership-interest",
        family="structured-hybrid-products",
        kind=EconomicIdentityKind.REFERENCE_OBJECT,
    )
    value = _qualification(
        certificate=_identity(2, family="structured-hybrid-products"),
        structure="mudarabah",
        certificate_interest="partnership-interest",
        underlyings=(partnership,),
        legs=(
            _leg(
                1,
                1,
                kind="mudarabah-agreement",
                role="venture-participation",
                related=partnership.binding_id,
            ),
            _leg(
                2,
                2,
                kind="declaration-of-trust",
                role="certificate-trust",
            ),
        ),
        distribution_source="mudarabah-profit",
        framework="iifm-sukuk-al-mudarabah-tier1",
        maturity=None,
    )
    assert value.maturity_date is None
    assert value.logical_values()[3] == ("mudarabah",)


def test_underlying_input_order_is_canonical() -> None:
    first = _binding(1, 10, role="leased-asset", interest="usufruct-interest")
    second = _binding(2, 11, role="reserve-asset", interest="ownership-interest")
    a = _qualification(underlyings=(second, first))
    b = _qualification(underlyings=(first, second))

    assert a.logical_values() == b.logical_values()
    assert a.underlying_interests[0].underlying_identity.identity_id == (
        first.underlying_identity.identity_id
    )


def test_same_underlying_with_different_role_or_interest_remains_distinct() -> None:
    first = _binding(1, 10, role="leased-asset", interest="usufruct-interest")
    second = _binding(2, 10, role="reserve-asset", interest="ownership-interest")
    value = _qualification(underlyings=(first, second))

    assert len(value.underlying_interests) == 2


def test_semantic_duplicate_underlying_rejected_with_different_ids() -> None:
    first = _binding(1, 10)
    duplicate = _binding(2, 10)

    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(underlyings=(first, duplicate))


def test_duplicate_underlying_binding_id_rejected() -> None:
    first = _binding(1, 10)
    second = SukukUnderlyingInterestBinding(
        binding_id=first.binding_id,
        underlying_identity=_identity(
            11,
            family="real-asset-reference",
            kind=EconomicIdentityKind.REFERENCE_OBJECT,
        ),
        role=SukukUnderlyingRoleCode("reserve-asset"),
        interest=SukukUnderlyingInterestCode("ownership-interest"),
        evidence_ref=SukukEvidenceRef(_uuid(3999)),
    )

    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(underlyings=(first, second))


def test_structural_leg_order_is_canonical_by_explicit_ordinal() -> None:
    binding = _binding(1, 10)
    first = _leg(
        1,
        1,
        kind="sale-purchase",
        role="asset-transfer",
        related=binding.binding_id,
    )
    second = _leg(
        2,
        2,
        kind="lease",
        role="usufruct-generation",
        related=binding.binding_id,
    )
    a = _qualification(underlyings=(binding,), legs=(second, first))
    b = _qualification(underlyings=(binding,), legs=(first, second))

    assert a.logical_values() == b.logical_values()
    assert tuple(leg.ordinal for leg in a.structural_legs) == (1, 2)


def test_changing_leg_ordinals_changes_contractual_structure() -> None:
    binding = _binding(1, 10)
    first = _leg(
        1,
        1,
        kind="sale-purchase",
        role="asset-transfer",
        related=binding.binding_id,
    )
    second = _leg(
        2,
        2,
        kind="lease",
        role="usufruct-generation",
        related=binding.binding_id,
    )
    reversed_first = _leg(
        1,
        2,
        kind="sale-purchase",
        role="asset-transfer",
        related=binding.binding_id,
    )
    reversed_second = _leg(
        2,
        1,
        kind="lease",
        role="usufruct-generation",
        related=binding.binding_id,
    )

    baseline = _qualification(
        underlyings=(binding,),
        legs=(first, second),
    ).logical_values()
    reordered = _qualification(
        underlyings=(binding,),
        legs=(reversed_first, reversed_second),
    ).logical_values()
    assert baseline != reordered


def test_duplicate_leg_id_and_ordinal_fail_closed() -> None:
    binding = _binding(1, 10)
    first = _leg(
        1,
        1,
        kind="lease",
        role="usufruct-generation",
        related=binding.binding_id,
    )
    duplicate_id = SukukStructuralLeg(
        leg_id=first.leg_id,
        ordinal=2,
        kind=SukukStructuralLegKindCode("service-agency"),
        role=SukukStructuralLegRoleCode("asset-servicing"),
        evidence_ref=SukukEvidenceRef(_uuid(5998)),
    )

    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(underlyings=(binding,), legs=(first, duplicate_id))

    duplicate_ordinal = _leg(
        2,
        1,
        kind="service-agency",
        role="asset-servicing",
    )
    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(underlyings=(binding,), legs=(first, duplicate_ordinal))


def test_leg_and_distribution_cannot_reference_undeclared_underlying() -> None:
    binding = _binding(1, 10)
    missing = SukukUnderlyingBindingId(_uuid(9999))
    bad_leg = _leg(
        1,
        1,
        kind="lease",
        role="usufruct-generation",
        related=missing,
    )

    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(underlyings=(binding,), legs=(bad_leg,))
    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(
            underlyings=(binding,),
            distribution_related=missing,
        )


def test_root_must_be_tradable_and_in_existing_bounded_family() -> None:
    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(certificate=_identity(1, family="equities"))
    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(
            certificate=_identity(
                1,
                kind=EconomicIdentityKind.REFERENCE_OBJECT,
            )
        )
    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(certificate=_identity(1, family="cash-money-market"))


def test_certificate_cannot_be_its_own_underlying() -> None:
    root = _identity(1)
    self_binding = SukukUnderlyingInterestBinding(
        binding_id=SukukUnderlyingBindingId(_uuid(2001)),
        underlying_identity=root,
        role=SukukUnderlyingRoleCode("certificate-asset"),
        interest=SukukUnderlyingInterestCode("ownership-interest"),
        evidence_ref=SukukEvidenceRef(_uuid(3001)),
    )

    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(certificate=root, underlyings=(self_binding,))


def test_mutable_or_empty_collections_fail_closed() -> None:
    binding = _binding(1, 10)
    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(
            underlyings=cast(
                tuple[SukukUnderlyingInterestBinding, ...],
                [binding],
            )
        )
    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(underlyings=())

    leg = _leg(1, 1, kind="lease", role="usufruct-generation")
    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(legs=cast(tuple[SukukStructuralLeg, ...], [leg]))
    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(legs=())


def test_collection_element_types_are_exact() -> None:
    binding = _binding(1, 10)
    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(
            underlyings=cast(
                tuple[SukukUnderlyingInterestBinding, ...],
                (binding, "bad"),
            )
        )
    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(
            legs=cast(
                tuple[SukukStructuralLeg, ...],
                (cast(SukukStructuralLeg, object()),),
            )
        )


def test_ordinal_rejects_bool_zero_and_negative() -> None:
    for invalid in (cast(int, True), 0, -1):
        with pytest.raises(SukukStructuralSemanticsValidationError):
            _leg(
                1,
                invalid,
                kind="lease",
                role="usufruct-generation",
            )


def test_date_roles_are_exact_and_perpetual_is_allowed() -> None:
    with pytest.raises(SukukStructuralSemanticsValidationError):
        SukukExternalShariahEvidence(
            framework=SukukShariahFrameworkCode("iifm-sukuk"),
            evidence_ref=SukukEvidenceRef(_uuid(1)),
            effective_date=cast(date, datetime(2026, 8, 15)),
        )

    value = _qualification(maturity=None)
    assert value.maturity_date is None

    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(maturity=date(2026, 8, 15))


def test_code_boundaries_reject_subclasses_and_noncanonical_material() -> None:
    class StringSubclass(str):
        pass

    invalid_values = (
        cast(str, StringSubclass("ijarah")),
        "Ijarah",
        "ijarah ",
        "ijarah/lease",
        "a" * 97,
    )
    for invalid in invalid_values:
        with pytest.raises(SukukStructuralSemanticsValidationError):
            SukukStructureCode(invalid)


def test_uuid_wrappers_reject_non_uuid_runtime_values() -> None:
    with pytest.raises(SukukStructuralSemanticsValidationError):
        SukukQualificationId(cast(UUID, "not-a-uuid"))
    with pytest.raises(SukukStructuralSemanticsValidationError):
        SukukEvidenceRef(cast(UUID, object()))


def test_wrapper_runtime_types_are_exact_at_composition_boundary() -> None:
    value = _qualification()
    object.__setattr__(value, "structure", cast(SukukStructureCode, object()))

    with pytest.raises(SukukStructuralSemanticsValidationError):
        value.logical_values()


def test_reflective_root_identity_corruption_fails_on_projection() -> None:
    value = _qualification()
    object.__setattr__(
        value.certificate_identity.identity_id,
        "value",
        cast(UUID, "corrupt"),
    )

    with pytest.raises(SukukStructuralSemanticsValidationError):
        value.logical_values()


def test_reflective_underlying_and_leg_corruption_fail_closed() -> None:
    value = _qualification()
    object.__setattr__(
        value.underlying_interests[0].role,
        "value",
        "Bad Role",
    )
    with pytest.raises(SukukStructuralSemanticsValidationError):
        value.logical_values()

    fresh = _qualification()
    object.__setattr__(fresh.structural_legs[0], "ordinal", cast(int, True))
    with pytest.raises(SukukStructuralSemanticsValidationError):
        fresh.logical_values()


def test_identity_family_str_subclass_laundering_is_rejected_locally() -> None:
    class StringSubclass(str):
        pass

    root = _identity(1)
    object.__setattr__(
        root.family,
        "value",
        StringSubclass("fixed-income-credit"),
    )

    with pytest.raises(SukukStructuralSemanticsValidationError):
        _qualification(certificate=root)


def test_structure_interest_distribution_and_framework_are_material() -> None:
    baseline = _qualification().logical_values()

    assert _qualification(structure="mudarabah").logical_values() != baseline
    assert (
        _qualification(certificate_interest="ownership-interest").logical_values()
        != baseline
    )
    assert (
        _qualification(distribution_source="asset-income").logical_values()
        != baseline
    )
    assert (
        _qualification(framework="external-board-reference").logical_values()
        != baseline
    )


def test_evidence_references_are_material() -> None:
    baseline = _qualification()
    altered = SukukStructuralQualification(
        qualification_id=baseline.qualification_id,
        certificate_identity=baseline.certificate_identity,
        structure=baseline.structure,
        certificate_interest=baseline.certificate_interest,
        underlying_interests=baseline.underlying_interests,
        structural_legs=baseline.structural_legs,
        distribution_source=baseline.distribution_source,
        shariah_evidence=baseline.shariah_evidence,
        issue_date=baseline.issue_date,
        maturity_date=baseline.maturity_date,
        evidence_ref=SukukEvidenceRef(_uuid(7000)),
    )

    assert baseline.logical_values() != altered.logical_values()


def test_qualification_is_frozen() -> None:
    value = _qualification()

    with pytest.raises(FrozenInstanceError):
        type(value).__setattr__(value, "maturity_date", None)


def test_source_has_no_engine_provider_or_implicit_clock_path() -> None:
    source = inspect.getsource(sukuk_module)

    assert "fixed_income_economics" not in source
    assert "datetime.now" not in source
    assert "uuid4" not in source
    assert "import requests" not in source
    assert "import httpx" not in source
    assert "def calculate" not in source
    assert "def compute" not in source
