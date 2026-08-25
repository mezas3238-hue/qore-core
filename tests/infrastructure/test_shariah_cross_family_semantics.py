from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.shariah_cross_family_semantics import (
    ShariahCrossFamilyCategory,
    ShariahCrossFamilyQualification,
    ShariahCrossFamilyQualificationId,
    ShariahCrossFamilyValidationError,
    ShariahEvidenceRef,
    ShariahFinancingLiquidityKind,
    ShariahFinancingLiquidityTerms,
    ShariahFrameworkCode,
    ShariahHedgingKind,
    ShariahHedgingQualificationTerms,
    ShariahParticipantBinding,
    ShariahParticipantBindingId,
    ShariahPartyReferenceId,
    ShariahPartyRoleCode,
    ShariahSyndicatedFinancingKind,
    ShariahSyndicatedFinancingTerms,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentity,
    EconomicIdentityId,
    EconomicIdentityKind,
    IdentityConstructionKind,
    IdentityEvidenceRef,
    IdentityFamilyCode,
)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _identity(
    value: int,
    family: str,
    *,
    kind: EconomicIdentityKind = EconomicIdentityKind.TRADABLE_INSTRUMENT,
    construction: IdentityConstructionKind = IdentityConstructionKind.NATIVE,
) -> EconomicIdentity:
    return EconomicIdentity(
        EconomicIdentityId(_uuid(value)),
        kind,
        IdentityFamilyCode(family),
        construction,
        IdentityEvidenceRef(_uuid(10000 + value)),
    )


def _evidence(value: int) -> ShariahEvidenceRef:
    return ShariahEvidenceRef(_uuid(value))


def _participant(
    value: int,
    *,
    party: int | None = None,
    role: str = "financier",
) -> ShariahParticipantBinding:
    return ShariahParticipantBinding(
        ShariahParticipantBindingId(_uuid(value)),
        ShariahPartyReferenceId(_uuid(value + 100 if party is None else party)),
        ShariahPartyRoleCode(role),
        _evidence(value + 200),
    )


def _financing(
    *,
    structure: ShariahFinancingLiquidityKind = ShariahFinancingLiquidityKind.MURABAHAH,
    identity: EconomicIdentity | None = None,
    participants: tuple[ShariahParticipantBinding, ...] | None = None,
    related: tuple[EconomicIdentityId, ...] = (),
    start: date = date(2026, 8, 25),
    end: date | None = None,
) -> ShariahFinancingLiquidityTerms:
    return ShariahFinancingLiquidityTerms(
        structure=structure,
        primary_identity=identity or _identity(1, "fixed-income-credit"),
        participants=participants
        or (
            _participant(10, role="financier"),
            _participant(11, role="customer"),
        ),
        start_date=start,
        evidence_ref=_evidence(12),
        related_identity_ids=related,
        end_date=end,
    )


def _hedging(
    *,
    structure: ShariahHedgingKind = ShariahHedgingKind.PROFIT_RATE_HEDGING,
    identity: EconomicIdentity | None = None,
    related: tuple[EconomicIdentityId, ...] = (),
) -> ShariahHedgingQualificationTerms:
    return ShariahHedgingQualificationTerms(
        structure=structure,
        hedged_identity=identity or _identity(20, "forwards-swaps-otc"),
        evidence_ref=_evidence(21),
        related_identity_ids=related,
    )


def _syndicated(
    *,
    structure: ShariahSyndicatedFinancingKind = ShariahSyndicatedFinancingKind.IJARAH,
    identity: EconomicIdentity | None = None,
    participants: tuple[ShariahParticipantBinding, ...] | None = None,
) -> ShariahSyndicatedFinancingTerms:
    return ShariahSyndicatedFinancingTerms(
        structure=structure,
        primary_identity=identity or _identity(30, "loans-credit-facilities"),
        participants=participants
        or (
            _participant(31, role="arranger"),
            _participant(32, role="participant"),
        ),
        evidence_ref=_evidence(33),
    )


def _qualification(
    category: ShariahCrossFamilyCategory,
    terms: (
        ShariahFinancingLiquidityTerms
        | ShariahHedgingQualificationTerms
        | ShariahSyndicatedFinancingTerms
    ),
    *,
    effective: date = date(2026, 8, 25),
    end: date | None = None,
) -> ShariahCrossFamilyQualification:
    return ShariahCrossFamilyQualification(
        qualification_id=ShariahCrossFamilyQualificationId(_uuid(100)),
        category=category,
        terms=terms,
        effective_date=effective,
        framework=ShariahFrameworkCode("iifm-retained-reference"),
        evidence_ref=_evidence(101),
        end_date=end,
    )


def test_versioned_retained_structure_sets_are_exact() -> None:
    assert tuple(item.value for item in ShariahFinancingLiquidityKind) == (
        "murabahah",
        "wakalah-agency",
        "collateralized-murabahah",
    )
    assert tuple(item.value for item in ShariahHedgingKind) == (
        "profit-rate-hedging",
        "cross-currency-hedging",
        "islamic-fx-forward",
    )
    assert tuple(item.value for item in ShariahSyndicatedFinancingKind) == (
        "ijarah",
        "murabahah",
    )


@pytest.mark.parametrize(
    ("structure", "family"),
    (
        (ShariahFinancingLiquidityKind.MURABAHAH, "fixed-income-credit"),
        (ShariahFinancingLiquidityKind.WAKALAH_AGENCY, "cash-money-market"),
        (
            ShariahFinancingLiquidityKind.COLLATERALIZED_MURABAHAH,
            "structured-hybrid-products",
        ),
        (ShariahFinancingLiquidityKind.MURABAHAH, "loans-credit-facilities"),
    ),
)
def test_financing_liquidity_accepts_retained_cross_family_surface(
    structure: ShariahFinancingLiquidityKind,
    family: str,
) -> None:
    terms = _financing(structure=structure, identity=_identity(200, family))
    result = _qualification(ShariahCrossFamilyCategory.FINANCING_LIQUIDITY, terms)
    assert result.logical_values()[1] == "financing-liquidity"


@pytest.mark.parametrize("structure", tuple(ShariahHedgingKind))
def test_hedging_qualifies_existing_otc_identity(
    structure: ShariahHedgingKind,
) -> None:
    result = _qualification(
        ShariahCrossFamilyCategory.HEDGING,
        _hedging(structure=structure),
    )
    assert result.logical_values()[2][0] == "shariah-hedging"


@pytest.mark.parametrize("structure", tuple(ShariahSyndicatedFinancingKind))
def test_syndicated_financing_qualifies_existing_loan_family(
    structure: ShariahSyndicatedFinancingKind,
) -> None:
    result = _qualification(
        ShariahCrossFamilyCategory.SYNDICATED_FINANCING,
        _syndicated(structure=structure),
    )
    assert result.logical_values()[2][0] == "shariah-syndicated-financing"


def test_category_and_terms_variant_must_match_exactly() -> None:
    with pytest.raises(
        ShariahCrossFamilyValidationError,
        match="category and terms variant must match exactly",
    ):
        _qualification(ShariahCrossFamilyCategory.HEDGING, _financing())

    with pytest.raises(
        ShariahCrossFamilyValidationError,
        match="category and terms variant must match exactly",
    ):
        _qualification(
            ShariahCrossFamilyCategory.SYNDICATED_FINANCING,
            _hedging(),
        )


def test_family_rules_fail_closed_where_family_is_material() -> None:
    with pytest.raises(ShariahCrossFamilyValidationError, match="family is not allowed"):
        _financing(identity=_identity(300, "forwards-swaps-otc"))

    with pytest.raises(ShariahCrossFamilyValidationError, match="family is not allowed"):
        _hedging(identity=_identity(301, "fx"))

    with pytest.raises(ShariahCrossFamilyValidationError, match="family is not allowed"):
        _syndicated(identity=_identity(302, "fixed-income-credit"))


def test_related_identity_links_are_exact_unique_and_canonical() -> None:
    first = EconomicIdentityId(_uuid(500))
    second = EconomicIdentityId(_uuid(400))
    terms = _hedging(related=(first, second))
    assert terms.related_identity_ids == (second, first)

    with pytest.raises(
        ShariahCrossFamilyValidationError,
        match="duplicate economic identities",
    ):
        _hedging(related=(first, EconomicIdentityId(_uuid(500))))


def test_participants_reject_duplicate_binding_id_and_duplicate_party_role() -> None:
    first = _participant(600, party=700, role="financier")
    same_binding = ShariahParticipantBinding(
        first.binding_id,
        ShariahPartyReferenceId(_uuid(701)),
        ShariahPartyRoleCode("customer"),
        _evidence(702),
    )
    with pytest.raises(ShariahCrossFamilyValidationError, match="binding ids must be unique"):
        _financing(participants=(first, same_binding))

    same_party_role = _participant(601, party=700, role="financier")
    with pytest.raises(ShariahCrossFamilyValidationError, match="party-role"):
        _financing(participants=(first, same_party_role))


def test_one_party_may_hold_distinct_contractual_roles() -> None:
    first = _participant(610, party=710, role="agent")
    second = _participant(611, party=710, role="financier")
    terms = _financing(participants=(first, second))
    assert len(terms.participants) == 2


def test_participant_order_is_canonical_and_caller_independent() -> None:
    first = _participant(620, party=900, role="customer")
    second = _participant(621, party=800, role="financier")
    forward = _financing(participants=(first, second))
    reverse = _financing(participants=(second, first))
    assert forward.logical_values() == reverse.logical_values()


def test_exact_collection_and_date_types_are_required() -> None:
    with pytest.raises(ShariahCrossFamilyValidationError, match="non-empty exact tuple"):
        _financing(participants=cast(Any, [_participant(630)]))

    with pytest.raises(ShariahCrossFamilyValidationError, match="exact tuple"):
        _hedging(related=cast(Any, [EconomicIdentityId(_uuid(631))]))

    bad_date = datetime(2026, 8, 25, 12, 0)
    with pytest.raises(ShariahCrossFamilyValidationError, match="exact date"):
        _financing(start=cast(Any, bad_date))

    with pytest.raises(ShariahCrossFamilyValidationError, match="exact date"):
        _qualification(
            ShariahCrossFamilyCategory.HEDGING,
            _hedging(),
            effective=cast(Any, bad_date),
        )


def test_chronology_is_explicit_and_fail_closed() -> None:
    with pytest.raises(ShariahCrossFamilyValidationError, match="end_date"):
        _financing(start=date(2026, 8, 25), end=date(2026, 8, 24))

    with pytest.raises(ShariahCrossFamilyValidationError, match="end_date"):
        _qualification(
            ShariahCrossFamilyCategory.HEDGING,
            _hedging(),
            effective=date(2026, 8, 25),
            end=date(2026, 8, 24),
        )


def test_uuid_and_code_subclass_laundering_are_rejected() -> None:
    class UUIDSubclass(UUID):
        pass

    class StrSubclass(str):
        pass

    with pytest.raises(ShariahCrossFamilyValidationError, match="exact UUID"):
        ShariahPartyReferenceId(UUIDSubclass(int=1))

    with pytest.raises(ShariahCrossFamilyValidationError, match="canonical lowercase"):
        ShariahFrameworkCode(StrSubclass("iifm"))


def test_economic_identity_wrapper_and_inner_state_are_revalidated() -> None:
    class EconomicIdentityIdSubclass(EconomicIdentityId):
        pass

    fabricated = object.__new__(EconomicIdentity)
    object.__setattr__(fabricated, "identity_id", EconomicIdentityIdSubclass(_uuid(700)))
    object.__setattr__(fabricated, "kind", EconomicIdentityKind.TRADABLE_INSTRUMENT)
    object.__setattr__(fabricated, "family", IdentityFamilyCode("forwards-swaps-otc"))
    object.__setattr__(fabricated, "construction", IdentityConstructionKind.NATIVE)
    object.__setattr__(fabricated, "evidence_ref", IdentityEvidenceRef(_uuid(701)))
    with pytest.raises(ShariahCrossFamilyValidationError, match="exact EconomicIdentityId"):
        _hedging(identity=fabricated)

    identity = _identity(702, "forwards-swaps-otc")
    terms = _hedging(identity=identity)
    object.__setattr__(identity.identity_id, "value", "corrupted")
    with pytest.raises(ShariahCrossFamilyValidationError, match="exact UUID"):
        terms.logical_values()


def test_economic_identity_family_code_is_revalidated_after_corruption() -> None:
    identity = _identity(710, "forwards-swaps-otc")
    terms = _hedging(identity=identity)
    object.__setattr__(identity.family, "value", "INVALID CODE")
    with pytest.raises(ShariahCrossFamilyValidationError, match="canonical lowercase"):
        terms.logical_values()


def test_continuous_reference_relationship_is_reapplied() -> None:
    fabricated = object.__new__(EconomicIdentity)
    object.__setattr__(fabricated, "identity_id", EconomicIdentityId(_uuid(720)))
    object.__setattr__(fabricated, "kind", EconomicIdentityKind.TRADABLE_INSTRUMENT)
    object.__setattr__(fabricated, "family", IdentityFamilyCode("forwards-swaps-otc"))
    object.__setattr__(
        fabricated,
        "construction",
        IdentityConstructionKind.CONTINUOUS_REFERENCE,
    )
    object.__setattr__(fabricated, "evidence_ref", IdentityEvidenceRef(_uuid(721)))
    with pytest.raises(ShariahCrossFamilyValidationError, match="reference object"):
        _hedging(identity=fabricated)


def test_nested_participant_state_is_revalidated_on_logical_values() -> None:
    participant = _participant(730)
    terms = _financing(participants=(participant, _participant(731)))
    object.__setattr__(participant.role, "value", "INVALID CODE")
    with pytest.raises(ShariahCrossFamilyValidationError, match="canonical lowercase"):
        terms.logical_values()


def test_logical_values_are_deterministic_and_revalidate_recursively() -> None:
    qualification = _qualification(
        ShariahCrossFamilyCategory.FINANCING_LIQUIDITY,
        _financing(
            structure=ShariahFinancingLiquidityKind.WAKALAH_AGENCY,
            identity=_identity(740, "cash-money-market"),
            related=(EconomicIdentityId(_uuid(742)), EconomicIdentityId(_uuid(741))),
            end=date(2027, 8, 25),
        ),
        end=date(2027, 8, 25),
    )
    first = qualification.logical_values()
    second = qualification.logical_values()
    assert first == second
    assert first[1] == "financing-liquidity"


def test_contract_has_no_implicit_clock_identity_or_operational_authority() -> None:
    import inspect

    import qore.infrastructure.shariah_cross_family_semantics as module

    source = inspect.getsource(module)
    assert "datetime.now" not in source
    assert "date.today" not in source
    assert "uuid4" not in source
    assert "requests." not in source
    assert "httpx." not in source
    assert "submit_order" not in source
    assert "settle_order" not in source
    assert "calculate_pv" not in source
    assert "religious_compliance" not in source
