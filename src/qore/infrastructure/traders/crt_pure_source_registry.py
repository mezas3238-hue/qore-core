"""Source-evidence registry primitives for CRT PURE.

No concept in this module is an executable trading rule.  The registry exists to force
source provenance and adjudication before a concept can be promoted into Strategy
Identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.traders.crt_pure_identity import (
    CrtPureAdjudicationState,
    CrtPureSourceTier,
)


class CrtPureConceptId(StrEnum):
    REFERENCE_RANGE = "reference_range"
    CRH_CRL = "crh_crl"
    EQUILIBRIUM = "equilibrium"
    LIQUIDATION_SWEEP = "liquidation_sweep"
    ONE_VS_TWO_SIDED_SWEEP = "one_vs_two_sided_sweep"
    RECLAIM_CLOSE_BACK_INSIDE = "reclaim_close_back_inside"
    ACCEPTANCE_OUTSIDE_RANGE = "acceptance_outside_range"
    CANDLE_1_2_3 = "candle_1_2_3"
    KISS_OF_DEATH = "kiss_of_death"
    JOURNEY = "journey"
    KEY_LEVELS = "key_levels"
    INVALIDATION = "invalidation"
    OPPORTUNITY_EXPIRY = "opportunity_expiry"
    NESTED_CRT = "nested_crt"
    TIMEFRAME_HIERARCHY = "timeframe_hierarchy"
    SESSION_TIME_RULES = "session_time_rules"
    ENTRY_FAMILIES = "entry_families"
    STRUCTURAL_STOP = "structural_stop"
    STRUCTURAL_DESTINATION = "structural_destination"
    CONTINUATION_REVERSAL = "continuation_reversal"
    FAILURE_CONDITIONS = "failure_conditions"
    REARM_IDENTITY = "rearm_identity"
    SAME_BAR_AMBIGUITY = "same_bar_ambiguity"
    BTCUSD_CONTINUOUS_MARKET = "btcusd_continuous_market"


@dataclass(frozen=True, slots=True)
class CrtPureSourceEvidence:
    """One source-bound piece of evidence for a CRT concept."""

    concept_id: CrtPureConceptId
    source_name: str
    source_tier: CrtPureSourceTier
    provenance: str
    locator: str
    normalized_statement: str
    adjudication: CrtPureAdjudicationState
    content_sha256: str | None = None
    ambiguity_notes: str = ""
    contradiction_notes: str = ""

    def __post_init__(self) -> None:
        for field_name, value in (
            ("source_name", self.source_name),
            ("provenance", self.provenance),
            ("locator", self.locator),
            ("normalized_statement", self.normalized_statement),
        ):
            if not value.strip():
                raise ValueError(f"{field_name} must be non-empty")
        if self.content_sha256 is not None:
            digest = self.content_sha256.lower()
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError("content_sha256 must be a 64-character hex digest")
        if (
            self.adjudication is CrtPureAdjudicationState.CANONICAL
            and self.source_tier is CrtPureSourceTier.LEVEL_B
        ):
            raise ValueError("LEVEL_B evidence cannot independently be CANONICAL")


@dataclass(frozen=True, slots=True)
class CrtPureConceptRecord:
    """Evidence collected for one CRT concept."""

    concept_id: CrtPureConceptId
    evidence: tuple[CrtPureSourceEvidence, ...] = ()

    @property
    def promotable_to_strategy_identity(self) -> bool:
        canonical = tuple(
            item
            for item in self.evidence
            if item.adjudication is CrtPureAdjudicationState.CANONICAL
            and item.source_tier in {
                CrtPureSourceTier.LEVEL_A,
                CrtPureSourceTier.LEVEL_A_PLUS,
            }
        )
        unresolved = any(
            item.adjudication is CrtPureAdjudicationState.AMBIGUOUS
            for item in self.evidence
        )
        contradicted = any(bool(item.contradiction_notes.strip()) for item in canonical)
        return bool(canonical) and not unresolved and not contradicted


CRT_PURE_REQUIRED_CONCEPTS: tuple[CrtPureConceptId, ...] = tuple(CrtPureConceptId)


CRT_PURE_SOURCE_REGISTRY: tuple[CrtPureConceptRecord, ...] = tuple(
    CrtPureConceptRecord(concept_id=concept_id)
    for concept_id in CRT_PURE_REQUIRED_CONCEPTS
)


def pending_concepts() -> tuple[CrtPureConceptId, ...]:
    """Return concepts that are not yet source-promotable."""

    return tuple(
        record.concept_id
        for record in CRT_PURE_SOURCE_REGISTRY
        if not record.promotable_to_strategy_identity
    )
