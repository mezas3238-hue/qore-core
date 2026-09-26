from __future__ import annotations

import pytest

from qore.infrastructure.core_stack_v2.knowledge_governance import (
    KnowledgeEvidence,
    KnowledgeItem,
    KnowledgeTier,
    promote_knowledge,
)


def _evidence() -> KnowledgeEvidence:
    return KnowledgeEvidence(
        causal_validation=True,
        temporal_stability=True,
        market_stability=True,
        holdout_pass=True,
        stress_pass=True,
        replication_pass=True,
        leakage_free=True,
    )


def test_research_knowledge_cannot_skip_validation() -> None:
    item = KnowledgeItem(
        knowledge_id="latent-reversal-mechanism",
        version=1,
        tier=KnowledgeTier.RESEARCH,
        parent_version=None,
        evidence=_evidence(),
        owner_certification_approved=True,
    )

    with pytest.raises(ValueError):
        promote_knowledge(item, target=KnowledgeTier.CERTIFIED)


def test_certification_requires_owner_governed_gate() -> None:
    item = KnowledgeItem(
        knowledge_id="latent-reversal-mechanism",
        version=2,
        tier=KnowledgeTier.VALIDATED,
        parent_version=1,
        evidence=_evidence(),
        owner_certification_approved=False,
    )

    with pytest.raises(ValueError):
        promote_knowledge(item, target=KnowledgeTier.CERTIFIED)


def test_validated_knowledge_can_be_certified_after_all_gates() -> None:
    item = KnowledgeItem(
        knowledge_id="latent-reversal-mechanism",
        version=2,
        tier=KnowledgeTier.VALIDATED,
        parent_version=1,
        evidence=_evidence(),
        owner_certification_approved=True,
    )

    certified = promote_knowledge(item, target=KnowledgeTier.CERTIFIED)

    assert certified.tier is KnowledgeTier.CERTIFIED
