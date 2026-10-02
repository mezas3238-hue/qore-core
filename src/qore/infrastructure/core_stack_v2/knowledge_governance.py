"""Governed continual-learning knowledge registry for Shared Core.

New ideas never overwrite certified knowledge directly. Shared keeps research,
validated and certified knowledge separate, with lineage and explicit evidence
gates. Certification requires an external owner-governed approval signal.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class KnowledgeTier(StrEnum):
    RESEARCH = "RESEARCH_KNOWLEDGE"
    VALIDATED = "VALIDATED_KNOWLEDGE"
    CERTIFIED = "CERTIFIED_KNOWLEDGE"


@dataclass(frozen=True, slots=True)
class KnowledgeEvidence:
    causal_validation: bool
    temporal_stability: bool
    market_stability: bool
    holdout_pass: bool
    stress_pass: bool
    replication_pass: bool
    leakage_free: bool


@dataclass(frozen=True, slots=True)
class KnowledgeItem:
    knowledge_id: str
    version: int
    tier: KnowledgeTier
    parent_version: int | None
    evidence: KnowledgeEvidence
    owner_certification_approved: bool = False

    def __post_init__(self) -> None:
        if not self.knowledge_id:
            raise ValueError("knowledge_id must be non-empty")
        if self.version < 1:
            raise ValueError("knowledge version must be positive")
        if self.parent_version is not None and self.parent_version >= self.version:
            raise ValueError("parent version must precede current version")


def can_promote_to_validated(item: KnowledgeItem) -> bool:
    evidence = item.evidence
    return (
        item.tier is KnowledgeTier.RESEARCH
        and evidence.causal_validation
        and evidence.temporal_stability
        and evidence.market_stability
        and evidence.leakage_free
    )


def can_promote_to_certified(item: KnowledgeItem) -> bool:
    evidence = item.evidence
    return (
        item.tier is KnowledgeTier.VALIDATED
        and evidence.holdout_pass
        and evidence.stress_pass
        and evidence.replication_pass
        and evidence.leakage_free
        and item.owner_certification_approved
    )


def promote_knowledge(
    item: KnowledgeItem,
    *,
    target: KnowledgeTier,
) -> KnowledgeItem:
    """Promote knowledge one governed tier at a time."""

    if target is item.tier:
        return item
    if target is KnowledgeTier.CERTIFIED and item.tier is KnowledgeTier.RESEARCH:
        raise ValueError("research knowledge cannot skip validation")
    if target is KnowledgeTier.VALIDATED:
        if not can_promote_to_validated(item):
            raise ValueError("research evidence is insufficient for validation")
    elif target is KnowledgeTier.CERTIFIED:
        if not can_promote_to_certified(item):
            raise ValueError("validated evidence is insufficient for certification")
    else:
        raise ValueError("knowledge demotion or invalid promotion is forbidden")

    return KnowledgeItem(
        knowledge_id=item.knowledge_id,
        version=item.version,
        tier=target,
        parent_version=item.parent_version,
        evidence=item.evidence,
        owner_certification_approved=item.owner_certification_approved,
    )
