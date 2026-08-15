from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from qore.infrastructure.structured_hybrid_synthetic_semantics import (
    StructuredComponentBinding,
    StructuredComponentRoleCode,
    StructuredContractLevel,
    StructuredContractLevelKind,
    StructuredConversionFeature,
    StructuredEvidenceRef,
    StructuredFeatureId,
    StructuredHybridSyntheticTerms,
    StructuredLevelUnitCode,
    StructuredPositiveRatio,
    StructuredTermsId,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentityId,
    IdentityEvidenceRef,
    IdentityRelationship,
    IdentityRelationshipCode,
    IdentityRelationshipId,
)


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(UUID(int=value))


def test_conversion_level_reference_context_does_not_create_fake_component() -> None:
    root = _identity(1)
    conversion_target = _identity(2)
    quotation_reference = _identity(3)
    relationship = IdentityRelationship(
        relationship_id=IdentityRelationshipId(UUID(int=10)),
        source_identity_id=root,
        target_identity_id=conversion_target,
        relationship=IdentityRelationshipCode("conversion-component"),
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_until=None,
        evidence_ref=IdentityEvidenceRef(UUID(int=11)),
        ordinal=1,
    )
    component = StructuredComponentBinding(
        root_identity_id=root,
        relationship=relationship,
        role=StructuredComponentRoleCode("conversion-target"),
        evidence_ref=StructuredEvidenceRef(UUID(int=12)),
    )
    feature = StructuredConversionFeature(
        feature_id=StructuredFeatureId(UUID(int=20)),
        target_identity_id=conversion_target,
        units_per_source_unit=StructuredPositiveRatio(Decimal("0.5")),
        conversion_level=StructuredContractLevel(
            value=Decimal("100"),
            kind=StructuredContractLevelKind.PRICE,
            reference_identity_id=quotation_reference,
            unit=StructuredLevelUnitCode("currency-per-unit"),
        ),
        evidence_ref=StructuredEvidenceRef(UUID(int=21)),
    )

    terms = StructuredHybridSyntheticTerms(
        terms_id=StructuredTermsId(UUID(int=30)),
        instrument_identity_id=root,
        components=(component,),
        features=(feature,),
        evidence_ref=StructuredEvidenceRef(UUID(int=31)),
    )

    assert terms.components[0].component_identity_id == conversion_target
    assert quotation_reference not in {
        item.component_identity_id for item in terms.components
    }
    assert feature.conversion_level is not None
    assert feature.conversion_level.reference_identity_id == quotation_reference
