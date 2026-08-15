from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.structured_hybrid_synthetic_semantics import (
    StructuredCapitalProtectionFeature,
    StructuredComponentBinding,
    StructuredComponentRoleCode,
    StructuredEvidenceRef,
    StructuredFeatureId,
    StructuredHybridSyntheticTerms,
    StructuredHybridSyntheticValidationError,
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


def _component(
    root: EconomicIdentityId,
    target: EconomicIdentityId,
    *,
    relationship_id: int,
) -> StructuredComponentBinding:
    return StructuredComponentBinding(
        root_identity_id=root,
        relationship=IdentityRelationship(
            relationship_id=IdentityRelationshipId(UUID(int=relationship_id)),
            source_identity_id=root,
            target_identity_id=target,
            relationship=IdentityRelationshipCode("structured-component"),
            effective_from=datetime(2026, 1, 1, tzinfo=UTC),
            effective_until=None,
            evidence_ref=IdentityEvidenceRef(UUID(int=relationship_id + 100)),
            ordinal=None,
        ),
        role=StructuredComponentRoleCode("principal"),
        evidence_ref=StructuredEvidenceRef(UUID(int=relationship_id + 200)),
    )


def _feature(target: EconomicIdentityId) -> StructuredCapitalProtectionFeature:
    return StructuredCapitalProtectionFeature(
        feature_id=StructuredFeatureId(UUID(int=50)),
        protected_identity_id=target,
        protected_principal_ratio=StructuredPositiveRatio(Decimal("1")),
        evidence_ref=StructuredEvidenceRef(UUID(int=51)),
    )


def test_top_level_wrong_terms_id_and_evidence_fail_closed() -> None:
    root = _identity(1)
    target = _identity(2)
    component = _component(root, target, relationship_id=10)
    feature = _feature(target)

    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredHybridSyntheticTerms(
            terms_id=cast(Any, UUID(int=30)),
            instrument_identity_id=root,
            components=(component,),
            features=(feature,),
            evidence_ref=StructuredEvidenceRef(UUID(int=31)),
        )
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredHybridSyntheticTerms(
            terms_id=StructuredTermsId(UUID(int=30)),
            instrument_identity_id=root,
            components=(component,),
            features=(feature,),
            evidence_ref=cast(Any, UUID(int=31)),
        )


def test_top_level_wrong_component_member_fails_closed() -> None:
    root = _identity(1)
    with pytest.raises(StructuredHybridSyntheticValidationError):
        StructuredHybridSyntheticTerms(
            terms_id=StructuredTermsId(UUID(int=30)),
            instrument_identity_id=root,
            components=cast(Any, ("not-a-component",)),
            features=cast(Any, (_feature(_identity(2)),)),
            evidence_ref=StructuredEvidenceRef(UUID(int=31)),
        )
