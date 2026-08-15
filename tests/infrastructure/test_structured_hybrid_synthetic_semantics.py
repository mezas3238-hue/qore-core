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
    ordinal: int | None,
    code: str = "structured-component",
) -> IdentityRelationship:
    return IdentityRelationship(
        relationship_id=IdentityRelationshipId(UUID(int=relationship_id)),
        source_identity_id=root,
        target_identity_id=target,
        relationship=IdentityRelationshipCode(code),
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_until=None,
        evidence_ref=IdentityEvidenceRef(UUID(int=relationship_id + 1000)),
        ordinal=ordinal,
    )


def _component(
    root: EconomicIdentityId,
    target: EconomicIdentityId,
    *,
    relationship_id: int,
    ordinal: int | None,
    role: str,
) -> StructuredComponentBinding:
    return StructuredComponentBinding(
        root_identity_id=root,
        relationship=_relationship(
            root,
            target,
            relationship_id=relationship_id,
            ordinal=ordinal,
        ),
        role=StructuredComponentRoleCode(role),
        evidence_ref=_evidence(relationship_id + 2000),
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
            ordinal=1,
            role="principal-component",
        ),
        _component(
            root,
            conversion,
            relationship_id=102,
            ordinal=2,
            role="conversion-component",
        ),
        _component(
            root,
            reference,
            relationship_id=103,
            ordinal=3,
            role="reference-component",
        ),
        _component(
            root,
            participation,
            relationship_id=104,
            ordinal=4,
            role="participation-component",
        ),
        _component(
            root,
            redemption,
            relationship_id=105,
            ordinal=5,
            role="redemption-component",
        ),
    )
    observation = _discrete_dates()
    features = (
        StructuredCapitalProtectionFeature(
            feature_id=_feature_id(201),
            protected_identity_id=principal,
            protected_principal_ratio=StructuredPositiveRatio(Decimal("1.00")),
            evidence_ref=_evidence(201),
        ),
        StructuredConversionFeature(
            feature_id=_feature_id(202),
            target_identity_id=conversion,
            units_per_source_unit=StructuredPositiveRatio(Decimal("0.25")),
            conversion_level=_level(
                conversion,
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
            observation=observation,
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
        components=components,
        features=features,
        evidence_ref=_evidence(999),
    )


def test_local_ids_are_not_economic_identity() -> None:
    terms_id = StructuredTermsId(UUID(int=1))
    feature_id = StructuredFeatureId(UUID(int=2))
    evidence = StructuredEvidenceRef(UUID(int=3))

    assert not isinstance(terms_id, EconomicIdentityId)
    assert not isinstance(feature_id, EconomicIdentityId)
    assert not isinstance(evidence, EconomicIdentityId)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: StructuredTermsId(cast(Any, "bad")),
        lambda: StructuredFeatureId(cast(Any, "bad")),
        lambda: StructuredEvidenceRef(cast(Any, "bad")),
    ],
)
def test_local_ids_fail_closed_on_wrong_uuid_type(factory: Any) -> None:
    with pytest.raises(StructuredHybridSyntheticValidationError):
        factory()


@pytest.mark.parametrize(
    "value",
    ["UPPER", "has space", "a/b", "token=abc", "", "a" * 65],
)
def test_canonical_codes_reject_noncanonical_or_secret_like_text(value: str) -> None:
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredComponentRoleCode(value)
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredBarrierKindCode(value)
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredObservationScheduleCode(value)
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredLevelUnitCode(value)


def test_component_retain_exact_umi02_relationship_material() -> None:
    root = _economic_id(1)
    target = _economic_id(2)
    relationship = _relationship(root, target, relationship_id=101, ordinal=1)
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


def test_component_rejects_reversed_direct_edge() -> None:
    root = _economic_id(1)
    target = _economic_id(2)
    reversed_relationship = _relationship(
        target,
        root,
        relationship_id=101,
        ordinal=1,
    )

    with pytest.raises(
        StructuredHybridSyntheticValidationError,
        match="source must equal root",
    ):
        StructuredComponentBinding(
            root_identity_id=root,
            relationship=reversed_relationship,
            role=StructuredComponentRoleCode("underlying"),
            evidence_ref=_evidence(1),
        )


def test_component_rejects_opaque_relationship_id_instead_of_relationship() -> None:
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredComponentBinding(
            root_identity_id=_economic_id(1),
            relationship=cast(Any, IdentityRelationshipId(UUID(int=1))),
            role=StructuredComponentRoleCode("underlying"),
            evidence_ref=_evidence(1),
        )


def test_contract_level_is_not_option_strike_and_has_explicit_unit() -> None:
    reference = _economic_id(2)
    level = _level(
        reference,
        "-0.01",
        kind=StructuredContractLevelKind.RATE,
        unit="decimal-rate",
    )

    assert level.logical_values() == (
        "-0.01",
        "rate",
        reference.logical_values(),
        ("decimal-rate",),
    )
    assert not hasattr(level, "price_quote_basis")
    assert not hasattr(level, "convention")


def test_contract_level_rejects_nonfinite_decimal_and_wrong_types() -> None:
    with pytest.raises(StructuredHybridSyntheticValidationError):
        _level(_economic_id(2), "NaN")
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredContractLevel(
            value=cast(Any, 100.0),
            kind=StructuredContractLevelKind.LEVEL,
            reference_identity_id=_economic_id(2),
            unit=StructuredLevelUnitCode("index-points"),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredContractLevel(
            value=Decimal("100"),
            kind=cast(Any, "level"),
            reference_identity_id=_economic_id(2),
            unit=StructuredLevelUnitCode("index-points"),
        )


def test_positive_ratio_is_canonical_and_not_capped_at_one() -> None:
    ratio = StructuredPositiveRatio(Decimal("1.1000"))
    assert ratio.logical_values() == ("1.1",)

    for invalid in (Decimal("0"), Decimal("-1"), Decimal("NaN")):
        with pytest.raises(StructuredHybridSyntheticValidationError):
            StructuredPositiveRatio(invalid)


def test_continuous_observation_rejects_date_or_schedule_material() -> None:
    StructuredObservationTerms(mode=StructuredObservationMode.CONTINUOUS)

    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredObservationTerms(
            mode=StructuredObservationMode.CONTINUOUS,
            explicit_dates=(date(2026, 1, 1),),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredObservationTerms(
            mode=StructuredObservationMode.CONTINUOUS,
            schedule_code=StructuredObservationScheduleCode("venue-schedule"),
        )


def test_discrete_observation_requires_exactly_one_mode() -> None:
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredObservationTerms(mode=StructuredObservationMode.DISCRETE)

    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredObservationTerms(
            mode=StructuredObservationMode.DISCRETE,
            explicit_dates=(date(2026, 1, 1),),
            schedule_code=StructuredObservationScheduleCode("venue-schedule"),
        )

    by_schedule = StructuredObservationTerms(
        mode=StructuredObservationMode.DISCRETE,
        schedule_code=StructuredObservationScheduleCode("venue-schedule"),
    )
    assert by_schedule.logical_values() == (
        "discrete",
        (),
        ("venue-schedule",),
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


def test_barrier_and_autocall_level_reference_must_match_feature_reference() -> None:
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


def test_feature_records_are_declarative_and_have_no_engine_methods() -> None:
    terms = _full_terms()
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


def test_redemption_date_rejects_datetime_laundering() -> None:
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredRedemptionFeature(
            feature_id=_feature_id(1),
            redemption_identity_id=_economic_id(2),
            redemption_ratio=StructuredPositiveRatio(Decimal("1")),
            redemption_date=cast(Any, datetime(2027, 1, 1, tzinfo=UTC)),
            evidence_ref=_evidence(1),
        )


def test_top_level_requires_nonempty_immutable_components_and_features() -> None:
    root = _economic_id(1)
    component = _component(
        root,
        _economic_id(2),
        relationship_id=101,
        ordinal=1,
        role="principal",
    )
    feature = StructuredCapitalProtectionFeature(
        feature_id=_feature_id(1),
        protected_identity_id=_economic_id(2),
        protected_principal_ratio=StructuredPositiveRatio(Decimal("1")),
        evidence_ref=_evidence(1),
    )

    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredHybridSyntheticTerms(
            terms_id=StructuredTermsId(UUID(int=1)),
            instrument_identity_id=root,
            components=(),
            features=(feature,),
            evidence_ref=_evidence(9),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredHybridSyntheticTerms(
            terms_id=StructuredTermsId(UUID(int=1)),
            instrument_identity_id=root,
            components=(component,),
            features=(),
            evidence_ref=_evidence(9),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredHybridSyntheticTerms(
            terms_id=StructuredTermsId(UUID(int=1)),
            instrument_identity_id=root,
            components=cast(Any, [component]),
            features=(feature,),
            evidence_ref=_evidence(9),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredHybridSyntheticTerms(
            terms_id=StructuredTermsId(UUID(int=1)),
            instrument_identity_id=root,
            components=(component,),
            features=cast(Any, [feature]),
            evidence_ref=_evidence(9),
        )


def test_top_level_rejects_component_root_mismatch() -> None:
    root = _economic_id(1)
    other_root = _economic_id(7)
    target = _economic_id(2)
    component = _component(
        other_root,
        target,
        relationship_id=101,
        ordinal=1,
        role="principal",
    )
    feature = StructuredCapitalProtectionFeature(
        feature_id=_feature_id(1),
        protected_identity_id=target,
        protected_principal_ratio=StructuredPositiveRatio(Decimal("1")),
        evidence_ref=_evidence(1),
    )

    with pytest.raises(StructuredHybridSyntheticValidationError, match="component root"):
        StructuredHybridSyntheticTerms(
            terms_id=StructuredTermsId(UUID(int=1)),
            instrument_identity_id=root,
            components=(component,),
            features=(feature,),
            evidence_ref=_evidence(9),
        )


def test_top_level_rejects_duplicate_relationship_id() -> None:
    root = _economic_id(1)
    first_target = _economic_id(2)
    second_target = _economic_id(3)
    first = _component(
        root,
        first_target,
        relationship_id=101,
        ordinal=1,
        role="principal",
    )
    second = StructuredComponentBinding(
        root_identity_id=root,
        relationship=IdentityRelationship(
            relationship_id=first.relationship.relationship_id,
            source_identity_id=root,
            target_identity_id=second_target,
            relationship=IdentityRelationshipCode("structured-component"),
            effective_from=datetime(2026, 1, 1, tzinfo=UTC),
            effective_until=None,
            evidence_ref=IdentityEvidenceRef(UUID(int=5000)),
            ordinal=2,
        ),
        role=StructuredComponentRoleCode("reference"),
        evidence_ref=_evidence(2),
    )
    feature = StructuredCapitalProtectionFeature(
        feature_id=_feature_id(1),
        protected_identity_id=first_target,
        protected_principal_ratio=StructuredPositiveRatio(Decimal("1")),
        evidence_ref=_evidence(1),
    )

    with pytest.raises(StructuredHybridSyntheticValidationError, match="ids must be unique"):
        StructuredHybridSyntheticTerms(
            terms_id=StructuredTermsId(UUID(int=1)),
            instrument_identity_id=root,
            components=(first, second),
            features=(feature,),
            evidence_ref=_evidence(9),
        )


def test_same_target_role_distinct_relationship_revisions_are_not_silently_deduped() -> None:
    root = _economic_id(1)
    target = _economic_id(2)
    first = _component(
        root,
        target,
        relationship_id=101,
        ordinal=1,
        role="principal",
    )
    second = StructuredComponentBinding(
        root_identity_id=root,
        relationship=IdentityRelationship(
            relationship_id=IdentityRelationshipId(UUID(int=102)),
            source_identity_id=root,
            target_identity_id=target,
            relationship=IdentityRelationshipCode("structured-component"),
            effective_from=datetime(2027, 1, 1, tzinfo=UTC),
            effective_until=None,
            evidence_ref=IdentityEvidenceRef(UUID(int=5102)),
            ordinal=2,
        ),
        role=StructuredComponentRoleCode("principal"),
        evidence_ref=_evidence(2),
    )
    feature = StructuredCapitalProtectionFeature(
        feature_id=_feature_id(1),
        protected_identity_id=target,
        protected_principal_ratio=StructuredPositiveRatio(Decimal("1")),
        evidence_ref=_evidence(1),
    )

    terms = StructuredHybridSyntheticTerms(
        terms_id=StructuredTermsId(UUID(int=1)),
        instrument_identity_id=root,
        components=(second, first),
        features=(feature,),
        evidence_ref=_evidence(9),
    )

    assert len(terms.components) == 2
    assert tuple(item.relationship.ordinal for item in terms.components) == (1, 2)


def test_component_ordinals_must_be_all_or_none_and_contiguous() -> None:
    root = _economic_id(1)
    target_one = _economic_id(2)
    target_two = _economic_id(3)
    feature = StructuredCapitalProtectionFeature(
        feature_id=_feature_id(1),
        protected_identity_id=target_one,
        protected_principal_ratio=StructuredPositiveRatio(Decimal("1")),
        evidence_ref=_evidence(1),
    )

    mixed = (
        _component(
            root,
            target_one,
            relationship_id=101,
            ordinal=1,
            role="principal",
        ),
        _component(
            root,
            target_two,
            relationship_id=102,
            ordinal=None,
            role="reference",
        ),
    )
    with pytest.raises(StructuredHybridSyntheticValidationError, match="all carry ordinals"):
        StructuredHybridSyntheticTerms(
            terms_id=StructuredTermsId(UUID(int=1)),
            instrument_identity_id=root,
            components=mixed,
            features=(feature,),
            evidence_ref=_evidence(9),
        )

    noncontiguous = (
        _component(
            root,
            target_one,
            relationship_id=101,
            ordinal=1,
            role="principal",
        ),
        _component(
            root,
            target_two,
            relationship_id=102,
            ordinal=3,
            role="reference",
        ),
    )
    with pytest.raises(StructuredHybridSyntheticValidationError, match="contiguous"):
        StructuredHybridSyntheticTerms(
            terms_id=StructuredTermsId(UUID(int=1)),
            instrument_identity_id=root,
            components=noncontiguous,
            features=(feature,),
            evidence_ref=_evidence(9),
        )


def test_component_order_canonicalizes_by_ordinal_when_present() -> None:
    root = _economic_id(1)
    target_one = _economic_id(2)
    target_two = _economic_id(3)
    first = _component(
        root,
        target_one,
        relationship_id=101,
        ordinal=1,
        role="principal",
    )
    second = _component(
        root,
        target_two,
        relationship_id=102,
        ordinal=2,
        role="reference",
    )
    feature = StructuredCapitalProtectionFeature(
        feature_id=_feature_id(1),
        protected_identity_id=target_one,
        protected_principal_ratio=StructuredPositiveRatio(Decimal("1")),
        evidence_ref=_evidence(1),
    )

    terms = StructuredHybridSyntheticTerms(
        terms_id=StructuredTermsId(UUID(int=1)),
        instrument_identity_id=root,
        components=(second, first),
        features=(feature,),
        evidence_ref=_evidence(9),
    )

    assert terms.components == (first, second)


def test_component_order_canonicalizes_by_relationship_id_without_ordinals() -> None:
    root = _economic_id(1)
    target_one = _economic_id(2)
    target_two = _economic_id(3)
    first = _component(
        root,
        target_one,
        relationship_id=101,
        ordinal=None,
        role="principal",
    )
    second = _component(
        root,
        target_two,
        relationship_id=102,
        ordinal=None,
        role="reference",
    )
    feature = StructuredCapitalProtectionFeature(
        feature_id=_feature_id(1),
        protected_identity_id=target_one,
        protected_principal_ratio=StructuredPositiveRatio(Decimal("1")),
        evidence_ref=_evidence(1),
    )

    terms = StructuredHybridSyntheticTerms(
        terms_id=StructuredTermsId(UUID(int=1)),
        instrument_identity_id=root,
        components=(second, first),
        features=(feature,),
        evidence_ref=_evidence(9),
    )

    assert terms.components == (first, second)


def test_every_feature_reference_must_be_a_direct_component_target() -> None:
    root = _economic_id(1)
    component_target = _economic_id(2)
    unbound_target = _economic_id(3)
    component = _component(
        root,
        component_target,
        relationship_id=101,
        ordinal=1,
        role="principal",
    )
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
    first = _economic_id(10)
    second = _economic_id(11)
    return DerivativeCompositionTerms(
        terms_id=DerivativeTermsId(UUID(int=1)),
        instrument_identity_id=root,
        legs=(
            DerivativeCompositionLeg(
                leg_id=DerivativeLegId(UUID(int=11)),
                ordinal=DerivativeLegOrdinal(1),
                component_identity_id=first,
                side=DerivativeCompositionSide.LONG,
                ratio=Decimal("1"),
                evidence_ref=DerivativeEvidenceRef(UUID(int=21)),
            ),
            DerivativeCompositionLeg(
                leg_id=DerivativeLegId(UUID(int=12)),
                ordinal=DerivativeLegOrdinal(2),
                component_identity_id=second,
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
    component = _component(
        root,
        target,
        relationship_id=101,
        ordinal=1,
        role="reference",
    )

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
    component = _component(
        root,
        target,
        relationship_id=101,
        ordinal=1,
        role="principal",
    )
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


def test_component_and_feature_caller_order_do_not_change_logical_values() -> None:
    first = _full_terms()
    second = StructuredHybridSyntheticTerms(
        terms_id=first.terms_id,
        instrument_identity_id=first.instrument_identity_id,
        components=tuple(reversed(first.components)),
        features=tuple(reversed(first.features)),
        evidence_ref=first.evidence_ref,
    )

    assert first.components == second.components
    assert first.features == second.features
    assert first.logical_values() == second.logical_values()


def test_logical_values_canonicalize_equal_decimals() -> None:
    reference = _economic_id(2)
    first = StructuredPositiveRatio(Decimal("1.00"))
    second = StructuredPositiveRatio(Decimal("1"))
    first_level = _level(reference, "100.000")
    second_level = _level(reference, "100")

    assert first.logical_values() == second.logical_values()
    assert first_level.logical_values() == second_level.logical_values()


def test_full_terms_are_frozen_and_deterministic() -> None:
    terms = _full_terms()
    assert terms.logical_values() == terms.logical_values()

    attribute = "evidence_ref"
    with pytest.raises(FrozenInstanceError):
        setattr(terms, attribute, _evidence(1000))


def test_full_terms_do_not_expose_observation_valuation_or_execution_authority() -> None:
    terms = _full_terms()
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
    )

    for name in forbidden:
        assert not hasattr(terms, name)


def test_full_terms_preserve_all_feature_families_without_flattening() -> None:
    terms = _full_terms()
    feature_names = tuple(feature.logical_values()[0] for feature in terms.features)

    assert feature_names == (
        "capital-protection",
        "conversion",
        "barrier",
        "autocall",
        "participation",
        "redemption",
    )


def test_structured_semantics_have_no_fake_current_revision_or_lifecycle_claim() -> None:
    terms = _full_terms()

    assert not hasattr(terms, "current_revision")
    assert not hasattr(terms, "as_of_relationship")
    assert not hasattr(terms, "lifecycle_event")
    assert not hasattr(terms, "triggered")
    assert not hasattr(terms, "exercised")
    assert not hasattr(terms, "settled")
