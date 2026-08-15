from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeCompositionLeg,
    DerivativeCompositionSide,
    DerivativeCompositionTerms,
    DerivativeEvidenceRef,
    DerivativeLegId,
    DerivativeLegOrdinal,
    DerivativeTermsId,
)
from qore.infrastructure.structured_hybrid_synthetic_semantics import (
    StructuredAutocallFeature,
    StructuredBarrierDirection,
    StructuredBarrierFeature,
    StructuredBarrierKindCode,
    StructuredCapitalProtectionFeature,
    StructuredComponentBinding,
    StructuredComponentRoleCode,
    StructuredContractLevel,
    StructuredContractLevelKind,
    StructuredConversionFeature,
    StructuredEvidenceRef,
    StructuredFeatureId,
    StructuredHybridSyntheticTerms,
    StructuredHybridSyntheticValidationError,
    StructuredLevelUnitCode,
    StructuredObservationMode,
    StructuredObservationScheduleCode,
    StructuredObservationTerms,
    StructuredParticipationDirection,
    StructuredParticipationFeature,
    StructuredPositiveRatio,
    StructuredRedemptionFeature,
    StructuredTermsId,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentityId,
    IdentityEvidenceRef,
    IdentityRelationship,
    IdentityRelationshipCode,
    IdentityRelationshipId,
)


def _economic_id(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(UUID(int=value))


def _evidence(value: int) -> StructuredEvidenceRef:
    return StructuredEvidenceRef(UUID(int=value))


def _feature_id(value: int) -> StructuredFeatureId:
    return StructuredFeatureId(UUID(int=value))


def _relationship(
    root: EconomicIdentityId,
    target: EconomicIdentityId,
    *,
    relationship_id: int,
    ordinal: int | None = None,
    code: str = "structured-component",
    effective_from: datetime | None = None,
) -> IdentityRelationship:
    return IdentityRelationship(
        relationship_id=IdentityRelationshipId(UUID(int=relationship_id)),
        source_identity_id=root,
        target_identity_id=target,
        relationship=IdentityRelationshipCode(code),
        effective_from=effective_from or datetime(2026, 1, 1, tzinfo=UTC),
        effective_until=None,
        evidence_ref=IdentityEvidenceRef(UUID(int=relationship_id + 10_000)),
        ordinal=ordinal,
    )


def _component(
    root: EconomicIdentityId,
    target: EconomicIdentityId,
    *,
    relationship_id: int,
    ordinal: int | None = None,
    code: str = "structured-component",
    role: str = "reference-component",
    effective_from: datetime | None = None,
) -> StructuredComponentBinding:
    return StructuredComponentBinding(
        root_identity_id=root,
        relationship=_relationship(
            root,
            target,
            relationship_id=relationship_id,
            ordinal=ordinal,
            code=code,
            effective_from=effective_from,
        ),
        role=StructuredComponentRoleCode(role),
        evidence_ref=_evidence(relationship_id + 20_000),
    )


def _level(
    reference: EconomicIdentityId,
    value: str = "100",
    *,
    kind: StructuredContractLevelKind = StructuredContractLevelKind.LEVEL,
    unit: str = "index-points",
) -> StructuredContractLevel:
    return StructuredContractLevel(
        value=Decimal(value),
        kind=kind,
        reference_identity_id=reference,
        unit=StructuredLevelUnitCode(unit),
    )


def _discrete_dates() -> StructuredObservationTerms:
    return StructuredObservationTerms(
        mode=StructuredObservationMode.DISCRETE,
        explicit_dates=(date(2026, 6, 1), date(2026, 3, 1)),
    )


def _capital_feature(
    target: EconomicIdentityId,
    feature_id: int = 201,
) -> StructuredCapitalProtectionFeature:
    return StructuredCapitalProtectionFeature(
        feature_id=_feature_id(feature_id),
        protected_identity_id=target,
        protected_principal_ratio=StructuredPositiveRatio(Decimal("1")),
        evidence_ref=_evidence(feature_id),
    )


def _full_terms() -> StructuredHybridSyntheticTerms:
    root = _economic_id(1)
    principal = _economic_id(2)
    conversion = _economic_id(3)
    reference = _economic_id(4)
    participation = _economic_id(5)
    redemption = _economic_id(6)
    components = (
        _component(
            root,
            principal,
            relationship_id=101,
            ordinal=11,
            role="principal-component",
        ),
        _component(
            root,
            conversion,
            relationship_id=102,
            ordinal=None,
            role="conversion-component",
        ),
        _component(
            root,
            reference,
            relationship_id=103,
            ordinal=7,
            code="market-reference",
            role="reference-component",
        ),
        _component(
            root,
            participation,
            relationship_id=104,
            ordinal=None,
            role="participation-component",
        ),
        _component(
            root,
            redemption,
            relationship_id=105,
            ordinal=2,
            code="redemption-reference",
            role="redemption-component",
        ),
    )
    features = (
        _capital_feature(principal),
        StructuredConversionFeature(
            feature_id=_feature_id(202),
            target_identity_id=conversion,
            units_per_source_unit=StructuredPositiveRatio(Decimal("0.25")),
            conversion_level=_level(
                _economic_id(30),
                "125",
                kind=StructuredContractLevelKind.PRICE,
                unit="currency-per-unit",
            ),
            evidence_ref=_evidence(202),
        ),
        StructuredBarrierFeature(
            feature_id=_feature_id(203),
            reference_identity_id=reference,
            barrier_kind=StructuredBarrierKindCode("knock-in"),
            direction=StructuredBarrierDirection.AT_OR_BELOW,
            level=_level(reference, "70"),
            observation=StructuredObservationTerms(
                mode=StructuredObservationMode.CONTINUOUS
            ),
            evidence_ref=_evidence(203),
        ),
        StructuredAutocallFeature(
            feature_id=_feature_id(204),
            reference_identity_id=reference,
            trigger_level=_level(reference, "100"),
            observation=_discrete_dates(),
            redemption_ratio=StructuredPositiveRatio(Decimal("1.05")),
            evidence_ref=_evidence(204),
        ),
        StructuredParticipationFeature(
            feature_id=_feature_id(205),
            reference_identity_id=participation,
            direction=StructuredParticipationDirection.INVERSE,
            participation_ratio=StructuredPositiveRatio(Decimal("2")),
            evidence_ref=_evidence(205),
        ),
        StructuredRedemptionFeature(
            feature_id=_feature_id(206),
            redemption_identity_id=redemption,
            redemption_ratio=StructuredPositiveRatio(Decimal("1")),
            redemption_date=date(2027, 1, 15),
            evidence_ref=_evidence(206),
        ),
    )
    return StructuredHybridSyntheticTerms(
        terms_id=StructuredTermsId(UUID(int=10)),
        instrument_identity_id=root,
        components=tuple(reversed(components)),
        features=tuple(reversed(features)),
        evidence_ref=_evidence(999),
    )


def test_local_ids_are_distinct_from_economic_identity() -> None:
    assert not isinstance(StructuredTermsId(UUID(int=1)), EconomicIdentityId)
    assert not isinstance(StructuredFeatureId(UUID(int=2)), EconomicIdentityId)
    assert not isinstance(StructuredEvidenceRef(UUID(int=3)), EconomicIdentityId)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: StructuredTermsId(cast(Any, "bad")),
        lambda: StructuredFeatureId(cast(Any, "bad")),
        lambda: StructuredEvidenceRef(cast(Any, "bad")),
    ],
)
def test_local_ids_reject_wrong_uuid_runtime_type(factory: Any) -> None:
    with pytest.raises(StructuredHybridSyntheticValidationError):
        factory()


@pytest.mark.parametrize(
    "code_type",
    [
        StructuredComponentRoleCode,
        StructuredBarrierKindCode,
        StructuredObservationScheduleCode,
        StructuredLevelUnitCode,
    ],
)
@pytest.mark.parametrize(
    "value",
    ["UPPER", "has space", "a/b", "token=abc", "", "a" * 65],
)
def test_public_codes_fail_closed_on_noncanonical_material(
    code_type: type[Any],
    value: str,
) -> None:
    with pytest.raises(StructuredHybridSyntheticValidationError):
        code_type(value)


def test_structured_level_preserves_kind_reference_unit_and_zero_negative_values() -> None:
    reference = _economic_id(2)
    negative = _level(
        reference,
        "-0.0100",
        kind=StructuredContractLevelKind.RATE,
        unit="decimal-rate",
    )
    zero = _level(
        reference,
        "0.000",
        kind=StructuredContractLevelKind.SPREAD,
        unit="decimal-spread",
    )

    assert negative.logical_values()[0] == "-0.01"
    assert zero.logical_values()[0] == "0"
    assert negative.logical_values()[1:] == (
        "rate",
        reference.logical_values(),
        ("decimal-rate",),
    )
    assert not hasattr(negative, "price_quote_basis")
    assert not hasattr(negative, "convention")


@pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("Infinity")])
def test_structured_level_rejects_nonfinite_values(bad: Decimal) -> None:
    with pytest.raises(StructuredHybridSyntheticValidationError):
        _level(_economic_id(2), str(bad))


def test_structured_level_rejects_wrong_runtime_types() -> None:
    reference = _economic_id(2)
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredContractLevel(
            value=cast(Any, 100.0),
            kind=StructuredContractLevelKind.LEVEL,
            reference_identity_id=reference,
            unit=StructuredLevelUnitCode("index-points"),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredContractLevel(
            value=Decimal("100"),
            kind=cast(Any, "level"),
            reference_identity_id=reference,
            unit=StructuredLevelUnitCode("index-points"),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredContractLevel(
            value=Decimal("100"),
            kind=StructuredContractLevelKind.LEVEL,
            reference_identity_id=cast(Any, UUID(int=2)),
            unit=StructuredLevelUnitCode("index-points"),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredContractLevel(
            value=Decimal("100"),
            kind=StructuredContractLevelKind.LEVEL,
            reference_identity_id=reference,
            unit=cast(Any, "index-points"),
        )


def test_positive_ratio_canonicalizes_and_is_not_artificially_capped() -> None:
    assert StructuredPositiveRatio(Decimal("2.5000")).logical_values() == ("2.5",)
    for invalid in (Decimal("0"), Decimal("-1"), Decimal("NaN")):
        with pytest.raises(StructuredHybridSyntheticValidationError):
            StructuredPositiveRatio(invalid)


def test_continuous_observation_carries_no_discrete_material() -> None:
    assert StructuredObservationTerms(
        mode=StructuredObservationMode.CONTINUOUS
    ).logical_values() == ("continuous", (), None)

    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredObservationTerms(
            mode=StructuredObservationMode.CONTINUOUS,
            explicit_dates=(date(2026, 1, 1),),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredObservationTerms(
            mode=StructuredObservationMode.CONTINUOUS,
            schedule_code=StructuredObservationScheduleCode("issuer-schedule"),
        )


def test_discrete_observation_requires_exactly_one_typed_mode() -> None:
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredObservationTerms(mode=StructuredObservationMode.DISCRETE)
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredObservationTerms(
            mode=StructuredObservationMode.DISCRETE,
            explicit_dates=(date(2026, 1, 1),),
            schedule_code=StructuredObservationScheduleCode("issuer-schedule"),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredObservationTerms(mode=cast(Any, "discrete"))
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredObservationTerms(
            mode=StructuredObservationMode.DISCRETE,
            schedule_code=cast(Any, "issuer-schedule"),
        )


def test_discrete_observation_dates_are_exact_unique_and_canonical() -> None:
    terms = _discrete_dates()
    assert terms.explicit_dates == (date(2026, 3, 1), date(2026, 6, 1))

    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredObservationTerms(
            mode=StructuredObservationMode.DISCRETE,
            explicit_dates=(date(2026, 1, 1), date(2026, 1, 1)),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredObservationTerms(
            mode=StructuredObservationMode.DISCRETE,
            explicit_dates=(cast(Any, datetime(2026, 1, 1, tzinfo=UTC)),),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredObservationTerms(
            mode=StructuredObservationMode.DISCRETE,
            explicit_dates=cast(Any, [date(2026, 1, 1)]),
        )


def test_component_retains_exact_relationship_and_rejects_reversed_edge() -> None:
    root = _economic_id(1)
    target = _economic_id(2)
    relationship = _relationship(root, target, relationship_id=101, ordinal=17)
    component = StructuredComponentBinding(
        root_identity_id=root,
        relationship=relationship,
        role=StructuredComponentRoleCode("underlying"),
        evidence_ref=_evidence(1),
    )
    assert component.relationship is relationship
    assert component.relationship_id == relationship.relationship_id
    assert component.component_identity_id == target
    assert relationship.logical_values() in component.logical_values()

    reversed_relationship = _relationship(
        target,
        root,
        relationship_id=102,
        ordinal=None,
    )
    with pytest.raises(StructuredHybridSyntheticValidationError, match="source"):
        StructuredComponentBinding(
            root_identity_id=root,
            relationship=reversed_relationship,
            role=StructuredComponentRoleCode("underlying"),
            evidence_ref=_evidence(2),
        )


def test_component_rejects_opaque_relationship_id_and_wrong_wrappers() -> None:
    root = _economic_id(1)
    target = _economic_id(2)
    relationship = _relationship(root, target, relationship_id=101)

    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredComponentBinding(
            root_identity_id=root,
            relationship=cast(Any, relationship.relationship_id),
            role=StructuredComponentRoleCode("underlying"),
            evidence_ref=_evidence(1),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredComponentBinding(
            root_identity_id=root,
            relationship=relationship,
            role=cast(Any, "underlying"),
            evidence_ref=_evidence(1),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredComponentBinding(
            root_identity_id=root,
            relationship=relationship,
            role=StructuredComponentRoleCode("underlying"),
            evidence_ref=cast(Any, UUID(int=1)),
        )


def test_feature_records_preserve_higher_order_semantics_without_engines() -> None:
    terms = _full_terms()
    feature_names = {feature.logical_values()[0] for feature in terms.features}
    assert feature_names == {
        "capital-protection",
        "conversion",
        "barrier",
        "autocall",
        "participation",
        "redemption",
    }

    forbidden = (
        "observe",
        "evaluate",
        "calculate",
        "price",
        "trigger",
        "exercise",
        "convert",
        "execute",
        "settle",
        "route",
        "adjust_balance",
        "adjust_position",
        "wallet",
        "custody",
        "rpc",
        "sign",
    )
    for feature in terms.features:
        for method in forbidden:
            assert not hasattr(feature, method)


def test_barrier_and_autocall_level_reference_must_match_primary_reference() -> None:
    reference = _economic_id(2)
    other = _economic_id(3)
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredBarrierFeature(
            feature_id=_feature_id(1),
            reference_identity_id=reference,
            barrier_kind=StructuredBarrierKindCode("knock-out"),
            direction=StructuredBarrierDirection.AT_OR_ABOVE,
            level=_level(other),
            observation=StructuredObservationTerms(
                mode=StructuredObservationMode.CONTINUOUS
            ),
            evidence_ref=_evidence(1),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredAutocallFeature(
            feature_id=_feature_id(2),
            reference_identity_id=reference,
            trigger_level=_level(other),
            observation=_discrete_dates(),
            redemption_ratio=StructuredPositiveRatio(Decimal("1")),
            evidence_ref=_evidence(2),
        )


def test_redemption_date_rejects_datetime_laundering() -> None:
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredRedemptionFeature(
            feature_id=_feature_id(1),
            redemption_identity_id=_economic_id(2),
            redemption_ratio=StructuredPositiveRatio(Decimal("1")),
            redemption_date=cast(Any, datetime(2027, 1, 1, tzinfo=UTC)),
            evidence_ref=_evidence(1),
        )


def test_top_level_requires_nonempty_immutable_component_and_feature_tuples() -> None:
    root = _economic_id(1)
    target = _economic_id(2)
    component = _component(root, target, relationship_id=101)
    feature = _capital_feature(target)

    cases: tuple[tuple[Any, Any], ...] = (
        ((), (feature,)),
        ((component,), ()),
        ([component], (feature,)),
        ((component,), [feature]),
    )
    for components, features in cases:
        with pytest.raises(StructuredHybridSyntheticValidationError):
            StructuredHybridSyntheticTerms(
                terms_id=StructuredTermsId(UUID(int=1)),
                instrument_identity_id=root,
                components=cast(Any, components),
                features=cast(Any, features),
                evidence_ref=_evidence(9),
            )


def test_top_level_rejects_root_mismatch_and_duplicate_relationship_id() -> None:
    root = _economic_id(1)
    other_root = _economic_id(7)
    target = _economic_id(2)
    feature = _capital_feature(target)
    wrong_root = _component(other_root, target, relationship_id=101)
    with pytest.raises(StructuredHybridSyntheticValidationError, match="component root"):
        StructuredHybridSyntheticTerms(
            terms_id=StructuredTermsId(UUID(int=1)),
            instrument_identity_id=root,
            components=(wrong_root,),
            features=(feature,),
            evidence_ref=_evidence(9),
        )

    first = _component(root, target, relationship_id=102)
    duplicate = StructuredComponentBinding(
        root_identity_id=root,
        relationship=IdentityRelationship(
            relationship_id=first.relationship.relationship_id,
            source_identity_id=root,
            target_identity_id=_economic_id(3),
            relationship=IdentityRelationshipCode("other-component"),
            effective_from=datetime(2027, 1, 1, tzinfo=UTC),
            effective_until=None,
            evidence_ref=IdentityEvidenceRef(UUID(int=5000)),
            ordinal=88,
        ),
        role=StructuredComponentRoleCode("other"),
        evidence_ref=_evidence(8),
    )
    with pytest.raises(StructuredHybridSyntheticValidationError, match="ids must be unique"):
        StructuredHybridSyntheticTerms(
            terms_id=StructuredTermsId(UUID(int=1)),
            instrument_identity_id=root,
            components=(first, duplicate),
            features=(feature,),
            evidence_ref=_evidence(9),
        )


def test_umi09_does_not_claim_umi02_ordinal_authority() -> None:
    root = _economic_id(1)
    first_target = _economic_id(2)
    second_target = _economic_id(3)
    third_target = _economic_id(4)
    first = _component(
        root,
        first_target,
        relationship_id=101,
        ordinal=50,
        code="component.a",
    )
    second = _component(
        root,
        second_target,
        relationship_id=102,
        ordinal=None,
        code="component.b",
    )
    third = _component(
        root,
        third_target,
        relationship_id=103,
        ordinal=2,
        code="component.c",
    )
    terms = StructuredHybridSyntheticTerms(
        terms_id=StructuredTermsId(UUID(int=1)),
        instrument_identity_id=root,
        components=(third, second, first),
        features=(_capital_feature(first_target),),
        evidence_ref=_evidence(9),
    )

    assert terms.components == (first, second, third)
    assert tuple(component.relationship.ordinal for component in terms.components) == (
        50,
        None,
        2,
    )


def test_duplicate_ordinals_in_distinct_umi02_scopes_are_not_reinterpreted() -> None:
    root = _economic_id(1)
    first_target = _economic_id(2)
    second_target = _economic_id(3)
    first = _component(
        root,
        first_target,
        relationship_id=101,
        ordinal=1,
        code="component.a",
    )
    second = _component(
        root,
        second_target,
        relationship_id=102,
        ordinal=1,
        code="component.b",
    )
    terms = StructuredHybridSyntheticTerms(
        terms_id=StructuredTermsId(UUID(int=1)),
        instrument_identity_id=root,
        components=(second, first),
        features=(_capital_feature(first_target),),
        evidence_ref=_evidence(9),
    )

    assert terms.components == (first, second)
    assert first.relationship.ordinal == second.relationship.ordinal == 1


def test_component_order_is_relationship_id_canonical_not_caller_or_ordinal_order() -> None:
    root = _economic_id(1)
    first_target = _economic_id(2)
    second_target = _economic_id(3)
    first = _component(root, first_target, relationship_id=101, ordinal=99)
    second = _component(root, second_target, relationship_id=102, ordinal=1)
    terms = StructuredHybridSyntheticTerms(
        terms_id=StructuredTermsId(UUID(int=1)),
        instrument_identity_id=root,
        components=(second, first),
        features=(_capital_feature(first_target),),
        evidence_ref=_evidence(9),
    )
    assert terms.components == (first, second)


def test_distinct_relationship_revisions_are_retained_not_silently_deduped() -> None:
    root = _economic_id(1)
    target = _economic_id(2)
    first = _component(
        root,
        target,
        relationship_id=101,
        ordinal=1,
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
    )
    second = _component(
        root,
        target,
        relationship_id=102,
        ordinal=1,
        effective_from=datetime(2027, 1, 1, tzinfo=UTC),
    )
    terms = StructuredHybridSyntheticTerms(
        terms_id=StructuredTermsId(UUID(int=1)),
        instrument_identity_id=root,
        components=(second, first),
        features=(_capital_feature(target),),
        evidence_ref=_evidence(9),
    )
    assert len(terms.components) == 2
    assert tuple(component.relationship_id for component in terms.components) == (
        first.relationship_id,
        second.relationship_id,
    )


def test_primary_feature_identity_must_be_direct_component_target() -> None:
    root = _economic_id(1)
    component_target = _economic_id(2)
    unbound_target = _economic_id(3)
    component = _component(root, component_target, relationship_id=101)
    feature = StructuredConversionFeature(
        feature_id=_feature_id(1),
        target_identity_id=unbound_target,
        units_per_source_unit=StructuredPositiveRatio(Decimal("1")),
        evidence_ref=_evidence(1),
    )
    with pytest.raises(StructuredHybridSyntheticValidationError, match="direct component"):
        StructuredHybridSyntheticTerms(
            terms_id=StructuredTermsId(UUID(int=1)),
            instrument_identity_id=root,
            components=(component,),
            features=(feature,),
            evidence_ref=_evidence(9),
        )


def _derivative_composition(root: EconomicIdentityId) -> DerivativeCompositionTerms:
    return DerivativeCompositionTerms(
        terms_id=DerivativeTermsId(UUID(int=1)),
        instrument_identity_id=root,
        legs=(
            DerivativeCompositionLeg(
                leg_id=DerivativeLegId(UUID(int=11)),
                ordinal=DerivativeLegOrdinal(1),
                component_identity_id=_economic_id(10),
                side=DerivativeCompositionSide.LONG,
                ratio=Decimal("1"),
                evidence_ref=DerivativeEvidenceRef(UUID(int=21)),
            ),
            DerivativeCompositionLeg(
                leg_id=DerivativeLegId(UUID(int=12)),
                ordinal=DerivativeLegOrdinal(2),
                component_identity_id=_economic_id(11),
                side=DerivativeCompositionSide.SHORT,
                ratio=Decimal("1"),
                evidence_ref=DerivativeEvidenceRef(UUID(int=22)),
            ),
        ),
        evidence_ref=DerivativeEvidenceRef(UUID(int=23)),
    )


def test_umi05_derivative_composition_cannot_be_laundered_as_umi09_feature() -> None:
    root = _economic_id(1)
    target = _economic_id(2)
    component = _component(root, target, relationship_id=101)
    with pytest.raises(StructuredHybridSyntheticValidationError, match="feature types"):
        StructuredHybridSyntheticTerms(
            terms_id=StructuredTermsId(UUID(int=1)),
            instrument_identity_id=root,
            components=(component,),
            features=cast(Any, (_derivative_composition(root),)),
            evidence_ref=_evidence(9),
        )


def test_duplicate_feature_ids_fail_closed() -> None:
    root = _economic_id(1)
    target = _economic_id(2)
    component = _component(root, target, relationship_id=101)
    feature_id = _feature_id(1)
    first = StructuredCapitalProtectionFeature(
        feature_id=feature_id,
        protected_identity_id=target,
        protected_principal_ratio=StructuredPositiveRatio(Decimal("1")),
        evidence_ref=_evidence(1),
    )
    second = StructuredParticipationFeature(
        feature_id=feature_id,
        reference_identity_id=target,
        direction=StructuredParticipationDirection.POSITIVE,
        participation_ratio=StructuredPositiveRatio(Decimal("1")),
        evidence_ref=_evidence(2),
    )
    with pytest.raises(StructuredHybridSyntheticValidationError, match="feature ids"):
        StructuredHybridSyntheticTerms(
            terms_id=StructuredTermsId(UUID(int=1)),
            instrument_identity_id=root,
            components=(component,),
            features=(first, second),
            evidence_ref=_evidence(9),
        )


def test_caller_order_and_decimal_format_do_not_change_deterministic_material() -> None:
    first = _full_terms()
    second = StructuredHybridSyntheticTerms(
        terms_id=first.terms_id,
        instrument_identity_id=first.instrument_identity_id,
        components=tuple(reversed(first.components)),
        features=tuple(reversed(first.features)),
        evidence_ref=first.evidence_ref,
    )
    assert first.logical_values() == second.logical_values()
    assert StructuredPositiveRatio(Decimal("1.00")).logical_values() == (
        StructuredPositiveRatio(Decimal("1")).logical_values()
    )


def test_full_terms_are_frozen_deterministic_and_have_no_runtime_authority() -> None:
    terms = _full_terms()
    assert terms.logical_values() == terms.logical_values()
    attribute = "evidence_ref"
    with pytest.raises(FrozenInstanceError):
        setattr(terms, attribute, _evidence(1000))

    forbidden = (
        "current_price",
        "mark_price",
        "funding_rate",
        "market_data",
        "observe",
        "evaluate",
        "calculate",
        "price",
        "exercise",
        "convert",
        "execute",
        "route",
        "settle",
        "adjust_balance",
        "adjust_position",
        "provider",
        "wallet",
        "custody",
        "rpc",
        "sign",
        "current_revision",
        "lifecycle_event",
        "triggered",
        "exercised",
        "settled",
    )
    for name in forbidden:
        assert not hasattr(terms, name)
